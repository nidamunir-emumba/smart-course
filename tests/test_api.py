"""API-level tests for the core journey via HTTP (register → course → publish → enroll)."""


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_full_enrollment_journey(client):
    # Instructor + student
    instructor = (await client.post(
        "/api/v1/users",
        json={"email": "prof@example.com", "full_name": "Prof", "role": "instructor"},
    )).json()
    student = (await client.post(
        "/api/v1/users",
        json={"email": "stud@example.com", "full_name": "Stud", "role": "student"},
    )).json()

    # Create a course with one module + one asset
    course_resp = await client.post(
        "/api/v1/courses",
        json={
            "title": "APIs 101",
            "instructor_id": instructor["id"],
            "modules": [
                {"title": "M1", "assets": [{"title": "A1", "type": "text", "content": "hi"}]}
            ],
        },
    )
    assert course_resp.status_code == 201
    course = course_resp.json()
    assert course["status"] == "draft"

    # Publish it
    published = (await client.post(f"/api/v1/courses/{course['id']}/publish")).json()
    assert published["status"] == "ready"

    # Enroll the student
    enr = await client.post(
        "/api/v1/enrollments",
        json={"student_id": student["id"], "course_id": course["id"]},
    )
    assert enr.status_code == 201
    body = enr.json()
    assert body["status"] == "active"
    assert body["progress"]["total_assets"] == 1

    # Duplicate enrollment -> 409
    dup = await client.post(
        "/api/v1/enrollments",
        json={"student_id": student["id"], "course_id": course["id"]},
    )
    assert dup.status_code == 409

    # Complete -> certificate issued
    done = await client.post(
        f"/api/v1/enrollments/{body['id']}/progress", json={"completed_assets": 1}
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["certificate"]["serial"].startswith("CERT-")
