# Research: Switchable Embedding Provider (TEI / GigaChat)

**Date**: 2026-03-01

## R1: GigaChatEmbeddings Client Library

**Decision**: Use `langchain_gigachat.GigaChatEmbeddings` from `langchain-gigachat==0.3.12`

**Rationale**:
- Already installed in Dockerfile (`pip install langchain-gigachat==0.3.12`)
- `langchain_community.embeddings.gigachat.GigaChatEmbeddings` is **deprecated** since community v0.3.5
- `langchain_gigachat` is the official standalone integration package
- Implements standard LangChain `Embeddings` interface (`embed_query`, `embed_documents`, async variants)

**Alternatives considered**:
- `langchain_community.embeddings.gigachat.GigaChatEmbeddings` — deprecated, will be removed in community 1.0
- Direct `gigachat` SDK — lower level, would need to wrap in LangChain interface manually

## R2: GigaChatEmbeddings Constructor Parameters

**Decision**: Use `credentials` + `model` + `verify_ssl_certs=False`

**Key parameters**:
```python
GigaChatEmbeddings(
    credentials=settings.giga_auth_data,  # same base64 as GigaChat LLM
    model=settings.embedding_model,       # "Embeddings" (default) or "Embeddings-2"
    verify_ssl_certs=False,               # GigaChat API uses self-signed certs
    timeout=60,
)
```

**Rationale**: Authentication is identical to `GigaChat()` LLM — uses same `giga_auth_data` base64 credentials. The `verify_ssl_certs=False` pattern already used in `factory.py:189` for GigaChat LLM.

## R3: Vector Dimension Mismatch

**Decision**: Detect dimension via `pg_attribute.atttypmod` SQL query, auto-recreate table on mismatch

**Rationale**:
- `langchain_postgres.PGEngine` has NO method to query existing table dimensions
- pgvector stores dimension as `atttypmod` in `pg_attribute` catalog
- Formula: `dimension = atttypmod - 4` (4-byte varlena header offset)
- For `vector(768)`: `atttypmod = 772`, `772 - 4 = 768`
- Project already uses `engine._pool.connect()` + `engine._run_as_sync()` pattern in `admin.py`

**SQL query**:
```sql
SELECT atttypmod - 4 AS dim
FROM pg_attribute
WHERE attrelid = '"portfolio_new"'::regclass
  AND attname = 'embedding';
```

**Alternatives considered**:
- `information_schema.columns` — less reliable for custom pgvector types
- Hardcode dimension per provider — fragile, doesn't support future models

## R4: Table Recreation Strategy

**Decision**: Use `init_vectorstore_table(overwrite_existing=True)` for recreation

**Rationale**:
- `overwrite_existing=True` does `DROP TABLE IF EXISTS` + `CREATE TABLE` with new `vector_size`
- Current admin endpoint only does `TRUNCATE` (preserves table structure including dimension)
- For dimension change, we MUST drop and recreate (cannot ALTER vector column dimension)
- After recreation: clear embedding cache in Redis, log warning about reingest needed

## R5: Automatic Dimension Detection at Startup

**Decision**: Perform one `embed_query("test")` call at startup to determine vector dimension

**Rationale**:
- Different embedding models produce different dimensions (768 for e5-base, 1024 for GigaChat Embeddings)
- Hardcoding dimension per provider is fragile (new models may differ)
- One test embed at startup costs ~100ms (negligible, happens once)
- Result cached for the lifetime of the process

**Implementation**:
```python
def _detect_embedding_dim() -> int:
    test_vec = embeddings().embed_query("test")
    return len(test_vec)
```

## R6: Embedding Cache Key Isolation

**Decision**: Existing `EMBEDDING_MODEL` in cache key provides sufficient isolation

**Rationale**:
- Embedding cache key format: `rag:emb:{model_name}:{sha256[:16]}`
- When switching from TEI (`text-embedding-3-large`) to GigaChat (`Embeddings`), model name changes
- Different model names → different cache keys → no stale vector conflicts
- Still clear cache on dimension mismatch as safety measure

## R7: Dependencies

**Decision**: No new pip dependencies needed

**Rationale**:
- `langchain-gigachat==0.3.12` already installed via Dockerfile (not in pyproject.toml, installed with `--no-deps`)
- `gigachat==0.1.43` already installed as explicit dependency in Dockerfile
- No changes to pyproject.toml needed (Dockerfile handles gigachat-specific deps)
