# Backlog: улучшение качества ответов агента `rag-api-new`

Цель: повысить качество и стабильность ответов (меньше “шума/хвостов”, меньше путаницы, полнота по спискам/достижениям) **без ломки текущего API/стрима**, с безопасным rollout через фичефлаги и fallback на текущую логику.

## Принципы внедрения

- Все изменения включаются фичефлагами в `services/rag-api-new/app/settings.py` (по умолчанию `false`).
- Новый путь всегда имеет fallback на текущий (пусто/ошибка/низкая уверенность).
- Любые изменения нормализации/типов документов требуют реиндекса:
  - `DELETE /api/v1/admin/collection`
  - `POST /api/v1/ingest/batch`

## Epic A — Intent‑aware + entity‑aware retrieval (точнее “попадать” в нужные документы)

### PR‑01 — Feature flags + параметры качества (низкий риск)

**Scope**
- Добавить фичефлаги и параметры, чтобы разворачивать улучшения поэтапно и безопасно.

**Файлы**
- `services/rag-api-new/app/settings.py`

**Задачи**
- [ ] Добавить флаги:
  - [ ] `RAG_ROUTER_V2`
  - [ ] `RAG_ATOMIC_DOCS`
  - [ ] `RAG_CONTEXT_PACKER_V2`
  - [ ] `AGENT_FACT_TOOL`
  - [ ] `AGENT_MEMORY_V2`
- [ ] Добавить параметры:
  - [ ] `RAG_LIST_MAX_ITEMS` (например, 12–20)
  - [ ] `RAG_PACK_BUDGET_CHARS` (например, 3600–5000)
  - [ ] `AGENT_RECENT_TURNS` (например, 2–3)
  - [ ] `AGENT_SUMMARY_TRIGGER_TURNS` (например, 6)
  - [ ] `AGENT_SUMMARY_MAX_CHARS` (например, 1200)

**Acceptance**
- [ ] При выключенных флагах поведение не меняется.
- [ ] `python -m compileall -q services/rag-api-new/app` проходит.

---

### PR‑04 — Router/Search v2: Intent + Entity + QueryPlan (средний риск, сильный эффект)

**Prereq**
- PR‑01

**Scope**
- Ввести слой `portfolio_search()` с планированием запроса (intent/entities), ограничениями типов документов и entity‑aware бустингом/фильтрацией.

**Файлы (новые)**
- `services/rag-api-new/app/rag/query_plan.py` (Intent/Entity/QueryPlan)
- `services/rag-api-new/app/rag/entities.py` (Entity extraction + registry)
- `services/rag-api-new/app/rag/search.py` (portfolio_search)

**Файлы (правки)**
- `services/rag-api-new/app/rag/core.py` (перевести /ask на search→answer с fallback)
- `services/rag-api-new/app/rag/retrieval.py` (гибридный retrieval: фильтрация/приоритизация под plan)
- `services/rag-api-new/app/rag/evidence.py` (entity‑bonus, при необходимости строгий фильтр)

**Задачи**
- [ ] Реализовать `Intent`: `ACHIEVEMENTS`, `CURRENT_JOB`, `LANGUAGES`, `RAG_USAGE`, `CONTACTS`, `PROJECT_DETAILS`, `GENERAL`.
- [ ] Реализовать `QueryPlan`:
  - [ ] `allowed_types`, `k_dense/k_bm/k_final`
  - [ ] `entity_policy` (`strict|boost|none`)
  - [ ] `packing_strategy` (см. PR‑03)
  - [ ] `min_confidence_for_answer` / fallback критерии
- [ ] Entity extraction:
  - [ ] проект: `name/slug` (включая короткие сущности типа `t2`)
  - [ ] компания: `company_name/company_slug`
  - [ ] технология: `tech name` (нормализованный ключ)
- [ ] Entity registry:
  - [ ] построение словаря алиасов по метаданным Chroma (кешировать)
  - [ ] логика disambiguation: 1 кандидат → strict, много → boost
- [ ] `portfolio_search()`:
  - [ ] строит plan
  - [ ] выполняет retrieval по plan
  - [ ] возвращает структурированный `SearchResult` (sources/confidence/evidence/items при наличии)
- [ ] Включение только при `RAG_ROUTER_V2=true`, иначе текущая логика.

**Acceptance (manual)**
- [ ] `где сейчас работает Дмитрий?` стабильно использует `profile/experience`.
- [ ] `где применял RAG?` не добавляет “не найдено в X”, если X не упоминали.
- [ ] `какие языки программирования знает?` не называет фреймворки “языками” (минимум: не смешивать “язык/фреймворк”).

---

## Epic B — Универсальная индексация списков/вложенных сущностей (атомарные факты)

### PR‑02 — Atomic docs: универсальные item‑документы (средний риск, требует реиндекса)

**Prereq**
- PR‑01

**Scope**
- Генерировать атомарные документы `type=item` для вложенных перечислений/списков (не только achievements).

**Файлы**
- `services/rag-api-new/app/indexing/normalizer.py`
- `services/rag-api-new/app/utils/metadata.py`
- `services/rag-api-new/app/routers/ingest_batch.py`

**Задачи**
- [ ] Добавить универсальный item‑extractor:
  - [ ] Markdown bullets (`-`, `•`, `—`, нумерованные списки)
  - [ ] списки объектов (`bullets/tags`)
  - [ ] key/value (`stats/contacts`)
- [ ] Генерация item‑доков:
  - [ ] `item_kind=achievement` из `experience.achievements_md` и `experience_project.achievements_md`
  - [ ] `item_kind=focus_bullet` из `focus_areas.bullets`
  - [ ] `item_kind=work_bullet` из `work_approaches.bullets`
  - [ ] `item_kind=tech_tag` из `tech_focus.tags`
  - [ ] `item_kind=stat` из `stats`
  - [ ] `item_kind=contact` из `contacts`
- [ ] Метаданные item‑доков:
  - [ ] `parent_type/parent_id/parent_doc_id`
  - [ ] entity‑поля + `*_key` для фильтрации/бустинга
  - [ ] `order_index`, `source_field`
- [ ] Стабильный `doc_id` для item‑доков (детерминированный).
- [ ] Включение только при `RAG_ATOMIC_DOCS=true`.

**Acceptance**
- [ ] После реиндекса `GET /api/v1/admin/stats` показывает `by_type.item`.
- [ ] Вопросы “про достижения” после реиндекса стабильно находят пункты (без “то есть/то нет”).

---

## Epic C — Контекст‑пэкинг под формат вопроса (не терять пункты)

### PR‑03 — Context packer v2 (средний риск, сильный эффект на полноту)

**Prereq**
- PR‑01 + PR‑02 (желательно, чтобы были item‑доки)

**Scope**
- Упаковывать контекст по стратегии: для списков отдавать пункты (items/sections), для остальных — компактно.

**Файлы**
- `services/rag-api-new/app/rag/context.py` (новый)
- `services/rag-api-new/app/rag/core.py` (подключение packer по plan)

**Задачи**
- [ ] Стратегии:
  - [ ] `COMPACT` (как сейчас)
  - [ ] `LIST_AWARE` (если есть `type=item`)
  - [ ] `ACHIEVEMENTS` (группировать по проекту/компании, лимиты по `RAG_LIST_MAX_ITEMS`)
  - [ ] `CONTACTS/STATS/TECH_TAGS` (детерминированный рендер из items)
- [ ] Бюджеты (chars/items/groups) через настройки.
- [ ] Включение только при `RAG_CONTEXT_PACKER_V2=true`.

**Acceptance**
- [ ] “достижения t2/АЛОР/F3/СКИО” возвращают все пункты (до лимита), не только первый.
- [ ] Для обычных вопросов ответы не становятся заметно длиннее/шумнее.

---

## Epic D — Развести “поиск фактов” и “генерацию” (агент не должен пересказывать пересказ)

### PR‑05 — Новый tool: `portfolio_search_tool` + правила ответа по фактам (низко‑средний риск)

**Prereq**
- PR‑04 (search слой)

**Scope**
- Добавить агенту инструмент, возвращающий структурированные факты (items/evidence/sources/confidence), а не готовый текст.

**Файлы**
- `services/rag-api-new/app/agent/tools.py`
- `services/rag-api-new/app/agent/graph.py`
- `services/rag-api-new/app/rag/search.py`

**Задачи**
- [ ] Реализовать `portfolio_search_tool(question)->dict`:
  - [ ] `intent`, `entities`
  - [ ] `items` (если есть)
  - [ ] `evidence_snippets` (коротко)
  - [ ] `sources`, `confidence`, `found`
- [ ] Оставить `portfolio_rag_tool` как legacy.
- [ ] Обновить промпт агента:
  - [ ] отвечать только по tool‑output
  - [ ] запрет “не найдено в X”, если X не упомянуто пользователем
  - [ ] для списков — выводить items (не обобщать)
- [ ] Включение через `AGENT_FACT_TOOL=true`.

**Acceptance**
- [ ] Агент перестаёт добавлять “лишние хвосты” (про неупомянутые сущности).
- [ ] Полнота списков сохраняется (пункты не теряются при “пересказе”).

---

## Epic E — Память диалога без “хвостов” (summary memory + follow-up)

### PR‑06 — Memory v2: follow‑up detector + summary (средний риск)

**Prereq**
- PR‑05 (желательно), PR‑01

**Scope**
- Уменьшить нерелевантные влияния истории: автономные вопросы не должны тянуть прошлые темы; follow‑up вопросы должны работать.

**Файлы (новые)**
- `services/rag-api-new/app/agent/followup.py`
- `services/rag-api-new/app/agent/memory.py`

**Файлы (правки)**
- `services/rag-api-new/app/routers/chat.py`

**Задачи**
- [ ] Follow‑up detector (детерминированный) + entity‑aware:
  - [ ] если вопрос не follow‑up → отвечать как “новый контекст” (не подмешивать историю/summary)
  - [ ] если follow‑up → подмешивать summary + последние N реплик
- [ ] Summary memory:
  - [ ] хранить `summary` + `recent_turns` (N из настроек)
  - [ ] обновлять summary после `AGENT_SUMMARY_TRIGGER_TURNS`
  - [ ] summary ограничить по `AGENT_SUMMARY_MAX_CHARS`
- [ ] Включение через `AGENT_MEMORY_V2=true`.

**Acceptance**
- [ ] “Опыт с Python” → “Где применял RAG?” не добавляет нерелевантные проекты/опровержения.
- [ ] Follow‑up (“а там какие достижения?”) продолжает работать корректно.

---

## Быстрый регресс‑чеклист (после каждого PR)

- [ ] `python -m compileall -q services/rag-api-new/app`
- [ ] Manual (после PR‑02/03/04/05/06 — с реиндексом):
  - [ ] `привет`
  - [ ] `кто ты`
  - [ ] `где сейчас работает Дмитрий?`
  - [ ] `какие достижения на проекте t2 / АЛОР / F3 TAIL / СКИО`
  - [ ] `какие языки программирования знает?`
  - [ ] `где применял RAG?`

