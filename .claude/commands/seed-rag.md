---
description: Seed pgvector with compliance policy embeddings (RBI guidelines, AML rules, lending policy)
allowed-tools: Bash(docker compose exec:*), Bash(docker compose run:*)
---

## Context

- Embedding service: !`cat agent-service/services/embedding_service.py 2>/dev/null | head -40 || echo "embedding_service.py not found"`
- Seed script: !`cat agent-service/scripts/seed_embeddings.py 2>/dev/null | head -30 || echo "seed script not found"`
- pgvector extension: !`docker compose exec postgres psql -U loan_user -d loan_db -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';" 2>/dev/null || echo "Postgres not running"`

## Your task

Seed the pgvector store with compliance policy documents for the RAG system used by the compliance agent node.

### Steps

1. **Verify pgvector is installed**
   ```
   docker compose exec postgres psql -U loan_user -d loan_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

2. **Check if seed script exists**
   - If `agent-service/scripts/seed_embeddings.py` does not exist, create it with stubs for:
     - Loading RBI guidelines (from `agent-service/data/rbi_guidelines.txt` or placeholder)
     - Loading AML rules
     - Loading internal lending policy
     - Chunking documents (512 tokens, 50 overlap)
     - Calling Anthropic embeddings (or OpenAI-compatible) to embed chunks
     - Upserting into pgvector table `compliance_embeddings(id, content, embedding, source, created_at)`

3. **Create the pgvector table** if it doesn't exist:
   ```sql
   CREATE TABLE IF NOT EXISTS compliance_embeddings (
     id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
     content text NOT NULL,
     embedding vector(1536),
     source varchar(255),
     created_at timestamptz DEFAULT now()
   );
   CREATE INDEX IF NOT EXISTS compliance_embeddings_embedding_idx
     ON compliance_embeddings USING ivfflat (embedding vector_cosine_ops);
   ```

4. **Run the seed script**:
   ```
   docker compose exec agent-service python -m scripts.seed_embeddings
   ```

5. **Verify** by counting rows:
   ```
   docker compose exec postgres psql -U loan_user -d loan_db -c "SELECT source, count(*) FROM compliance_embeddings GROUP BY source;"
   ```

Report the number of chunks embedded per source document.
