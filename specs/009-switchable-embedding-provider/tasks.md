# Tasks: Switchable Embedding Provider (TEI / GigaChat)

**Input**: Design documents from `/specs/009-switchable-embedding-provider/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Included (plan Step 6 explicitly defines test requirements).

**Organization**: Tasks organized by logical increments — infrastructure config, core switching, dimension safety, observability.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all descriptions

---

## Phase 1: Infrastructure Config

**Purpose**: Add `EMBEDDING_PROVIDER` env var to all config files — enables the switch without changing any Python code yet.

- [x] T001 [P] Add `EMBEDDING_PROVIDER=tei` to `infra/.env.dev` next to existing `EMBEDDING_MODEL` line
- [x] T002 [P] Add `EMBEDDING_PROVIDER=tei` to `infra/.env.local` next to existing `EMBEDDING_MODEL` line
- [x] T003 [P] Add `EMBEDDING_PROVIDER=tei` to `infra/.env.prod` next to existing `EMBEDDING_MODEL` line
- [x] T004 [P] Add `EMBEDDING_PROVIDER=tei` with comment `# tei (local TEI) or gigachat (cloud GigaChat API)` to `infra/.env.example` next to existing `EMBEDDING_MODEL` line
- [x] T005 [P] Add `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-tei}` to rag-api environment section in `infra/docker-compose.local.yaml` next to existing `embedding_model: ${EMBEDDING_MODEL}` line
- [x] T006 [P] Add `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-tei}` to rag-api environment section in `infra/docker-compose-prod.yaml` next to existing `embedding_model: ${EMBEDDING_MODEL:-text-embedding-3-large}` line

**Checkpoint**: All env/compose files have `EMBEDDING_PROVIDER`. No behavioral change yet (default=tei).

---

## Phase 2: Foundational — Settings

**Purpose**: Add `embedding_provider` field to Pydantic settings — blocking prerequisite for all Python changes.

- [x] T007 Add `embedding_provider: Literal["tei", "gigachat"] = "tei"` field to `Settings` class in `services/rag-api-new/app/settings.py` in the `# === Embedding ===` section, with docstring `"""Embedding provider: 'tei' (local TEI) or 'gigachat' (cloud GigaChat API)."""`. Add `Literal` to the existing `typing` import.

**Checkpoint**: `settings().embedding_provider` returns `"tei"` by default. No behavioral change yet.

---

## Phase 3: US1 — Embedding Provider Factory (Priority: P1)

**Goal**: Replace hardcoded TEI embedding client with switchable factory that returns TEI or GigaChat based on `EMBEDDING_PROVIDER`.

**Independent Test**: Set `EMBEDDING_PROVIDER=gigachat` + `GIGA_AUTH_DATA=<creds>` + `EMBEDDING_MODEL=Embeddings`, restart service, check logs for `"Embedding provider: gigachat"`.

### Implementation

- [x] T008 [US1] Modify `embeddings()` function in `services/rag-api-new/app/deps.py`: change return type from `OpenAIEmbeddings` to `Embeddings` (import from `langchain_core.embeddings`). Add provider branching: if `embedding_provider == "gigachat"` → validate `giga_auth_data` is set (raise `RuntimeError` if not) → return `GigaChatEmbeddings(credentials=giga_auth_data, model=embedding_model, verify_ssl_certs=False, timeout=60)` (import from `langchain_gigachat`). Else (default tei) → return current `OpenAIEmbeddings` as-is. Add `logger.info` for selected provider.

**Checkpoint**: With `EMBEDDING_PROVIDER=tei` behavior is identical to before. With `gigachat` it creates GigaChatEmbeddings.

---

## Phase 4: US2 — Dimension Detection & Mismatch Handling (Priority: P1)

**Goal**: Auto-detect embedding vector dimension at startup and handle pgvector table dimension mismatch (drop+recreate table, clear cache).

**Independent Test**: Start service with `EMBEDDING_PROVIDER=gigachat` against existing 768-dim table → logs show WARNING about mismatch, table recreated with 1024-dim, embedding cache cleared.

### Implementation

- [x] T009 [US2] Add `_detect_embedding_dim()` function in `services/rag-api-new/app/deps.py`: calls `embeddings().embed_query("test")`, returns `len(result)`, logs detected dimension. Cache result in module-level `_embedding_dim` variable.

- [x] T010 [US2] Add `_get_table_vector_dim(engine, table_name)` function in `services/rag-api-new/app/deps.py`: uses `engine._pool.connect()` + `engine._run_as_sync()` pattern (same as `admin.py`) to execute SQL `SELECT atttypmod - 4 FROM pg_attribute WHERE attrelid = :tbl::regclass AND attname = 'embedding' AND atttypmod > 0`. Returns `int | None` (None if table doesn't exist). Add `from sqlalchemy import text` import.

- [x] T011 [US2] Modify `pg_engine()` function in `services/rag-api-new/app/deps.py`: replace hardcoded `vector_size=768` with dynamic flow: (1) create engine from connection string, (2) call `_detect_embedding_dim()` to get current provider's dimension, (3) call `_get_table_vector_dim()` to check existing table, (4) if table exists AND dimensions mismatch → log WARNING, call `engine.init_vectorstore_table(overwrite_existing=True, vector_size=detected_dim, ...)`, clear embedding cache via `CacheService(settings()).invalidate_embedding_cache()`, log INFO "Table recreated with vector_size={dim}, reingest required", (5) if table doesn't exist → call `init_vectorstore_table(overwrite_existing=False, vector_size=detected_dim, ...)` as before, (6) if dimensions match → normal startup log.

**Checkpoint**: Startup correctly detects dimensions, handles mismatch by recreating table. Existing TEI setup (768-dim) works without change.

---

## Phase 5: US3 — Admin Stats Enhancement (Priority: P2)

**Goal**: Expose current embedding provider and vector dimension in admin stats endpoint for observability.

**Independent Test**: `GET /api/v1/admin/stats` returns `embedding_provider`, `embedding_model`, `vector_dimension` fields.

### Implementation

- [x] T012 [US3] Add `embedding_provider`, `embedding_model`, and `vector_dimension` fields to the stats response in `services/rag-api-new/app/routers/admin.py`. Use `settings().embedding_provider`, `settings().embedding_model`, and the cached `_embedding_dim` from `deps.py` (expose via a getter function `get_embedding_dim()` in deps.py that returns the cached value).

**Checkpoint**: Admin stats show current embedding configuration.

---

## Phase 6: Tests

**Purpose**: Unit tests for provider switching, dimension detection, and mismatch handling.

- [x] T013 [P] Create test file `services/rag-api-new/tests/test_embedding_provider.py` with tests: (1) `test_default_provider_is_tei` — verify `Settings()` with no env override has `embedding_provider == "tei"`, (2) `test_gigachat_provider_requires_auth` — verify `embeddings()` raises `RuntimeError` when `embedding_provider="gigachat"` but `giga_auth_data=None` (mock settings), (3) `test_tei_provider_creates_openai_embeddings` — verify `embeddings()` returns `OpenAIEmbeddings` when provider is `tei` (mock settings), (4) `test_gigachat_provider_creates_gigachat_embeddings` — verify `embeddings()` returns `GigaChatEmbeddings` when provider is `gigachat` with valid `giga_auth_data` (mock settings + GigaChatEmbeddings constructor), (5) `test_detect_embedding_dim` — mock `embeddings().embed_query` to return a list of 1024 floats, verify `_detect_embedding_dim()` returns 1024, (6) `test_dimension_mismatch_triggers_recreate` — mock `_get_table_vector_dim` returning 768 and `_detect_embedding_dim` returning 1024, verify `pg_engine()` calls `init_vectorstore_table` with `overwrite_existing=True`.

**Checkpoint**: All tests pass with `pytest services/rag-api-new/tests/test_embedding_provider.py`.

---

## Phase 7: Polish & Validation

**Purpose**: Final verification and documentation consistency.

- [x] T014 Verify backward compatibility: confirm that with no `EMBEDDING_PROVIDER` set (or `=tei`), the full existing flow works unchanged — `embeddings()` returns `OpenAIEmbeddings`, `pg_engine()` uses 768-dim, no warnings in logs
- [x] T015 Update `CLAUDE.md` embedding-related sections: add `EMBEDDING_PROVIDER` to Environment Variables table, update `deps.py` description to mention switchable factory, add note about dimension auto-detection in Common Pitfalls

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Infra Config)**: No dependencies — all 6 tasks run in parallel
- **Phase 2 (Settings)**: No code dependency on Phase 1, but logically follows
- **Phase 3 (Factory)**: Depends on Phase 2 (needs `embedding_provider` field)
- **Phase 4 (Dimension)**: Depends on Phase 3 (needs `embeddings()` factory)
- **Phase 5 (Admin Stats)**: Depends on Phase 4 (needs `_embedding_dim` cached value)
- **Phase 6 (Tests)**: Depends on Phase 4 (tests all core logic)
- **Phase 7 (Polish)**: Depends on all phases complete

### Parallel Opportunities

```
Phase 1: T001 ─┬─ T002 ─┬─ T003 ─┬─ T004 ─┬─ T005 ─┬─ T006  (all parallel)
               └────────┴────────┴────────┴────────┴───────
Phase 2: T007                                               (sequential)
Phase 3: T008                                               (sequential)
Phase 4: T009 → T010 → T011                                 (sequential, same file)
Phase 5: T012                                               (sequential)
Phase 6: T013                                               (parallel with Phase 5)
Phase 7: T014 → T015                                        (sequential, final)
```

---

## Implementation Strategy

### MVP (Phases 1-4)

1. Complete Phase 1: Add env var to all config files
2. Complete Phase 2: Add settings field
3. Complete Phase 3: Implement factory switching
4. Complete Phase 4: Implement dimension detection
5. **VALIDATE**: Test with `EMBEDDING_PROVIDER=tei` (no change) and `EMBEDDING_PROVIDER=gigachat` (new path)

### Full Delivery (Phases 1-7)

1. MVP above
2. Add admin stats (Phase 5)
3. Add tests (Phase 6)
4. Polish + CLAUDE.md update (Phase 7)

---

## Notes

- All Python changes are in `services/rag-api-new/` (active service directory)
- `langchain-gigachat==0.3.12` is already installed in Dockerfile — no dependency changes needed
- `GigaChatEmbeddings` import from `langchain_gigachat` (NOT deprecated `langchain_community`)
- `verify_ssl_certs=False` required for GigaChat API (self-signed certs, same as GigaChat LLM)
- Dimension detection uses `pg_attribute.atttypmod - 4` formula (pgvector stores dim + 4 in typmod)
- Cache clearing on mismatch uses existing `CacheService.invalidate_embedding_cache()` from `app/cache/cache_service.py`
