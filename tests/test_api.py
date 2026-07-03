"""API-level tests for the core journey via HTTP.

register (with password) → login → create course → publish → enroll → complete,
plus the authentication/authorization behavior that now guards those endpoints.
"""


async def _register(client, email, role, password="password123", name="T"):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": name, "role": role, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client, email, password="password123"):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_login_and_me(client):
    await _register(client, "ada@example.com", "instructor", name="Ada")
    token = await _login(client, "ada@example.com")

    me = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"
    assert me.json()["role"] == "instructor"


async def test_login_wrong_password_rejected(client):
    await _register(client, "bob@example.com", "student")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_endpoints_require_authentication(client):
    # No Authorization header -> rejected before any business logic runs.
    resp = await client.get("/api/v1/courses")
    assert resp.status_code in (401, 403)


async def test_student_cannot_create_course(client):
    await _register(client, "sam@example.com", "student")
    token = await _login(client, "sam@example.com")
    resp = await client.post(
        "/api/v1/courses", json={"title": "X", "modules": []}, headers=_auth(token)
    )
    assert resp.status_code == 403


async def test_full_enrollment_journey(client):
    await _register(client, "prof@example.com", "instructor", name="Prof")
    await _register(client, "stud@example.com", "student", name="Stud")
    itoken = await _login(client, "prof@example.com")
    stoken = await _login(client, "stud@example.com")

    # Instructor creates a course (instructor_id derived from the token, not the body).
    course_resp = await client.post(
        "/api/v1/courses",
        json={
            "title": "APIs 101",
            "modules": [
                {"title": "M1", "assets": [{"title": "A1", "type": "text", "content": "hi"}]}
            ],
        },
        headers=_auth(itoken),
    )
    assert course_resp.status_code == 201, course_resp.text
    course = course_resp.json()
    assert course["status"] == "draft"

    # Publish it (owner instructor).
    published = await client.post(
        f"/api/v1/courses/{course['id']}/publish", headers=_auth(itoken)
    )
    assert published.status_code == 200
    assert published.json()["status"] == "ready"

    # Student enrolls (student_id derived from the token).
    enr = await client.post(
        "/api/v1/enrollments", json={"course_id": course["id"]}, headers=_auth(stoken)
    )
    assert enr.status_code == 201, enr.text
    body = enr.json()
    assert body["status"] == "active"
    assert body["progress"]["total_assets"] == 1

    # Duplicate enrollment -> 409
    dup = await client.post(
        "/api/v1/enrollments", json={"course_id": course["id"]}, headers=_auth(stoken)
    )
    assert dup.status_code == 409

    # Complete -> certificate issued
    done = await client.post(
        f"/api/v1/enrollments/{body['id']}/progress",
        json={"completed_assets": 1},
        headers=_auth(stoken),
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["certificate"]["serial"].startswith("CERT-")
