"""add lesson_completions (per-lesson progress)

Revision ID: 0004_lesson_completions
Revises: 0003_notifications
Create Date: 2026-07-05

One row per (enrollment, asset) a student has finished; Progress counters are
derived from these rows. Existing enrollments have no rows — their numeric
progress remains until they next touch a lesson.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_lesson_completions"
down_revision: str | None = "0003_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_completions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("enrollment_id", "asset_id", name="uq_lesson_completion"),
    )
    op.create_index("ix_lesson_completions_enrollment_id", "lesson_completions", ["enrollment_id"])
    op.create_index("ix_lesson_completions_asset_id", "lesson_completions", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_completions_asset_id", table_name="lesson_completions")
    op.drop_index("ix_lesson_completions_enrollment_id", table_name="lesson_completions")
    op.drop_table("lesson_completions")
