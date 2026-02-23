# Implementation Plan: Migrate ChromaDB to pgvector

**Branch**: `001-migrate-pgvector` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-migrate-pgvector/spec.md`

## Summary

Миграция RAG API с ChromaDB на pgvector (через `langchain_postgres.PGVectorStore`).
Заменяет отдельный ChromaDB-сервис на расширение pgvector в существующем
PostgreSQL, используя общую БД `ai_portfolio_new`. Включает обновление
кода rag-api-new, Docker-инфраструктуры (local + prod), env-конфигурации,
Python-зависимостей и всей документации (CLAUDE.md, CLAUDE_RU.md,
DOCKER-LOCAL.md, DOCKER-PROD.md).

**Ключевое решение из research**: используем `PGVectorStore` (не deprecated
`PGVector`), что даёт одну таблицу на коллекцию и dedicated metadata columns
для оптимизации фильтров. Подробнее: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, langchain-postgres v0.0.17+ (PGVectorStore), psycopg v3, SQLAlchemy 2.0
**Storage**: PostgreSQL 16 (pgvector/pgvector:pg16) + Redis
**Testing**: pytest (`services/rag-api-new/tests/`)
**Target Platform**: Docker Compose (Linux containers)
**Project Type**: Microservices (web-service)
**Performance Goals**: Время ответа агента не увеличивается >10% vs текущее
**Constraints**: ~200 документов, seq scan достаточен (HNSW не нужен)
**Scale/Scope**: ~120-200 векторов, 768 dimensions (multilingual-e5-base)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | Все файлы UTF-8, Cyrillic-текст не затрагивается миграцией |
| II. Root-Cause Resolution | PASS | Миграция устраняет root cause: лишний сервис ChromaDB. Clean cut, без workarounds |
| III. Clean Architecture | PASS | `_filter_complex_metadata()` удаляется (DRY/KISS). PGVectorStore — чистая замена |
| IV. Service Directory Discipline | PASS | Все изменения в `services/rag-api-new/`, `infra/`. Frontend не затрагивается |
| V. API Versioning & Contracts | PASS | API-эндпоинты `/api/v1/*` не меняются. NDJSON-стрим сохраняется |
| VI. Database Migration Discipline | N/A | PGVectorStore создаёт таблицу автоматически. Content API модели не меняются |
| VII. Simplicity & YAGNI | PASS | Убираем сервис, упрощаем код. Metadata columns — только для реально используемых фильтров |

**Post-design re-check**: All gates PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-migrate-pgvector/
├── plan.md              # This file
├── spec.md              # Feature specification (6 user stories, 31 FR)
├── research.md          # Phase 0: langchain_postgres research (8 decisions)
├── data-model.md        # Phase 1: pgvector table schema
├── quickstart.md        # Phase 1: verification steps
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files to modify)

```text
services/rag-api-new/
├── app/
│   ├── deps.py                    # [MODIFY] Replace Chroma → PGEngine + PGVectorStore
│   ├── settings.py                # [MODIFY] Remove chroma_*, add database_url, collection_name
│   ├── rag/
│   │   └── retrieval.py           # [MODIFY] Replace fetch_by_ids() → vs.get_by_ids()
│   ├── routers/
│   │   ├── admin.py               # [MODIFY] Replace chromadb API → SQL queries via PGEngine
│   │   └── ingest.py              # [MODIFY] Remove _filter_complex_metadata()
│   └── indexing/
│       └── normalizer.py          # [VERIFY] Ensure metadata values are JSONB-compatible
├── pyproject.toml                 # [MODIFY] Replace chromadb → langchain-postgres + psycopg
├── Dockerfile                     # [VERIFY] No changes needed
└── Dockerfile.prod                # [VERIFY] No changes needed

infra/
├── docker-compose.local.yaml      # [MODIFY] Remove chroma, update postgres image, update rag-api env
├── docker-compose-prod.yaml       # [MODIFY] Same as local
├── init/postgres-init.sql         # [MODIFY] Add CREATE EXTENSION vector
├── .env.dev                       # [MODIFY] Remove CHROMA_*, configure DATABASE_URL for rag-api
├── .env.local                     # [MODIFY] Same
├── .env.prod                      # [MODIFY] Same
└── .env.example                   # [MODIFY] Same + update documentation section

Root documentation:
├── CLAUDE.md                      # [MODIFY] Replace all ChromaDB → pgvector across all sections
└── CLAUDE_RU.md                   # [MODIFY] Sync with CLAUDE.md

infra/ documentation:
├── DOCKER-LOCAL.md                # [MODIFY] Remove chroma from services table, update examples
└── DOCKER-PROD.md                 # [MODIFY] Remove chroma from services table + health checks
```

**Structure Decision**: Существующая microservices-структура сохраняется.
Новых директорий не создаётся. Модификации ограничены существующими файлами
в `services/rag-api-new/` и `infra/`.

## Key Architectural Decisions

### 1. PGVectorStore вместо deprecated PGVector

См. [research.md — R1](research.md).

`PGVectorStore` (актуальный) создаёт одну таблицу `portfolio_new` вместо
двух shared-таблиц deprecated `PGVector`. Поддерживает dedicated metadata
columns для быстрой SQL-фильтрации.

### 2. Dedicated Metadata Columns

4 поля вынесены в отдельные PostgreSQL-колонки (быстрая фильтрация):

| Column | Type | Used In |
|--------|------|---------|
| `type` | TEXT | Каждый поисковый запрос (HybridRetriever) |
| `project_id` | TEXT | `expand_by_project()` compound filter |
| `ref_id` | TEXT | Стандартный ID документа |
| `doc_id` | TEXT | `fetch_by_ids()` |

Остальные ~25 полей метаданных → JSONB overflow (`langchain_metadata`).

### 3. Общий DATABASE_URL

RAG API подключается к той же БД `ai_portfolio_new`, что и Content API.
Таблица `portfolio_new` не конфликтует с таблицами Content API.
Единый `pg_dump` покрывает всё.

### 4. Clean Cut (без fallback)

ChromaDB удаляется полностью: код, зависимости, Docker-сервис, env-переменные.
Никаких fallback-режимов или feature flags. При ~200 документах миграция
тривиальна — ингест занимает секунды.

### 5. Нативный JSONB (удаление _filter_complex_metadata)

Функция `_filter_complex_metadata()` удаляется. Списки (`technologies`,
`project_ids`) хранятся как нативные JSONB-массивы. Удаляются `_csv`-поля.

## File Change Map

### Critical Path (блокирующие изменения)

| Priority | File | Change | Depends On |
|----------|------|--------|------------|
| 1 | `pyproject.toml` | Replace chromadb → langchain-postgres, psycopg | — |
| 2 | `settings.py` | Remove chroma_*, add database_url, collection_name | — |
| 3 | `deps.py` | Replace Chroma → PGEngine + PGVectorStore | 1, 2 |
| 4 | `ingest.py` | Remove `_filter_complex_metadata()` | 3 |
| 5 | `retrieval.py` | Replace `fetch_by_ids()` → `get_by_ids()` | 3 |
| 6 | `admin.py` | Replace chromadb API → SQL via PGEngine | 3 |

### Infrastructure (параллельно с кодом)

| Priority | File | Change |
|----------|------|--------|
| 7 | `postgres-init.sql` | Add `CREATE EXTENSION IF NOT EXISTS "vector"` |
| 8 | `docker-compose.local.yaml` | Remove chroma, update postgres image, update rag-api env |
| 9 | `docker-compose-prod.yaml` | Same as local |
| 10 | `.env.dev` | Remove CHROMA_*, add DATABASE_URL |
| 11 | `.env.local` | Same |
| 12 | `.env.prod` | Same |
| 13 | `.env.example` | Same + documentation |

### Documentation (после кода и инфраструктуры)

| Priority | File | Change |
|----------|------|--------|
| 14 | `CLAUDE.md` | Replace all ChromaDB → pgvector |
| 15 | `CLAUDE_RU.md` | Sync with CLAUDE.md |
| 16 | `DOCKER-LOCAL.md` | Remove chroma, update examples |
| 17 | `DOCKER-PROD.md` | Remove chroma, update examples |

### Verification

| Priority | Action |
|----------|--------|
| 18 | Run existing tests (`pytest tests/`) |
| 19 | Docker Compose up + rag-ingest + agent test |
| 20 | Grep for remaining "chroma" references |

## Complexity Tracking

> No Constitution Check violations. No complexity justifications needed.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| PGVectorStore vs PGVector | PGVectorStore | PGVector deprecated. Simplicity = use current, not legacy |
| 4 dedicated metadata columns | type, project_id, ref_id, doc_id | Only fields used in filters. YAGNI for the rest |
| Raw SQL for admin | TRUNCATE / SELECT COUNT | PGVectorStore has no `delete_collection()`. SQL is the direct solution |
| No HNSW index | seq scan | ~200 vectors, HNSW overhead not justified |
