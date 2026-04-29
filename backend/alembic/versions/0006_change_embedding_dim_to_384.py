"""change_embedding_dim_to_384

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-29

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "resumes",
        "skill_vector",
        type_=Vector(384),
        existing_nullable=True,
        postgresql_using="NULL::vector(384)",
    )


def downgrade() -> None:
    op.alter_column(
        "resumes",
        "skill_vector",
        type_=Vector(1536),
        existing_nullable=True,
        postgresql_using="NULL::vector(1536)",
    )
