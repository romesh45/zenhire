"""add evaluations table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.String(10), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("followup_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("technical_accuracy", sa.Float(), nullable=True),
        sa.Column("depth_of_explanation", sa.Float(), nullable=True),
        sa.Column("problem_solving", sa.Float(), nullable=True),
        sa.Column("communication_clarity", sa.Float(), nullable=True),
        sa.Column("relevance", sa.Float(), nullable=True),
        sa.Column("reasoning_quality", sa.Float(), nullable=True),
        sa.Column("hallucination_flags", JSONB(), nullable=True),
        sa.Column("audit_trace", sa.Text(), nullable=True),
        sa.Column("recruiter_summary", sa.Text(), nullable=True),
        sa.Column("eval_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluations_session_id", "evaluations", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluations_session_id", table_name="evaluations")
    op.drop_table("evaluations")
