"""Course lifecycle transitions, ownership, and role-aware visibility (item 2)."""
import pytest

from app.models.enums import CourseStatus, UserRole
from app.services import courses as csvc
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError
from tests.factories import make_course, make_user


# ---------- service-level: lifecycle transitions ----------
async def test_unpublish_then_archive(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id)  # published -> READY
    assert course.status == CourseStatus.READY

    c = await csvc.unpublish_course(session, course.id, actor=instr)
    assert c.status == CourseStatus.DRAFT

    c = await csvc.archive_course(session, course.id, actor=instr)
    assert c.status == CourseStatus.ARCHIVED


async def test_publish_only_from_draft(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id)  # already READY
    with pytest.raises(ConflictError):
        await csvc.publish_course(session, course.id, actor=instr)


async def test_delete_only_draft(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    ready = await make_course(session, instr.id)  # READY
    with pytest.raises(ConflictError):
        await csvc.delete_course(session, ready.id, actor=instr)

    draft = await make_course(session, instr.id, publish=False)  # DRAFT
    await csvc.delete_course(session, draft.id, actor=instr)
    with pytest.raises(NotFoundError):
        await csvc.get_course(session, draft.id)


async def test_non_owner_cannot_modify(session):
    owner = await make_user(session, UserRole.INSTRUCTOR)
    other = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, owner.id)
    with pytest.raises(ForbiddenError):
        await csvc.unpublish_course(session, course.id, actor=other)


async def test_admin_can_modify_any_course(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    admin = await make_user(session, UserRole.ADMIN)
    course = await make_course(session, instr.id)
    c = await csvc.archive_course(session, course.id, actor=admin)
    assert c.status == CourseStatus.ARCHIVED


# ---------- service-level: role-aware listing ----------
async def test_list_visibility_by_role(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    student = await make_user(session, UserRole.STUDENT)
    ready = await make_course(session, instr.id)  # READY
    draft = await make_course(session, instr.id, publish=False)  # DRAFT

    student_ids = {c.id for c in await csvc.list_courses(session, viewer=student)}
    assert ready.id in student_ids and draft.id not in student_ids

    instr_ids = {c.id for c in await csvc.list_courses(session, viewer=instr)}
    assert ready.id in instr_ids and draft.id in instr_ids


async def test_list_pagination(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    for _ in range(5):
        await make_course(session, instr.id)
    page = await csvc.list_courses(session, viewer=instr, limit=2, offset=0)
    assert len(page) == 2
    page2 = await csvc.list_courses(session, viewer=instr, limit=2, offset=4)
    assert len(page2) == 1


# ---------- HTTP-level: endpoint wiring ----------
async def _register(client, email, role):
    r = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "T", "role": role, "password": "password123"},
    )
    assert r.status_code == 201, r.text


async def _token(client, email):
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_http_unpublish_hides_from_students(client):
    await _register(client, "i@x.dev", "instructor")
    await _register(client, "s@x.dev", "student")
    ihdr = await _token(client, "i@x.dev")
    shdr = await _token(client, "s@x.dev")

    cid = (await client.post(
        "/api/v1/courses",
        json={"title": "C", "modules": [{"title": "M", "assets": []}]},
        headers=ihdr,
    )).json()["id"]
    await client.post(f"/api/v1/courses/{cid}/publish", headers=ihdr)

    # Student sees it while READY.
    assert cid in {c["id"] for c in (await client.get("/api/v1/courses", headers=shdr)).json()}

    # After unpublish, it's hidden from the student (list + direct get 404).
    await client.post(f"/api/v1/courses/{cid}/unpublish", headers=ihdr)
    assert cid not in {c["id"] for c in (await client.get("/api/v1/courses", headers=shdr)).json()}
    assert (await client.get(f"/api/v1/courses/{cid}", headers=shdr)).status_code == 404


async def test_http_delete_draft(client):
    await _register(client, "i2@x.dev", "instructor")
    ihdr = await _token(client, "i2@x.dev")
    cid = (await client.post(
        "/api/v1/courses", json={"title": "D", "modules": []}, headers=ihdr
    )).json()["id"]

    assert (await client.delete(f"/api/v1/courses/{cid}", headers=ihdr)).status_code == 204
    assert (await client.get(f"/api/v1/courses/{cid}", headers=ihdr)).status_code == 404
