"""Student-side enrollment management: unenroll (cancel) and archive/unarchive."""
from app.models.enums import UserRole
from tests.factories import make_course, make_user


async def _register(client, email):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "T", "role": "student", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client, email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _enrolled(client, session, email, *, limit=None):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, enrollment_limit=limit)
    await _register(client, email)
    headers = await _login(client, email)
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return course, resp.json()["id"], headers


async def test_unenroll_cancels_and_frees_seat(client, session):
    course, enrollment_id, headers = await _enrolled(
        client, session, "u1@example.com", limit=1
    )

    # Seat taken: a second student is turned away.
    await _register(client, "u2@example.com")
    other = await _login(client, "u2@example.com")
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=other
    )
    assert resp.status_code == 409

    # Unenroll → history kept, seat freed.
    resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/unenroll", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=other
    )
    assert resp.status_code == 201


async def test_unenroll_then_reenroll_fresh(client, session):
    course, enrollment_id, headers = await _enrolled(client, session, "u3@example.com")

    await client.post(f"/api/v1/enrollments/{enrollment_id}/progress", json={"completed_assets": 1}, headers=headers)
    await client.post(f"/api/v1/enrollments/{enrollment_id}/unenroll", headers=headers)

    # Re-enroll: a NEW enrollment with fresh progress; the old row remains as history.
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 201
    fresh = resp.json()
    assert fresh["id"] != enrollment_id
    assert fresh["progress"]["completed_assets"] == 0

    mine = (await client.get(f"/api/v1/enrollments/student/{fresh['student_id']}", headers=headers)).json()
    assert sorted(e["status"] for e in mine) == ["active", "cancelled"]


async def test_completed_course_cannot_unenroll(client, session):
    _, enrollment_id, headers = await _enrolled(client, session, "u4@example.com")
    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress", json={"completed_assets": 2}, headers=headers
    )
    assert resp.json()["status"] == "completed"

    resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/unenroll", headers=headers)
    assert resp.status_code == 409
    assert "certificate" in resp.json()["detail"].lower()


async def test_archive_and_unarchive(client, session):
    _, enrollment_id, headers = await _enrolled(client, session, "u5@example.com")

    resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/archive", headers=headers)
    assert resp.status_code == 200
    archived_at = resp.json()["archived_at"]
    assert archived_at is not None
    # Status and progress untouched.
    assert resp.json()["status"] == "active"

    # Idempotent: archiving again keeps the original timestamp.
    resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/archive", headers=headers)
    assert resp.json()["archived_at"] == archived_at

    resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/unarchive", headers=headers)
    assert resp.json()["archived_at"] is None


async def test_only_owner_may_manage(client, session):
    _, enrollment_id, _ = await _enrolled(client, session, "u6@example.com")
    await _register(client, "intruder2@example.com")
    intruder = await _login(client, "intruder2@example.com")

    for action in ("unenroll", "archive", "unarchive"):
        resp = await client.post(f"/api/v1/enrollments/{enrollment_id}/{action}", headers=intruder)
        assert resp.status_code == 403, action
