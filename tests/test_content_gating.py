"""Lesson bodies are gated behind enrollment: syllabus visible to all, content
only after enrolling (owner/admin excepted)."""
from app.models.enums import UserRole
from app.schemas.enrollment import EnrollmentCreate
from app.services import enrollments as enrollment_service
from tests.factories import make_course, make_user


async def _register(client, email, role="student"):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "T", "role": role, "password": "password123"},
    )
    return resp.json()


async def _login(client, email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_non_enrolled_student_sees_syllabus_not_bodies(client, session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)  # text assets with content "…"
    await _register(client, "browse@example.com")
    headers = await _login(client, "browse@example.com")

    resp = await client.get(f"/api/v1/courses/{course.id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_locked"] is True
    # Structure is present…
    assert body["modules"][0]["title"] == "Module 1"
    assert len(body["modules"][0]["assets"]) == 2
    # …but every text body is withheld.
    for m in body["modules"]:
        for a in m["assets"]:
            if a["type"] == "text":
                assert a["content"] is None
            assert a["title"]  # titles always visible


async def test_enrolled_student_sees_bodies(client, session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    user = await _register(client, "enrolled@example.com")
    headers = await _login(client, "enrolled@example.com")

    import uuid as _uuid

    await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), _uuid.UUID(user["id"])
    )

    resp = await client.get(f"/api/v1/courses/{course.id}", headers=headers)
    body = resp.json()
    assert body["content_locked"] is False
    assert any(
        a["content"] for m in body["modules"] for a in m["assets"] if a["type"] == "text"
    )


async def test_owner_sees_own_bodies_without_enrolling(client, session):
    instructor = await make_user(session, UserRole.INSTRUCTOR, name="Owner")
    course = await make_course(session, instructor.id)
    # Log the owning instructor in.
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": instructor.email, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.get(f"/api/v1/courses/{course.id}", headers=headers)
    body = resp.json()
    assert body["content_locked"] is False
    assert body["modules"][0]["assets"][0]["content"] is not None


async def test_cancelled_enrollment_relocks_content(client, session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    user = await _register(client, "left@example.com")
    headers = await _login(client, "left@example.com")

    import uuid as _uuid

    e = await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=course.id), _uuid.UUID(user["id"])
    )
    await enrollment_service.unenroll(session, e.id)

    resp = await client.get(f"/api/v1/courses/{course.id}", headers=headers)
    assert resp.json()["content_locked"] is True
