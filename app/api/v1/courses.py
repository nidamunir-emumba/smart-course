"""Course/module/asset management + publishing. STUB.

`POST /{id}/publish` should start the Temporal ContentPublishingWorkflow (durable,
multi-step: extract -> chunk -> embed -> index -> mark ready) rather than doing the
work inline. See app/workflows/publishing.py.
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_course():
    raise NotImplementedError


@router.post("/{course_id}/publish")
async def publish_course(course_id: str):
    """Kick off the durable publishing workflow; returns immediately."""
    raise NotImplementedError
