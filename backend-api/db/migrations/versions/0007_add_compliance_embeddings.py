"""add compliance_embeddings table for pgvector RAG

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE IF NOT EXISTS compliance_embeddings (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            content     text NOT NULL,
            embedding   vector(1536),
            source      varchar(255),
            chunk_index integer DEFAULT 0,
            created_at  timestamptz DEFAULT now()
        )
    """)

    # IVFFlat index for fast cosine similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS compliance_embeddings_embedding_idx
        ON compliance_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS compliance_embeddings_embedding_idx")
    op.execute("DROP TABLE IF EXISTS compliance_embeddings")
