"""Domain enumerations, backed by native PostgreSQL enum types.

Uses the `(str, Enum)` idiom (Python 3.10-compatible) so members compare equal to
their string value. `pg_enum` persists the lowercase *value* (e.g. "active"), not the
member name, which keeps DB values conventional and matches SQL predicates.
"""
from enum import Enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class CourseStatus(str, Enum):
    DRAFT = "draft"            # created, editable, not visible to students
    PUBLISHING = "publishing"  # publish workflow in progress
    READY = "ready"            # processing complete, available to students
    ARCHIVED = "archived"


class AssetType(str, Enum):
    TEXT = "text"
    VIDEO = "video"
    PDF = "pdf"
    LINK = "link"


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """SQLAlchemy Enum column that stores the member value (not name)."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
