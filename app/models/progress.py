"""Progress model — one row per enrollment, tracks completion for analytics (FR-6)."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment


class Progress(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "progress"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    total_assets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_assets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    enrollment: Mapped["Enrollment"] = relationship(back_populates="progress")
