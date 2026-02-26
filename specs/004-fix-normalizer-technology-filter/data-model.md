# Data Model: Fix Technology Query Bugs

**Branch**: `004-fix-normalizer-technology-filter`
**Date**: 2026-02-26

No new data models or schema migrations required. This feature modifies behavior within existing data structures.

---

## Existing Entities Affected

### FactItem (normalizer input)

`FactItem` carries a `type` field that determines how the normalizer filters it.

**Current whitelist for `technology_usage` intent:**
```
("technology_usage", "technology", "project")
```

**After fix:**
```
("technology_usage", "technology", "project", "experience", "experience_project")
```

No schema change. The `type` field values `"experience"` and `"experience_project"` already exist and are produced by the search pipeline.

---

### TechnologyNode (graph knowledge graph)

**Current state**: TECHNOLOGY nodes are returned in insertion order from `get_nodes_by_type()`. Items dict contains only `{name, category}`.

**After fix**: Items are sorted by recency before being placed in the `items` list. The `items` dict shape does not change — still `{name, category}`. The sort is computed transiently (not persisted) using USES edge traversal.

**Recency computation (transient, not stored)**:

```
For each TECHNOLOGY node t:
  connected_projects = [source_node of each incoming USES edge to t]
  dates = [p.data.get("end_date") or p.data.get("start_date") for p in connected_projects]
  recency_key = max(dates, default="0000-00-00")

Sort technologies by recency_key DESC
```

Date format used: ISO date string (lexicographic sort = chronological sort for YYYY-MM-DD format).

---

### LimitsConfigV3 (plan schema)

No change to schema. The executor override is behavioral only.

| Field | Current default | After fix |
|-------|----------------|-----------|
| `max_items` | 10 | 10 (unchanged default) |

The executor for `technology_overview` will use `max(plan.limits.max_items, 25)` at runtime without modifying the schema or the plan object.

---

## No New Tables / Collections / Indexes

This fix modifies only Python logic. No PostgreSQL, Redis, or pgvector schema changes.
