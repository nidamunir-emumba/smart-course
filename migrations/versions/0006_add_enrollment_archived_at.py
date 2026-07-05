"""add enrollments.archived_at (student-side shelving)

Revision ID: 0006_enrollment_archived
Revises: 0005_backfill_completions
Create Date: 2026-07-05

Lets a student hide an enrollment from their default dashboard view without
touching status or progress. NULL = not archived.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_enrollment_archived"
down_revision: str | None = "0005_backfill_completions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "enrollments", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("enrollments", "archived_at")
