# Implementation Plan: Fix Technology Query Bugs

**Branch**: `004-fix-normalizer-technology-filter` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)

## Summary

Fix two distinct bugs in the technology query pipeline of `rag-api-new`:

1. **Bug 1 (Normalizer filter)**: `technology_usage_filter` drops `experience`/`experience_project` documents, causing inconsistent answers for technology usage questions. Fix: expand the whitelist in `normalizer.py`.

2. **Bug 2 (Graph truncation)**: `technology_overview` query returns only the first ~12 alphabetically-sorted technologies (all legacy .NET/C#), missing the primary Python/AI stack. Fix: add recency sort in `graph/query.py` + override `max_items` limit in `execute_plan.py` for this intent.

Both fixes are surgical changes to existing files with no schema migrations, no new files, no frontend changes.

---

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: LangChain 1.x, LangGraph 1.x (existing pipeline)
**Storage**: No schema changes. Redis plan cache must be cleared post-deploy.
**Testing**: pytest — `services/rag-api-new/tests/`
**Target Platform**: Docker container (rag-api service in `infra/docker-compose.local.yaml`)
**Project Type**: Backend microservice (RAG API)
**Performance Goals**: No change expected. Recency sort is O(T × P) where T = ~20 techs, P = ~5 projects per tech — negligible.
**Constraints**: Fix must not affect other intents. No planner prompt changes. No schema changes.
**Scale/Scope**: 3 files modified, ~10–20 lines of code total.

---

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | All modified files are existing Python files in UTF-8. No new Cyrillic text introduced. |
| II. Root-Cause Resolution | PASS | Both fixes address root causes: whitelist gap in normalizer, no-sort + low max_items in graph/executor. No workarounds. |
| III. Clean Architecture | PASS | Changes are in the correct architectural layers (normalizer for filtering, graph for data retrieval, executor for orchestration). No SOLID violations. |
| IV. Service Directory Discipline | PASS | All changes in `services/rag-api-new/` — the active service directory. |
| V. API Versioning | PASS | No API endpoint changes. |
| VI. Database Migration | PASS | No SQLAlchemy model changes. No Alembic migration needed. |
| VII. Simplicity & YAGNI | PASS | Minimum changes: one tuple expansion, one sort call, one conditional max(). No new abstractions or helpers. |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-fix-normalizer-technology-filter/
├── spec.md              ✅
├── plan.md              ✅ (this file)
├── research.md          ✅
├── data-model.md        ✅
├── quickstart.md        ✅
├── checklists/
│   └── requirements.md  ✅
└── tasks.md             (created by /speckit.tasks)
```

### Source Code — Files to Modify

```text
services/rag-api-new/
├── app/
│   ├── agent/
│   │   ├── normalizer/
│   │   │   └── normalizer.py          # Bug 1: expand technology_usage_filter whitelist
│   │   └── executor/
│   │       └── execute_plan.py        # Bug 2B: override max_items for technology_overview
│   └── graph/
│       └── query.py                   # Bug 2A: recency sort in _technologies_query()
└── tests/
    └── (existing test files to verify, new tests for bug coverage)
```

---

## Phase 1: Bug 1 — Normalizer Filter Fix

### Change: `normalizer.py`

**Location**: `services/rag-api-new/app/agent/normalizer/normalizer.py`

Find the `technology_usage_filter` block (~lines 89–94):

```python
# BEFORE
if intent_str == "technology_usage":
    tech_facts = [f for f in filtered if f.type in ("technology_usage", "technology", "project")]
    if tech_facts:
        filtered = tech_facts
        rules_applied.append("technology_usage_filter")
```

```python
# AFTER
if intent_str == "technology_usage":
    tech_facts = [f for f in filtered if f.type in (
        "technology_usage", "technology", "project",
        "experience", "experience_project",
    )]
    if tech_facts:
        filtered = tech_facts
        rules_applied.append("technology_usage_filter")
```

**Why**: `experience` and `experience_project` documents contain technology usage descriptions in their achievements text. They are the primary source for "where was X technology used" answers.

---

## Phase 2: Bug 2A — Recency Sort in Graph Query

### Change: `graph/query.py`

**Location**: `services/rag-api-new/app/graph/query.py`, function `_technologies_query()`, the "all technologies" branch (~lines 456–466)

**Before:**
```python
# Все технологии (only when NO entity_key specified)
techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
items = [{"name": t.name, "category": t.data.get("category")} for t in techs]
```

**After:**
```python
# Все технологии (only when NO entity_key specified)
techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)

# Sort by recency: technology last used in the most recent project comes first
def _tech_recency_key(tech_node) -> str:
    uses_edges = store.get_incoming_edges(tech_node.id, EdgeType.USES)
    dates = []
    for edge in uses_edges:
        project = store.get_node(edge.source_id)
        if project:
            date = project.data.get("end_date") or project.data.get("start_date") or ""
            if date:
                dates.append(date)
    return max(dates, default="0000-00-00")

techs_sorted = sorted(techs, key=_tech_recency_key, reverse=True)
items = [{"name": t.name, "category": t.data.get("category")} for t in techs_sorted]
```

**Tie-breaking**: Technologies used in multiple projects use the most-recent project's end_date. If project has no date, it falls to `"0000-00-00"` (placed last). Technologies with identical recency key are in stable insertion order.

**Note on `sources`**: The existing `sources=[_node_to_source(t) for t in techs[:10]]` line should also use `techs_sorted[:10]` to maintain consistency.

---

## Phase 3: Bug 2B — Max Items Override in Executor

### Change: `execute_plan.py`

**Location**: `services/rag-api-new/app/agent/executor/execute_plan.py`

Find the `all_facts[:plan.limits.max_items]` line and add an intent-specific override:

**Before:**
```python
limited_facts = all_facts[: plan.limits.max_items]
```

**After:**
```python
# For technology_overview, ensure all technologies are returned (portfolio has ~20)
_MAX_ITEMS_TECHNOLOGY_OVERVIEW = 25
effective_max_items = plan.limits.max_items
if hasattr(plan, "intents") and any(
    str(i).lower() == "technology_overview" for i in plan.intents
):
    effective_max_items = max(effective_max_items, _MAX_ITEMS_TECHNOLOGY_OVERVIEW)
limited_facts = all_facts[:effective_max_items]
```

**Note**: The exact attribute name for intents on the plan object (`plan.intents` vs `plan.intents[0].value`) must be verified against the actual `QueryPlanV2`/`QueryPlanV3` schema during implementation.

---

## Phase 4: Deployment

### Post-deploy steps (mandatory)

1. Rebuild and restart the `rag-api` Docker service:
   ```bash
   docker compose -f infra/docker-compose.local.yaml up -d --build rag-api
   ```

2. Clear plan cache (REQUIRED — old cached plans have wrong max_items):
   ```bash
   curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans
   ```

3. Verify fixes — see `quickstart.md` for test commands.

---

## Complexity Tracking

No constitution violations. No complexity justification needed.

The `_tech_recency_key` helper function is defined inline (nested function) within `_technologies_query()` to avoid creating a module-level function for a single-use operation (KISS / YAGNI).
