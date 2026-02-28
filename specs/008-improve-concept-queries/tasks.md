# Tasks: Graph Concept Resolution

**Input**: Design documents from `/specs/008-improve-concept-queries/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included — test file validates concept mapping and backward compatibility.

**Organization**: Single user story (US1). No setup/foundational phases needed — existing project, single-file change.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

---

## Phase 1: User Story 1 - Graph Concept Resolution (Priority: P1)

**Goal**: Когда entity_key для концепции (machine-learning, ai-agents, rag) не найден как нода в графе, маппить его на TechCategory и возвращать проекты по этой категории вместо пустого результата.

**Independent Test**: Вызвать `_technologies_query(entity_key="machine-learning")` — должен вернуть проекты с ML-технологиями. Вызвать с `entity_key="python"` — должен работать как раньше (нода найдена напрямую).

### Implementation

- [x] T001 [US1] Add `CONCEPT_TO_CATEGORY` mapping dict to `services/rag-api-new/app/graph/query.py` (module level, after `CATEGORY_DISPLAY_NAMES`)
- [x] T002 [US1] Add concept fallback logic in `_technologies_query()` in `services/rag-api-new/app/graph/query.py` (before empty result return at lines 444-457)
- [x] T003 [P] [US1] Create unit tests in `services/rag-api-new/tests/test_concept_resolution.py` covering: ML mapping, AI-agents mapping, RAG mapping, unknown concept, existing technology not intercepted, case insensitivity
- [x] T004 [US1] Run full test suite (`pytest tests/ -v`) and verify no regressions in `services/rag-api-new/`
- [x] T005 [US1] Rebuild rag-api in Docker and verify concept resolution with manual queries (per quickstart.md)

**Checkpoint**: Graph queries for concepts return projects instead of empty results. Existing technology queries unaffected.

---

## Dependencies & Execution Order

### Phase Dependencies

- T001 → T002 (dict must exist before fallback logic references it)
- T003 can run in parallel with T001+T002 (different file)
- T004 depends on T001+T002+T003 (all code must be written before test run)
- T005 depends on T004 (tests must pass before Docker deployment)

### Parallel Opportunities

```
T001 (add dict) ──→ T002 (add fallback) ──→ T004 (run tests) → T005 (Docker verify)
                                              ↑
T003 (write tests) ───────────────────────────┘
```

T001+T002 (production code) and T003 (test code) can be written in parallel since they modify different files.

---

## Implementation Strategy

### MVP (this IS the MVP)

1. T001+T002: Production code (~15 lines added to query.py)
2. T003: Tests (~80 lines in new test file)
3. T004: Verify all 103+ tests pass
4. T005: Manual Docker verification with real queries

### Scope

- **1 file modified**: `services/rag-api-new/app/graph/query.py`
- **1 file created**: `services/rag-api-new/tests/test_concept_resolution.py`
- **~20 lines** production code
- **~80 lines** test code
- **Zero** risk of regression (fallback activates only on currently-empty path)

---

## Notes

- [P] tasks = different files, no dependencies
- T001 and T002 are sequential (same file, T002 references dict from T001)
- T003 builds a minimal graph fixture using `build_graph()` with a small ExportPayload
- T005 uses verification steps from quickstart.md
- Commit after T004 passes (all tests green)
