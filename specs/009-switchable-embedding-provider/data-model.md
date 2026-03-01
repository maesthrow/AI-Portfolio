# Data Model: Switchable Embedding Provider

**Date**: 2026-03-01

## Settings Model Changes

### New Fields in `Settings` (Pydantic BaseSettings)

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `embedding_provider` | `Literal["tei", "gigachat"]` | `"tei"` | `EMBEDDING_PROVIDER` | Embedding provider selector |

### Existing Fields (reused, no changes)

| Field | Type | Default | Env Var | Usage |
|-------|------|---------|---------|-------|
| `embedding_model` | `str` | `"text-embedding-3-large"` | `EMBEDDING_MODEL` | TEI: cache key only; GigaChat: model name (`Embeddings`, `Embeddings-2`) |
| `tei_base_url` | `str \| AnyUrl` | `"http://tei:80/v1"` | `TEI_BASE_URL` | TEI endpoint (used when provider=tei) |
| `giga_auth_data` | `str \| None` | `None` | `GIGA_AUTH_DATA` | Base64 credentials (used when provider=gigachat) |
| `embedding_batch_size` | `int` | `4` | `EMBEDDING_BATCH_SIZE` | Batch size for ingestion |

## Module-Level State Changes

### `deps.py` — New cached values

| Name | Type | Scope | Description |
|------|------|-------|-------------|
| `_embedding_dim` | `int` | Module-level cached | Detected vector dimension from test embed |

## pgvector Table

### Table: `portfolio_new` (existing, dimension becomes dynamic)

| Column | Type | Notes |
|--------|------|-------|
| `id` | `UUID` | Primary key |
| `content` | `TEXT` | Document text |
| `embedding` | `vector(N)` | N = detected dim (768 for TEI, 1024 for GigaChat) |
| `type` | `TEXT` | Metadata: document type |
| `project_id` | `TEXT` | Metadata: project reference |
| `ref_id` | `TEXT` | Metadata: entity reference |
| `doc_id` | `TEXT` | Metadata: document ID |

**Note**: `vector(N)` dimension is determined at startup via test embed, NOT hardcoded.

## State Transitions

```
App Startup
    │
    ├─ embedding_provider == "tei"
    │   └─ Create OpenAIEmbeddings(base_url=TEI_BASE_URL)
    │
    └─ embedding_provider == "gigachat"
        └─ Create GigaChatEmbeddings(credentials=giga_auth_data, model=EMBEDDING_MODEL)
    │
    ▼
Detect dimension: embed_query("test") → len(vector)
    │
    ▼
Check existing table dimension (SQL: pg_attribute.atttypmod - 4)
    │
    ├─ Table not exists → init_vectorstore_table(vector_size=detected_dim)
    ├─ Dimensions match → normal startup
    └─ Dimensions mismatch:
        ├─ WARNING log
        ├─ init_vectorstore_table(overwrite_existing=True, vector_size=detected_dim)
        ├─ Clear embedding cache (Redis)
        └─ INFO log: "reingest required"
```

## Validation Rules

- `embedding_provider` must be `"tei"` or `"gigachat"` (enforced by `Literal` type)
- When `embedding_provider == "gigachat"`: `giga_auth_data` must not be None (fail-fast at startup with clear error)
- `embedding_model` is always a string, no validation beyond non-empty
