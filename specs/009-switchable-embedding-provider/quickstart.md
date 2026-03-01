# Quickstart: Switchable Embedding Provider

## Switch to GigaChat Embeddings (Production)

### 1. Set environment variables

In your `.env` or docker-compose environment:

```bash
EMBEDDING_PROVIDER=gigachat
EMBEDDING_MODEL=Embeddings
GIGA_AUTH_DATA=<your-base64-credentials>
```

### 2. Restart rag-api

```bash
docker compose -f docker-compose.local.yaml up -d --build rag-api
```

On startup, the service will:
- Detect GigaChat embedding dimension (1024)
- Compare with existing pgvector table dimension (768)
- Drop and recreate table with correct dimension
- Log: "Table recreated with vector_size=1024, reingest required"

### 3. Run reingest

```bash
docker compose -f docker-compose.local.yaml up rag-ingest
```

### 4. (Optional) Skip TEI service

Since GigaChat embeddings are cloud-based, TEI is not needed:

```bash
docker compose -f docker-compose.local.yaml up -d postgres redis content-api rag-api litellm
# Note: no 'tei' in the service list
```

## Switch Back to TEI (Local/Dev)

```bash
EMBEDDING_PROVIDER=tei
# or simply remove EMBEDDING_PROVIDER (defaults to "tei")
```

Restart + reingest as above. TEI service must be running.

## Verify Current Provider

Check logs on startup:
```
INFO: Embedding provider: gigachat (model=Embeddings, dim=1024)
INFO: pgvector table 'portfolio_new' dimension matches (1024)
```

Or via admin API:
```bash
GET /api/v1/admin/stats
# Response includes embedding_provider and vector_dimension
```
