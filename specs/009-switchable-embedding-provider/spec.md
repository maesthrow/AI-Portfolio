# Feature Spec: Switchable Embedding Provider (TEI / GigaChat)

## Overview

Добавить возможность переключения embedding-провайдера в rag-api-new между локальным TEI (multilingual-e5-base, 768-dim) и облачным GigaChat Embeddings API (1024-dim) через один параметр `EMBEDDING_PROVIDER` в настройках. Цель — ускорить RAG-pipeline в продакшне на сервере без GPU, где TEI на CPU работает медленно.

## Problem Statement

- В продакшне нет GPU, TEI (multilingual-e5-base) на CPU выдаёт ~50-200ms на батч → медленный векторный поиск
- Локально (dev, GPU 3060 12GB) всё работает быстро
- Облачный GigaChat Embeddings API решает проблему: сетевой roundtrip ~30-80ms быстрее CPU-инференса
- Нужен простой переключатель без изменения остальной архитектуры

## Functional Requirements

### Configuration

- **`EMBEDDING_PROVIDER`** — новый env-параметр: `tei` (default) | `gigachat`
- **`EMBEDDING_MODEL`** — существующий параметр, переиспользуется:
  - `tei`: игнорируется TEI-сервисом, используется как cache key namespace (как сейчас)
  - `gigachat`: передаётся как `model` в `GigaChatEmbeddings` (e.g. `Embeddings`, `Embeddings-2`)
- При `gigachat`: credentials берутся из существующего `giga_auth_data` (base64)

### Embedding Client Factory

- Единая фабрика `embeddings()` в `deps.py` возвращает `Embeddings` интерфейс (LangChain base class)
- `tei` → `OpenAIEmbeddings(base_url=TEI_BASE_URL)` (как сейчас)
- `gigachat` → `GigaChatEmbeddings(credentials=giga_auth_data, model=EMBEDDING_MODEL)`
- Результат кешируется через `@lru_cache()` (как сейчас)

### Automatic Dimension Detection

- При старте приложения выполняется тестовый `embed_query("test")` для определения размерности вектора
- Размерность (`vector_size`) больше НЕ хардкодится как 768 — берётся из результата тестового embed
- Размерность кешируется и передаётся в `pg_engine().init_vectorstore_table(vector_size=detected_dim)`

### Auto-Reingest on Dimension Mismatch

- При старте: проверить текущую размерность pgvector-колонки в таблице `portfolio_new`
- Если размерность таблицы != размерности нового провайдера:
  - Логировать WARNING о несовпадении
  - Пересоздать таблицу с новой размерностью (`overwrite_existing=True`)
  - Очистить embedding-кеш в Redis
  - Логировать INFO: "Table recreated with vector_size={dim}, reingest required"
  - **НЕ запускать reingest автоматически** — только подготовить таблицу, reingest через `rag-ingest` сервис или API
- Если размерности совпадают — ничего не делать (штатный запуск)

### Chunker

- Chunker НЕ изменяется (MAX_CHARS=1800, ~350-450 токенов < 512 лимит GigaChat)
- GigaChat API сам обрезает тексты при превышении контекстного окна (safety net)

### TEI in Docker Compose

- TEI остаётся в docker-compose файлах без изменений
- Оператор сам решает запускать ли TEI (`docker compose up` с/без `tei`)
- При `EMBEDDING_PROVIDER=gigachat` TEI не используется, можно не запускать

## Non-Functional Requirements

### Performance

- GigaChat Embeddings API latency: ~30-80ms per request (network roundtrip)
- Embedding cache в Redis снижает повторные вызовы до ~1ms (cache hit)
- Dimension detection при старте: +1 API call (~100ms), выполняется однократно

### Reliability

- При недоступности GigaChat API — embedding вызов падает с ошибкой (fail-fast, как и TEI)
- Embedding cache (Redis) остаётся fail-open (graceful degradation)

### Backward Compatibility

- `EMBEDDING_PROVIDER` по умолчанию `tei` — без изменения env ничего не ломается
- Существующие pgvector данные (768-dim) работают с `tei` без изменений
- Переключение на `gigachat` требует reingest (ожидаемо, не баг)

## Out of Scope

- Изменение chunker (MAX_CHARS остаётся 1800)
- Изменение docker-compose файлов (TEI остаётся)
- Поддержка других embedding-провайдеров (OpenAI, Cohere и т.д.) — только TEI и GigaChat
- Автоматический запуск reingest при смене провайдера (только подготовка таблицы)
- Изменение reranker (BAAI/bge-reranker-base остаётся на CPU)

## Technical Context

### Current Embedding Flow
```
rag-api-new → OpenAIEmbeddings(base_url=TEI) → TEI HTTP → multilingual-e5-base (768-dim)
```

### Target Embedding Flow (switchable)
```
EMBEDDING_PROVIDER=tei:
  rag-api-new → OpenAIEmbeddings(base_url=TEI) → TEI HTTP → multilingual-e5-base (768-dim)

EMBEDDING_PROVIDER=gigachat:
  rag-api-new → GigaChatEmbeddings(credentials) → GigaChat API → Embeddings model (1024-dim)
```

### Key Files to Modify
- `services/rag-api-new/app/settings.py` — add `EMBEDDING_PROVIDER`
- `services/rag-api-new/app/deps.py` — embedding factory, dynamic vector_size
- `infra/.env.dev`, `infra/.env.local`, `infra/.env.prod`, `infra/.env.example` — add `EMBEDDING_PROVIDER=tei`
- `infra/docker-compose.local.yaml`, `infra/docker-compose-prod.yaml` — pass `EMBEDDING_PROVIDER` to rag-api

### Dependencies
- `langchain_community.embeddings.gigachat.GigaChatEmbeddings`
- Existing `giga_auth_data` env var (already used for GigaChat LLM)

## Clarifications

### Session 2026-03-01

- Q: Какой режим переключения между моделями? → A: Auto-reingest при несовпадении dimensions (пересоздание таблицы + очистка кеша, reingest через rag-ingest сервис)
- Q: Как обрабатывать чанки превышающие 512-токенный лимит GigaChat? → A: Доверяем API truncation, chunker не трогаем (1800 символов ≈ 350-450 токенов < 512)
- Q: Какой клиент для GigaChat Embeddings? → A: `GigaChatEmbeddings` из `langchain_community`, использует существующий `giga_auth_data`
- Q: Как выглядит конфигурация переключения? → A: `EMBEDDING_PROVIDER=tei|gigachat` + переиспользуем `EMBEDDING_MODEL` (для gigachat передаётся как model name), dimensions определяются автоматически через тестовый embed
- Q: Как поступить с TEI в проде? → A: TEI остаётся в compose, оператор решает запускать или нет
