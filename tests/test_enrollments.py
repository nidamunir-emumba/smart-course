"""Enrollment rule tests (FR-1.3) + progress/completion/certificate (FR-3)."""
import pytest

from app.models.enums import EnrollmentStatus, UserRole
from app.schemas.enrollment import EnrollmentCreate
from app.services import enrollments as svc
from app.services.exceptions import (
    CourseNotPublishedError,
    DuplicateEnrollmentError,
    EnrollmentLimitReachedError,
    PrerequisitesNotMetError,
)
from tests.factories import make_course, make_user


async def test_enroll_success_initializes_progress(session):
    student = await make_user(session, UserRole.STUDENT)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=3)

    enr = await svc.enroll(session, EnrollmentCreate(student_id=student.id, course_id=course.id))

    assert enr.status == EnrollmentStatus.ACTIVE
    assert enr.progress is not None
    assert enr.progress.total_assets == 3
    assert enr.progress.percent_complete == 0.0


async def test_duplicate_active_enrollment_rejected(session):
    student = await make_user(session, UserRole.STUDENT)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)

    payload = EnrollmentCreate(student_id=student.id, course_id=course.id)
    await svc.enroll(session, payload)
    with pytest.raises(DuplicateEnrollmentError):
        await svc.enroll(session, payload)


async def test_enroll_requires_published_course(session):
    student = await make_user(session, UserRole.STUDENT)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, publish=False)  # stays DRAFT

    with pytest.raises(CourseNotPublishedError):
        await svc.enroll(session, EnrollmentCreate(student_id=student.id, course_id=course.id))


async def test_enrollment_limit_enforced(session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, enrollment_limit=1)
    s1 = await make_user(session, UserRole.STUDENT)
    s2 = await make_user(session, UserRole.STUDENT)

    await svc.enroll(session, EnrollmentCreate(student_id=s1.id, course_id=course.id))
    with pytest.raises(EnrollmentLimitReachedError):
        await svc.enroll(session, EnrollmentCreate(student_id=s2.id, course_id=course.id))


async def test_prerequisites_enforced_then_allowed(session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    prereq = await make_course(session, instructor.id, n_assets=1)
    advanced = await make_course(session, instructor.id, prerequisite_ids=[prereq.id])
    student = await make_user(session, UserRole.STUDENT)

    # Unmet prerequisite -> rejected.
    with pytest.raises(PrerequisitesNotMetError):
        await svc.enroll(session, EnrollmentCreate(student_id=student.id, course_id=advanced.id))

    # Complete the prerequisite, then enrollment is allowed.
    pre_enr = await svc.enroll(
        session, EnrollmentCreate(student_id=student.id, course_id=prereq.id)
    )
    await svc.set_progress(session, pre_enr.id, completed_assets=1)  # -> COMPLETED

    enr = await svc.enroll(
        session, EnrollmentCreate(student_id=student.id, course_id=advanced.id)
    )
    assert enr.status == EnrollmentStatus.ACTIVE


async def test_reenroll_after_cancel_keeps_history(session):
    student = await make_user(session, UserRole.STUDENT)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)

    first = await svc.enroll(
        session, EnrollmentCreate(student_id=student.id, course_id=course.id)
    )
    # Cancel the active enrollment.
    first.status = EnrollmentStatus.CANCELLED
    await session.commit()

    # Re-enrollment is allowed and creates a new active row (history retained).
    again = await svc.enroll(
        session, EnrollmentCreate(student_id=student.id, course_id=course.id)
    )
    assert again.id != first.id

    history = await svc.list_for_student(session, student.id)
    assert len(history) == 2


async def test_completion_issues_certificate(session):
    student = await make_user(session, UserRole.STUDENT)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)

    enr = await svc.enroll(session, EnrollmentCreate(student_id=student.id, course_id=course.id))
    completed = await svc.set_progress(session, enr.id, completed_assets=2)

    assert completed.status == EnrollmentStatus.COMPLETED
    assert completed.completed_at is not None
    assert completed.progress.percent_complete == 100.0
    assert completed.certificate is not None
    assert completed.certificate.serial.startswith("CERT-")
