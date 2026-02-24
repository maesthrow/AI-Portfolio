# Research: Fix Project List Query

## Decision 1: New intent vs reusing existing

**Decision**: Добавить новый `PROJECT_LIST` intent во все три enum'а (Intent, IntentV2, IntentV3).

**Rationale**: Переиспользование `experience_summary` или `project_details` смешивает разные семантики. `project_details` — это "детали одного проекта по slug", `experience_summary` — "история работы по компаниям". Перечисление проектов с фильтрами — самостоятельный тип запроса.

**Alternatives considered**:
- Reuse `experience_summary` — отклонено: возвращает группировку по компаниям, не по проектам. Нельзя фильтровать по технологии или типу.
- Reuse `project_details` без entity_id — отклонено: `_project_details_query("")` возвращает пустой результат by design (строки 473-481 query.py).
- Extend `technology_usage` — отклонено: tech-centric ("где использовался X"), а не project-centric ("какие проекты соответствуют фильтру").

## Decision 2: Filter mechanism

**Decision**: Фильтры передаются как args в `tool_calls` планнера → извлекаются в `execute_plan.py` → прокидываются через `graph_query_tool.py` → попадают в `_list_projects_query()`.

**Rationale**: Следует существующему паттерну — `tech_category` уже передаётся этим путём. Добавление `kind` и `domain` как дополнительных опциональных args — консистентно.

**Alternatives considered**:
- Encode filters in entity_id (e.g., `"kind:personal"`) — отклонено: перегружает семантику entity_id.
- Use `scope` field в QueryPlanV3 — отклонено: scope предназначен для уровня запроса (global/company/project), а не для фильтрации проектов.

## Decision 3: Technology matching strategy for "LLM projects"

**Decision**: Использовать `tech_category` фильтр (e.g., `ml_framework`) для сопоставления групп технологий. Планнер маппит термины пользователя ("LLM") на соответствующую категорию.

**Rationale**: В графе уже есть `_projects_by_tech_category_query()`, делающая это для intent TECHNOLOGIES. Та же логика переиспользуется через shared helper. Словарь `TECHNOLOGIES_WITH_CATEGORIES` обеспечивает маппинг category → tech names.

**Alternatives considered**:
- Exact tech name match only — отклонено: "LLM" — это концепция, а не одна технология.
- Full-text search — отклонено: ненадёжно, не использует структурированные данные категорий.

## Decision 4: Experience projects vs standalone projects

**Decision**: `_list_projects_query()` итерирует ВСЕ PROJECT-ноды. Фильтрация по технологиям работает только для проектов с USES-рёбрами (standalone). Experience-проекты появляются в нефильтрованных листингах.

**Key finding**: Experience project nodes НЕ имеют `data["technologies"]` и НЕ имеют USES-рёбер (builder.py строки 188-245). Standalone project nodes имеют и то, и другое.

**Decision on this gap**: Фильтрация по технологиям опирается на USES-рёбра (только standalone). Приемлемо: primary use case (personal projects) — только standalone; коммерческие детализируются через experience summaries.

## Decision 5: Planner prompt changes — scope

**Decision**: Точечные изменения промпта: описание нового intent, **замена** двух конфликтующих примеров, 3 новых примера, семантическое правило разграничения. НЕ перестраивать существующий промпт.

**Rationale**: Constitution VII (Simplicity & YAGNI). Промпт хорошо работает для остальных intent'ов.

## Decision 6: Устранение дублирования с `_projects_by_tech_category_query()`

**Decision**: Вынести общую логику фильтрации по tech_category в хелпер `_collect_projects_by_tech_category()`. Обе функции используют его.

**Rationale**: Без хелпера `_list_projects_query(tech_category=...)` содержит 40+ строк кода, идентичных `_projects_by_tech_category_query()` (строки 820-864): получение технологий по категории → поиск проектов через USES-рёбра → сортировка. Прямое нарушение DRY (Constitution III).

**Alternatives considered**:
- Оставить обе функции независимыми — отклонено: дублирование, при изменении логики нужно менять в двух местах.
- Удалить `_projects_by_tech_category_query()` и перенаправить на `_list_projects_query()` — отклонено: меняет intent в результате (TECHNOLOGIES → PROJECT_LIST), может сломать downstream normalizer/answer. Высокий blast radius.

## Decision 7: Семантическое разграничение project_list vs technology_usage

**Decision**: Добавить явное правило в промпт планнера:
- "проекты с/по X" → `project_list` + `tech_category` (фокус: перечислить проекты)
- "где/как применялся X" → `technology_usage` + `entity_id` (фокус: применение технологии)

**Rationale**: Без правила планнер путается между "ML проекты" и "Где применялся ML?", потому что оба связаны с технологиями.

**Alternatives considered**:
- Не добавлять правило — отклонено: LLM может не обобщить из примеров для пограничных формулировок.
- Объединить intents — отклонено: разные семантики, форматы ответов, хендлеры.

## Decision 8: Deterministic answer for project_list

**Decision**: Добавить детерминированный путь ответа для `project_list` в AnswerLLM.

**Rationale**: Граф возвращает уже отфильтрованные проекты. Детерминизм гарантирует, что в ответе ТОЛЬКО факты из графа — LLM не может добавить лишние проекты (как было с F3 TAIL/СКИО). Адресует SC-002 ("zero false positives").

**Alternatives considered**:
- LLM-based answering — отклонено: LLM может добавить проекты "из памяти".

## Decision 9: Прокидывание args через executor

**Decision**: Расширить `execute_plan.py` и `execute_graph_query()` для извлечения и передачи `kind`/`domain` из `tool_call.args`.

**Rationale**: Единственный путь из плана LLM в граф-хендлер. Паттерн установлен для `tech_category` — добавление аналогичных параметров консистентно.

**Alternatives considered**:
- Передавать `**kwargs` — отклонено: менее безопасно, нет явной типизации.
