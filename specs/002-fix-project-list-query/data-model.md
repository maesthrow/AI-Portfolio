# Data Model: Fix Project List Query

## Existing Entities (no changes)

### GraphNode (PROJECT type)

Two subtypes exist in the graph:

**Standalone Project** (from `payload.projects` in builder.py):
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `name` | str | No | Project display name |
| `slug` | str | No | URL-safe identifier |
| `domain` | str | Yes | e.g. "Web AI", "Telecom" |
| `period` | str | Yes | e.g. "2025 — н.в." |
| `description_md` | str | Yes | Short markdown description |
| `long_description_md` | str | Yes | Detailed markdown description |
| `repo_url` | str | Yes | GitHub repository URL |
| `demo_url` | str | Yes | Live demo URL |
| `featured` | bool | No | Whether project is featured |
| `company_name` | str | Yes | None = personal project |
| `technologies` | list[str] | No | Technology name strings |

Has USES edges to TECHNOLOGY nodes.

**Experience Project** (from `exp.projects` in builder.py):
| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `name` | str | No | Project name |
| `slug` | str | No | URL-safe identifier |
| `period` | str | Yes | Work period |
| `description_md` | str | Yes | Project description |
| `achievements_md` | str | Yes | Achievements markdown |
| `experience_id` | int | No | Parent experience ID |
| `company_slug` | str | No | Parent company slug |
| `company_name` | str | No | Always set (from company) |
| `kind` | str | No | "commercial" or "personal" |

Does NOT have `technologies` list or USES edges.

### Technology Node
| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Technology display name |
| `slug` | str | URL-safe identifier |
| `category` | str | From TECHNOLOGIES_WITH_CATEGORIES |

### Relationships (existing, unchanged)
- PERSON → PROJECT (CREATED)
- PROJECT → TECHNOLOGY (USES) — standalone projects only
- PROJECT → COMPANY (BELONGS_TO) — experience projects only

## New Query Interface

### `_list_projects_query()` return format

Returns `GraphQueryResult` with items list. Each item is a dict:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Project name |
| `slug` | str | Project slug |
| `description` | str | description_md content |
| `technologies` | list[str] | Technology names (standalone: from data + USES; experience: empty) |
| `period` | str or None | Time period |
| `company_name` | str or None | Company name (None = personal) |
| `domain` | str or None | Project domain |
| `repo_url` | str or None | Repository URL |
| `demo_url` | str or None | Demo URL |
| `kind` | str | "personal" or "commercial" (derived from company_name) |
| `text` | str | Formatted text for AnswerLLM (name + kind_label + description) |

### Filter Parameters

| Parameter | Type | Values | Effect |
|-----------|------|--------|--------|
| `kind` | str or None | `"personal"`, `"commercial"` | personal: `company_name` is None; commercial: `company_name` is not None |
| `tech_category` | str or None | Any TechCategory value | Via shared helper: finds TECHNOLOGY nodes by category, then projects via USES edges |
| `domain` | str or None | Domain string | Case-insensitive partial match against `data["domain"]` |

### Shared Helper Interface

```python
_collect_projects_by_tech_category(
    projects: list[GraphNode],
    category: str,
) -> list[tuple[GraphNode, list[str]]]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `projects` | list[GraphNode] | Input project nodes to filter |
| `category` | str | Technology category (e.g. "ml_framework") |
| **Return** | list[tuple] | (project_node, matching_tech_names) sorted by count desc |

Used by both `_list_projects_query()` and `_projects_by_tech_category_query()`.

### Args Pipeline

```
PlannerLLM → QueryPlanV3.tool_calls[].args
  ↓
execute_plan.py → extracts: intent, entity_id, tech_category, kind, domain
  ↓
graph_query_tool.py → execute_graph_query(intent, entity_id, tech_category, kind, domain)
  ↓
query.py → graph_query_with_filters(intent, entity_key, tech_category, kind, domain)
  ↓
_list_projects_query(entity_key, kind, tech_category, domain)
```

### FactItem type for project_list results

Graph query tool `_item_to_fact()` (graph_query_tool.py) will match project_list items via existing duck-typing:
- Item has `name`, `description`, `domain`, `period` → text is auto-formatted
- `fact_type` will be determined by existing logic (falls through to `intent.value` = "project_list")
