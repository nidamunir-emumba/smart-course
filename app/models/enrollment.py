"""Enrollment model — links a student to a course, with retained history.

Duplicate-enrollment rule (FR-1.3): a student may hold at most ONE *active* enrollment
per course, but cancelled/completed rows are kept for history. Enforced by a partial
unique index (active only), so re-enrollment after cancellation is still allowed.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import EnrollmentStatus, pg_enum

if TYPE_CHECKING:
    from app.models.certificate import Certificate
    from app.models.course import Course
    from app.models.lesson_completion import LessonCompletion
    from app.models.progress import Progress
    from app.models.user import User


class Enrollment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        # At most one ACTIVE enrollment per (student, course); history rows exempt.
        Index(
            "uq_active_enrollment",
            "student_id",
            "course_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        pg_enum(EnrollmentStatus, "enrollment_status"),
        default=EnrollmentStatus.ACTIVE,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    student: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")
    progress: Mapped["Progress | None"] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan", uselist=False
    )
    certificate: Mapped["Certificate | None"] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan", uselist=False
    )
    completions: Mapped[list["LessonCompletion"]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )

    @property
    def completed_asset_ids(self) -> list[uuid.UUID]:
        """Asset ids this student has finished (requires completions loaded)."""
        return [c.asset_id for c in self.completions]
