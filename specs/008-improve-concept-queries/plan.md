# Implementation Plan: Graph Concept Resolution

**Branch**: `008-improve-concept-queries` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-improve-concept-queries/spec.md`

## Summary

Добавить fallback-маппинг concept→TechCategory в `_technologies_query()` (graph/query.py), чтобы запросы с entity_key для абстрактных концепций (machine-learning, ai-agents, rag) возвращали проекты по соответствующей TechCategory вместо пустого результата.

Изменение затрагивает **один файл** и активируется **только** когда entity_key не найден как technology-нода или project-нода в графе (zero regression risk).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, LangChain 1.x, LangGraph 1.x
**Storage**: PostgreSQL 16 (pgvector), in-memory GraphStore
**Testing**: pytest (103 tests, 1 pre-existing failure unrelated)
**Target Platform**: Docker (Linux container)
**Project Type**: web-service (microservices)
**Performance Goals**: N/A (static dict lookup, no latency impact)
**Constraints**: UTF-8 encoding for all Cyrillic text
**Scale/Scope**: Single file change, ~20 lines of production code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | No new files with user-facing text; dict keys are ASCII slugs |
| II. Root-Cause Resolution | PASS | Root cause: graph has no concept nodes; fix: resolve concepts to categories at query time |
| III. Clean Architecture | PASS | Reuses existing `_projects_by_tech_category_query()`; no new abstractions |
| IV. Service Directory | PASS | Change in `services/rag-api-new/` (active service) |
| V. API Versioning | PASS | No API changes; internal graph query layer only |
| VI. DB Migration | PASS | No model changes |
| VII. Simplicity & YAGNI | PASS | Static dict + 1 conditional check; reuses existing function; no over-engineering |

**Post-Phase 1 re-check**: All gates still PASS. No new concerns.

## Project Structure

### Documentation (this feature)

```text
specs/008-improve-concept-queries/
├── spec.md              # Feature specification (scoped to FR-003)
├── plan.md              # This file
├── research.md          # Phase 0: code path analysis, mapping decisions
├── data-model.md        # Phase 1: CONCEPT_TO_CATEGORY mapping schema
├── quickstart.md        # Phase 1: deployment and verification guide
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
services/rag-api-new/
├── app/
│   └── graph/
│       └── query.py          # MODIFIED: add CONCEPT_TO_CATEGORY + fallback in _technologies_query()
└── tests/
    └── test_concept_resolution.py  # NEW: tests for concept→category mapping
```

**Structure Decision**: Minimal change — one production file modified, one test file added. No new modules, no architectural changes.

## Implementation Design

### Change 1: CONCEPT_TO_CATEGORY mapping dict

**File**: `services/rag-api-new/app/graph/query.py`
**Location**: Module level, after `CATEGORY_DISPLAY_NAMES` dict (line ~33)

Add a static dictionary mapping concept slugs to TechCategory values:

```python
CONCEPT_TO_CATEGORY: dict[str, str] = {
    "machine-learning": "ml_framework",
    "ml": "ml_framework",
    "ai-agents": "concept",
    "ai-agent": "concept",
    "rag": "concept",
    "computer-vision": "ml_framework",
    "cv": "ml_framework",
    "nlp": "ml_framework",
}
```

**Rationale**: Static dict is simplest (YAGNI). Slugs match what the planner generates in entity_id. 1:1 mapping per clarification decision.

### Change 2: Concept fallback in `_technologies_query()`

**File**: `services/rag-api-new/app/graph/query.py`
**Location**: In `_technologies_query()`, between the partial project match (line ~415) and the empty result return (lines 444-457)

Replace the current "not found → empty" path with concept resolution:

```python
# Before returning empty, check if entity_key matches a known concept
mapped_category = CONCEPT_TO_CATEGORY.get(entity_key.lower())
if mapped_category:
    logger.info(
        "Concept resolution: entity_key '%s' mapped to tech_category '%s'",
        entity_key,
        mapped_category,
    )
    return _projects_by_tech_category_query(mapped_category, limit=20)

# Original empty result return (unchanged)
logger.warning(...)
return GraphQueryResult(items=[], ...)
```

**Rationale**:
- Activates ONLY when entity_key is not found as technology node AND not found as project node
- Delegates to existing `_projects_by_tech_category_query()` — no code duplication
- Existing entity_keys (Python, PostgreSQL, LangChain) found by `get_node_by_slug()` at line 376, never reach this code

### Change 3: Tests

**File**: `services/rag-api-new/tests/test_concept_resolution.py` (new)

Tests to add:
1. `test_concept_mapping_ml` — entity_key="machine-learning" → returns projects with ml_framework technologies
2. `test_concept_mapping_ai_agents` — entity_key="ai-agents" → returns projects with concept technologies
3. `test_concept_mapping_rag` — entity_key="rag" → returns projects with concept technologies
4. `test_concept_mapping_unknown` — entity_key="blockchain" → returns empty (no mapping)
5. `test_existing_technology_not_intercepted` — entity_key="python" → found as node, concept mapping NOT activated
6. `test_concept_mapping_case_insensitive` — entity_key="Machine-Learning" → still maps correctly

Tests will build a minimal graph using `build_graph()` with a small `ExportPayload` containing technologies from different categories.

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Concept mapping intercepts real technology slug | High | Zero | Mapping checked AFTER node lookup; existing nodes found first |
| Wrong concept→category mapping | Medium | Low | Static dict reviewable; limited to 5 known concepts |
| `_projects_by_tech_category_query` returns unexpected format | Low | Zero | Already used by `graph_query_with_filters`, proven in production |

## Complexity Tracking

No complexity violations. Single-file change with static dict lookup — well within Principle VII bounds.
