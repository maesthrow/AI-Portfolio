# Implementation Plan: Fix Project List Query

**Branch**: `002-fix-project-list-query` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-fix-project-list-query/spec.md`

## Summary

Добавить новый граф-хендлер `_list_projects_query()` для перечисления проектов с фильтрами (kind, tech_category, technology, domain). Добавить intent `PROJECT_LIST` в три enum'а (Intent, IntentV2, IntentV3). Обновить промпт планнера: заменить конфликтующие примеры, добавить семантическое правило разграничения с `technology_usage`. Прокинуть новые параметры `kind`/`domain` через executor → graph_query_tool → query.py. Добавить детерминированный ответ для `project_list` в AnswerLLM. Вынести общую логику фильтрации по tech_category в хелпер, чтобы избежать дублирования с `_projects_by_tech_category_query()`.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: LangGraph 1.x, LangChain 1.x, FastAPI
**Storage**: PostgreSQL 16 + pgvector (knowledge graph — in-memory)
**Testing**: pytest (existing tests in `services/rag-api-new/tests/`)
**Target Platform**: Linux Docker container
**Project Type**: Web service (RAG API microservice)
**Performance Goals**: Без регрессии латентности (~0ms для in-memory графа)
**Constraints**: Граф в памяти, пересоздаётся при каждом ingest. ~7 проектов, ~50 technology-нод.
**Scale/Scope**: Изменения только в `services/rag-api-new/`, 10 файлов модифицируются + 1 новый тест

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | Изменения в существующих Python-файлах, без новых текстовых файлов с кириллицей |
| II. Root-Cause Resolution | PASS | Исправляем корневую причину: отсутствие граф-хендлера для листинга + некорректная маршрутизация планнера |
| III. Clean Architecture | PASS | Общая логика tech_category вынесена в хелпер (DRY). Новый хендлер следует паттерну существующих |
| IV. Service Directory Discipline | PASS | Все изменения в `services/rag-api-new/` (активный сервис) |
| V. API Versioning & Contracts | PASS | Без новых HTTP-эндпоинтов; только внутренние граф-запросы |
| VI. Database Migration Discipline | N/A | Без изменений SQLAlchemy-моделей |
| VII. Simplicity & YAGNI | PASS | Минимальные изменения: 1 хендлер, 1 хелпер, 1 intent, обновление промпта. Никаких спекулятивных фич |

## Project Structure

### Documentation (this feature)

```text
specs/002-fix-project-list-query/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (files to modify)

```text
services/rag-api-new/app/
├── rag/
│   └── search_types.py              # [M] Add PROJECT_LIST to legacy Intent enum
├── graph/
│   └── query.py                     # [M] Add _list_projects_query(), helper, register
├── agent/
│   ├── planner/
│   │   ├── schemas_v3.py            # [M] Add PROJECT_LIST to IntentV3 enum
│   │   ├── schemas.py               # [M] Add PROJECT_LIST to IntentV2 enum
│   │   └── prompts.py               # [M] REPLACE + ADD examples, ADD semantic rule
│   ├── executor/
│   │   └── execute_plan.py          # [M] Extract and pass kind/domain from tool_call.args
│   ├── tools/
│   │   └── graph_query_tool.py      # [M] Add PROJECT_LIST to _INTENT_MAPPING, accept kind/domain
│   └── answer/
│       ├── answer_llm.py            # [M] Add deterministic path for project_list
│       └── prompts.py               # [M] Add project_list to NOT_FOUND_BY_INTENT
│   └── render/
│       └── renderer.py              # [M] Add project_list to _get_group_title()
└── tests/
    └── test_project_list.py         # [N] New test file
```

**Legend**: [M] = Modified, [N] = New

**Structure Decision**: Все изменения в существующей структуре `services/rag-api-new/app/`. Новых директорий нет. Единственный новый файл — тест.

## Design

### Change 1: Add `PROJECT_LIST` to all three Intent enums

Три enum'а нужно держать в синхроне — это штатный паттерн проекта для обратной совместимости.

**File: `app/rag/search_types.py`** — Legacy Intent enum (line ~24, перед GENERAL):
```python
PROJECT_LIST = "project_list"
```

**File: `app/agent/planner/schemas_v3.py`** — IntentV3 enum (line ~67, перед GENERAL_UNSTRUCTURED):
```python
PROJECT_LIST = "project_list"
```

**File: `app/agent/planner/schemas.py`** — IntentV2 enum (line ~29, перед GENERAL_UNSTRUCTURED):
```python
PROJECT_LIST = "project_list"
```

### Change 2: New `_list_projects_query()` + shared helper

**File: `app/graph/query.py`**

#### 2a. Extract shared helper `_collect_projects_by_tech_category()`

Вынести общую логику из `_projects_by_tech_category_query()` (строки 820-864) в переиспользуемый хелпер. Хелпер принимает список PROJECT-нод и категорию, возвращает отфильтрованный список с привязанными технологиями.

```python
def _collect_projects_by_tech_category(
    projects: list[GraphNode],
    category: str,
) -> list[tuple[GraphNode, list[str]]]:
    """
    Отфильтровать проекты по категории технологий.

    Для каждого проекта проверяет USES-рёбра к TECHNOLOGY-нодам
    с matching category. Возвращает пары (project, [tech_names]).

    Args:
        projects: Список PROJECT-нод для фильтрации
        category: Категория технологий (ml_framework, language, etc.)

    Returns:
        Список кортежей (project_node, matching_tech_names),
        отсортированный по количеству совпавших технологий (desc)
    """
    store = get_graph_store()
    category_lower = category.lower()

    # 1. Собрать все технологии нужной категории
    all_techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
    category_tech_ids = {
        t.id: t.name for t in all_techs
        if (t.data.get("category") or "").lower() == category_lower
    }

    if not category_tech_ids:
        return []

    # 2. Для каждого проекта найти пересечение с category_tech_ids через USES
    result = []
    for project in projects:
        uses_edges = store.get_outgoing_edges(project.id, EdgeType.USES)
        matched_techs = [
            category_tech_ids[e.target_id]
            for e in uses_edges
            if e.target_id in category_tech_ids
        ]
        if matched_techs:
            result.append((project, matched_techs))

    # Сортировка: больше совпавших технологий → выше
    result.sort(key=lambda x: len(x[1]), reverse=True)
    return result
```

#### 2b. Refactor `_projects_by_tech_category_query()` to use the helper

Заменить строки 820-864 существующей функции на вызов хелпера. Остальная логика (формирование items, sources, логирование) остаётся как есть.

**Было** (строки 820-893):
```python
# 1. Get all technologies in this category
techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
category_lower = category.lower()
filtered_techs = [...]
# ... 70 lines of filtering logic ...
projects_sorted = sorted(...)
```

**Стало**:
```python
all_projects = store.get_nodes_by_type(NodeType.PROJECT)
matched = _collect_projects_by_tech_category(all_projects, category)

if not matched:
    # ... existing empty result handling ...

# 3. Build result items (existing code continues from here)
top_projects = matched[:limit]
items = []
for project, techs_used in top_projects:
    # ... existing item building logic (lines 897-928) ...
```

Логика формирования items и text остаётся идентичной. Рефакторинг затрагивает ТОЛЬКО механизм фильтрации.

#### 2c. New function `_list_projects_query()`

```python
def _list_projects_query(
    entity_key: str | None = None,
    *,
    kind: str | None = None,           # "personal" | "commercial"
    tech_category: str | None = None,   # e.g. "ml_framework"
    domain: str | None = None,          # e.g. "Web AI"
) -> GraphQueryResult:
    """
    Перечисление проектов с опциональными фильтрами.

    Возвращает ВСЕ проекты, отфильтрованные по:
    - kind: personal (company_name is None) / commercial (company_name is not None)
    - tech_category: проекты, использующие технологии из категории (через хелпер)
    - domain: проекты с совпадающим доменом (case-insensitive partial match)

    Args:
        entity_key: Не используется для project_list (зарезервирован для совместимости)
        kind: Фильтр по типу: "personal" или "commercial"
        tech_category: Фильтр по категории технологий
        domain: Фильтр по домену проекта
    """
    store = get_graph_store()
    projects = store.get_nodes_by_type(NodeType.PROJECT)

    # === Filter by kind ===
    if kind == "personal":
        projects = [p for p in projects if not p.data.get("company_name")]
    elif kind == "commercial":
        projects = [p for p in projects if p.data.get("company_name")]

    # === Filter by domain ===
    if domain:
        domain_lower = domain.lower()
        projects = [
            p for p in projects
            if domain_lower in (p.data.get("domain") or "").lower()
        ]

    # === Filter by tech_category (через shared helper) ===
    if tech_category:
        matched = _collect_projects_by_tech_category(projects, tech_category)
        # Преобразуем обратно в список проектов (сохраняем порядок)
        projects = [project for project, _ in matched]

    # === Build items ===
    items = []
    for p in projects:
        company_name = p.data.get("company_name")
        derived_kind = "commercial" if company_name else "personal"

        # Собираем технологии из data["technologies"] и USES edges
        tech_names = list(p.data.get("technologies") or [])
        uses_edges = store.get_outgoing_edges(p.id, EdgeType.USES)
        for edge in uses_edges:
            tech_node = store.get_node(edge.target_id)
            if tech_node and tech_node.name not in tech_names:
                tech_names.append(tech_node.name)

        # Формируем текст
        kind_label = "коммерческий" if company_name else "личный проект"
        if company_name:
            kind_label = f"коммерческий, {company_name}"
        desc = p.data.get("description_md") or ""
        tech_str = ", ".join(tech_names[:5])
        if len(tech_names) > 5:
            tech_str += f" и ещё {len(tech_names) - 5}"

        items.append({
            "name": p.name,
            "slug": p.slug,
            "description": desc,
            "technologies": tech_names,
            "period": p.data.get("period"),
            "company_name": company_name,
            "domain": p.data.get("domain"),
            "repo_url": p.data.get("repo_url"),
            "demo_url": p.data.get("demo_url"),
            "kind": derived_kind,
            "text": f"{p.name} ({kind_label}) — {desc[:120]}{'...' if len(desc) > 120 else ''}",
        })

    sources = [_node_to_source(p) for p in projects[:10]]

    logger.info(
        "list_projects: kind=%s tech_category=%s domain=%s → %d projects",
        kind, tech_category, domain, len(items),
    )

    return GraphQueryResult(
        items=items,
        found=bool(items),
        sources=sources,
        confidence=1.0 if items else 0.0,
        intent=Intent.PROJECT_LIST,
        entity_key=entity_key,
    )
```

#### 2d. Register in handlers dict and `graph_query_with_filters()`

**In `handlers` dict** (line ~653):
```python
Intent.PROJECT_LIST: lambda: _list_projects_query(entity_key),
```

**In `graph_query_with_filters()`** — добавить ДО существующих проверок (после строки 697, перед TECHNOLOGIES check):
```python
if intent == Intent.PROJECT_LIST:
    return _list_projects_query(
        entity_key,
        kind=kind,
        tech_category=tech_category,
        domain=domain,
    )
```

Сигнатура `graph_query_with_filters()` расширяется двумя параметрами:
```python
def graph_query_with_filters(
    intent: Intent,
    entity_key: str | None = None,
    tech_category: str | None = None,
    company_key: str | None = None,
    project_key: str | None = None,
    kind: str | None = None,       # NEW
    domain: str | None = None,     # NEW
    limit: int = 20,
) -> GraphQueryResult:
```

### Change 3: Pass `kind`/`domain` through the tool pipeline

#### 3a. `execute_plan.py` — extract new args from tool_call

**File: `app/agent/executor/execute_plan.py`** (lines 230-240)

Добавить извлечение `kind` и `domain` из `tool_call.args` и передачу в `execute_graph_query()`:

```python
if tool_call.tool == "graph_query_tool":
    intent = tool_call.args.get("intent", "general")
    entity_id = tool_call.args.get("entity_id")
    tech_category = tool_call.args.get("tech_category")
    kind = tool_call.args.get("kind")           # NEW
    domain = tool_call.args.get("domain")        # NEW

    facts, sources, found, confidence = execute_graph_query(
        intent=intent,
        entity_id=entity_id,
        tech_category=tech_category,
        kind=kind,                               # NEW
        domain=domain,                           # NEW
    )
    return facts, sources, found, confidence, ""
```

#### 3b. `graph_query_tool.py` — accept and pass new params

**File: `app/agent/tools/graph_query_tool.py`**

1. Добавить в `_INTENT_MAPPING` (line ~28):
```python
IntentV2.PROJECT_LIST: "project_list",
```

2. Расширить сигнатуру `execute_graph_query()`:
```python
def execute_graph_query(
    intent: str,
    entity_id: str | None = None,
    tech_category: str | None = None,
    scope: str | None = None,
    company_id: str | None = None,
    project_id: str | None = None,
    kind: str | None = None,       # NEW
    domain: str | None = None,     # NEW
    limit: int = 20,
) -> tuple[list[FactItem], list[dict[str, Any]], bool, float]:
```

3. Расширить условие вызова `graph_query_with_filters()` (line ~106):
```python
if tech_category or company_key or project_key or kind or domain:
    result = graph_query_with_filters(
        intent=intent_enum,
        entity_key=entity_key,
        tech_category=tech_category,
        company_key=company_key,
        project_key=project_key,
        kind=kind,         # NEW
        domain=domain,     # NEW
        limit=limit,
    )
```

### Change 4: Planner prompt update (CRITICAL — resolves D2 and D3)

**File: `app/agent/planner/prompts.py`**

#### 4a. Add intent description (в секцию ДОСТУПНЫЕ ИНТЕНТЫ, line ~20)

Добавить ПЕРЕД `general_unstructured`:
```
- project_list - перечисление проектов с опциональными фильтрами (личные/коммерческие, по технологии, по домену). НЕ для деталей конкретного проекта — для этого project_details
```

Уточнить описание `project_details`:
```
- project_details - детали КОНКРЕТНОГО проекта по имени/slug. Только с entity_id формата "project:<slug>". Никогда с "person:<slug>"
```

#### 4b. Add semantic disambiguation rule (в секцию ПРАВИЛА ПЛАНИРОВАНИЯ, после правила 6)

```
7. РАЗГРАНИЧЕНИЕ project_list vs technology_usage:
   - "Какие проекты с LLM?" / "ML проекты" / "проекты с PostgreSQL" → project_list + tech_category
     (фокус: ПЕРЕЧИСЛИТЬ ПРОЕКТЫ, отфильтрованные по технологии)
   - "Где применялся RAG?" / "В каких проектах используется Python?" → technology_usage + entity_id
     (фокус: ИСПОЛЬЗОВАНИЕ КОНКРЕТНОЙ ТЕХНОЛОГИИ — где и как)
   - Ключевое отличие: "проекты с/по/используя X" → project_list; "где/как применялся X" → technology_usage
```

#### 4c. Add graph_query_tool args description

Добавить в описание `graph_query_tool` args (line ~24):
```
   args: {"intent": "<intent>", "entity_id": "<entity_id>", "tech_category": "<category>", "kind": "<personal|commercial>", "domain": "<domain>"}

   kind - ОБЯЗАТЕЛЬНО для project_list когда пользователь уточняет тип:
   - "personal" - личные проекты (без привязки к компании)
   - "commercial" - коммерческие проекты (при компании)
```

#### 4d. REPLACE existing "Какие у тебя есть проекты?" example (lines 178-191)

**УДАЛИТЬ** старый пример и **ЗАМЕНИТЬ** на:
```
Вопрос: "Какие у тебя есть проекты?"
{
  "intents": ["project_list"],
  "entities": [],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "project_list"}}
  ],
  "render_style": "grouped_bullets",
  "answer_style": "natural_ru",
  "confidence": 0.9
}
```

#### 4e. REPLACE existing "ML проекты" example (lines 239-252)

**УДАЛИТЬ** старый пример (использовал `technology_usage`) и **ЗАМЕНИТЬ** на:
```
Вопрос: "ML проекты" / "AI-проекты"
{
  "intents": ["project_list"],
  "entities": [],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "project_list", "tech_category": "ml_framework"}}
  ],
  "render_style": "grouped_bullets",
  "answer_style": "natural_ru",
  "confidence": 0.85
}
```

#### 4f. ADD new examples for filtered project listing

```
Вопрос: "Какие есть личные проекты?"
{
  "intents": ["project_list"],
  "entities": [],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "project_list", "kind": "personal"}}
  ],
  "render_style": "grouped_bullets",
  "answer_style": "natural_ru",
  "confidence": 0.9
}

Вопрос: "Коммерческие проекты"
{
  "intents": ["project_list"],
  "entities": [],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "project_list", "kind": "commercial"}}
  ],
  "render_style": "grouped_bullets",
  "answer_style": "natural_ru",
  "confidence": 0.9
}

Вопрос: "Какие есть проекты с LLM?"
{
  "intents": ["project_list"],
  "entities": [],
  "tool_calls": [
    {"tool": "graph_query_tool", "args": {"intent": "project_list", "tech_category": "ml_framework"}}
  ],
  "render_style": "grouped_bullets",
  "answer_style": "natural_ru",
  "confidence": 0.85
}
```

### Change 5: Deterministic answer for `project_list`

#### 5a. `answer_llm.py` — add deterministic path

**File: `app/agent/answer/answer_llm.py`**

В методе `_try_deterministic_answer()` (line ~214), добавить ПЕРЕД `return None`:
```python
if intents == ["project_list"] or "project_list" in intents:
    return self._answer_project_list(facts=payload.items)
```

Новый метод:
```python
def _answer_project_list(self, facts: list) -> str | None:
    """Детерминированная генерация ответа для списка проектов."""
    if not facts:
        return None
    preamble = "Проекты:" if len(facts) > 1 else ""
    return self._deterministic_render(facts, preamble=preamble)
```

**Зачем**: Граф возвращает уже отфильтрованные проекты. Детерминированный рендеринг гарантирует, что ответ содержит ТОЛЬКО факты из графа — нет риска галлюцинаций LLM (например, добавления F3 TAIL в ответ про LLM-проекты).

#### 5b. `answer/prompts.py` — add not-found message

**File: `app/agent/answer/prompts.py`** (line ~80)

Добавить в `NOT_FOUND_BY_INTENT`:
```python
"project_list": "Проектов, соответствующих запросу, не найдено.",
```

### Change 6: Renderer group title for `project_list`

**File: `app/agent/render/renderer.py`** — метод `_get_group_title()` (line ~295)

Без этого изменения `"project_list".title()` → `"Project_List"` появляется как заголовок группы в `grouped_bullets` стиле (fallback Python `.title()` на строке 305). Добавить 1 строку в dict `titles`:

```python
titles = {
    "achievement": "Достижения",
    "technology": "Технологии",
    "technology_usage": "Проекты",
    "project": "Проекты",
    "project_list": "Проекты",          # NEW
    "experience": "Опыт",
    "contact": "Контакты",
    "text": "Информация",
    "document": "Документы",
}
```

**Зачем**: Детерминированный путь (`_answer_project_list`) форсирует `RenderStyle.BULLETS`, поэтому `grouped_bullets` в норме не задействуется для `project_list`. Однако если LLM-путь всё же сработает (например, при пустом списке + evidence из RAG), заголовок группы отобразится корректно — "Проекты", а не "Project_List".

### What is NOT changed

- `_project_details_query()` — не трогаем, работает для деталей одного проекта по slug
- `_projects_by_tech_category_query()` — рефакторится на использование хелпера, но **внешнее поведение** идентично (intent остаётся TECHNOLOGIES)
- `_profile_query()`, `_experience_query()`, `_technologies_query()` — не трогаем
- Router (greeting/cv/off-topic) — не трогаем
- Streaming, rate-limiting, cache infrastructure — не трогаем
- Frontend — не трогаем
- Content API — не трогаем
- Docker configuration — не трогаем
- `POPULAR_QUESTIONS` / `prefetch.py` — не трогаем (после сброса кэша + re-ingest, новые правильные планы будут сгенерированы)
- Normalizer — не нужны новые правила (граф возвращает уже отфильтрованные данные)
- ScopeGuard — не активен, не затрагивается

### Analysis findings addressed

| Finding | ID | Resolution |
|---------|-----|------------|
| `_projects_by_tech_category_query()` дублирует логику | D1 | Общая логика вынесена в хелпер `_collect_projects_by_tech_category()`. Обе функции его используют — DRY |
| Пример "Какие у тебя есть проекты?" конфликтует | D2 | Старый пример **заменяется** (не дополняется) на `project_list` |
| "ML проекты" неоднозначен между intents | D3 | Старый пример **заменяется** на `project_list`. Добавлено семантическое правило разграничения в промпт |
| `_languages_query()` — мёртвый код | C1 | Не в скоупе этой задачи (Constitution VII: Simplicity). Можно почистить отдельно |
| Двойная нормализация render_style | C2 | Не в скоупе этой задачи (pre-existing, не ухудшается) |
| `_get_group_title("project_list")` → "Project_List" | G1 | Добавлена запись `"project_list": "Проекты"` в `renderer.py` (Change 6) |

## Complexity Tracking

Нет нарушений конституции, требующих обоснования. Все изменения минимальны и следуют существующим паттернам.

Единственное "расширение" сверх минимума — вынесение хелпера `_collect_projects_by_tech_category()`. Обоснование: без хелпера два пути (TECHNOLOGIES + tech_category и PROJECT_LIST + tech_category) содержат 40+ строк идентичного кода фильтрации. Хелпер — это не абстракция "на будущее", а устранение реального дублирования (Constitution III: DRY).
