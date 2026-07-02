"""SQLAlchemy ORM models (PostgreSQL source of truth).

All models are imported here so `Base.metadata` is fully populated for Alembic
autogenerate (see migrations/env.py) and for `Base.metadata.create_all` in tests.

Core entities: User, Course, Module, Asset, Enrollment, Progress, Certificate.
"""
from app.models.certificate import Certificate
from app.models.course import Asset, Course, Module, course_prerequisites
from app.models.enrollment import Enrollment
from app.models.progress import Progress
from app.models.user import User

__all__ = [
    "User",
    "Course",
    "Module",
    "Asset",
    "course_prerequisites",
    "Enrollment",
    "Progress",
    "Certificate",
]
