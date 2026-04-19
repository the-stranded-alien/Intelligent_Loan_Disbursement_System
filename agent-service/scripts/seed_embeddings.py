"""
Seed the pgvector compliance_embeddings table with RBI guidelines, AML rules,
and LoanFlow's internal lending policy.

Run once (or re-run idempotently) after `alembic upgrade head`:

    docker compose exec agent-service python -m scripts.seed_embeddings

Requires OPENAI_API_KEY in the environment.

Chunking strategy: split on double-newline paragraph boundaries, then further
split any chunk exceeding MAX_CHARS at the nearest sentence boundary.
"""

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_CHARS = 1500    # soft max characters per chunk (≈ 400 tokens)
OVERLAP_CHARS = 150  # overlap between adjacent chunks to preserve context

SOURCES = [
    ("rbi_guidelines.txt",  "RBI Lending Guidelines"),
    ("aml_rules.txt",       "AML & CFT Rules"),
    ("lending_policy.txt",  "LoanFlow Internal Lending Policy"),
]


# ── Chunking ───────────────────────────────────────────────────────────────────

def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; filter empty paragraphs."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _split_large_paragraph(para: str, max_chars: int) -> list[str]:
    """Break an oversized paragraph at sentence boundaries."""
    if len(para) <= max_chars:
        return [para]
    chunks = []
    sentences = para.replace(". ", ".|").replace("! ", "!|").replace("? ", "?|").split("|")
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence + " "
        else:
            current += sentence + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_document(text: str) -> list[str]:
    """
    Chunk a policy document into segments suitable for embedding.
    Returns a list of text chunks with light overlap between consecutive chunks.
    """
    paragraphs = _split_paragraphs(text)
    raw_chunks: list[str] = []
    for para in paragraphs:
        raw_chunks.extend(_split_large_paragraph(para, MAX_CHARS))

    # Add overlap: prepend the tail of the previous chunk to the current one
    final_chunks: list[str] = []
    for i, chunk in enumerate(raw_chunks):
        if i > 0 and OVERLAP_CHARS > 0:
            tail = raw_chunks[i - 1][-OVERLAP_CHARS:]
            chunk = tail + " " + chunk
        final_chunks.append(chunk)

    return final_chunks


# ── DB helpers ─────────────────────────────────────────────────────────────────

def clear_source(conn, source_name: str) -> int:
    """Delete existing chunks for this source so re-seeding is idempotent."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM compliance_embeddings WHERE source = %s", (source_name,))
        deleted = cur.rowcount
    conn.commit()
    return deleted


def insert_chunk(conn, content: str, source: str, chunk_index: int, embedding: list[float]) -> None:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO compliance_embeddings (content, embedding, source, chunk_index)
            VALUES (%s, %s::vector, %s, %s)
            """,
            (content, embedding_str, source, chunk_index),
        )
    conn.commit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    # Validate environment
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        logger.error("OPENAI_API_KEY is not set. Cannot generate embeddings.")
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed. Run: pip install psycopg[binary]")
        sys.exit(1)

    from config.settings import settings

    openai_client = OpenAI(api_key=openai_key)
    conn = psycopg.connect(settings.database_url)

    total_chunks = 0

    for filename, source_name in SOURCES:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            logger.warning("Data file not found: %s — skipping", filepath)
            continue

        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_document(text)

        deleted = clear_source(conn, source_name)
        if deleted:
            logger.info("Cleared %d existing chunks for '%s'", deleted, source_name)

        logger.info("Embedding %d chunks for '%s' ...", len(chunks), source_name)

        for idx, chunk in enumerate(chunks):
            try:
                response = openai_client.embeddings.create(
                    model=settings.embedding_model,
                    input=chunk,
                    dimensions=settings.embedding_dimensions,
                )
                embedding = response.data[0].embedding
                insert_chunk(conn, chunk, source_name, idx, embedding)

                if (idx + 1) % 10 == 0:
                    logger.info("  ... %d/%d chunks embedded", idx + 1, len(chunks))

            except Exception as e:
                logger.error("Failed to embed chunk %d of '%s': %s", idx, source_name, e)
                raise

        logger.info("Seeded %d chunks for '%s'", len(chunks), source_name)
        total_chunks += len(chunks)

    conn.close()

    logger.info("Done. Total chunks seeded: %d", total_chunks)

    # Verification query
    verify_conn = psycopg.connect(settings.database_url)
    try:
        with verify_conn.cursor() as cur:
            cur.execute("SELECT source, count(*) FROM compliance_embeddings GROUP BY source ORDER BY source")
            rows = cur.fetchall()
        logger.info("Verification:")
        for source, count in rows:
            logger.info("  %-45s %d chunks", source, count)
    finally:
        verify_conn.close()


if __name__ == "__main__":
    main()
