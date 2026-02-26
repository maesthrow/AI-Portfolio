# Tasks: Fix Technology Query Bugs

**Input**: Design documents from `/specs/004-fix-normalizer-technology-filter/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Scope**: 3 files modified, ~20 lines of code total. No new files, no migrations, no frontend changes.

**Tests**: No new test files requested. Existing test suite runs as regression check (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Verify Starting Point)

**Purpose**: Confirm exact line locations before making changes. Fast verification against actual code.

- [x] T001 [P] Read `services/rag-api-new/app/agent/normalizer/normalizer.py` — locate `technology_usage_filter` block and confirm current whitelist tuple (expected: `("technology_usage", "technology", "project")`)
- [x] T002 [P] Read `services/rag-api-new/app/graph/query.py` — locate `_technologies_query()` function and the "Все технологии" branch (lines ~456–466), confirm `techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)` with no sort
- [x] T003 [P] Read `services/rag-api-new/app/agent/executor/execute_plan.py` — locate `all_facts[:plan.limits.max_items]` line; determine: (a) exact type signature of the plan object (`QueryPlanV2` vs `QueryPlanV3`), (b) whether `.intents` attribute exists and its type (list of `IntentV3` enum? list of strings?), (c) whether `IntentV3` is a `str`-Enum (`class IntentV3(str, Enum)`) or a standard Enum. Result determines how T006 writes the comparison (needed for the override condition in T006)

**Checkpoint**: All three file locations confirmed — implementation can begin

---

## Phase 2: Foundational

**No foundational tasks required.** Both bugs are independent; each fix is in a separate file with no shared prerequisites. Bug 1 (normalizer) and Bug 2 (graph + executor) can be implemented in either order or in parallel.

---

## Phase 3: User Stories 1 & 2 — Normalizer Filter Fix (Priority: P1) 🎯 MVP

**Goal**: Fix `technology_usage_filter` to retain `experience` and `experience_project` documents, making "какой опыт с компьютерным зрением" return the same correct answer as "где использовал компьютерное зрение".

**Independent Test**: Ask "какой опыт с компьютерным зрением" → agent must return t2/Aston CV experience with Detectron2/Ultralytics/YOLO. Both this query and "где использовал компьютерное зрение" must give consistent results.

### Implementation

- [x] T004 [US1] [US2] Expand `technology_usage_filter` whitelist in `services/rag-api-new/app/agent/normalizer/normalizer.py`:
  - Find the tuple `("technology_usage", "technology", "project")` in the `technology_usage_filter` block
  - Change to `("technology_usage", "technology", "project", "experience", "experience_project")`
  - No other changes in this file

**Checkpoint — Bug 1 done**: Rebuild rag-api, ask "какой опыт с компьютерным зрением", verify t2/CV experience appears. Logs should show `rules=['technology_usage_filter']` and experience docs present in facts.

---

## Phase 4: User Story 3 — Technology Overview Fix (Priority: P1)

**Goal**: Fix `technology_overview` queries to return all ~20 technologies sorted by recency (most recent projects first), so "какими технологиями владеет Дмитрий" shows the primary Python/AI stack, not just legacy .NET/C#.

**Independent Test**: After fix and cache clear, ask "какими технологиями владеет Дмитрий" → response must include Python, LangChain, FastAPI, LangGraph. At least 15 technologies total returned. Technologies from 2024-2025 projects appear before 2021-2023 technologies.

### Implementation

- [x] T005 [P] [US3] Add recency sort to `_technologies_query()` in `services/rag-api-new/app/graph/query.py`:
  - In the "Все технологии (only when NO entity_key specified)" branch (~line 456)
  - Add a nested helper `_tech_recency_key(tech_node)` that traverses incoming `USES` edges, collects project `end_date`/`start_date` from `node.data`, returns `max(dates, default="0000-00-00")`
  - Replace `techs` with `techs_sorted = sorted(techs, key=_tech_recency_key, reverse=True)`
  - Update `items` list comprehension to use `techs_sorted`
  - Update `sources=[_node_to_source(t) for t in techs[:10]]` → `techs_sorted[:10]`

- [x] T006 [P] [US3] Add `max_items` override for `technology_overview` in `services/rag-api-new/app/agent/executor/execute_plan.py`:
  - Define constant `_MAX_ITEMS_TECHNOLOGY_OVERVIEW = 25` near the top of the method or as a module constant
  - **Before writing the override, apply the T003 result to choose the correct comparison:**
    - If `IntentV3` is a `str`-Enum (`class IntentV3(str, Enum)`): use `str(i) == "technology_overview"` or `i == IntentV3.TECHNOLOGY_OVERVIEW`
    - If `IntentV3` is a standard Enum: use `i.value == "technology_overview"` or `i.value.lower() == "technology_overview"`
    - If `.intents` attribute doesn't exist on the plan object (V2 vs V3 mismatch): use `getattr(plan, 'intents', None) or []` and access `.value` if needed
    - Safest universal form: `getattr(i, 'value', str(i)).lower() == "technology_overview"`
  - Before `limited_facts = all_facts[:plan.limits.max_items]`, add:
    ```python
    _MAX_ITEMS_TECHNOLOGY_OVERVIEW = 25
    effective_max_items = plan.limits.max_items
    if any(
        getattr(i, 'value', str(i)).lower() == "technology_overview"
        for i in getattr(plan, 'intents', []) or []
    ):
        effective_max_items = max(effective_max_items, _MAX_ITEMS_TECHNOLOGY_OVERVIEW)
    limited_facts = all_facts[:effective_max_items]
    ```
  - Replace the original `limited_facts = all_facts[:plan.limits.max_items]` with the new block
  - **Note**: the `getattr` wrappers handle both V2/V3 schema differences and both str-Enum and standard Enum cases — no risk of `AttributeError` or silent mismatch

**Checkpoint — Bug 2 done**: Rebuild rag-api, clear plan cache (`DELETE /api/v1/admin/cache/plans`), ask "какими технологиями владеет Дмитрий" → logs show `items=20+`, response includes Python, LangChain, FastAPI, and other AI stack technologies before .NET entries.

---

## Phase 5: User Story 4 — Regression Verification (Priority: P2)

**Goal**: Confirm no existing functionality is broken by the two fixes.

**Independent Test**: All tests in `services/rag-api-new/tests/` pass.

### Verification

- [ ] T007 [US4] Run existing test suite: `cd services/rag-api-new && pytest tests/ -v`
  - All tests must pass
  - If any test fails: investigate whether the failure is a pre-existing issue or caused by T004/T005/T006
  - Specifically verify: `test_smoke.py`, `test_tz_v3_acceptance.py`, `test_project_list.py`
  - **⚠️ Environment note**: some tests make real LLM API calls (GigaChat, DeepSeek). Ensure `GIGA_AUTH_DATA` and `DEEPSEEK_API_KEY` are set in the environment, OR skip live-API tests with: `pytest tests/ -v -k "not llm and not providers"`. A failure due to missing API keys is an environment issue, not a code regression.

**Checkpoint — No regressions**: All existing tests green.

---

## Phase 6: Polish & Deployment

**Purpose**: Mandatory deployment steps and final validation per quickstart.md.

- [ ] T008 Rebuild and restart rag-api Docker service: `docker compose -f infra/docker-compose.local.yaml up -d --build rag-api`
- [ ] T009 Clear plan cache (REQUIRED): `curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans`
- [ ] T010 [P] Run Bug 1 quickstart verification: ask "какой опыт с компьютерным зрением" and "где использовал компьютерное зрение" — both must return t2/Aston CV experience (see quickstart.md)
- [ ] T011 [P] Run Bug 2 quickstart verification: ask "какими технологиями владеет Дмитрий" — must include Python, LangChain, FastAPI and at least 5 other AI/Python stack technologies (see quickstart.md)
- [ ] T012 Update `specs/004-fix-normalizer-technology-filter/checklists/requirements.md` — confirm all SC-001 through SC-007 are met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately, all 3 tasks in parallel
- **Foundational (Phase 2)**: N/A — skipped
- **Phase 3 (US1/US2)**: Can start after T001 confirms normalizer line location
- **Phase 4 (US3)**: Can start after T002 and T003 confirm graph/executor locations; **T005 and T006 can run in parallel** (different files)
- **Phase 5 (US4)**: After T004, T005, T006 complete
- **Phase 6 (Deploy)**: After all implementation and tests pass

### User Story Dependencies

- **US1/US2 (Bug 1)**: Depends only on T001 (line verification) — fully independent of Bug 2
- **US3 (Bug 2)**: Depends on T002 + T003 — fully independent of Bug 1
- **US4 (No regression)**: Depends on Bug 1 AND Bug 2 fixes being complete

### Parallel Opportunities

Phase 1: T001, T002, T003 — all parallel (read-only, different files)
Phase 4: T005, T006 — parallel (different files: graph/query.py vs execute_plan.py)
Phase 6: T010, T011 — parallel (different test scenarios)

---

## Parallel Example: Phase 4 (Bug 2)

```bash
# Both can be worked on simultaneously (different files):
Task T005: Add recency sort in services/rag-api-new/app/graph/query.py
Task T006: Add max_items override in services/rag-api-new/app/agent/executor/execute_plan.py
```

---

## Implementation Strategy

### MVP First (Bug 1 Only — 1 file, 1 line change)

1. Complete Phase 1 (T001 only)
2. Complete T004 (Bug 1 normalizer fix)
3. **STOP and VALIDATE**: Ask "какой опыт с компьютерным зрением" — must work
4. Commit Bug 1 fix

### Incremental Delivery

1. Fix Bug 1 (T001 → T004) → validate → commit
2. Fix Bug 2 (T002, T003 → T005, T006) → validate → commit
3. Run regression tests (T007) → commit
4. Deploy (T008–T012)

---

## Notes

- [P] tasks = different files, no shared state, safe to run in parallel
- Bug 1 (normalizer) and Bug 2 (graph+executor) are fully independent — can be done in any order or in parallel
- **CRITICAL**: T009 (plan cache clear) MUST run after T008 (rebuild). Without it, Bug 2 fix may not take effect for cached queries.
- The intents list access in T006 must match the actual plan object attribute — verify against real plan schema during T003
