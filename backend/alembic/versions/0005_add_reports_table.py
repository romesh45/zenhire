"""add reports table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("interview_score", sa.Float(), nullable=False),
        sa.Column("resume_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("borderline", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("floor_override", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hallucination_penalty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bluff_carry", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("full_report", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_reports_session_id"),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_session_id", table_name="reports")
    op.drop_table("reports")
