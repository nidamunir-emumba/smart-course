"""initial schema — users, courses, modules, assets, enrollments, progress, certificates

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-03

Hand-authored to mirror app/models. Regenerate anytime with:
    make revision m="..."   (alembic autogenerate against Postgres)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("student", "instructor", "admin", name="user_role")
course_status = sa.Enum("draft", "publishing", "ready", "archived", name="course_status")
asset_type = sa.Enum("text", "video", "pdf", "link", name="asset_type")
enrollment_status = sa.Enum("active", "completed", "cancelled", name="enrollment_status")

_TS = dict(server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("instructor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", course_status, nullable=False),
        sa.Column("enrollment_limit", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_courses_instructor_id", "courses", ["instructor_id"])

    op.create_table(
        "course_prerequisites",
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prerequisite_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "modules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_modules_course_id", "modules", ["course_id"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("module_id", sa.Uuid(), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("type", asset_type, nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("url", sa.String(1024)),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_assets_module_id", "assets", ["module_id"])

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", enrollment_status, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])
    # At most one ACTIVE enrollment per (student, course); history rows exempt.
    op.create_index(
        "uq_active_enrollment",
        "enrollments",
        ["student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "progress",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("enrollment_id", sa.Uuid(), sa.ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_assets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_assets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("percent_complete", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_progress_enrollment_id", "progress", ["enrollment_id"])

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("enrollment_id", sa.Uuid(), sa.ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("serial", sa.String(64), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), **_TS),
    )
    op.create_index("ix_certificates_enrollment_id", "certificates", ["enrollment_id"])
    op.create_index("ix_certificates_serial", "certificates", ["serial"])


def downgrade() -> None:
    op.drop_table("certificates")
    op.drop_table("progress")
    op.drop_index("uq_active_enrollment", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("assets")
    op.drop_table("modules")
    op.drop_table("course_prerequisites")
    op.drop_table("courses")
    op.drop_table("users")
    for enum in (enrollment_status, asset_type, course_status, user_role):
        enum.drop(op.get_bind(), checkfirst=True)
