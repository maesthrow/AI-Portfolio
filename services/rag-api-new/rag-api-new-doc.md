# rag-api-new — архитектура и логика сервиса

Документ описывает сервис `services/rag-api-new` (FastAPI + RAG + LangChain/LangGraph): как устроена индексация, поиск (dense + BM25), ранжирование, упаковка контекста, генерация ответа и агент с инструментами и памятью.

---

## 1) Назначение сервиса

`rag-api-new` — backend для ответов “по портфолио” разработчика (профиль, опыт, проекты, технологии, достижения, контакты и т.д.).

Два основных режима:

1) **RAG-ответ (sync)**: endpoint `/api/v1/ask` строит ответ LLM на основе найденного контекста.
2) **Агент (stream)**: endpoint `/api/v1/agent/chat/stream` запускает ReAct-агента, который **обязан** сначала вызвать инструмент (tool) для получения фактов, и только потом формировать ответ.

---

## 2) Компоненты и зависимости

### Внутренние модули (в коде)

- `services/rag-api-new/app/main.py` — FastAPI приложение, CORS, роутеры.
- `services/rag-api-new/app/settings.py` — настройки (env), feature flags, тюнинг качества.
- `services/rag-api-new/app/deps.py` — провайдеры зависимостей: embeddings, Chroma client, vectorstore, reranker, chat LLM, agent.
- `services/rag-api-new/app/indexing/*` — нормализация данных, чанкинг, BM25.
- `services/rag-api-new/app/rag/*` — retrieval (hybrid), query plan, entity extraction, rerank, evidence selection, packer контекста, prompting.
- `services/rag-api-new/app/agent/*` — системные правила агента, инструменты, память v2, детектор follow-up.
- `services/rag-api-new/app/schemas/*` — Pydantic-схемы запросов/ответов.

### Внешние сервисы (типичная схема запуска)

`rag-api-new` напрямую общается с:

- **ChromaDB (HTTP)** — хранит документы и их эмбеддинги, выполняет `similarity_search`.
- **LiteLLM (OpenAI-совместимый API)** — проксирует:
  - `/v1/embeddings` для эмбеддингов,
  - `/v1/chat/completions` для чата (LLM).
- **Reranker (CrossEncoder)** — модель sentence-transformers для переоценки (rerank) кандидатов.

Опционально:
- **GigaChat** — если `chat_model` начинается с `gigachat` (см. `services/rag-api-new/app/deps.py`).

---

## 3) Настройки и feature flags

Настройки описаны в `services/rag-api-new/app/settings.py`.

### Базовые параметры

- `litellm_base_url`, `litellm_api_key` — OpenAI-совместимый endpoint (обычно LiteLLM).
- `chat_model` — алиас чат-модели (через LiteLLM) или `gigachat*`.
- `embedding_model` — алиас модели эмбеддингов (через LiteLLM).
- `reranker_model` — CrossEncoder для rerank (по умолчанию `BAAI/bge-reranker-base`).
- `chroma_host`, `chroma_port`, `chroma_collection` — Chroma подключение.

### Feature flags (качество/эволюция)

- `rag_router_v2` - включает v2-маршрутизацию поиска через `portfolio_search` (intent/entity-aware). В режиме v3 (`planner_llm_v3=true`) `portfolio_search` возвращает retrieval-контекст (без вызова `portfolio_rag_answer`), чтобы финальный ответ генерировал Answer LLM.
- `planner_llm_v3` - включает LLM-планировщик `QueryPlanV2` с post-sanitize (нормализация `entity_id` по EntityRegistry) и расширенными debug-логами: plan JSON, tool calls, answer prompt/контекст; включает self-check retrieval с автоматическим fallback на гибридный поиск при недостаточном контексте.
- `rag_atomic_docs` - при ingest/batch генерирует атомарные документы `type=item` (achievements/tags/bullets/contacts/stats).
- `rag_context_packer_v2` - (deprecated, always enabled) включает упаковщик контекста (`pack_context`).
- `agent_fact_tool` - агент использует `portfolio_search_tool` (структурированный поиск фактов), а не `portfolio_rag_tool` (готовый текстовый RAG-ответ).
- `agent_memory_v2` - включает внешнюю память v2 (follow-up detector + rolling summary), отключая встроенный checkpointer LangGraph.

### Тюнинг

- `rag_list_max_items` — максимум items для списковых ответов.
- `rag_pack_budget_chars` — бюджет символов на “упакованный контекст”.
- `agent_recent_turns` — сколько последних пар (вопрос/ответ) держать в краткой памяти.
- `agent_summary_trigger_turns` — как часто обновлять summary.
- `agent_summary_max_chars` — размер summary.

---

## 4) API и основные сценарии

Роутеры подключены в `services/rag-api-new/app/main.py`.

### Health/Meta

- `GET /healthz` — статус + текущие модели/коллекция.
- `GET /meta` — только `chat_model` / `embedding_model`.

### Ingest

- `POST /api/v1/ingest` — upsert документов (низкоуровневый API).
  - Вход: `IngestRequest` (`services/rag-api-new/app/schemas/ingest.py`).
  - Действия: delete ids → add_texts (Chroma) → add_texts (BM25) → snapshot/save BM25 → очистка entity registry cache.
- `POST /api/v1/ingest/batch` — ingest “портфолио-экспорта” (высокоуровневый API).
  - Вход: `ExportPayload` (`services/rag-api-new/app/schemas/export.py`).
  - Действия: `normalize_export(...)` → `upsert_documents(...)`.

### RAG (без агента)

- `POST /api/v1/ask` — синхронный RAG-ответ.
  - Внутри: `app.rag.core.portfolio_rag_answer(...)`.

### Агент (stream)

- `POST /api/v1/agent/chat/stream` — NDJSON-стриминг ответа агента.
  - Отдаёт `application/x-ndjson`, события:
    - `{"type":"start", ...}`
    - `{"type":"tool_start","tool":"..."}` / `{"type":"tool_end"}`
    - `{"type":"delta","content":"..."}` (части ответа)
    - `{"type":"error","message":"..."}` (если ошибка)
    - `{"type":"end","usage":{...}}`

### Admin

- `DELETE /api/v1/admin/collection` — удалить коллекцию Chroma + сбросить BM25 + очистить кэш сущностей.
- `GET /api/v1/admin/stats` — count + (опционально) распределение по `type` (если документов не слишком много).

---

## 5) Модель данных в векторном хранилище

### Документ (как хранится в Chroma)

Нормализованный документ имеет:

- `id`/`doc_id` — строковый ID (например `project:12`, `experience:3:c1`, `item:achievement:experience_project:10:ab12cd...`).
- `text` — текст, который эмбеддится и участвует в поиске.
- `metadata` — метаданные (тип, ref_id, поля проекта/компании и т.п.).

Генерация `doc_id` и `content_hash` — `services/rag-api-new/app/utils/metadata.py` (`make_doc`, `chunk_doc`).

### Типы документов (`metadata["type"]`)

Основные типы, которые делает normalizer (`services/rag-api-new/app/indexing/normalizer.py`):

- `profile`
- `experience`
- `experience_project`
- `project`
- `technology`
- `publication`
- `focus_area`
- `work_approach`
- `tech_focus`
- `stat`
- `contact`
- `catalog` (агрегации по технологиям/компаниям и т.п.)
- `item` (атомарные факты; см. ниже)

### Атомарные документы `type=item`

Если включён `rag_atomic_docs`, ingest/batch создаёт “атомарные” элементы списков как отдельные документы:

- `item_kind=achievement` — достижения из markdown-буллетов опыта/проектов.
- `item_kind=contact` — контакты.
- `item_kind=stat` — ключевые цифры.
- `item_kind=tech_tag` — теги tech focus.
- `item_kind=focus_bullet` — пункты focus areas.
- `item_kind=work_bullet` — пункты work approach.

У `item`-документов важные поля:

- `item_kind`, `order_index`, `source_field`
- `parent_type`, `parent_id`, `parent_doc_id`
- нормализованные ключи для entity-матчинга: `project_name_key`, `project_slug_key`, `company_name_key`, `company_slug_key`, и т.п.

---

## 6) Индексация (ingest) — как данные попадают в Chroma/BM25

### 6.1 normalize_export (портфолио-экспорт → документы)

`services/rag-api-new/app/indexing/normalizer.py:normalize_export(...)` превращает `ExportPayload` в поток `NormalizedDoc = (doc_id, text, metadata)`.

Ключевые шаги:

1) **Формирование текстов**: для каждого сущностного объекта собирается текст-представление (поля + markdown секции).
2) **Чанкинг**: `split_text` (`services/rag-api-new/app/indexing/chunker.py`) режет длинные блоки на куски до ~`MAX_CHARS=900`.
   - Если чанков несколько — создаются документы `...:c1`, `...:c2`, ... с `metadata.parent_id` и `metadata.part`.
3) **Атомарные item-доки (опционально)**:
   - достижения вытаскиваются из markdown списков `achievements_md` и становятся отдельными `item`-доками;
   - для experience и experience_project есть дедуп: один и тот же буллет не дублируется дважды.
4) **Защита от “mojibake”**: `_fix_text` делает best-effort латин1->utf8, если видит “сломанные” символы.

### 6.2 upsert_documents (загрузка в Chroma + BM25)

`services/rag-api-new/app/routers/ingest.py:upsert_documents(...)`:

1) Выбирает батч-размер эмбеддинга: `embedding_batch_size` (если есть в env) иначе 16.
2) Делает best-effort delete по ID в Chroma и BM25.
3) Добавляет тексты в Chroma: `vs.add_texts(texts, metadatas, ids)` — эмбеддинги считаются через `OpenAIEmbeddings` (`services/rag-api-new/app/deps.py:embeddings`), но фактически уходят в `litellm_base_url`.
4) Добавляет тексты в BM25 (локальный in-memory индекс) и сохраняет снапшот в файл `.bm25.<collection>.pkl` (`services/rag-api-new/app/indexing/persistence.py`).
5) Инвалидирует кэш сущностей: `clear_entity_registry_cache()` — иначе entity registry останется “старым”.

Нюанс: метаданные перед upsert “упрощаются” (`_filter_complex_metadata`) — списки/словари сериализуются в JSON/CSV, чтобы Chroma гарантированно принял значения.

---

## 7) Поиск (retrieval) — dense + BM25, RRF, MMR и расширение по проекту

В v2-режиме основная точка входа: `services/rag-api-new/app/rag/search.py:portfolio_search(...)`.

### 7.1 Query Plan (intent + entities + фильтры + бюджеты)

`services/rag-api-new/app/rag/query_plan.py:build_query_plan(...)` делает:

1) **Intent detection** (эвристики по токенам) → `Intent`:
   - `CONTACTS`, `CURRENT_JOB`, `ACHIEVEMENTS`, `TECHNOLOGIES`, `LANGUAGES`, `PROJECT_DETAILS`, иначе `GENERAL`.
   - Запросы про RAG/LLM/Agents и кейсы вида "где применял <технология>" трактуются как `TECHNOLOGIES` (без отдельного частного intent).
2) **Entity extraction**:
   - строится `EntityRegistry` из всех metadatas в Chroma (`get_entity_registry`, кэшируется),
   - из вопроса выделяются `EntityMatch` по алиасам (проекты/компании/технологии).
3) **Entity policy**:
   - `STRICT` — если ровно 1 проект (или 1 компания), чтобы “не расползаться” по базе,
   - `BOOST` — если несколько сущностей (поднять релевантные, но не отрезать).
4) **Ограничения retrieval**:
   - `allowed_types` (набор типов документов),
   - `item_kinds` (если нужны атомарные `item`),
   - `where` (например `{"category":"language"}` для языков).
5) **Бюджеты**:
   - `k_dense`, `k_bm`, `k_final`, `evidence_k`.
6) **Хинты ответа**:
   - `style_hint` (`LIST`, `ULTRASHORT`, …),
   - `answer_instructions` (доп. инструкции для ответа).

### 7.2 HybridRetriever: dense + BM25 → кандидаты

`services/rag-api-new/app/rag/retrieval.py:HybridRetriever.retrieve(...)`:

1) **Dense**: `Chroma.similarity_search(question, k=k_dense, filter=...)`.
   - Для Chroma v2 есть нюанс формата where: если условий > 1, они оборачиваются в `{"$and":[...]}`
     (см. `_to_chroma_where`), иначе сервер может вернуть ошибку `"Expected where to have exactly one operator"`.
2) **BM25**: `bm25.search(collection, question, k=k_bm)` — лексический поиск по токенам.
3) **RRF merge**: `rrf_merge(dense_ids, bm25_ids)` объединяет два ранжирования.
4) **fetch_by_ids**: документы, которых не было в dense, подтягиваются из Chroma по IDs (через `collection.get(ids=...)`),
   чтобы hybrid merge был стабильным.
5) **Фильтры**:
   - по `allowed_types`,
   - по `where` (часть применяется на клиенте через `_filter_where` для надёжности).
6) **MMR-упорядочивание (упрощённое)**: `mmr_order` дедуплицирует по `(parent_id/doc_id, part)`, чтобы снизить повторы.
7) **expand_by_project**:
   - если в найденных документах есть `project_id`, добавляются похожие `project`/`experience_project` для этих `project_id`,
   - метка `metadata.expanded=True` → позже понижение score в reranker (`*0.8`).
8) Если `strict=True`, фильтры применяются повторно после расширения.

### 7.3 Отдельный “item pass” для списков

`services/rag-api-new/app/rag/search.py:_retrieve_for_plan(...)` делает special-case:

- если план содержит `item_kinds` и допускает `type=item`, сначала retrieval выполняется **только по item-докам**
  с фильтром `{"type":"item","item_kind":{"$in":[...]}}` и (если есть явная сущность) с уточняющими полями
  (`project_slug`, `company_slug`, `*_key`).
- затем отдельно retrieval по “базовым” типам (без `item`),
- результаты merge-ятся без дублей.

Это важно: фильтр `item_kind` нельзя просто “нацепить” на общий retrieval, иначе мы случайно отсечём базовые документы.

---

## 8) Ранжирование и отбор evidence

### 8.1 CrossEncoder rerank

`services/rag-api-new/app/rag/rank.py:rerank(...)`:

- строит пары `[question, doc_text]`,
- прогоняет через `CrossEncoder.predict`,
- сортирует по score по убыванию,
- penalize “expanded” документы (`*0.8`).

Модель задаётся `reranker_model`; устройство (CPU/GPU) выбирается в `services/rag-api-new/app/deps.py:reranker()`.

### 8.2 Entity-aware policy поверх rerank score

`services/rag-api-new/app/rag/evidence.py:apply_entity_policy(...)`:

- `strict`: в пределах `scope_types` оставляет только документы, матчящиеся по сущности (slug/key/name). Если отрезало всё — возвращает исходный список (safe fallback).
- `boost`: умножает score релевантных документов (ограничено по коэффициенту), затем пересортировка.

### 8.3 Evidence selection (diversity + keyword bonus)

`services/rag-api-new/app/rag/evidence.py:select_evidence(...)`:

- извлекает keywords из вопроса (`services/rag-api-new/app/rag/nlp.py:keywords`),
- вводит:
  - **type weight** (например `profile`/`experience` слегка выше),
  - **мягкий бонус** за совпадение keyword в тексте/метаданных,
  - **дедуп** по базовому документу (`parent_id/doc_id/ref_id` + `part`).
- выдаёт top-K “разнообразных” evidence.

### 8.4 Confidence

Уверенность — эвристика по reranker-score и покрытию evidence:

- берётся среднее и максимум score,
- нормализуется (если нужно),
- умножается на coverage (`len(evidence)/k`).

См. `services/rag-api-new/app/rag/search.py:_compute_confidence(...)` и `services/rag-api-new/app/rag/core.py:_compute_confidence(...)`.

---

## 9) Упаковка контекста (context packer)

Контекст — это строка, которая подставляется в промпт LLM в блок “Данные о Дмитрии”.

### 9.1 pack_context (v1)

`services/rag-api-new/app/rag/evidence.py:pack_context(...)`:

- берёт 1-2 предложения из каждого evidence-документа,
- добавляет заголовок вида `[type] title`,
- режет по char_budget (`token_budget * 4`).

### 9.2 pack_context (списки и атомарные item-доки)

`services/rag-api-new/app/rag/evidence.py:pack_context(...)`:

1) Определяет стратегию по вопросу (`_infer_strategy`):
   - `ACHIEVEMENTS`, `CONTACTS`, `STATS`, `TECH_TAGS`, `FOCUS_BULLETS`, `WORK_BULLETS`, иначе `COMPACT`.
2) Для “списочных” стратегий:
   - сначала пытается использовать `type=item` с нужным `item_kind`,
   - группирует (например достижения — по проекту/компании), сортирует детерминированно по `order_index`, дедупит,
   - ограничивает `max_items` и `char_budget`.
3) Для достижений есть fallback: если item-доков нет, пробует извлечь буллеты из секций документов “Достижения:” (`_pack_achievements_from_docs`).
4) Если ничего не получилось — возвращает `pack_context` (v1).

Зачем это нужно:
- списки (контакты/достижения/теги) гораздо стабильнее и точнее отдавать “атомарными” фактами, чем кусками длинных описаний.

---

## 10) Генерация ответа (не агент)

Главная функция: `services/rag-api-new/app/rag/core.py:portfolio_rag_answer(...)`.

### 10.1 v2-режим (по умолчанию)

Если `rag_router_v2=True`:

1) Вызывается `portfolio_search(...)` → `SearchResult(plan, evidence, sources, confidence, ...)`.
2) Если `plan.answer_instructions` задан — он объединяется с `system_prompt` запроса.
3) Строится `system_prompt` через `make_system_prompt(...)` (`services/rag-api-new/app/rag/prompting.py`).
4) Строится `context` через `pack_context` (always enabled).
5) Формируются сообщения:
   - `build_messages_for_answer(system_prompt, question, context, style_hint, confidence)`.
   - Если confidence ниже порога — добавляется “осторожный режим” (коротко, попросить уточнить).
6) LLM вызывается через `chat_llm()` (`services/rag-api-new/app/deps.py:chat_llm`) и выдаёт финальный текст.
7) Ответ возвращается вместе с `sources`, `confidence`, `found`, `model`, `collection`.

Если кандидатов нет — используется `build_messages_when_empty(...)` (“Данных нет, уточните…”).

### 10.2 v1-fallback

Если v2 выключен или упал — используется упрощённый intent routing (`_detect_intent`) + `HybridRetriever` + rerank + evidence selection.

---

## 11) Агент: логика, инструменты, память, follow-up

### 11.1 Как собирается агент (LangGraph/LangChain)

`services/rag-api-new/app/agent/graph.py:build_agent_graph()`:

- системный промпт агента = `make_system_prompt(None)` + набор “жёстких правил”:
  - `AGENT_SYSTEM_PROMPT_FACT` (если `agent_fact_tool=True`)
  - иначе `AGENT_SYSTEM_PROMPT_LEGACY`
- набор tools:
  - fact-режим: `portfolio_search_tool`, `list_projects_tool`
  - legacy-режим: `portfolio_rag_tool`, `list_projects_tool`
- checkpointer:
  - если `agent_memory_v2=True` → `checkpointer=None` (память ведём сами, вне LangGraph),
  - иначе `MemorySaver()` и память хранится внутри графа по `thread_id`.

### 11.2 Инструменты агента (tools)

Определены в `services/rag-api-new/app/agent/agent_tools.py` (файловые tool-обёртки для агента). План-исполнитель использует пакет `services/rag-api-new/app/agent/tools/`.

#### v3: Planner LLM → Executor → Answer LLM

Используется полный пайплайн из `services/rag-api-new/app/agent/rag_tool.py:portfolio_rag_tool`:

1) PlannerLLM строит `QueryPlanV2` (intents/entities/tool_calls).
2) PlanExecutor выполняет tool_calls и собирает `FactsPayload`.
3) AnswerLLM формирует финальный пользовательский ответ по фактам.

Нюансы:
- При гибридном поиске `portfolio_search(...)` может вернуть только `evidence` (упакованный контекст) без `items`; поэтому `services/rag-api-new/app/agent/tools/portfolio_search_tool.py` делает best-effort парсинг `evidence` в `FactItem`, чтобы рендер/ответ не зависели от свободной интерпретации LLM.
- Для intent `technology_usage` AnswerLLM сначала пытается ответить детерминированно из строк вида `Используется в: ...` (и при необходимости «восстанавливается» из evidence, если LLM ошибочно вернул not-found).

#### `portfolio_search_tool(question) -> dict`

В fact-режиме это основной инструмент "получить факты".

Внутри:

- вызывает `services/rag-api-new/app/rag/search.py:portfolio_search`,
- возвращает структурированный результат:
  - `intent`, `entity_policy`, `entities` (project/company/technology),
  - `allowed_types`, `item_kinds`,
  - `confidence`, `found`, `collection`,
  - `items` (атомарные факты из evidence `type=item`),
  - `achievements` (достижения, сгруппированные и дедуплицированные),
  - `evidence_snippets` (короткие выдержки из документов),
  - `sources` (id/title/url/repo/demo),
  - `answer_instructions` (если есть),
  - `ambiguity` (несколько совпавших проектов/компаний).

Ключевой принцип: агент должен “опираться на факты”, а не пересказывать сгенерированный текст.

#### `portfolio_rag_tool(question) -> dict`

Legacy-инструмент, возвращает уже готовый ответ:

- вызывает `services/rag-api-new/app/rag/core.py:portfolio_rag_answer`,
- возвращает `{ok, answer, sources, confidence, ...}`.

#### `list_projects_tool(limit=10) -> str`

Векторный поиск “проекты разработчика” с фильтром `type=project` и выдача списка.

### 11.3 Жёсткие правила агента (анти-галлюцинации)

В `AGENT_SYSTEM_PROMPT_FACT`:

- если вопрос о Дмитрии/проектах/компаниях/технологиях/достижениях/документации — **обязан** сначала вызвать `portfolio_search_tool`.
- финальный ответ строит **только** на основе tool-output (не добавляет фактов “из головы”).
- при `ok=false`/`error` — сообщает о технической ошибке.
- при низкой `confidence` — нейтрально просит уточнить (какой проект/компания/период).
- для списков — отвечает списком, детерминированно.

### 11.4 Streaming endpoint и формат событий

`services/rag-api-new/app/routers/chat.py`:

- запускает `agent_app()` (граф агента),
- стримит события LangChain/LangGraph через `astream_events` (если доступно),
- переводит их в NDJSON:
  - `on_tool_start` → `{"type":"tool_start"}`
  - `on_tool_end` → `{"type":"tool_end"}`
  - `on_chat_model_stream` → `{"type":"delta","content":"..."}`
- собирает usage (если модель отдаёт `usage_metadata`) и возвращает в `end`.

Нюанс: `system_prompt` из `ChatRequest` в streaming-чате добавляется в **текст вопроса** как “Доп. инструкции: ...”, а не как SystemMessage.

### 11.5 Память v2: follow-up + summary (process-local)

Если `agent_memory_v2=True`, память реализована “снаружи” графа:

1) Перед ответом берётся snapshot: `memory_store.snapshot(thread_id, recent_turns=N)`.
2) Строится `FollowUpContext(summary, recent_turns, entity_ids)`.
3) `detect_follow_up(question, ctx)` решает:
   - follow-up -> сохраняем память и подмешиваем её в `messages`,
   - не follow-up -> `memory_store.reset(thread_id)` и начинаем “с чистого листа”.
4) После ответа `memory_store.record_turn(...)`:
   - сохраняет turn,
   - накапливает pending_turns,
   - когда pending_turns >= `agent_summary_trigger_turns` — возвращает `SummaryJob`.
5) SummaryJob выполняется в background task:
   - `generate_summary(llm, previous_summary, turns)` просит LLM обновить короткое summary (русский, без упоминания tool/reasoning).
   - `apply_summary(job, summary)` обновляет summary и удаляет обработанные pending turns.

Хранилище памяти: `services/rag-api-new/app/agent/memory.py` — LRU по session_id, полностью в памяти процесса.

### 11.6 Детектор follow-up

`services/rag-api-new/app/agent/followup.py:detect_follow_up(...)`:

- Отсекает:
  - пустой вопрос,
  - отсутствие истории,
  - приветствия,
  - явный reset (“забудь”, “новая тема”, “start over”…).
- Считает score по эвристикам:
  - overlap по сущностям (entity ids) с прошлым контекстом,
  - фразы-коннекторы ("а ещё...", "тогда...") и местоименные ссылки ("там/это/он/она/про это..."),
  - короткость вопроса,
  - “недосказанность с тематическим словом” (например “какие достижения?”, если уже есть entity_ids),
  - штраф для self-contained тем (если нет entity_ids).
- Если score >= threshold (по умолчанию 1.6) -> считаем follow-up.

Entity ids для этого детектора извлекаются best-effort через `app.rag.entities` (если Chroma недоступна — detector деградирует в чисто лексический режим).

---

## 12) Кэширование и ограничения (важные нюансы эксплуатации)

### Кэши

- `settings()`, `embeddings()`, `chroma_client()`, `reranker()`, `chat_llm()` — `lru_cache` в `services/rag-api-new/app/deps.py`.
- `get_entity_registry(collection)` — `lru_cache` в `services/rag-api-new/app/rag/entities.py`.
  - обязательно чистить после ingest (`clear_entity_registry_cache`).
- `memory_store` и `bm25` — **process-local** (не шарятся между воркерами/репликами).

### Ограничения

- **BM25**:
  - индекс живёт в памяти процесса;
  - снапшот сохраняется в `.bm25.<collection>.pkl`, но загрузка делается только при ingest (`bm25_try_load`);
  - после рестарта без ingest BM25-часть может быть пустой (dense всё равно работает).
- **Память агента v2**:
  - хранится в памяти процесса, не переживает рестарт;
  - при `uvicorn --workers > 1` разные воркеры не делят историю диалога.
- **Сеть/модели**:
  - reranker CrossEncoder может требовать скачивания весов (если нет кэша моделей).

---

## 13) “Сквозные” последовательности (как это работает end-to-end)

### 13.1 Загрузка данных (ingest/batch)

1) Клиент отправляет `ExportPayload` → `POST /api/v1/ingest/batch`.
2) `normalize_export(...)` генерирует документы (включая `item`, если включено).
3) `upsert_documents(...)` кладёт всё в Chroma + обновляет BM25.
4) Чистится кэш registry сущностей.

### 13.2 Обычный RAG-ответ (`/ask`)

1) `portfolio_rag_answer` вызывает `portfolio_search`.
2) Retrieval: dense+BM25 → RRF → fetch_by_ids → MMR → expand_by_project.
3) Rerank CrossEncoder → entity policy → evidence selection → confidence.
4) Context packer v2 (если включён) делает “правильный формат” для списков.
5) LLM отвечает строго по данным из контекста.

### 13.3 Агентный чат (`/agent/chat/stream`)

1) По `session_id` берётся snapshot памяти.
2) `detect_follow_up` решает: продолжение темы или reset.
3) Агент получает messages (summary + последние turns + текущий вопрос).
4) Агент вызывает обязательный tool (`portfolio_search_tool`), получает факты.
5) Агент формирует ответ, стримит токены.
6) Память обновляется, summary (при необходимости) считается асинхронно.
