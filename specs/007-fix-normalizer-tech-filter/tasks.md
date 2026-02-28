# Tasks: Fix Normalizer technology_usage Filter

**Input**: Design documents from `/specs/007-fix-normalizer-tech-filter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — the spec defines 6 success criteria (SC-001 through SC-006) and research.md identifies 5 specific test scenarios against existing `TestNormalizer` infrastructure.

**Organization**: Tasks grouped by user story. This is a small single-file bugfix — all production code changes are in `normalizer.py`, all test changes in `test_tz_v3_acceptance.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: No setup needed — existing project, existing test infrastructure.

*Skipped — all infrastructure already exists.*

---

## Phase 2: Foundational (Core Code Changes)

**Purpose**: Apply all production code changes to `normalizer.py`. These changes are prerequisites for ALL user story tests.

**CRITICAL**: All 3 changes below are in the same file but target different code locations. They MUST all complete before user story testing begins.

- [x] T001 Add "AI Agents" entry to TECH_ABBREVIATIONS dict in `services/rag-api-new/app/agent/normalizer/normalizer.py` (after line 37, "Large Language Model" entry). Entry: `"AI Agents": ["AI-агенты", "ИИ-агенты", "агентные системы", "агентн"]` — implements FR-004
- [x] T002 Expand type filter tuple in `technology_usage` block (~line 112) of `services/rag-api-new/app/agent/normalizer/normalizer.py` — add `"profile"`, `"focus_area"`, `"tech_focus"`, `"catalog"` to the allowed types tuple — implements FR-001 and FR-005
- [x] T003 Add explicit zero-result fallback with logging in `services/rag-api-new/app/agent/normalizer/normalizer.py` (~line 116) — add `else` branch to existing `if tech_facts:` guard with `logger.warning()` and `rules_applied.append("technology_usage_filter_fallback")` — implements FR-003

**Checkpoint**: All production code changes complete. Run `pytest tests/test_tz_v3_acceptance.py -v -k "TestNormalizer"` to verify existing tests still pass (SC-004).

---

## Phase 3: User Story 1+2 — AI Agents Query Returns Relevant Answer (Priority: P1) MVP

**Goal**: The query "какой опыт с ИИ агентами" returns a substantive answer. The normalizer retains profile-type facts that contain the queried technology keyword, and rejects profile facts that do NOT match.

**Independent Test**: Create FactItems with types `profile`, `experience`, `technology` where the profile mentions "AI-агенты". Call `normalize()` with `intent="technology_usage"` and `entity_names=["AI agents"]`. Assert the profile fact is retained.

### Tests for User Story 1+2

- [x] T004 [P] [US1] Add test `test_technology_usage_retains_profile_and_focus_area_with_keyword` to `TestNormalizer` in `services/rag-api-new/tests/test_tz_v3_acceptance.py` — create FactItems: a `profile` with text containing "AI-агенты для Сбера", a `focus_area` with text "LLM / AI-Agents / RAG\n- Разработка агентных сценариев", + `experience` facts without the keyword. Call `normalize(intent="technology_usage", entity_names=["AI agents"], question="опыт с ИИ агентами")`. Assert both `profile` and `focus_area` facts ARE in filtered output (covers US1-scenario-2), and irrelevant experience facts are filtered out by Rule 2b content matching.
- [x] T005 [P] [US1] Add test `test_technology_usage_rejects_profile_without_keyword` to `TestNormalizer` in `services/rag-api-new/tests/test_tz_v3_acceptance.py` — create a profile FactItem with text about "Python-разработчик" (no PostgreSQL mention) + a technology fact about PostgreSQL. Call `normalize(intent="technology_usage", entity_names=["PostgreSQL"], question="где используется PostgreSQL")`. Assert profile fact is NOT in filtered output (no false positives, SC-003).
- [x] T006 [P] [US1] Add test `test_tech_abbreviations_ai_agents_mapping` to `TestNormalizer` in `services/rag-api-new/tests/test_tz_v3_acceptance.py` — call `FactNormalizer._build_content_keywords(entity_names=["AI agents"])`. Assert result contains both "ai agents" and "ai-агенты" (verifies TECH_ABBREVIATIONS bidirectional mapping works for the new entry).

**Checkpoint**: Tests T004-T006 pass. Profile facts with matching keywords are retained; profile facts without keywords are rejected. TECH_ABBREVIATIONS maps AI agent terms correctly.

---

## Phase 4: User Story 3 — ML Queries Include tech_focus Data (Priority: P1)

**Goal**: The query "какой опыт с машинным обучением" returns an answer that includes specific ML tools from the `tech_focus` document (PyTorch, YOLO, etc.), regardless of which intent the planner assigns.

**Independent Test**: Create FactItems with types `tech_focus`, `focus_area`, `experience`. Call `normalize(intent="technology_usage", entity_names=["Machine Learning"], question="какой опыт с машинным обучением")`. Assert `tech_focus` and `focus_area` facts containing ML keywords are retained.

### Tests for User Story 3

- [x] T007 [P] [US3] Add test `test_technology_usage_retains_tech_focus_focus_area_and_catalog` to `TestNormalizer` in `services/rag-api-new/tests/test_tz_v3_acceptance.py` — create FactItems: `tech_focus` with text "ML и CV — PyTorch, YOLO, Detectron2", `focus_area` with text "LLM / AI-Agents / RAG\n- Разработка агентных сценариев", `catalog` with text "technologies_all: Python, Machine Learning, PyTorch, Docker" (covers FR-005), `experience` with text about unrelated company. Call `normalize(intent="technology_usage", entity_names=["Machine Learning"], question="опыт с машинным обучением")`. Assert `tech_focus` and `catalog` facts ARE retained (both contain ML keywords), `focus_area` fact is filtered (no ML keyword), irrelevant experience is filtered.

**Checkpoint**: Test T007 passes. `tech_focus` documents with ML keywords survive normalizer filtering for `technology_usage` intent.

---

## Phase 5: User Story 4 — Broader Concept Queries (Priority: P2)

**Goal**: Queries about other concepts (RAG, Computer Vision, NLP) also return correct answers including profile/focus_area/tech_focus data.

**Independent Test**: Already covered by T005 (false positive prevention) and T007 (tech_focus retention). The expanded type list + Rule 2b keyword matching is generic — no concept-specific code. This phase adds the zero-result fallback test.

### Tests for User Story 4

- [x] T008 [US4] Add test `test_technology_usage_zero_result_fallback` to `TestNormalizer` in `services/rag-api-new/tests/test_tz_v3_acceptance.py` — create FactItems where ALL have types NOT in the expanded whitelist (e.g., all `stat` type). Call `normalize(intent="technology_usage")`. Assert the original unfiltered facts are returned (fallback behavior, FR-003) and `"technology_usage_filter_fallback"` is in `rules_applied`.

**Checkpoint**: Test T008 passes. Zero-result fallback preserves unfiltered facts when type filter removes everything.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify all success criteria, run full test suite, manual verification.

- [x] T009 Run full existing test suite: `pytest services/rag-api-new/tests/ -v` — verify ALL existing tests pass without modification (SC-004)
- [ ] T010 Run quickstart.md manual verification steps against local Docker deployment: (1) "какой опыт с ИИ агентами" → substantive answer (SC-001), (2) "какой опыт с машинным обучением" → includes PyTorch/YOLO (SC-006), (3) "где используется PostgreSQL" → no profile false positive (SC-003), (4) "расскажи про опыт с RAG" → includes profile + focus_area (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: No dependencies — starts immediately. T001, T002, T003 target different locations in the same file so they execute sequentially.
- **Phase 3 (US1+2)**: Depends on Phase 2 completion (code changes must be applied before tests run)
- **Phase 4 (US3)**: Depends on Phase 2 completion. Independent of Phase 3.
- **Phase 5 (US4)**: Depends on Phase 2 completion. Independent of Phases 3-4.
- **Phase 6 (Polish)**: Depends on all previous phases.

### User Story Dependencies

- **US1+2 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US3 (P1)**: Can start after Phase 2 — independent of US1+2
- **US4 (P2)**: Can start after Phase 2 — independent of US1+2 and US3

### Parallel Opportunities

- T004, T005, T006 can all run in parallel (different test functions, no dependencies)
- T007 can run in parallel with T004-T006 (different test function)
- T008 depends only on Phase 2, not on T004-T007

---

## Parallel Example: User Story 1+2 Tests

```bash
# All US1 tests can be written in parallel (different test functions):
Task: T004 "test_technology_usage_retains_profile_with_keyword"
Task: T005 "test_technology_usage_rejects_profile_without_keyword"
Task: T006 "test_tech_abbreviations_ai_agents_mapping"
```

---

## Implementation Strategy

### MVP First (Phase 2 + Phase 3)

1. Complete Phase 2: Apply all 3 code changes to `normalizer.py`
2. Complete Phase 3: Write and verify US1+2 tests
3. **STOP and VALIDATE**: Run `pytest -v -k "TestNormalizer"` — all tests green
4. The core bug is fixed at this point

### Incremental Delivery

1. Phase 2 → Code changes applied → existing tests pass
2. Phase 3 → US1+2 tests pass → AI agents query works (MVP!)
3. Phase 4 → US3 tests pass → ML/tech_focus queries verified
4. Phase 5 → US4 test passes → zero-result fallback verified
5. Phase 6 → Full suite + manual verification → ready for merge

---

## Notes

- All production changes are in ONE file: `services/rag-api-new/app/agent/normalizer/normalizer.py`
- All test changes are in ONE file: `services/rag-api-new/tests/test_tz_v3_acceptance.py`
- FR-002 (profile full text check) requires NO code change — the profile document's `text` field already contains subtitle, current_position, summary (set by `indexing/normalizer.py:_profile_docs`). The existing `_filter_fact_bullets` checks `fact_text.lower()` which already includes these fields.
- T001-T003 are sequential because they modify the same file, but they target non-overlapping code locations (lines 37, 112, 116)
- Total: 10 tasks (3 code changes + 5 tests + 2 verification)
