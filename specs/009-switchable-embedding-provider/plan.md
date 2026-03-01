# Implementation Plan: Switchable Embedding Provider (TEI / GigaChat)

**Branch**: `009-switchable-embedding-provider` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-switchable-embedding-provider/spec.md`

## Summary

Add a switchable embedding provider in rag-api-new controlled by a single `EMBEDDING_PROVIDER` env var (`tei` | `gigachat`). The TEI path remains as-is (default). The GigaChat path uses `GigaChatEmbeddings` from `langchain-gigachat` (already installed). Vector dimension is auto-detected at startup via a test embed call. On dimension mismatch with existing pgvector table, the table is recreated and embedding cache cleared (reingest required via `rag-ingest` service).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, LangChain 1.x, langchain-gigachat 0.3.12, langchain-postgres
**Storage**: PostgreSQL 16 with pgvector extension
**Testing**: pytest (`services/rag-api-new/tests/`)
**Target Platform**: Linux server (Docker), Windows dev
**Project Type**: Web service (microservice)
**Performance Goals**: Embedding latency < 100ms per query (vs ~200ms TEI on CPU)
**Constraints**: Backward compatible — `EMBEDDING_PROVIDER=tei` (default) must not change behavior
**Scale/Scope**: ~200 documents in pgvector, single-user RAG pipeline

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | No new text files with Cyrillic; only Python code changes |
| II. Root-Cause Resolution | PASS | Addresses root cause (CPU-bound TEI on server without GPU) |
| III. Clean Architecture | PASS | Factory pattern in `deps.py`, no new abstractions beyond necessity |
| IV. Service Directory Discipline | PASS | All changes in `services/rag-api-new/` |
| V. API Versioning & Contracts | PASS | No new API endpoints; admin/stats enhancement is additive |
| VI. Database Migration Discipline | N/A | pgvector table managed by langchain-postgres, not Alembic |
| VII. Simplicity & YAGNI | PASS | Single env var switch, reuses existing config, no over-engineering |

**Post-Phase-1 Re-check**: All gates PASS. No violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/009-switchable-embedding-provider/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: data model changes
├── quickstart.md        # Phase 1: usage guide
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files to modify)

```text
services/rag-api-new/
├── app/
│   ├── settings.py          # Add EMBEDDING_PROVIDER field
│   ├── deps.py              # Embedding factory + dimension detection + mismatch handling
│   └── routers/
│       └── admin.py         # Add embedding info to /admin/stats response
└── tests/
    └── test_embedding_provider.py  # New: unit tests for provider switching

infra/
├── .env.dev                 # Add EMBEDDING_PROVIDER=tei
├── .env.local               # Add EMBEDDING_PROVIDER=tei
├── .env.prod                # Add EMBEDDING_PROVIDER=tei (change to gigachat when ready)
├── .env.example             # Add EMBEDDING_PROVIDER=tei with comment
├── docker-compose.local.yaml   # Pass EMBEDDING_PROVIDER to rag-api service
└── docker-compose-prod.yaml    # Pass EMBEDDING_PROVIDER to rag-api service
```

**Structure Decision**: Changes span rag-api-new application code (3 existing + 1 new test file) and infrastructure config (4 env files + 2 compose files). The env → compose → settings chain follows the existing pattern used for all other env vars (e.g., `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE`).

## Implementation Design

### Step 1: Settings (`settings.py`)

Add one new field:

```python
# === Embedding ===
embedding_provider: Literal["tei", "gigachat"] = "tei"
"""Embedding provider: 'tei' (local TEI) or 'gigachat' (cloud GigaChat API)."""
```

No changes to existing `embedding_model`, `tei_base_url`, or `giga_auth_data` fields.

### Step 2: Embedding Factory (`deps.py`)

Replace current `embeddings()` function:

```python
@lru_cache()
def embeddings() -> Embeddings:
    s = settings()
    if s.embedding_provider == "gigachat":
        if not s.giga_auth_data:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gigachat requires GIGA_AUTH_DATA to be set"
            )
        from langchain_gigachat import GigaChatEmbeddings
        logger.info("Embedding provider: gigachat (model=%s)", s.embedding_model)
        return GigaChatEmbeddings(
            credentials=s.giga_auth_data,
            model=s.embedding_model,
            verify_ssl_certs=False,
            timeout=60,
        )
    # Default: TEI
    logger.info("Embedding provider: tei (url=%s)", s.tei_base_url)
    return OpenAIEmbeddings(
        api_key="dummy",
        base_url=str(s.tei_base_url),
        model=s.embedding_model,
    )
```

Return type changes from `OpenAIEmbeddings` to `Embeddings` (LangChain base class).

### Step 3: Dimension Detection + Mismatch Handling (`deps.py`)

Add dimension detection in `pg_engine()`:

```python
def _detect_embedding_dim() -> int:
    """Determine vector dimension by running a test embedding."""
    vec = embeddings().embed_query("test")
    dim = len(vec)
    logger.info("Detected embedding dimension: %d", dim)
    return dim

def _get_table_vector_dim(engine: PGEngine, table_name: str) -> int | None:
    """Query existing pgvector column dimension from pg_attribute catalog."""
    async def _query():
        async with engine._pool.connect() as conn:
            result = await conn.execute(text(
                "SELECT atttypmod - 4 FROM pg_attribute "
                "WHERE attrelid = :tbl::regclass AND attname = 'embedding' "
                "AND atttypmod > 0"
            ), {"tbl": table_name})
            row = result.fetchone()
            return row[0] if row else None
    try:
        return engine._run_as_sync(_query())
    except Exception:
        return None  # Table doesn't exist yet
```

Modified `pg_engine()` flow:
1. Create engine from connection string
2. Detect embedding dimension via test embed
3. Check if table exists and get current dimension
4. If table exists and dimensions mismatch → `init_vectorstore_table(overwrite_existing=True)` + clear embedding cache
5. If table doesn't exist → `init_vectorstore_table(overwrite_existing=False)`
6. Log result

### Step 4: Admin Stats Enhancement (`admin.py`)

Add embedding provider info to existing `/api/v1/admin/stats` response:

```python
# In the stats response, add:
"embedding_provider": settings().embedding_provider,
"embedding_model": settings().embedding_model,
"vector_dimension": _detect_embedding_dim(),  # or cached value
```

### Step 5: Infrastructure Config (env files + docker-compose)

**Env files** — add `EMBEDDING_PROVIDER` next to existing `EMBEDDING_MODEL`:

| File | Value | Notes |
|------|-------|-------|
| `infra/.env.dev` | `EMBEDDING_PROVIDER=tei` | Dev environment (local TEI with GPU) |
| `infra/.env.local` | `EMBEDDING_PROVIDER=tei` | Local environment |
| `infra/.env.prod` | `EMBEDDING_PROVIDER=tei` | Prod (change to `gigachat` when deploying with cloud embeddings) |
| `infra/.env.example` | `EMBEDDING_PROVIDER=tei` | With comment: `# tei (local TEI) or gigachat (cloud GigaChat API)` |

**Switching to GigaChat in prod** — change two vars in `.env.prod`:
```bash
EMBEDDING_PROVIDER=gigachat
EMBEDDING_MODEL=Embeddings          # or Embeddings-2 (GigaChat model name)
# GIGA_AUTH_DATA must also be set (already exists for GigaChat LLM)
```

`EMBEDDING_MODEL` is already present in all env files (currently `embedding-default` for TEI). When provider is `tei`, this value is used only as Redis cache key namespace. When provider is `gigachat`, it is passed as `model=` to `GigaChatEmbeddings`.

**Docker Compose** — pass `EMBEDDING_PROVIDER` to rag-api service environment:

`docker-compose.local.yaml` (rag-api environment section):
```yaml
EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-tei}
```

`docker-compose-prod.yaml` (rag-api environment section):
```yaml
EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-tei}
```

Place next to existing `embedding_model: ${EMBEDDING_MODEL}` line. The `:-tei` fallback ensures backward compatibility if env var not set.

**Flow**: `.env.*` → docker-compose `${EMBEDDING_PROVIDER:-tei}` → container env → `settings.py` Pydantic reads from env → `deps.py` embedding factory.

### Step 6: Tests (`test_embedding_provider.py`)

Unit tests covering:
- Default provider is `tei`
- `gigachat` provider creates `GigaChatEmbeddings` instance
- `gigachat` without `giga_auth_data` raises RuntimeError
- Dimension detection returns correct length
- Mismatch detection triggers table recreation (mocked)

## Complexity Tracking

No constitution violations. No complexity justification needed.
