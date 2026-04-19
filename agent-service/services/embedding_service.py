"""
Embedding service — wraps OpenAI text-embedding-3-small for pgvector RAG.

Stores and retrieves compliance policy chunks from the compliance_embeddings
table. Used by the compliance agent node to look up relevant policy text at
inference time.
"""

import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_openai_client():
    """Lazy-load OpenAI client to avoid import errors if openai is not installed."""
    try:
        from openai import OpenAI
        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        return OpenAI(api_key=api_key)
    except ImportError:
        raise RuntimeError("openai package not installed — run: pip install openai")


def _get_db_connection():
    """Return a raw psycopg connection for pgvector queries."""
    import psycopg
    return psycopg.connect(settings.database_url)


class EmbeddingService:
    """Generates and stores embeddings in pgvector for RAG queries."""

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text using OpenAI."""
        client = _get_openai_client()
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
        return response.data[0].embedding

    def similarity_search(self, query: str, k: int = 5) -> list[dict]:
        """
        Find the top-k most similar compliance policy chunks for a given query.
        Returns list of {content, source, similarity} dicts.
        """
        query_embedding = self.embed(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, source,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM compliance_embeddings
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding_str, embedding_str, k),
                )
                rows = cur.fetchall()
                return [
                    {"content": r[0], "source": r[1], "similarity": float(r[2])}
                    for r in rows
                ]
        finally:
            conn.close()

    def upsert(self, content: str, source: str, chunk_index: int = 0) -> str:
        """
        Embed text and insert into compliance_embeddings.
        Returns the inserted row id.
        """
        embedding = self.embed(content)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO compliance_embeddings (content, embedding, source, chunk_index)
                    VALUES (%s, %s::vector, %s, %s)
                    RETURNING id
                    """,
                    (content, embedding_str, source, chunk_index),
                )
                row_id = cur.fetchone()[0]
                conn.commit()
                return str(row_id)
        finally:
            conn.close()


embedding_service = EmbeddingService()
