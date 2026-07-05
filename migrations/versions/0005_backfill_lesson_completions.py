"""backfill lesson_completions from pre-existing progress counters

Revision ID: 0005_backfill_completions
Revises: 0004_lesson_completions
Create Date: 2026-07-05

Enrollments that recorded progress before per-lesson tracking have a counter
but no completion rows, so the outline shows every lesson unchecked (and a
completed course shows 1/1 with an empty check). Materialize the counter the
same way set_progress does: the first N lessons in course order.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_backfill_completions"
down_revision: str | None = "0004_lesson_completions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    gaps = bind.execute(
        sa.text(
            """
            SELECT e.id AS enrollment_id, e.course_id, p.completed_assets
            FROM enrollments e
            JOIN progress p ON p.enrollment_id = e.id
            WHERE p.completed_assets > 0
              AND NOT EXISTS (
                SELECT 1 FROM lesson_completions lc WHERE lc.enrollment_id = e.id
              )
            """
        )
    ).fetchall()

    for gap in gaps:
        assets = bind.execute(
            sa.text(
                """
                SELECT a.id
                FROM assets a
                JOIN modules m ON a.module_id = m.id
                WHERE m.course_id = :course_id
                ORDER BY m.order_index, a.order_index
                LIMIT :n
                """
            ),
            {"course_id": gap.course_id, "n": gap.completed_assets},
        ).fetchall()
        for asset in assets:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO lesson_completions (id, enrollment_id, asset_id)
                    VALUES (:id, :enrollment_id, :asset_id)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "enrollment_id": gap.enrollment_id,
                    "asset_id": asset.id,
                },
            )


def downgrade() -> None:
    # Rows created here are indistinguishable from organic ones; leave them.
    pass
