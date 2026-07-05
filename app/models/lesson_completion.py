"""Per-lesson completion — one row per (enrollment, asset) a student has finished.

The source of truth for progress: Progress counters are derived from these rows
(recomputed on every change), so the outline can show exactly which lessons are
done rather than just a count.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import UUIDMixin


class LessonCompletion(UUIDMixin, Base):
    __tablename__ = "lesson_completions"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "asset_id", name="uq_lesson_completion"),
    )

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    enrollment: Mapped["Enrollment"] = relationship(back_populates="completions")  # noqa: F821
