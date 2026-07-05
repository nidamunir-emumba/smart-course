"""Adding a lesson (unpublish → add → republish): completed enrollments freeze,
active enrollments recompute + get notified."""
import uuid

from app.models.enums import AssetType, UserRole
from app.schemas.course import AssetCreate
from app.schemas.enrollment import EnrollmentCreate
from app.services import courses as course_service
from app.services import enrollments as enrollment_service
from app.services import notifications as notification_service
from tests.factories import make_course, make_user


async def _add_lesson_and_republish(session, course, instructor):
    """The real instructor flow: content edits require draft."""
    await course_service.unpublish_course(session, course.id, instructor)
    module_id = course.modules[0].id
    await course_service.add_asset(
        session,
        course.id,
        module_id,
        AssetCreate(title="Bonus lesson", type=AssetType.TEXT, content="new", order_index=99),
        instructor,
    )
    return await course_service.publish_course(session, course.id, instructor)


async def test_completed_enrollment_freezes_certificate(session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)
    student = await make_user(session, UserRole.STUDENT)

    e = await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), student.id
    )
    completed = await enrollment_service.set_progress(session, e.id, 2)  # 2/2 → COMPLETED
    assert completed.status.value == "completed"
    cert_serial = completed.certificate.serial

    await _add_lesson_and_republish(session, course, instructor)

    after = await enrollment_service.get_enrollment(session, e.id)
    # Certificate earned = frozen: still completed, still 100%, same certificate.
    assert after.status.value == "completed"
    assert after.progress.percent_complete == 100.0
    assert after.progress.total_assets == 2  # denominator NOT bumped
    assert after.certificate.serial == cert_serial

    # A soft FYI notification, no email involved.
    notes = await notification_service.list_for_user(session, student.id)
    kinds = [n.kind for n in notes]
    assert "course_update" in kinds


async def test_active_enrollment_recomputes_and_notifies(session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)
    student = await make_user(session, UserRole.STUDENT)

    e = await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), student.id
    )
    # Complete one of two → 50%, still ACTIVE.
    asset0 = course.modules[0].assets[0].id
    await enrollment_service.complete_lesson(session, e.id, asset0)
    mid = await enrollment_service.get_enrollment(session, e.id)
    assert mid.progress.percent_complete == 50.0

    await _add_lesson_and_republish(session, course, instructor)

    after = await enrollment_service.get_enrollment(session, e.id)
    # Denominator followed the course: 1 of 3 now = 33%, still active, still 1 done.
    assert after.status.value == "active"
    assert after.progress.total_assets == 3
    assert after.progress.completed_assets == 1
    assert round(after.progress.percent_complete, 1) == 33.3

    notes = await notification_service.list_for_user(session, student.id)
    assert any(n.kind == "course_update" for n in notes)


async def test_no_lesson_added_no_notification(session):
    """Republishing after a title-only edit (same count) notifies nobody."""
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)
    student = await make_user(session, UserRole.STUDENT)
    e = await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), student.id
    )
    await enrollment_service.complete_lesson(
        session, e.id, course.modules[0].assets[0].id
    )

    # Unpublish and republish with no content change.
    await course_service.unpublish_course(session, course.id, instructor)
    await course_service.publish_course(session, course.id, instructor)

    notes = await notification_service.list_for_user(session, student.id)
    assert not any(n.kind == "course_update" for n in notes)


async def test_cancelled_enrollment_untouched(session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)
    student = await make_user(session, UserRole.STUDENT)
    e = await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), student.id
    )
    await enrollment_service.unenroll(session, e.id)

    await _add_lesson_and_republish(session, course, instructor)

    notes = await notification_service.list_for_user(session, student.id)
    assert not any(n.kind == "course_update" for n in notes)
