# Research: Graph Concept Resolution

**Date**: 2026-02-28
**Feature**: 008-improve-concept-queries

## R1: Code Path for entity_key "Not Found" in Graph

**Decision**: Add concept→TechCategory fallback in `_technologies_query()` before the empty result return (lines 444-457 of `query.py`).

**Rationale**: The code path is:
1. Planner generates `entity_id=technology:machine-learning`
2. `execute_graph_query()` (graph_query_tool.py:63-70) parses `entity_key="machine-learning"`
3. No `tech_category` provided → routes to `graph_query(intent, entity_key)` (line 125)
4. `graph_query()` dispatches to `_technologies_query(entity_key="machine-learning")` (line 681)
5. `store.get_node_by_slug("machine-learning")` → NOT FOUND (no such technology node)
6. Partial match against projects → NOT FOUND
7. Returns empty result with `confidence=0.0` (lines 444-457)

The fallback should go between step 6 and 7: check concept mapping → delegate to `_projects_by_tech_category_query(mapped_category)`.

**Alternatives considered**:
- Adding concept nodes to the graph during build → rejected: changes graph schema, affects all queries
- Modifying `graph_query_with_filters` → rejected: the planner doesn't send `tech_category` in this path
- Modifying `execute_graph_query` in graph_query_tool.py → rejected: less cohesive, graph layer should handle its own resolution

## R2: Concept → TechCategory Mapping Dictionary

**Decision**: Static dictionary in `query.py` mapping concept slugs to TechCategory values.

**Rationale**: The planner generates entity_id slugs like `technology:machine-learning`, `technology:ai-agents`, `technology:rag`. These are predictable patterns. A static dict is simplest and most maintainable.

**Mapping table** (based on existing TechCategory enum and portfolio content):

| Concept slug patterns | TechCategory | Technologies found |
|---|---|---|
| `machine-learning`, `ml` | `ml_framework` | PyTorch, YOLO, Detectron2, LangChain, LangGraph, vLLM |
| `ai-agents`, `ai-agent`, `ии-агенты` | `concept` | RAG, LLM, ReAct |
| `rag` | `concept` | RAG, LLM, ReAct |
| `computer-vision`, `cv` | `ml_framework` | PyTorch, YOLO, Detectron2 |
| `nlp` | `ml_framework` | LangChain, sentence-transformers |

**Alternatives considered**:
- Dynamic mapping from TechCategory enum → rejected: no reliable way to infer which category a concept slug maps to
- Fuzzy matching → rejected: adds complexity, risk of false positives (violates YAGNI)

## R3: Existing `_projects_by_tech_category_query()` Reusability

**Decision**: Reuse `_projects_by_tech_category_query(category, limit)` directly — it already does exactly what's needed.

**Rationale**: This function (query.py:894-986):
- Takes a category string
- Finds all projects using technologies from that category
- Returns `GraphQueryResult` with project details, technologies used, and descriptions
- Sorts by tech count (most relevant first)
- Already used by `graph_query_with_filters` when `tech_category` is provided

No new query logic needed — just the mapping lookup and delegation.

## R4: Backward Compatibility

**Decision**: Concept mapping activates ONLY after ALL existing lookups fail (technology node, project node, partial project match).

**Rationale**: The concept mapping is inserted as the LAST check before returning empty result. Existing entity_keys that match real nodes (Python, PostgreSQL, LangChain) are found by `store.get_node_by_slug()` at line 376 and never reach the concept mapping code. Zero risk of regression.

**Verification**: All existing tests pass unchanged (103 pass, 1 pre-existing failure unrelated to our changes).
