"""Per-lesson completion: toggles, derived progress, auto-complete, authz."""
from app.models.enums import UserRole
from tests.factories import make_course, make_user


async def _register(client, email, role="student", name="T"):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": name, "role": role, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client, email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _enrolled_student(client, session, n_assets=3):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=n_assets)
    asset_ids = [str(a.id) for m in course.modules for a in m.assets]
    await _register(client, "lc@example.com")
    headers = await _login(client, "lc@example.com")
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"], asset_ids, headers


async def test_complete_lesson_updates_progress_and_ids(client, session):
    enrollment_id, asset_ids, headers = await _enrolled_student(client, session)

    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[1]}/complete", headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["progress"]["completed_assets"] == 1
    assert body["completed_asset_ids"] == [asset_ids[1]]

    # Completing the same lesson again is a no-op.
    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[1]}/complete", headers=headers
    )
    assert resp.json()["progress"]["completed_assets"] == 1


async def test_uncomplete_lesson(client, session):
    enrollment_id, asset_ids, headers = await _enrolled_student(client, session)

    await client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[0]}/complete", headers=headers
    )
    resp = await client.delete(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[0]}/complete", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["progress"]["completed_assets"] == 0
    assert resp.json()["completed_asset_ids"] == []


async def test_completing_every_lesson_completes_course(client, session):
    enrollment_id, asset_ids, headers = await _enrolled_student(client, session, n_assets=2)

    for aid in asset_ids:
        resp = await client.post(
            f"/api/v1/enrollments/{enrollment_id}/lessons/{aid}/complete", headers=headers
        )
    body = resp.json()
    assert body["status"] == "completed"
    assert body["certificate"] is not None
    assert sorted(body["completed_asset_ids"]) == sorted(asset_ids)

    # Un-completing after the course is completed is rejected (certificate issued).
    resp = await client.delete(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[0]}/complete", headers=headers
    )
    assert resp.status_code == 409


async def test_lesson_must_belong_to_course(client, session):
    enrollment_id, _, headers = await _enrolled_student(client, session)
    other_instructor = await make_user(session, UserRole.INSTRUCTOR)
    other_course = await make_course(session, other_instructor.id)
    foreign_asset = str(other_course.modules[0].assets[0].id)

    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{foreign_asset}/complete", headers=headers
    )
    assert resp.status_code == 404


async def test_only_owner_may_toggle(client, session):
    enrollment_id, asset_ids, _ = await _enrolled_student(client, session)
    await _register(client, "intruder@example.com")
    intruder = await _login(client, "intruder@example.com")

    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/{asset_ids[0]}/complete", headers=intruder
    )
    assert resp.status_code == 403


async def test_bulk_set_progress_materializes_completions(client, session):
    """The count-based endpoint stays consistent: it creates per-lesson rows."""
    enrollment_id, asset_ids, headers = await _enrolled_student(client, session, n_assets=3)

    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        json={"completed_assets": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["progress"]["completed_assets"] == 2
    # First two lessons in course order.
    assert body["completed_asset_ids"] == asset_ids[:2]
