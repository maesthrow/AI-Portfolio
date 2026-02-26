# Research: Fix Technology Query Bugs

**Branch**: `004-fix-normalizer-technology-filter`
**Date**: 2026-02-26

## Bug 1 — Normalizer technology_usage_filter

### Root Cause (confirmed)

**File**: `services/rag-api-new/app/agent/normalizer/normalizer.py` ~lines 89–94

```python
if intent_str == "technology_usage":
    tech_facts = [f for f in filtered if f.type in ("technology_usage", "technology", "project")]
    if tech_facts:
        filtered = tech_facts
        rules_applied.append("technology_usage_filter")
```

The whitelist `("technology_usage", "technology", "project")` does not include `experience` or `experience_project`. When the hybrid search returns a relevant `experience` document (e.g., Aston/t2 with CV achievements) but no `project` doc for the same technology, the experience doc is silently dropped.

### Decision: Expand whitelist

**Decision**: Add `"experience"` and `"experience_project"` to the whitelist tuple.

**Rationale**: Technology usage information is routinely stored in `experience` docs (job achievements) and `experience_project` docs (project descriptions within a job). Excluding them from `technology_usage` queries is architecturally incorrect — they are the primary source of "where was this technology used" information.

**Alternatives considered**:
- Move the filter to retrieval stage (rejected: normalizer is the right layer for intent-based filtering)
- Remove the filter entirely (rejected: would allow irrelevant stat/profile docs to pollute answers)

**Risk**: Low. One-tuple change. Fallback behavior (keep all if no matching types) is preserved.

---

## Bug 2 — Technology Overview Truncation

### Root Cause (confirmed, two layers)

**Layer 1 — No recency sort in `_technologies_query()`**

**File**: `services/rag-api-new/app/graph/query.py`, lines 456–466

```python
# Все технологии (only when NO entity_key specified)
techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
items = [{"name": t.name, "category": t.data.get("category")} for t in techs]
```

`get_nodes_by_type()` returns nodes in insertion order (graph build order = content-api alphabetical seeding order). C#, .NET, ADO.NET etc. were seeded in older projects; Python, LangChain, FastAPI were seeded in newer projects. Alphabetical insertion means `.` and `A` prefixes (legacy .NET stack) come first.

**Layer 2 — Executor `max_items` truncation**

**File**: `services/rag-api-new/app/agent/executor/execute_plan.py`

```python
limited_facts = all_facts[:plan.limits.max_items]
```

`LimitsConfigV3.max_items` defaults to 10. The cached plan had `max_items=12`. The graph returned 20 facts; executor cut to 12 — all from the alphabetical head.

### Decision A: Recency sort in `_technologies_query()`

**Decision**: Before building `items`, sort `techs` by the most-recent project date that uses each technology (via graph USES edges), descending.

**Recency computation**: For each TECHNOLOGY node, traverse incoming USES edges to find all PROJECT nodes. Take `max(end_date, start_date)` across all connected projects. Sort technologies by this max date descending. Technologies with no project connections (should not happen) fall to the end.

**Rationale**: Technologies from 2024-2025 projects (Python, LangChain, LangGraph, FastAPI) will rank before technologies from 2021-2023 projects (.NET, C#, ADO.NET). Even if the executor cuts to 12, the top 12 will be the most relevant.

**Alternatives considered**:
- Sort by usage count (number of projects): already exists in `_technologies_by_category_query()` for category queries. Rejected for general overview because Python might have fewer projects than Docker, but Python is more primary.
- Add priority field to technology nodes: too invasive, requires schema/data changes.
- Sort alphabetically within category tiers: does not solve the recency problem.

### Decision B: Override max_items in executor for technology_overview

**Decision**: In `execute_plan.py`, when the primary intent is `technology_overview`, use `max(plan.limits.max_items, 25)` as the effective limit before the slice.

**Rationale**: `LimitsConfigV3.max_items` defaults to 10 and the LLM planner may generate any value. For `technology_overview`, a portfolio has ~20 technologies by design, and all should be returned to the answer LLM. Overriding in the executor for this specific intent is surgical and avoids changing the planner prompt or default schema values.

**Alternative considered**: Add shortcut in `shortcuts.py` for technology_overview with `max_items=25`. Rejected because shortcuts must match specific regex patterns and "какими технологиями владеет Дмитрий" has many paraphrases; the executor override is more robust.

**Alternative considered**: Change `LimitsConfigV3.max_items` default from 10 to 25. Rejected because this would increase token usage for all intents unnecessarily.

### Decision C: Plan cache clearing on deployment

**Decision**: Plan cache must be cleared after deploying the fix. Old cached plans with `max_items=12` will still be served from Redis until cleared.

**Command**: `DELETE /api/v1/admin/cache/plans`

---

## Files to Modify (complete list)

| File | Change | Bug |
|------|--------|-----|
| `services/rag-api-new/app/agent/normalizer/normalizer.py` | Expand `technology_usage_filter` whitelist | Bug 1 |
| `services/rag-api-new/app/graph/query.py` | Add recency sort in `_technologies_query()` | Bug 2A |
| `services/rag-api-new/app/agent/executor/execute_plan.py` | Override max_items for technology_overview | Bug 2B |

No new files. No migrations. No frontend changes.
