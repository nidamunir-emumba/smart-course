"""Enrollment endpoints. STUB.

`POST /` should start the Temporal EnrollmentWorkflow (record -> init progress ->
analytics -> notify) with an idempotency key so duplicate submits are safe.
See app/workflows/enrollment.py.
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def enroll():
    raise NotImplementedError
