# Tasks: Migrate ChromaDB to pgvector

**Input**: Design documents from `/specs/001-migrate-pgvector/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Not explicitly requested. Verification tasks included in Polish phase.

**Organization**: Tasks grouped by user story. US2 (ingest) precedes US1 (search)
because data must exist before search can be tested. US5 (SQL capabilities) is
merged into US1 since `fetch_by_ids()` is required for search to work.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions

- RAG API: `services/rag-api-new/`
- Infrastructure: `infra/`
- Root docs: project root

---

## Phase 1: Setup

**Purpose**: Replace Python dependencies and update application settings.
No code logic changes — only package declarations and config fields.

- [x] T001 [P] Replace `langchain-chroma` and `chromadb` with `langchain-postgres>=0.0.17` and `psycopg[binary]>=3.1` in `services/rag-api-new/pyproject.toml`
- [x] T002 [P] Update `services/rag-api-new/app/settings.py`: remove fields `chroma_host`, `chroma_port`, `chroma_collection` and property `chroma_client_kwargs`; add field `database_url` (str, from env `DATABASE_URL`) and rename/keep `collection_name` (str, default `"portfolio_new"`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Replace ChromaDB vectorstore initialization with PGVectorStore.
This is the single most critical change — ALL user stories depend on it.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Rewrite `services/rag-api-new/app/deps.py`: remove `import chromadb`, `from chromadb.config import Settings`, `from langchain_chroma import Chroma`; remove `chroma_client()` function; add `pg_engine()` function returning `PGEngine.from_connection_string(settings().database_url)`; add `init_vectorstore_table()` call with `table_name="portfolio_new"`, `vector_size=768`, `metadata_columns=[Column("type", TEXT), Column("project_id", TEXT), Column("ref_id", TEXT), Column("doc_id", TEXT)]`; replace `vectorstore()` function to return `PGVectorStore.create_sync(engine=pg_engine(), table_name=settings().collection_name, embedding_service=embeddings(), metadata_columns=["type", "project_id", "ref_id", "doc_id"])`. Ensure `embeddings()` function remains unchanged.
- [x] T003a Verify `services/rag-api-new/app/main.py`: ensure no startup/shutdown events reference ChromaDB; update any lifespan handler if it initializes chroma_client

**Checkpoint**: `deps.py` imports compile, PGEngine connects to PostgreSQL, `vectorstore()` returns a PGVectorStore instance.

---

## Phase 3: User Story 2 — Batch-ингест (Priority: P2) — First because data is needed for search

**Goal**: Documents from Content API are ingested into pgvector with native JSONB metadata.

**Independent Test**: Run `rag-ingest`, verify `/api/v1/admin/stats` shows correct document count and type breakdown.

### Implementation for User Story 2

- [x] T004 [US2] Remove function `_filter_complex_metadata()` and its helper logic (lines 18-37) from `services/rag-api-new/app/routers/ingest.py`; update `upsert_documents()` to pass `it.metadata` directly to `vs.add_texts()` without flattening; remove `_csv`-suffix field generation
- [x] T005 [US2] Verify `services/rag-api-new/app/indexing/normalizer.py` produces metadata values compatible with JSONB (lists as Python lists, dicts as Python dicts, no custom objects). Check all `make_doc()` and `chunk_doc()` calls ensure `technologies`, `project_ids`, `project_slugs`, `project_names` are plain Python lists
- [x] T006 [US2] Update `upsert_documents()` in `services/rag-api-new/app/routers/ingest.py` to use PGVectorStore API: `vs.delete(ids=ids_all)` (same API) then `vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)` (same API). Verify upsert semantics work (delete + re-add)
- [x] T006a [US2] Verify `services/rag-api-new/app/routers/ingest_batch.py` uses the same `upsert_documents()` from `ingest.py` (shared import) or update its own metadata handling to pass metadata without flattening; ensure batch endpoint `/api/v1/ingest/batch` works with PGVectorStore

**Checkpoint**: Batch ingest completes, documents stored in `portfolio_new` table with correct metadata.

---

## Phase 4: User Story 1 — AI-агент поиск (Priority: P1) + User Story 5 — SQL capabilities (Priority: P5) — MVP

**Goal**: Agent answers questions using pgvector search with same quality as ChromaDB. `fetch_by_ids()` uses native `get_by_ids()` instead of ChromaDB internal hack.

**Independent Test**: Ask agent 10 questions from `POPULAR_QUESTIONS`, compare answer quality with pre-migration baseline.

### Implementation for User Story 1 + 5

- [x] T007 [US1] Rewrite `fetch_by_ids()` function in `services/rag-api-new/app/rag/retrieval.py`: remove the `getattr(vs, "_collection", None)` ChromaDB hack (lines 13-39); replace with `vs.get_by_ids(ids)` which returns `list[Document]`; convert to `list[Doc]` format matching existing return type
- [x] T008 [US1] Verify `similarity_search_by_vector(embedding, k, filter)` calls in `services/rag-api-new/app/rag/retrieval.py` work with PGVectorStore: check `HybridRetriever.retrieve()` dense search path (line ~157) with filter `{"type": {"$in": [...]}}` and `expand_by_project()` (line ~107) with compound filter `{"type": {"$in": [...]}, "project_id": {"$in": [...]}}`; no code changes expected if API is compatible, but verify and fix if needed
- [x] T009 [US1] Verify `DenseRetriever.retrieve()` in `services/rag-api-new/app/rag/retrieval.py` works with PGVectorStore filter parameter (same verification as T008 but for the simpler retriever class)
- [x] T009a [US1] Verify `services/rag-api-new/app/rag/search.py` orchestration layer: ensure `portfolio_search()` passes correct parameters to `HybridRetriever` and no ChromaDB-specific logic remains. Removed stale `_csv` suffix fields from `matches_entity_ext()` and `_extract_project_names_from_metadata()` in `answer_llm.py`

**Checkpoint**: Agent answers questions correctly. `fetch_by_ids()` uses SQL. Hybrid search works end-to-end.

---

## Phase 5: User Story 4 — Администрирование коллекции (Priority: P4)

**Goal**: Admin endpoints (stats, clear collection) work via SQL instead of ChromaDB API.

**Independent Test**: Call each admin endpoint, verify response schema and data correctness.

### Implementation for User Story 4

- [x] T010 [US4] Rewrite `clear_collection()` in `services/rag-api-new/app/routers/admin.py`: remove `from app.deps import chroma_client`; replace `client.delete_collection(collection_name)` with SQL `TRUNCATE TABLE "{collection_name}"` via PGEngine; keep BM25 `bm25.reset(collection_name)` call; remove `vectorstore(collection_name)` re-creation call (PGVectorStore table persists after TRUNCATE)
- [x] T011 [US4] Rewrite `collection_stats()` in `services/rag-api-new/app/routers/admin.py`: remove `client.get_or_create_collection()`, `coll.count()`, `coll.get(include=["metadatas"])` ChromaDB calls; replace with SQL queries via PGEngine: `SELECT COUNT(*) FROM "{collection_name}"` for total count and `SELECT type, COUNT(*) FROM "{collection_name}" GROUP BY type` for per-type breakdown
- [x] T012 [US4] Update imports in `services/rag-api-new/app/routers/admin.py`: remove `chroma_client` import from `app.deps`; add `pg_engine` import from `app.deps`; ensure all admin endpoints use PGEngine for database access

**Checkpoint**: `GET /api/v1/admin/stats` returns correct counts. `DELETE /api/v1/admin/collection` clears all vectors.

---

## Phase 6: User Story 3 — Инфраструктура без ChromaDB (Priority: P3)

**Goal**: Docker Compose and env files updated. ChromaDB service removed. PostgreSQL uses pgvector image.

**Independent Test**: `docker compose up -d` succeeds, no `chroma` service, pgvector extension active.

### Implementation for User Story 3

- [x] T013 [P] [US3] Update `infra/init/postgres-init.sql`: add `CREATE EXTENSION IF NOT EXISTS "vector";` after existing `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
- [x] T014 [US3] Update `infra/docker-compose.local.yaml`: change postgres image from `postgres:16` to `pgvector/pgvector:pg16`; remove entire `chroma` service block; remove `chroma_data` from volumes declaration; remove `chroma` from rag-api `depends_on`; add `depends_on: postgres` to rag-api; replace `CHROMA_HOST`, `CHROMA_PORT`, `chroma_collection`, `ANONYMIZED_TELEMETRY` env vars in rag-api with `DATABASE_URL` using same connection string as content-api
- [x] T015 [US3] Update `infra/docker-compose-prod.yaml`: same changes as T014 (postgres image, remove chroma service/volume/depends_on, add DATABASE_URL to rag-api env)
- [x] T016 [P] [US3] Update `infra/.env.dev`: remove `CHROMA_PORT` from ports section; remove entire Chroma section (`CHROMA_HOST`, `CHROMA_COLLECTION`); verify `DATABASE_URL` is defined and accessible for rag-api
- [x] T017 [P] [US3] Update `infra/.env.local`: same changes as T016 (remove CHROMA_PORT, CHROMA_HOST, CHROMA_COLLECTION)
- [x] T018 [P] [US3] Update `infra/.env.prod`: remove `CHROMA_COLLECTION` from internal ports section; remove entire Chroma section (`CHROMA_HOST`, `CHROMA_PORT`)
- [x] T019 [P] [US3] Update `infra/.env.example`: remove `CHROMA_PORT` from ports section; replace entire `ChromaDB (Vector Database)` section with pgvector documentation referencing `DATABASE_URL` and `COLLECTION_NAME`

**Checkpoint**: Docker Compose starts without chroma. PostgreSQL has pgvector extension. All env files clean.

---

## Phase 7: User Story 6 — Документация (Priority: P6)

**Goal**: All documentation updated. No ChromaDB references remain.

**Independent Test**: `grep -ri "chroma"` across repo returns no active references.

### Implementation for User Story 6

- [x] T020 [US6] Update `CLAUDE.md`: replace all ChromaDB references with pgvector throughout the file — Architecture section (RAG API description, vector store references), Environment Variables (remove CHROMA_*, add pgvector connection), Docker services (remove chroma service, update postgres image), Common Pitfalls (remove ChromaDB-specific pitfalls, add pgvector notes), File Structure (remove chroma references), Data Flow (update RAG ingestion flow), Technology Stack table (ChromaDB → pgvector), Key Architectural Patterns (update Hybrid Retrieval section)
- [x] T021 [US6] Update `CLAUDE_RU.md`: synchronize all changes from T020, ensuring Russian translation is consistent with updated `CLAUDE.md`
- [x] T022 [P] [US6] Update `infra/DOCKER-LOCAL.md`: remove `chroma` row from services table (line ~229); update comment on line ~161 from "ChromaDB" to "pgvector"; update any curl examples referencing chroma
- [x] T023 [P] [US6] Update `infra/DOCKER-PROD.md`: remove `chroma` row from services table (line ~287); remove `docker inspect ai-folio-chroma-1` health check example (line ~263); update comment on line ~195 from "ChromaDB" to "pgvector"

**Checkpoint**: All documentation reflects pgvector. No ChromaDB references.

---

## Phase 8: Polish & Verification

**Purpose**: End-to-end verification, test suite, final cleanup.

- [x] T024 Run `pytest tests/ -v` in `services/rag-api-new/` and fix any failures caused by migration. Fixed 3 pre-existing test failures: unpacked tuple return from `AnswerLLM.generate()`, added `timeout=90` to GigaChat mock. Result: 96 passed, 20 skipped
- [x] T025 Start full Docker Compose stack (`docker compose -f docker-compose.local.yaml up -d`), run `rag-ingest`, verify `/api/v1/admin/stats` returns correct document counts. Result: 87 docs ingested, graph 81 nodes/163 edges, prefetch 33 cache + 6 shortcuts, admin stats confirmed
- [x] T026 Test AI agent with 5+ questions from `POPULAR_QUESTIONS` via `/api/v1/agent/chat/stream`, verify quality of answers and measure response time. Result: agent works, answers factually correct. Performance issues documented in `known-issues.md` (planner retry, low confidence, 52s latency, 15k tokens) — all pre-existing, not migration-related
- [x] T027 Run `grep -ri "chroma" --include="*.py" --include="*.yaml" --include="*.md" --include="*.toml" --include="*.env*" --include="*.sql"` across repo (excluding `.git/`, `node_modules/`, `specs/`, `.specify/`) and fix any remaining active references. This task serves as catch-all for FR-024 (remove ALL chromadb/langchain_chroma imports) beyond the files explicitly covered by T003 and T012
- [x] T028 Verify `pg_dump` of `ai_portfolio_new` includes both content-api tables and `portfolio_new` vector table. Result: 19 tables in single DB — 18 content-api + 1 pgvector (`portfolio_new` with `vector(768)`). Single `pg_dump` backs up everything

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US2 Ingest (Phase 3)**: Depends on Phase 2 — needed for US1 testing
- **US1 Search (Phase 4)**: Depends on Phase 2 + Phase 3 (data must exist)
- **US4 Admin (Phase 5)**: Depends on Phase 2 only (independent of US1/US2)
- **US3 Infra (Phase 6)**: Independent of code phases (can run in parallel after Phase 1)
- **US6 Docs (Phase 7)**: Depends on all code + infra phases
- **Polish (Phase 8)**: Depends on ALL phases

### User Story Dependencies

```
Phase 1: Setup (T001, T002)
    ↓
Phase 2: Foundational (T003)
    ↓
    ├─── Phase 3: US2 Ingest (T004-T006)
    │        ↓
    │    Phase 4: US1 Search (T007-T009) ← MVP checkpoint
    │
    ├─── Phase 5: US4 Admin (T010-T012) ← can parallel with US2/US1
    │
    └─── Phase 6: US3 Infra (T013-T019) ← can parallel with code phases
              ↓
         Phase 7: US6 Docs (T020-T023)
              ↓
         Phase 8: Polish (T024-T028)
```

### Parallel Opportunities

**Within Phase 1:**
```
T001 [P] pyproject.toml ──┐
                           ├── both independent files
T002 [P] settings.py ─────┘
```

**Within Phase 6 (US3 Infra):**
```
T013 [P] postgres-init.sql ─────┐
T016 [P] .env.dev ──────────────┤
T017 [P] .env.local ────────────┼── all independent files
T018 [P] .env.prod ─────────────┤
T019 [P] .env.example ──────────┘

T014 docker-compose.local.yaml ─┐
                                 ├── sequential (same pattern)
T015 docker-compose-prod.yaml ──┘
```

**Within Phase 7 (US6 Docs):**
```
T022 [P] DOCKER-LOCAL.md ──┐
                            ├── independent files
T023 [P] DOCKER-PROD.md ───┘

T020 CLAUDE.md ─────┐
                     ├── sequential (T021 syncs from T020)
T021 CLAUDE_RU.md ──┘
```

**Cross-phase parallelism:**
```
Phase 5 (US4 Admin) can run in parallel with Phase 3 (US2) + Phase 4 (US1)
Phase 6 (US3 Infra) can start after Phase 1, parallel with all code phases
```

---

## Implementation Strategy

### MVP First (Phases 1-4)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003)
3. Complete Phase 3: US2 Ingest (T004-T006)
4. Complete Phase 4: US1 Search (T007-T009)
5. **STOP and VALIDATE**: Test agent with POPULAR_QUESTIONS
6. If agent answers correctly → MVP achieved

### Full Migration (Phases 5-8)

7. Complete Phase 5: US4 Admin (T010-T012)
8. Complete Phase 6: US3 Infra (T013-T019)
9. Complete Phase 7: US6 Docs (T020-T023)
10. Complete Phase 8: Polish & Verification (T024-T028)

### Rollback Plan

If MVP validation fails at step 5:
- `git stash` all changes
- Revert to ChromaDB (branch `develop` has working state)
- Investigate root cause before retrying

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US5 (SQL capabilities) merged into US1 — `fetch_by_ids()` fix is required for search
- Commit after each phase or logical group
- Stop at any checkpoint to validate independently
- Total: 31 tasks across 8 phases (T003a, T006a, T009a added by /speckit.analyze)
