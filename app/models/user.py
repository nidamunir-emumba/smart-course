"""User model — students, instructors, admins share one table, distinguished by role."""
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import UserRole, pg_enum

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.enrollment import Enrollment


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable: pre-auth rows have no password and simply can't log in.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"), nullable=False, default=UserRole.STUDENT
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Courses this user teaches (instructor). Enrollments they hold (student).
    taught_courses: Mapped[list["Course"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
