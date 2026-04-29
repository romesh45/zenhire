"""add resume skill_vector field

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector extension must exist before we can use the vector type
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "resumes",
        sa.Column(
            "skill_vector",
            sa.Text(),  # temporary TEXT placeholder — we alter to vector below
            nullable=True,
        ),
    )
    # Convert the column to the proper vector(1536) type
    op.execute("ALTER TABLE resumes ALTER COLUMN skill_vector TYPE vector(1536) USING NULL")

    # HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX resumes_skill_vector_hnsw "
        "ON resumes USING hnsw (skill_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS resumes_skill_vector_hnsw")
    op.drop_column("resumes", "skill_vector")
