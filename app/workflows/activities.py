"""Activities for the EnrollmentWorkflow — each one idempotent, so Temporal
can retry any step after a crash without double-processing.

Activities run in the worker process: each opens its own DB session and may
freely import the app. (The workflow definition itself must stay import-clean
for Temporal's sandbox — it calls these by name.)
"""
import uuid

from sqlalchemy import select
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.db.postgres import SessionLocal
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.models.notification import Notification
from app.schemas.enrollment import EnrollmentCreate
from app.services import analytics as analytics_service
from app.services import courses as course_service
from app.services import enrollments as enrollment_service
from app.services import notifications as notification_service
from app.services import users as user_service
from app.services.exceptions import DomainError, DuplicateEnrollmentError
from app.tasks import dispatch
from app.tasks.notifications import send_course_welcome


@activity.defn
async def record_enrollment(student_id: str, course_id: str) -> str:
    """Insert the enrollment + its progress row (one ACID transaction).

    Idempotent: a retry that lost the race to itself hits the partial-unique
    index, and we return the existing active enrollment instead. Business-rule
    violations are non-retryable — retrying won't make a full course emptier.
    """
    async with SessionLocal() as session:
        try:
            enrollment = await enrollment_service.enroll(
                session, EnrollmentCreate(course_id=uuid.UUID(course_id)), uuid.UUID(student_id)
            )
            return str(enrollment.id)
        except DuplicateEnrollmentError:
            # Already recorded (an earlier attempt of this very workflow, or a
            # concurrent duplicate submit) — converge on the existing row.
            result = await session.execute(
                select(Enrollment).where(
                    Enrollment.student_id == uuid.UUID(student_id),
                    Enrollment.course_id == uuid.UUID(course_id),
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:  # cancelled in between — genuinely conflicting
                raise ApplicationError("Enrollment conflict", non_retryable=True) from None
            return str(existing.id)
        except DomainError as exc:
            raise ApplicationError(
                exc.message, type=type(exc).__name__, non_retryable=True
            ) from exc


@activity.defn
async def update_analytics(enrollment_id: str, course_id: str) -> None:
    """Bump course + platform enrollment counters in Mongo.

    Idempotent via the analytics_applied dedupe collection (key = enrollment
    id) — a retried or replayed workflow counts each enrollment exactly once.
    """
    await analytics_service.record_enrollment(enrollment_id, course_id)


@activity.defn
async def send_enrollment_notifications(enrollment_id: str) -> None:
    """Welcome the student: in-app feed row + queued email.

    Idempotent for the feed row (skip if this enrollment's notification
    already exists). The email is at-least-once by design — a crash between
    queueing and acknowledging may re-send one welcome email, which is the
    acceptable side of that trade.
    """
    async with SessionLocal() as session:
        enrollment = await enrollment_service.get_enrollment(
            session, uuid.UUID(enrollment_id)
        )
        student = await user_service.get_user(session, enrollment.student_id)
        course = await course_service.get_course(session, enrollment.course_id)

        link = f"/courses/{course.id}"
        already = await session.execute(
            select(Notification.id).where(
                Notification.user_id == student.id,
                Notification.kind == "enrollment",
                Notification.link == link,
            )
        )
        if already.scalar_one_or_none() is None:
            await notification_service.create(
                session,
                student.id,
                kind="enrollment",
                title=f"You're enrolled: {course.title}",
                body=(
                    "Work through the modules at your own pace — finishing every "
                    "lesson earns your certificate."
                ),
                link=link,
            )

        dispatch.fire(send_course_welcome, student.email, student.full_name, course.title)


ENROLLMENT_ACTIVITIES = [record_enrollment, update_analytics, send_enrollment_notifications]
