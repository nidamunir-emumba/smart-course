"""Course, Module, Asset models + course prerequisites (self-referential M2M)."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import AssetType, CourseStatus, pg_enum

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.user import User


# A course may require other courses as prerequisites. Association table (course -> prereq).
course_prerequisites = Table(
    "course_prerequisites",
    Base.metadata,
    Column("course_id", Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("prerequisite_id", Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)


class Course(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[CourseStatus] = mapped_column(
        pg_enum(CourseStatus, "course_status"), default=CourseStatus.DRAFT, nullable=False
    )
    # Null = unlimited. Enforced in the enrollment service (FR-1.3).
    enrollment_limit: Mapped[int | None] = mapped_column(Integer)

    instructor: Mapped["User"] = relationship(back_populates="taught_courses")
    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    prerequisites: Mapped[list["Course"]] = relationship(
        secondary=course_prerequisites,
        primaryjoin=lambda: Course.id == course_prerequisites.c.course_id,
        secondaryjoin=lambda: Course.id == course_prerequisites.c.prerequisite_id,
    )

    @property
    def prerequisite_ids(self) -> list[uuid.UUID]:
        """Prerequisite course ids (requires prerequisites loaded) — lets the
        frontend discover learning-path chains from the course list."""
        return [p.id for p in self.prerequisites]


class Module(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "modules"

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="modules")
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Asset.order_index"
    )


class Asset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AssetType] = mapped_column(pg_enum(AssetType, "asset_type"), nullable=False)
    # Inline text (TEXT/markdown) or external URL (VIDEO/PDF/LINK).
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1024))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    module: Mapped["Module"] = relationship(back_populates="assets")
