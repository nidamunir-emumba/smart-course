"""Certificate model — issued once an enrollment is completed (one per enrollment)."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment


class Certificate(UUIDMixin, Base):
    __tablename__ = "certificates"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    serial: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    enrollment: Mapped["Enrollment"] = relationship(back_populates="certificate")
