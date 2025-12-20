# ТЗ: Planner LLM + Answer LLM для `rag-api-new`

## 1. Цель

Сделать предсказуемый и качественный пайплайн ответов AI-агента:

1) **Planner LLM** анализирует запрос пользователя (и при необходимости короткий контекст диалога), определяет **намерения (intents)** и **сущности (entities)**, формирует **QueryPlan** (строго структурированный JSON).

2) **Executor** исполняет QueryPlan: вызывает нужные инструменты (в первую очередь Graph-RAG, при необходимости классический векторный поиск + BM25), получает **факты/контекст**.

3) **Answer LLM** генерирует финальный ответ **только на основе полученных фактов** + **строгих правил рендера**.

4) **Старое хардкодное планирование полностью удаляется** вместе со связанными зависимостями/кодом.

## 2. Ожидаемый результат

- Уходит “костыльная” логика определения интента по ключевикам.
- Агент перестаёт:
  - добавлять “хвосты” типа «не найдено других упоминаний…»
  - выводить тех. артефакты (confidence, внутренние id, ссылки вида `[1] – …`)
- Агент **всегда перечисляет все релевантные пункты** (в пределах лимитов) — не “топ-1”.
- Ответы становятся стабильными, структурными и “человечными”.

## 3. Термины

- **Planner LLM** — модель, возвращающая *только план*, не пользовательский текст.
- **Answer LLM** — модель, генерирующая финальный ответ пользователю.
- **QueryPlan** — структурированная схема с интентами, сущностями, последовательностью вызова инструментов, лимитами и стилем ответа.
- **FactsPayload** — структурированный результат работы инструментов (Graph-RAG / Chroma fallback).
- **Renderer** — детерминированный форматтер (markdown bullets / short answer / grouped lists).

## 4. Ограничения и принципы

### Архитектурные принципы

- SOLID / DRY / KISS.
- Чёткие границы модулей: `planner` ≠ `executor` ≠ `answer` ≠ `tools` ≠ `rendering`.
- Минимум “магии” и скрытых эвристик.

### Требование пользователя

- **Старое планирование удалить полностью**:
  - код определения интента через литералы/ключевики
  - связанные структуры/модули, которые нужны только для legacy-планирования  
  *(если модуль используется в других местах — оставлять, но вычистить ветки legacy-логики)*

### Источники фактов

- Основная стратегия: **Graph-RAG** (in-memory dict graph).
- Fallback: **ChromaDB semantic RAG** для неструктурных вопросов / при отсутствии сущностей / при неполноте графа.

## 5. Новый пайплайн (LangGraph)

### 5.1. Стадии графа

1) **Input normalization**
   - нормализация пробелов, языка, trim
2) **Memory Gate (follow-up detection)**
   - если сомнительный follow-up → сбросить память и делать независимый поиск
   - если явный follow-up → дать Planner’у краткое summary контекста
3) **Entity Resolution**
   - EntityRegistry v2 с алиасами (например: АЛОР → `alor-broker` и т.п.)
   - выход: список сущностей с `canonical_id`, `type`, `aliases`, `confidence`
4) **Planner LLM → QueryPlan**
   - строгий JSON (валидация)
5) **Execute QueryPlan**
   - последовательные tool calls по плану
   - сбор FactsPayload
6) **Render Facts → Answer Context**
   - нормализация фактов, дедуп, лимиты
   - шаблонные структуры списков
7) **Answer LLM**
   - генерация пользовательского ответа *только на основе Answer Context*
8) **Post-check (optional, deterministic)**
   - sanity check: нет тех. артефактов, нет forbidden фраз, нет confidence/ids
   - если нарушено → повторный рендер/повторный ответ с более строгими constraints

## 6. QueryPlan: контракт Planner LLM

### 6.1. Формат: строго JSON (Pydantic / function calling)

**QueryPlan** (пример структуры):

```json
{
  "intents": ["PROJECT_ACHIEVEMENTS"],
  "entities": [
    {"type": "project", "id": "project:alor-broker", "name": "АЛОР Брокер"}
  ],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "PROJECT_ACHIEVEMENTS", "entity_id": "project:alor-broker"}}
  ],
  "fallback": {
    "enabled": true,
    "tool": "portfolio_search_tool",
    "when": ["NO_RESULTS", "LOW_COVERAGE"]
  },
  "limits": {
    "max_items": 10,
    "max_groups": 4,
    "max_paragraphs": 4
  },
  "render_style": "BULLETS",
  "answer_style": "NATURAL_RU",
  "confidence": 0.86
}
```

### 6.2. Intents (минимальный набор на старт)

- `CURRENT_JOB`
- `PROJECT_DETAILS`
- `PROJECT_ACHIEVEMENTS`
- `PROJECT_TECH_STACK`
- `TECHNOLOGY_USAGE` (где/как применял какую-либо технологию)
- `EXPERIENCE_SUMMARY`
- `TECHNOLOGY_OVERVIEW` (знает/использовал)
- `CONTACTS`
- `GENERAL_UNSTRUCTURED` (вопрос без явных сущностей → Chroma fallback)

> Важно: `intents` — **список**, Planner может назначать несколько интентов.

### 6.3. Правила Planner LLM

Planner обязан:

- Использовать **только** перечисленные intents/tools.
- Всегда возвращать JSON по схеме.
- Если сущность не найдена в EntityRegistry → intent может быть `GENERAL_UNSTRUCTURED` и использовать fallback поиск.
- Проставлять лимиты:
  - технологии: максимум 10–12
  - достижения/буллеты: максимум 8–10
  - длинные описательные блоки: максимум 3–4

### 6.4. Валидация и восстановление

Если QueryPlan:

- невалиден по схеме
- содержит неизвестный tool/intent
- `confidence < threshold` (например 0.5)

то система делает:

1) **вторую попытку** planner-а с сообщением «исправь JSON согласно схеме»
2) если снова плохо → **дефолтный план без legacy-хардкода**:
   - `GENERAL_UNSTRUCTURED`
   - `tool_calls=[portfolio_search_tool]`
   - `render_style=SHORT|BULLETS` по типу ответа

> Это не “старое планирование”, а аварийный минимальный план.

## 7. Инструменты и контракты

### 7.1. `graph_query_tool` (primary)

- Вход: `intent`, `entity_id`
- Выход: `FactsPayload` (items + typed metadata)
- Обязан возвращать данные **без внутренних id в user-facing виде**, id допускаются только в `sources`.

### 7.2. `portfolio_search_tool` (fallback, Chroma)

- Вход: `query`, `filters`, `top_k`, `doc_types`
- Выход: `FactsPayload`

### 7.3. `FactsPayload` (единый контракт)

```json
{
  "found": true,
  "items": [
    {"type": "achievement", "text": "...", "source": {"id": "...", "title": "..."}},
    {"type": "project", "title": "...", "summary": "..."}
  ],
  "groups": [
    {"title": "Проекты с RAG", "items": [...]}
  ],
  "meta": {"coverage": 0.9},
  "sources": [{"id": "project:ai-portfolio", "label": "AI-Portfolio"}]
}
```

## 8. Rendering: шаблонные ответы

### 8.1. Обязательные стили

- `BULLETS` — основной (markdown bullets)
- `GROUPED_BULLETS` — группировка по сущности (например «Проекты → достижения»)
- `SHORT` — короткий ответ (1–3 абзаца)
- `TABLE` (опционально) — только для некоторых сущностей

### 8.2. Запреты в финальном тексте

Answer LLM **не должен**:

- писать «рекомендуется уточнить у Дмитрия»
- писать «конфиденциальность низкая»
- писать «конкретных упоминаний не найдено» если пользователь не спрашивал про отсутствие
- выводить `(confidence: …)` и внутренние id/скобочные ref типа `[1] – …`

### 8.3. Полнота списков

Если вопрос просит перечисление:

- выводить **все найденные элементы** до `limits.max_items`
- не выбирать “топ-1” без причины

Если элементов больше лимита:

- показать первые N + строку «ещё X (по запросу могу вывести)».

## 9. Изменения в коде

### 9.1. Удалить legacy planning

- Удалить модуль/функции keyword-match интента.
- Удалить связанный “планирующий” код, который больше не используется.
- Удалить тесты/конфиги, относящиеся только к legacy планированию.
- Почистить зависимости/импорты.
- Удалить модули/методы, которые теперь не используются

### 9.2. Добавить новые модули

Рекомендуемая структура:

- `agent/planner/`
  - `schemas.py` (Pydantic модели QueryPlan)
  - `planner_llm.py` (вызов LLM + retry/repair)
  - `prompts.py`
- `agent/executor/`
  - `execute_plan.py`
- `agent/answer/`
  - `answer_llm.py`
- `agent/render/`
  - `renderer.py` (детерминированные шаблоны)
- `agent/tools/`
  - `graph_query_tool.py`
  - `portfolio_search_tool.py` (обёртка существующего)
- `agent/graph/`
  - `store.py` (DictGraphStore)
  - `builder.py` (GraphBuilder)
- `agent/memory/`
  - `followup.py` (строгий gate)
  - `summarizer.py` (опционально)

### 9.3. Отрефакторить получившийся код, убрать все лишнее, оптимизировать, убедиться в чистоте кода. 

## 10. Набор тестов и критерии приёмки

### 10.1. Unit

- QueryPlan schema validation
- planner_llm retry/repair
- execute_plan корректно вызывает инструменты по очереди
- renderer:
  - bullets/grouping/limits
  - фильтрация forbidden артефактов (ids/confidence)

### 10.2. Integration / E2E (регресс-набор)

Запросы должны давать стабильные ответы:

- «Где сейчас работает Дмитрий?»
- «Достижения на проекте АЛОР»
- «Где применял RAG?»
- «Какие технологии использовал в AI-Portfolio?»
- «Контакты Дмитрия»
- Follow-up:
  - «Где применял RAG?» → «А какие проекты в Aston?»

**Критерии:**

- Нет тех. мусора (confidence, внутренние ids, `[1] – ...`)
- Нет лишних отрицаний про неупомянутые сущности
- Списки полные (до лимитов), не “топ-1”
- Graph-RAG используется первым для структурных вопросов
- Chroma fallback используется для неструктурных

## 11. План внедрения (эпики)

### Epic 1: Planner LLM + QueryPlan контракт

- схемы + prompt + retry/repair + валидация

### Epic 2: Executor + tool orchestration

- выполнение последовательности инструментов, сбор FactsPayload

### Epic 3: Renderer + запреты/лимиты

- детерминированный markdown bullets/grouping

### Epic 4: Answer LLM (строгие правила)

- генерация ответа только по FactsPayload/RenderContext

### Epic 5: Удаление legacy planning и рефакторинг

- удаление модулей/импортов/веток/тестов/лишних конфигов и флагов(всего, что больше не требуется и является мусором)
- рефакторинг/чистка

## 12. Конфигурация (рекомендуется)

- `PLANNER_MODEL=...`
- `ANSWER_MODEL=...`
- `PLANNER_TEMPERATURE=0.0..0.2`
- `ANSWER_TEMPERATURE=0.2..0.5`
- `PLANNER_MAX_TOKENS=...`
- `PLAN_CONFIDENCE_THRESHOLD=0.5`
- `MAX_TOOL_CALLS=3..5`
