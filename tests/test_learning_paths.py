"""Learning paths: transitive prerequisite resolution + friendly enroll errors."""
from app.models.enums import UserRole
from app.services import courses as course_service
from app.services import enrollments as enrollment_service
from app.schemas.enrollment import EnrollmentCreate
from tests.factories import make_course, make_user


async def _register(client, email, name="T"):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": name, "role": "student", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client, email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _chain(session):
    """A → B → C (each the prerequisite of the next)."""
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    a = await make_course(session, instructor.id)
    b = await make_course(session, instructor.id, prerequisite_ids=[a.id])
    c = await make_course(session, instructor.id, prerequisite_ids=[b.id])
    return a, b, c


async def test_enroll_error_names_courses_not_uuids(client, session):
    _, b, _ = await _chain(session)
    await _register(client, "path1@example.com")
    headers = await _login(client, "path1@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(b.id)}, headers=headers
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "Intro Course" in detail  # the human title…
    assert str(b.id) not in detail  # …and no raw UUIDs


async def test_path_resolves_transitively_in_order(client, session):
    a, b, c = await _chain(session)
    await _register(client, "path2@example.com")
    headers = await _login(client, "path2@example.com")

    resp = await client.get(f"/api/v1/courses/{c.id}/path", headers=headers)
    assert resp.status_code == 200, resp.text
    steps = resp.json()
    # C requires B requires A → the full chain, foundations first, target last.
    assert [s["course_id"] for s in steps] == [str(a.id), str(b.id), str(c.id)]
    assert [s["is_target"] for s in steps] == [False, False, True]
    assert all(s["met"] is False for s in steps)


async def test_path_annotates_student_progress(client, session):
    a, b, c = await _chain(session)
    user = await _register(client, "path3@example.com")
    headers = await _login(client, "path3@example.com")

    # Complete A, get halfway through B (each course has 2 lessons).
    import uuid as _uuid

    student_id = _uuid.UUID(user["id"])
    ea = await enrollment_service.enroll(session, EnrollmentCreate(course_id=a.id), student_id)
    await enrollment_service.set_progress(session, ea.id, 2)
    eb = await enrollment_service.enroll(session, EnrollmentCreate(course_id=b.id), student_id)
    await enrollment_service.set_progress(session, eb.id, 1)

    resp = await client.get(f"/api/v1/courses/{c.id}/path", headers=headers)
    steps = {s["course_id"]: s for s in resp.json()}
    assert steps[str(a.id)]["met"] is True
    assert steps[str(a.id)]["enrollment_status"] == "completed"
    assert steps[str(b.id)]["met"] is False
    assert steps[str(b.id)]["enrollment_status"] == "active"
    assert steps[str(b.id)]["percent_complete"] == 50.0
    assert steps[str(c.id)]["enrollment_status"] is None


async def test_path_for_course_without_prereqs_is_just_itself(client, session):
    a, _, _ = await _chain(session)
    await _register(client, "path4@example.com")
    headers = await _login(client, "path4@example.com")

    resp = await client.get(f"/api/v1/courses/{a.id}/path", headers=headers)
    steps = resp.json()
    assert len(steps) == 1 and steps[0]["is_target"] is True


async def test_shared_prerequisite_appears_once(session):
    """Diamond: D requires B and C, both require A → A listed once, first."""
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    a = await make_course(session, instructor.id)
    b = await make_course(session, instructor.id, prerequisite_ids=[a.id])
    c = await make_course(session, instructor.id, prerequisite_ids=[a.id])
    d = await make_course(session, instructor.id, prerequisite_ids=[b.id, c.id])

    path = await course_service.learning_path(session, d.id)
    ids = [course.id for course in path]
    assert ids.count(a.id) == 1
    assert ids[0] == a.id and ids[-1] == d.id
    assert len(ids) == 4
