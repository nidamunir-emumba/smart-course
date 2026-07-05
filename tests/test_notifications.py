"""Notification tests.

Two layers:
  - dispatch: the right Celery task is queued (task.delay captured via monkeypatch)
    at the right moments — registration, enrollment, and exactly once on completion.
  - content: tasks render and hand a sensible email to the emailer (run in-process
    by calling the task function body directly).
"""
import pytest

from app.models.enums import UserRole
from app.tasks import dispatch, emailer, notifications
from tests.factories import make_course, make_user


@pytest.fixture
def sent(monkeypatch):
    """Capture task dispatches as (task_name, args) tuples instead of hitting a broker."""
    calls: list[tuple[str, tuple]] = []

    def fake_fire(task, *args):
        calls.append((task.name, args))

    monkeypatch.setattr(dispatch, "fire", fake_fire)
    return calls


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


# ── Dispatch wiring ──────────────────────────────────────────────────────────


async def test_registration_dispatches_welcome(client, sent):
    await _register(client, "new@example.com", "student", name="New Student")

    names = [name for name, _ in sent]
    assert names == [notifications.send_registration_welcome.name]
    _, args = sent[0]
    assert args == ("new@example.com", "New Student", "student")


async def test_enroll_dispatches_course_welcome(client, session, sent):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    await _register(client, "learner@example.com", "student", name="Lea Learner")
    headers = await _login(client, "learner@example.com")
    sent.clear()  # drop the registration dispatch

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    assert resp.status_code == 201, resp.text

    assert [name for name, _ in sent] == [notifications.send_course_welcome.name]
    _, args = sent[0]
    assert args == ("learner@example.com", "Lea Learner", "Intro Course")


async def test_completion_dispatches_congrats_exactly_once(client, session, sent):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id, n_assets=2)
    await _register(client, "fin@example.com", "student", name="Fin Isher")
    headers = await _login(client, "fin@example.com")

    resp = await client.post(
        "/api/v1/enrollments", json={"course_id": str(course.id)}, headers=headers
    )
    enrollment_id = resp.json()["id"]
    sent.clear()

    # Partial progress → no congrats.
    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        json={"completed_assets": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    assert sent == []

    # Reaching 100% → exactly one congrats, carrying the certificate serial.
    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        json={"completed_assets": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    cert_serial = resp.json()["certificate"]["serial"]
    assert [name for name, _ in sent] == [notifications.send_completion_congrats.name]
    _, args = sent[0]
    assert args == ("fin@example.com", "Fin Isher", "Intro Course", cert_serial)

    # Posting 100% again → still just the one congrats.
    resp = await client.post(
        f"/api/v1/enrollments/{enrollment_id}/progress",
        json={"completed_assets": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(sent) == 1


async def test_broker_down_does_not_fail_request(client, monkeypatch):
    """dispatch.fire swallows broker errors — registration still returns 201."""

    def boom(*args, **kwargs):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(notifications.send_registration_welcome, "delay", boom)
    resp = await client.post(
        "/api/v1/users",
        json={
            "email": "offline@example.com",
            "full_name": "Off Line",
            "role": "student",
            "password": "password123",
        },
    )
    assert resp.status_code == 201


# ── Task content ─────────────────────────────────────────────────────────────


@pytest.fixture
def outbox(monkeypatch):
    """Capture emails handed to the emailer by task bodies."""
    box: list[dict] = []
    monkeypatch.setattr(
        notifications,
        "send_email",
        lambda to, subject, body: box.append({"to": to, "subject": subject, "body": body}),
    )
    return box


def test_course_welcome_email_content(outbox):
    notifications.send_course_welcome("s@example.com", "Sam Smith", "Async Python")
    (mail,) = outbox
    assert mail["to"] == "s@example.com"
    assert "Async Python" in mail["subject"]
    assert "Hi Sam" in mail["body"]
    assert "certificate" in mail["body"]


def test_completion_email_includes_serial(outbox):
    notifications.send_completion_congrats(
        "s@example.com", "Sam Smith", "Async Python", "CERT-ABC123"
    )
    (mail,) = outbox
    assert "CERT-ABC123" in mail["body"]
    assert "Async Python" in mail["subject"]


def test_registration_email_speaks_to_role(outbox):
    notifications.send_registration_welcome("i@example.com", "Ida Ins", "instructor")
    notifications.send_registration_welcome("s@example.com", "Stu Dent", "student")
    instructor_mail, student_mail = outbox
    assert "course" in instructor_mail["body"].lower()
    assert "enroll" in student_mail["body"].lower()


def test_console_backend_logs_instead_of_sending(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="app.tasks.emailer"):
        emailer.send_email("t@example.com", "Subject line", "Body text")
    assert any(
        "t@example.com" in r.getMessage() and "Subject line" in r.getMessage()
        for r in caplog.records
    )
