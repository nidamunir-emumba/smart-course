"""Aggregates all v1 routers. Mounted under /api/v1 in app.main."""
from fastapi import APIRouter

from app.api.v1 import assistant, auth, content, courses, enrollments, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(content.router, prefix="/courses", tags=["course-content"])
api_router.include_router(enrollments.router, prefix="/enrollments", tags=["enrollments"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
