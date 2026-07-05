"""In-app notification feed tests: rows created at the right moments, feed is
private to its owner, read state behaves."""
from app.models.enums import UserRole
from tests.factories import make_course, make_user


async def _register(client, email, role, name="T"):
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


async def test_registration_creates_welcome_notification(client):
    await _register(client, "n1@example.com", "student")
    headers = await _login(client, "n1@example.com")

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["kind"] == "welcome"
    assert items[0]["read_at"] is None

    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json() == {"unread": 1}


async def test_enrollment_and_completion_create_notifications(client, session):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=1)
    await _register(client, "n2@example.com", "student")
    headers = await _login(client, "n2@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 201
    enrollment_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        json={"completed_assets": 1},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/api/v1/notifications", headers=headers)
    kinds = [n["kind"] for n in resp.json()]
    # Newest first: completion, enrollment, welcome.
    assert kinds == ["completion", "enrollment", "welcome"]
    completion = resp.json()[0]
    assert completion["link"] == f"/certificate/{enrollment_id}"


async def test_mark_read_and_read_all(client):
    await _register(client, "n3@example.com", "student")
    headers = await _login(client, "n3@example.com")

    (item,) = (await client.get("/api/v1/notifications", headers=headers)).json()

    resp = await client.post(f"/api/v1/notifications/{item['id']}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None

    resp = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert resp.json() == {"unread": 0}

    resp = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert resp.json() == {"unread": 0}


async def test_feed_is_private(client):
    await _register(client, "owner@example.com", "student")
    owner_headers = await _login(client, "owner@example.com")
    (item,) = (await client.get("/api/v1/notifications", headers=owner_headers)).json()

    await _register(client, "other@example.com", "student")
    other_headers = await _login(client, "other@example.com")

    # Another user sees their own feed only, and can't mark foreign rows read.
    resp = await client.get("/api/v1/notifications", headers=other_headers)
    assert [n["kind"] for n in resp.json()] == ["welcome"]
    assert resp.json()[0]["id"] != item["id"]

    resp = await client.post(f"/api/v1/notifications/{item['id']}/read", headers=other_headers)
    assert resp.status_code == 404

    resp = await client.get("/api/v1/notifications", headers=other_headers)
    assert resp.json()[0]["read_at"] is None
