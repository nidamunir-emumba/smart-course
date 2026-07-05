"""Lesson Q&A: grounding, auth, visibility, and graceful degradation."""
import pytest

from app.ai import qa
from app.models.enums import UserRole
from tests.factories import make_course, make_user


class FakeModel:
    """Stands in for the LangChain chat model; records the prompt it got."""

    def __init__(self):
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages

        class R:
            content = "Because FastAPI and SQLAlchemy live in one Python process."

        return R()


@pytest.fixture
def fake_llm(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(qa, "get_chat_model", lambda streaming=False: model)
    return model


async def _register(client, email):
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "T", "role": "student", "password": "password123"},
    )
    assert resp.status_code == 201
    return resp.json()


async def _login(client, email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_qa_grounds_in_the_lesson(client, session, fake_llm):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    asset = course.modules[0].assets[0]
    await _register(client, "qa1@example.com")
    headers = await _login(client, "qa1@example.com")

    resp = await client.post(
        "/api/v1/assistant/qa",
        json={
            "course_id": str(course.id),
            "asset_id": str(asset.id),
            "question": "Why does FastAPI appear twice in the diagram?",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert "one Python process" in resp.json()["answer"]

    # The prompt the model saw is grounded: course title, lesson title, lesson body.
    human = fake_llm.messages[-1][1]
    assert course.title in human
    assert asset.title in human
    assert (asset.content or "") in human
    assert "Why does FastAPI appear twice" in human


async def test_qa_without_lesson_uses_course_outline(client, session, fake_llm):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    await _register(client, "qa2@example.com")
    headers = await _login(client, "qa2@example.com")

    resp = await client.post(
        "/api/v1/assistant/qa",
        json={"course_id": str(course.id), "question": "What does this course cover?"},
        headers=headers,
    )
    assert resp.status_code == 200
    human = fake_llm.messages[-1][1]
    assert "Module 1" in human  # the outline is present…
    assert "currently reading" not in human  # …but no lesson body was attached


async def test_qa_requires_auth_and_valid_lesson(client, session, fake_llm):
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)

    resp = await client.post(
        "/api/v1/assistant/qa",
        json={"course_id": str(course.id), "question": "anonymous?"},
    )
    assert resp.status_code in (401, 403)

    other = await make_course(session, instructor.id)
    foreign_asset = other.modules[0].assets[0]
    await _register(client, "qa3@example.com")
    headers = await _login(client, "qa3@example.com")
    resp = await client.post(
        "/api/v1/assistant/qa",
        json={
            "course_id": str(course.id),
            "asset_id": str(foreign_asset.id),
            "question": "lesson from another course?",
        },
        headers=headers,
    )
    assert resp.status_code == 404


async def test_qa_degrades_gracefully_without_llm(client, session, monkeypatch):
    def broken(streaming=False):
        raise RuntimeError("no api key")

    monkeypatch.setattr(qa, "get_chat_model", broken)
    instructor = await make_user(session, UserRole.INSTRUCTOR)
    course = await make_course(session, instructor.id)
    await _register(client, "qa4@example.com")
    headers = await _login(client, "qa4@example.com")

    resp = await client.post(
        "/api/v1/assistant/qa",
        json={"course_id": str(course.id), "question": "does this fail nicely?"},
        headers=headers,
    )
    assert resp.status_code == 503
    assert "ANTHROPIC_API_KEY" in resp.json()["detail"]
