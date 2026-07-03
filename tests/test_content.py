"""Module & asset CRUD on draft courses (item 2, part B)."""
import uuid

import pytest

from app.models.enums import AssetType, UserRole
from app.schemas.course import AssetCreate, AssetUpdate, ModuleCreate, ModuleUpdate
from app.services import courses as csvc
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError
from tests.factories import make_course, make_user


# ---------- service level ----------
async def test_add_update_delete_module(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id, publish=False, n_assets=0)

    course = await csvc.add_module(
        session, course.id, ModuleCreate(title="New", order_index=1), actor=instr
    )
    mod = next(m for m in course.modules if m.title == "New")

    course = await csvc.update_module(
        session, course.id, mod.id, ModuleUpdate(title="Renamed"), actor=instr
    )
    assert any(m.title == "Renamed" for m in course.modules)

    course = await csvc.delete_module(session, course.id, mod.id, actor=instr)
    assert all(m.id != mod.id for m in course.modules)


async def test_add_update_delete_asset(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id, publish=False, n_assets=1)
    mod = course.modules[0]

    course = await csvc.add_asset(
        session, course.id, mod.id,
        AssetCreate(title="Extra", type=AssetType.TEXT, content="x"), actor=instr,
    )
    assert len(course.modules[0].assets) == 2
    asset = next(a for a in course.modules[0].assets if a.title == "Extra")

    course = await csvc.update_asset(
        session, course.id, mod.id, asset.id, AssetUpdate(title="Edited"), actor=instr
    )
    assert any(a.title == "Edited" for a in course.modules[0].assets)

    course = await csvc.delete_asset(session, course.id, mod.id, asset.id, actor=instr)
    assert all(a.id != asset.id for a in course.modules[0].assets)


async def test_content_edit_requires_draft(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id)  # READY
    with pytest.raises(ConflictError):
        await csvc.add_module(session, course.id, ModuleCreate(title="X"), actor=instr)


async def test_content_edit_requires_owner(session):
    owner = await make_user(session, UserRole.INSTRUCTOR)
    other = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, owner.id, publish=False)
    with pytest.raises(ForbiddenError):
        await csvc.add_module(session, course.id, ModuleCreate(title="X"), actor=other)


async def test_missing_module_raises(session):
    instr = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instr.id, publish=False)
    with pytest.raises(NotFoundError):
        await csvc.update_module(
            session, course.id, uuid.uuid4(), ModuleUpdate(title="X"), actor=instr
        )


# ---------- HTTP level ----------
async def test_http_module_asset_flow(client):
    await client.post(
        "/api/v1/users",
        json={"email": "i@c.dev", "full_name": "I", "role": "instructor", "password": "password123"},
    )
    tok = (await client.post(
        "/api/v1/auth/login", json={"email": "i@c.dev", "password": "password123"}
    )).json()["access_token"]
    hdr = {"Authorization": f"Bearer {tok}"}

    cid = (await client.post(
        "/api/v1/courses", json={"title": "C", "modules": []}, headers=hdr
    )).json()["id"]

    # Add a module, then an asset inside it.
    course = (await client.post(
        f"/api/v1/courses/{cid}/modules", json={"title": "M1"}, headers=hdr
    )).json()
    mid = course["modules"][0]["id"]

    resp = await client.post(
        f"/api/v1/courses/{cid}/modules/{mid}/assets",
        json={"title": "A1", "type": "text", "content": "hi"},
        headers=hdr,
    )
    assert resp.status_code == 201
    assert resp.json()["modules"][0]["assets"][0]["title"] == "A1"

    # Editing content of a published course is rejected (409).
    await client.post(f"/api/v1/courses/{cid}/publish", headers=hdr)
    blocked = await client.post(
        f"/api/v1/courses/{cid}/modules", json={"title": "M2"}, headers=hdr
    )
    assert blocked.status_code == 409
