"""The durable enrollment path: 202 semantics, synchronous validation,
workflow-id idempotency, graceful degradation. The Temporal client is faked
at the endpoint seam; activity/worker behavior is exercised live (see PR)."""
import pytest
from temporalio.exceptions import WorkflowAlreadyStartedError

import app.api.v1.enrollments as enroll_endpoint
from app.core.config import settings
from app.models.enums import UserRole
from app.schemas.enrollment import EnrollmentCreate
from app.services import enrollments as enrollment_service
from tests.factories import make_course, make_user


class FakeTemporalClient:
    def __init__(self, raise_already_started: bool = False):
        self.calls: list[dict] = []
        self.raise_already_started = raise_already_started

    async def start_workflow(self, name, *, args, id, task_queue):
        self.calls.append({"name": name, "args": args, "id": id, "task_queue": task_queue})
        if self.raise_already_started:
            raise WorkflowAlreadyStartedError(id, name)


@pytest.fixture
def durable(monkeypatch):
    """Enable the workflow path with a recording fake client."""
    fake = FakeTemporalClient()
    monkeypatch.setattr(settings, "enrollment_workflow_enabled", True)

    async def fake_get_client():
        return fake

    monkeypatch.setattr(enroll_endpoint, "get_temporal_client", fake_get_client)
    return fake


async def _student(client, email):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "T", "role": "student", "password": "password123"},
    )
    user = resp.json()
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return user, {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_enroll_returns_202_and_starts_workflow(client, session, durable):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    user, headers = await _student(client, "wf1@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 202, resp.text
    expected_id = f"enroll-{user['id']}-{course.id}"
    assert resp.json() == {"status": "accepted", "workflow_id": expected_id}

    assert len(durable.calls) == 1
    call = durable.calls[0]
    assert call["name"] == "EnrollmentWorkflow"
    assert call["args"] == [user["id"], str(course.id)]
    assert call["id"] == expected_id  # deterministic → duplicate submits dedupe


async def test_validation_stays_synchronous(client, session, durable):
    """Business-rule rejections must reach the caller as 4xx BEFORE any
    workflow is queued — a 202 for a doomed enrollment would be a lie."""
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    draft = await make_course(session, instructor.id, publish=False)
    ready = await make_course(session, instructor.id)
    user, headers = await _student(client, "wf2@example.com")

    # Unpublished course → 409, no workflow.
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(draft.id)}, headers=headers
    )
    assert resp.status_code == 409
    assert durable.calls == []

    # Already actively enrolled (row created via the service) → 409, no workflow.
    import uuid as _uuid

    await enrollment_service.enroll(
        session, EnrollmentCreate(course_id=ready.id), _uuid.UUID(user["id"])
    )
    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(ready.id)}, headers=headers
    )
    assert resp.status_code == 409
    assert durable.calls == []


async def test_duplicate_submit_while_processing_is_idempotent(client, session, monkeypatch):
    """A concurrent duplicate hits WorkflowAlreadyStartedError → still 202,
    same workflow id — one enrollment, no matter how many clicks."""
    fake = FakeTemporalClient(raise_already_started=True)
    monkeypatch.setattr(settings, "enrollment_workflow_enabled", True)

    async def fake_get_client():
        return fake

    monkeypatch.setattr(enroll_endpoint, "get_temporal_client", fake_get_client)

    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    _, headers = await _student(client, "wf3@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 202


async def test_temporal_down_degrades_to_503(client, session, monkeypatch):
    monkeypatch.setattr(settings, "enrollment_workflow_enabled", True)

    async def broken_client():
        raise ConnectionError("temporal unreachable")

    monkeypatch.setattr(enroll_endpoint, "get_temporal_client", broken_client)

    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    _, headers = await _student(client, "wf4@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()
