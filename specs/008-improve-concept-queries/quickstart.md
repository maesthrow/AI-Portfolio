# Quickstart: Graph Concept Resolution

**Date**: 2026-02-28
**Feature**: 008-improve-concept-queries

## What Changed

Added a concept→TechCategory fallback in `_technologies_query()` (graph/query.py).
When an entity_key is not found as a technology or project node, the graph now checks
a static concept mapping and returns projects by tech category instead of empty result.

## File Changed

- `services/rag-api-new/app/graph/query.py` — added `CONCEPT_TO_CATEGORY` dict + fallback logic in `_technologies_query()`

## How It Works

Before (entity_key="machine-learning"):
```
get_node_by_slug → None → empty result → fallback to vector search
```

After:
```
get_node_by_slug → None → CONCEPT_TO_CATEGORY["machine-learning"] → "ml_framework"
→ _projects_by_tech_category_query("ml_framework") → projects with ML technologies
```

## Concepts Mapped

| Concept | Slugs | Category |
|---------|-------|----------|
| Machine Learning | machine-learning, ml | ml_framework |
| AI Agents | ai-agents, ai-agent | concept |
| RAG | rag | concept |
| Computer Vision | computer-vision, cv | ml_framework |
| NLP | nlp | ml_framework |

## Testing

```bash
cd services/rag-api-new
pytest tests/ -v -k "concept"
```

## Verification

After deploying, test with:
1. Query: "какой опыт с машинным обучением" → planner generates `entity_id=technology:machine-learning` → graph returns ML projects (not empty)
2. Query: "расскажи про RAG" → planner generates `entity_id=technology:rag` → graph returns concept projects (not empty)
3. Query: "где используется Python" → `entity_id=technology:python` → works as before (node found directly)
