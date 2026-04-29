"""add recruiters, sessions, resumes tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # recruiters
    op.create_table(
        "recruiters",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_recruiters_email", "recruiters", ["email"])

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("created_by_recruiter_id", sa.UUID(), nullable=False),
        sa.Column("candidate_name", sa.String(255), nullable=False),
        sa.Column("candidate_email", sa.String(255), nullable=False),
        sa.Column("candidate_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_recruiter_id"], ["recruiters.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # resumes
    op.create_table(
        "resumes",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("pdf_data", sa.LargeBinary(), nullable=False),
        sa.Column("resume_structured", JSONB(), nullable=True),
        sa.Column("resume_score", sa.Float(), nullable=True),
        sa.Column("skill_gaps", JSONB(), nullable=True),
        sa.Column("job_fit_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # add FK on existing jobs.created_by_recruiter_id
    op.create_foreign_key(
        "fk_jobs_recruiter",
        "jobs",
        "recruiters",
        ["created_by_recruiter_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_recruiter", "jobs", type_="foreignkey")
    op.drop_table("resumes")
    op.drop_table("sessions")
    op.drop_index("ix_recruiters_email", table_name="recruiters")
    op.drop_table("recruiters")
