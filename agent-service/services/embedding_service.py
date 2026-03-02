from config.settings import settings


class EmbeddingService:
    """Generates and stores embeddings in pgvector for RAG queries."""

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        # TODO: Call OpenAI / Anthropic embedding API (text-embedding-3-small)
        pass

    async def similarity_search(self, query: str, k: int = 5) -> list[dict]:
        """Find the top-k most similar documents in the compliance_policies collection."""
        # TODO: Embed query, run pgvector <=> cosine distance query, return docs
        pass

    async def upsert(self, doc_id: str, text: str, metadata: dict):
        """Add or update a document embedding in pgvector."""
        # TODO: Embed text, INSERT/UPDATE in vectors table
        pass


embedding_service = EmbeddingService()
