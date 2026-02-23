# Research: Migrate ChromaDB to pgvector

**Date**: 2026-02-23
**Branch**: `001-migrate-pgvector`

## R1: langchain-postgres — PGVector vs PGVectorStore

### Decision

Использовать **`PGVectorStore`** (не deprecated `PGVector`).

### Rationale

- `PGVector` deprecated с версии `langchain-postgres` v0.0.14 (апрель 2025)
- `PGVectorStore` — активно развиваемая замена (v0.0.17, февраль 2026)
- `PGVectorStore` имеет архитектурные преимущества:
  - Одна таблица на коллекцию (а не две shared-таблицы)
  - Выделенные `metadata_columns` для часто фильтруемых полей (быстрее JSONB)
  - `get_by_ids()` — нативный метод (замена хаку с `vs._collection.get()`)

### Alternatives Considered

| Вариант | Плюсы | Минусы | Решение |
|---------|-------|--------|---------|
| `PGVector` (deprecated) | Простая миграция, конструктор аналогичен Chroma | Deprecated, нет metadata_columns | Отклонён |
| `PGVectorStore` | Актуальный, metadata_columns, одна таблица | Другой конструктор (PGEngine + create_sync) | **Выбран** |
| Прямой pgvector без LangChain | Полный контроль | Нужно писать всю интеграцию с нуля | Отклонён |

## R2: API-совместимость PGVectorStore с текущим кодом

### Decision

API-совместимость подтверждена для всех ключевых методов. Несовместимости
требуют точечных изменений.

### Findings

**Полностью совместимые методы (без изменений кода):**

| Метод | Текущее использование | PGVectorStore |
|-------|----------------------|---------------|
| `add_texts(texts, metadatas, ids)` | `ingest.py:72` | Идентичная сигнатура, upsert-семантика |
| `delete(ids)` | `ingest.py:58` | Идентичная сигнатура |
| `similarity_search_by_vector(embedding, k, filter)` | `retrieval.py:107,157` | Идентичная сигнатура |

**Фильтры метаданных:**

| Оператор | Текущее использование | PGVectorStore |
|----------|----------------------|---------------|
| `{"type": {"$in": [...]}}` | `retrieval.py:157` | Поддерживается |
| `{"type": {"$in": [...]}, "project_id": {"$in": [...]}}` | `retrieval.py:110` | Поддерживается (implicit AND) |

Дополнительные операторы PGVectorStore: `$eq`, `$ne`, `$lt`, `$lte`,
`$gt`, `$gte`, `$between`, `$exists`, `$like`, `$ilike`, `$and`, `$or`, `$not`.

**Требующие изменений:**

| Место | Текущий код | Новый подход |
|-------|-------------|--------------|
| `retrieval.py:19-27` — `fetch_by_ids()` | `vs._collection.get(ids=ids)` (ChromaDB internal) | `vs.get_by_ids(ids)` (нативный метод PGVectorStore) |
| `admin.py:33` — clear collection | `client.delete_collection(name)` (chromadb HTTP) | `TRUNCATE TABLE "portfolio_new"` (raw SQL) |
| `admin.py:50-56` — stats | `coll.count()` + `coll.get(include=["metadatas"])` | `SELECT COUNT(*), ... FROM "portfolio_new"` (raw SQL) |
| `deps.py:40-56` — инициализация | `chromadb.HttpClient()` + `Chroma()` | `PGEngine.from_connection_string()` + `PGVectorStore.create_sync()` |

## R3: Инициализация PGVectorStore

### Decision

Использовать `PGEngine` + `init_vectorstore_table()` + `PGVectorStore.create_sync()`.

### Rationale

PGVectorStore требует явной инициализации таблицы. Процесс:

```
1. PGEngine.from_connection_string(DATABASE_URL)
2. engine.init_vectorstore_table(
     table_name="portfolio_new",
     vector_size=768,
     metadata_columns=[Column("type", "TEXT"), ...],
     overwrite_existing=False
   )
3. PGVectorStore.create_sync(
     engine=engine,
     table_name="portfolio_new",
     embedding_service=embeddings,
     metadata_columns=["type", "project_id", ...]
   )
```

### Metadata Columns (для оптимизации фильтрации)

Выделенные колонки для часто фильтруемых полей:

| Поле | Тип | Используется в фильтрах | Основание |
|------|-----|------------------------|-----------|
| `type` | TEXT | `retrieval.py:157` — каждый запрос | Основной фильтр HybridRetriever |
| `project_id` | TEXT | `retrieval.py:110` — expand_by_project | Compound-фильтр |
| `ref_id` | TEXT | — | Стандартное поле всех документов |
| `doc_id` | TEXT | `fetch_by_ids()` | Fetch по ID |

Остальные метаданные (`name`, `slug`, `company_name`, `technologies`,
`content_hash` и др.) хранятся в JSONB-колонке `langchain_metadata`.

## R4: Схема таблицы PGVectorStore

### Decision

Одна таблица `portfolio_new` с выделенными metadata_columns.

### Table Schema

```sql
CREATE TABLE portfolio_new (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content      TEXT NOT NULL,
    embedding    vector(768) NOT NULL,
    -- Dedicated metadata columns (fast filtering):
    type         TEXT,
    project_id   TEXT,
    ref_id       TEXT,
    doc_id       TEXT,
    -- Overflow metadata (JSONB):
    langchain_metadata JSON
);
```

**Отличие от deprecated PGVector:**
- PGVector: две shared-таблицы `langchain_pg_collection` + `langchain_pg_embedding`
- PGVectorStore: одна таблица на коллекцию (`portfolio_new`)

## R5: Подключение к PostgreSQL

### Decision

RAG API использует общий `DATABASE_URL` (та же БД `ai_portfolio_new`).
Драйвер: `psycopg` (v3), НЕ `psycopg2`.

### Rationale

- `PGVectorStore` требует `psycopg` (v3) в connection string
- Формат: `postgresql+psycopg://user:password@postgres:5432/ai_portfolio_new`
- Content API уже использует `postgresql+psycopg://...` — совместимо
- Таблица `portfolio_new` не конфликтует с таблицами content-api

### Connection String

```
DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

В Docker Compose RAG API получает тот же `DATABASE_URL`, что и Content API.

## R6: Docker-образ PostgreSQL

### Decision

Использовать `pgvector/pgvector:pg16`.

### Rationale

- Официальный образ с предустановленным pgvector
- `CREATE EXTENSION IF NOT EXISTS vector` — достаточно в init-скрипте
- Заменяет `postgres:16` в обоих compose-файлах (local + prod)
- Полностью совместим с существующими данными (тот же PostgreSQL 16)

## R7: Удаление `_filter_complex_metadata()`

### Decision

Удалить функцию. Метаданные хранятся нативно в JSONB.

### Rationale

- ChromaDB требовал flat metadata (только str/int/float/bool)
- `_filter_complex_metadata()` сериализовала списки в JSON-строки + `_csv`-суффиксы
- PGVectorStore хранит metadata в JSONB — вложенные структуры поддерживаются нативно
- Поля-списки (`technologies`, `project_ids`, `project_slugs`) будут храниться
  как JSONB-массивы, а не как сериализованные строки

### Impact

- Упрощение кода ингеста
- Нативные JSONB-фильтры для массивов (потенциал: `@>` оператор)
- Удалить `_csv`-суффиксные поля (`technologies_csv`, `project_ids_csv`)

## R8: Admin-операции без ChromaDB

### Decision

Заменить raw chromadb API на прямые SQL-запросы через PGEngine.

### Implementation Approach

| Операция | Текущий код | Новый подход |
|----------|-------------|--------------|
| Очистка коллекции | `client.delete_collection(name)` | `TRUNCATE TABLE "portfolio_new"` |
| Пересоздание коллекции | `vectorstore(collection_name)` | `engine.init_vectorstore_table(overwrite_existing=False)` |
| Подсчёт документов | `coll.count()` | `SELECT COUNT(*) FROM "portfolio_new"` |
| Статистика по типам | `coll.get(include=["metadatas"])` | `SELECT type, COUNT(*) FROM "portfolio_new" GROUP BY type` |

Преимущество: SQL-запросы эффективнее, чем загрузка всех метаданных в память
(текущий подход ChromaDB загружает ВСЕ документы для подсчёта по типам).
