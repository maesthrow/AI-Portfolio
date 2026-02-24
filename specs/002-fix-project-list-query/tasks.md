# Tasks: Fix Project List Query

**Input**: Design documents from `/specs/002-fix-project-list-query/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Included — spec.md раздел "User Scenarios & Testing" помечен как mandatory.

**Organization**: Задачи сгруппированы по user story для независимой реализации и проверки каждой истории.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно выполнять параллельно (разные файлы, нет незавершённых зависимостей)
- **[Story]**: Какой user story принадлежит задача (US1..US4)
- Все пути относительно `services/rag-api-new/`

---

## Phase 1: Foundational — Enum & Pipeline Plumbing

**Purpose**: Инфраструктурные изменения, которые блокируют ВСЕ user story — регистрация intent в трёх enum'ах и прокладка аргументов `kind`/`domain` через pipeline.

**⚠️ CRITICAL**: Ни одна user story не может быть реализована до завершения этой фазы.

- [x] T001 [P] Add `PROJECT_LIST = "project_list"` to `Intent` enum in `app/rag/search_types.py` (before `GENERAL_UNSTRUCTURED`, following existing ordering)
- [x] T0 [P] Add `PROJECT_LIST = "project_list"` to `IntentV3` enum in `app/agent/planner/schemas_v3.py` (before `GENERAL_UNSTRUCTURED`)
- [x] T0 [P] Add `PROJECT_LIST = "project_list"` to `IntentV2` enum in `app/agent/planner/schemas.py` (before `GENERAL_UNSTRUCTURED`)
- [x] T0 Extend `graph_query_with_filters()` signature with `kind: str | None = None` and `domain: str | None = None` params in `app/graph/query.py`; add `if intent == Intent.PROJECT_LIST:` branch that calls `_list_projects_query()` (stub function — will be implemented in Phase 2)
- [x] T0 [P] Add `IntentV2.PROJECT_LIST: "project_list"` to `_INTENT_MAPPING`; extend `execute_graph_query()` signature with `kind`/`domain` params; pass them to `graph_query_with_filters()` and update the `if tech_category or company_key or project_key:` condition to `if tech_category or company_key or project_key or kind or domain:` in `app/agent/tools/graph_query_tool.py`
- [x] T0 [P] Extract `kind = tool_call.args.get("kind")` and `domain = tool_call.args.get("domain")` in `_execute_tool()` and pass to `execute_graph_query()` in `app/agent/executor/execute_plan.py`

**Checkpoint**: Enum зарегистрирован во всех трёх местах. Pipeline аргументов `kind`/`domain` проходит до `graph_query_with_filters()`. Сервис импортируется без ошибок.

---

## Phase 2: User Story 1 — List Personal Projects (Priority: P1) 🎯 MVP

**Goal**: Когда пользователь спрашивает "Какие есть личные проекты?", агент возвращает все личные проекты (без company affiliation) без галлюцинаций.

**Independent Test**: `curl` к агенту с вопросом "какие есть личные проекты" → ответ содержит AI-Portfolio, HyperKeeper, ReAct-Agent; НЕ содержит t2, F3 TAIL, СКИО.

### Implementation for User Story 1

- [x] T0 [US1] Extract shared helper `_collect_projects_by_tech_category(projects, category)` that filters project nodes by tech category via USES edges, as specified in plan.md Change 2a, in `app/graph/query.py`
- [x] T0 [US1] Refactor `_projects_by_tech_category_query()` to call `_collect_projects_by_tech_category()` instead of the inline 40-line filtering block per plan.md Change 2b in `app/graph/query.py`; verify external behavior is identical (same items format, same confidence=1.0)
- [x] T0 [US1] Implement `_list_projects_query(entity_key, *, kind, tech_category, domain)` per plan.md Change 2c: filter by kind (personal = company_name is None), by domain, by tech_category via helper; build items dict with name/slug/description/technologies/period/company_name/domain/repo_url/demo_url/kind/text fields; register in `handlers` dict as `Intent.PROJECT_LIST: lambda: _list_projects_query(entity_key)` in `app/graph/query.py`
- [x] T0 [P] [US1] Add `_answer_project_list(self, facts)` deterministic method; register it in `_try_deterministic_answer()` by adding `if intents == ["project_list"] or "project_list" in intents: return self._answer_project_list(payload.items)` before `return None` in `app/agent/answer/answer_llm.py`
- [x] T0 [P] [US1] Add `"project_list": "Проектов, соответствующих запросу, не найдено."` to `NOT_FOUND_BY_INTENT` dict in `app/agent/answer/prompts.py`
- [x] T0 [P] [US1] Add `"project_list": "Проекты"` to `titles` dict in `_get_group_title()` method in `app/agent/render/renderer.py`
- [x] T0 [US1] Add to `app/agent/planner/prompts.py`: (1) `project_list` intent description before `general_unstructured` in the intents section; (2) `kind` and `domain` params to `graph_query_tool` args description; (3) example "Какие есть личные проекты?" with `{"intent": "project_list", "kind": "personal"}` per plan.md Change 4a/4c/4f

### Tests for User Story 1

- [x] T0 [US1] Create `tests/test_project_list.py` with US1 unit tests: (a) `test_list_personal_projects` — assert `_list_projects_query(kind="personal")` returns only projects where `company_name` is None; (b) `test_personal_projects_no_commercial` — assert commercial projects absent; (c) `test_no_filters_returns_all` — assert `_list_projects_query()` with no args returns all PROJECT nodes

**Checkpoint**: `pytest tests/test_project_list.py` — T014 тесты проходят. Ручная проверка: "какие есть личные проекты" → все 3 личных проекта, 0 коммерческих.

---

## Phase 3: User Story 2 — List Projects by Technology (Priority: P1)

**Goal**: Когда пользователь спрашивает "Какие есть проекты с LLM?" или "ML проекты", агент возвращает только проекты с LLM-технологиями; F3 TAIL и СКИО исключены.

**Independent Test**: "какие проекты с LLM" → содержит t2/AI-Portfolio/HyperKeeper/ReAct-Agent; НЕ содержит F3 TAIL, СКИО. "Где применялся RAG?" → по-прежнему technology_usage (регрессия отсутствует).

### Implementation for User Story 2

- [x] T0 [US2] Update `app/agent/planner/prompts.py`: (1) **REPLACE** существующий пример "ML проекты" (technology_usage + tech_category) на `project_list + tech_category: ml_framework`; (2) **ADD** пример "Какие есть проекты с LLM?" с `{"intent": "project_list", "tech_category": "ml_framework"}`; (3) **ADD** правило 7 разграничения project_list vs technology_usage per plan.md Change 4b/4e/4f

### Tests for User Story 2

- [x] T0 [US2] Add US2 tests to `tests/test_project_list.py`: (a) `test_tech_category_filter` — assert `_list_projects_query(tech_category="ml_framework")` returns only projects with ml_framework technologies via USES edges; (b) `test_tech_category_no_false_positives` — assert projects without ml_framework tech are excluded; (c) `test_unknown_tech_category_returns_empty` — assert `_list_projects_query(tech_category="kotlin")` returns empty items with `found=False`

**Checkpoint**: `pytest tests/test_project_list.py` — все тесты проходят. "ML проекты" идёт через `project_list`, "Где применялся RAG?" по-прежнему через `technology_usage`.

---

## Phase 4: User Story 3 + User Story 4 — Commercial & All Projects (Priority: P2)

**Goal**: "Коммерческие проекты" → только company-affiliated проекты. "Какие есть проекты" → все 7 проектов полным списком.

**Independent Test US3**: "коммерческие проекты" → содержит t2, F3 TAIL, СКИО; НЕ содержит AI-Portfolio, HyperKeeper, ReAct-Agent.
**Independent Test US4**: "расскажи о проектах" → все проекты без пропусков, без дубликатов.

### Implementation for User Story 3

- [x] T0 [US3] Add to `app/agent/planner/prompts.py`: example "Коммерческие проекты" with `{"intent": "project_list", "kind": "commercial"}` per plan.md Change 4f

### Implementation for User Story 4

- [x] T0 [US4] **REPLACE** existing "Какие у тебя есть проекты?" example (currently uses `["project_details", "experience_summary"]`) with `project_list` + no filters per plan.md Change 4d in `app/agent/planner/prompts.py`

### Tests for User Story 3 + 4

- [x] T0 [US3] Add US3 tests to `tests/test_project_list.py`: (a) `test_list_commercial_projects` — assert `_list_projects_query(kind="commercial")` returns only projects with non-None `company_name`; (b) `test_commercial_no_personal` — assert personal projects absent
- [x] T0 [US4] Add US4 tests to `tests/test_project_list.py`: (a) `test_list_all_projects_count` — assert `_list_projects_query()` returns all PROJECT nodes from graph; (b) `test_combined_filters` — assert `_list_projects_query(kind="personal", tech_category="ml_framework")` applies both filters correctly

**Checkpoint**: `pytest tests/test_project_list.py` — все тесты проходят. Все четыре user story работают корректно.

---

## Phase 5: Polish & Validation

**Purpose**: Финальная валидация, сброс кэша, запуск полного набора тестов.

- [x] T0 Run `pytest services/rag-api-new/tests/test_project_list.py -v` — убедиться, что все тесты зелёные
- [x] T0 Run existing test suite `pytest services/rag-api-new/tests/ -v --ignore=services/rag-api-new/tests/test_project_list.py` — убедиться, что нет регрессий в существующих тестах
- [x] T0 Clear plan cache after implementation: `curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans` and re-run ingest per `specs/002-fix-project-list-query/quickstart.md` step 11

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: Нет зависимостей — стартует сразу. Блокирует всё остальное.
- **Phase 2 (US1)**: Зависит от Phase 1. После завершения US1 — MVP готов.
- **Phase 3 (US2)**: Зависит от Phase 1 + Phase 2 (prompts.py изменяется последовательно).
- **Phase 4 (US3+US4)**: Зависит от Phase 1 + Phase 2 + Phase 3 (prompts.py последовательно).
- **Phase 5 (Polish)**: Зависит от всех предыдущих фаз.

### Task Dependencies (critical path)

```
T001 ─┐
T002 ─┼─► T004 ─► T007 ─► T008 ─┐
T003 ─┘           T007 ─► T009 ─┘─► T010, T011, T012, T013, T014
                                         │
T005 ────────────────────────────────────┘  (graph_query_tool.py — независимо от query.py)
T006 ──────────────────────────────────────  (execute_plan.py — независимо от всего выше)
```

### User Story Dependencies

- **US1 (P1)**: Стартует после Phase 1. Является MVP — можно остановиться здесь для первого деплоя.
- **US2 (P1)**: Зависит от US1 только из-за prompts.py (последовательная запись). Логически независим.
- **US3 + US4 (P2)**: Зависят от US2 только из-за prompts.py. Логически независимы.

### Parallel Opportunities (Phase 1)

T001, T002, T003 → разные файлы, нет зависимостей → запускать одновременно.
T005, T006 → разные файлы, нет зависимостей между собой → запускать одновременно с T004.

### Parallel Opportunities (Phase 2 — US1)

T010, T011, T012 → разные файлы, не зависят от T007–T009 → параллельно с рефакторингом query.py.

```bash
# Параллельно с T007–T009 (query.py):
Task: "Add _answer_project_list() in answer_llm.py"          # T010
Task: "Add not-found message in answer/prompts.py"            # T011
Task: "Add _get_group_title entry in renderer.py"             # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 — Phase 1 + Phase 2)

1. Завершить Phase 1 (T001–T006) — инфраструктура готова
2. Завершить Phase 2 (T007–T014) — US1 реализована
3. **ОСТАНОВИТЬСЯ И ПРОВЕРИТЬ**: "какие есть личные проекты" → 3 проекта, 0 галлюцинаций
4. Деплой если готово — это уже устраняет критический баг SC-001

### Incremental Delivery

1. Phase 1 → Foundation ready (pipeline plumbing)
2. Phase 2 → US1 MVP: личные проекты работают → Deploy/Demo
3. Phase 3 → US2: LLM-проекты без F3 TAIL → Deploy/Demo
4. Phase 4 → US3+US4: коммерческие и все проекты → Deploy/Demo
5. Phase 5 → Polish + validation

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 23 |
| Phase 1 (Foundational) | 6 tasks |
| Phase 2 (US1) | 8 tasks |
| Phase 3 (US2) | 2 tasks |
| Phase 4 (US3+US4) | 4 tasks |
| Phase 5 (Polish) | 3 tasks |
| Parallelizable tasks | 9 (T001–T003, T005–T006, T010–T012, T019–T020) |
| New files | 1 (`tests/test_project_list.py`) |
| Modified files | 10 |
| Suggested MVP scope | Phase 1 + Phase 2 (US1 only) |
