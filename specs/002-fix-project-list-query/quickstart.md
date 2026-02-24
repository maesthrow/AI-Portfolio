# Quickstart: Fix Project List Query

## What This Changes

Добавляет возможность AI-агенту корректно отвечать на вопросы о перечислении проектов:
- "Какие есть личные проекты?"
- "Какие есть проекты с LLM?"
- "Коммерческие проекты"
- "Расскажи о проектах"
- "ML проекты" / "AI-проекты"

## Files Modified (9 files + 1 new)

| File | Change | Risk |
|------|--------|------|
| `app/rag/search_types.py` | Add `PROJECT_LIST` to Intent enum | None — additive |
| `app/agent/planner/schemas_v3.py` | Add `PROJECT_LIST` to IntentV3 enum | None — additive |
| `app/agent/planner/schemas.py` | Add `PROJECT_LIST` to IntentV2 enum | None — additive |
| `app/graph/query.py` | Add `_list_projects_query()`, shared helper, refactor `_projects_by_tech_category_query()` | Low — новая функция + рефакторинг existing на helper |
| `app/agent/tools/graph_query_tool.py` | Add mapping + accept `kind`/`domain` params | Low — расширение existing сигнатуры |
| `app/agent/executor/execute_plan.py` | Extract and pass `kind`/`domain` from tool_call.args | Low — 2 новые строки extraction |
| `app/agent/planner/prompts.py` | REPLACE 2 examples, ADD 3 examples, ADD semantic rule | Medium — промпт влияет на планнер |
| `app/agent/answer/answer_llm.py` | Add deterministic path for `project_list` | Low — новый elif branch |
| `app/agent/answer/prompts.py` | Add `project_list` to NOT_FOUND_BY_INTENT | None — additive |
| `tests/test_project_list.py` | New test file | None |

## Implementation Order

1. **Add `PROJECT_LIST` to enums** (`search_types.py`, `schemas_v3.py`, `schemas.py`) — разблокирует intent
2. **Extract shared helper** `_collect_projects_by_tech_category()` in `query.py` — DRY prep
3. **Refactor** `_projects_by_tech_category_query()` to use helper — verify no regression
4. **Add `_list_projects_query()`** in `query.py` — core logic, uses same helper
5. **Update routing** in `graph_query_with_filters()` — register handler
6. **Update `graph_query_tool.py`** — add mapping, accept new params
7. **Update `execute_plan.py`** — extract and pass `kind`/`domain`
8. **Update planner prompt** (`prompts.py`) — REPLACE old examples, ADD new ones + rule
9. **Add deterministic answer** (`answer_llm.py`, `answer/prompts.py`)
10. **Write tests** — verify all scenarios from spec
11. **Clear plan cache** — so old cached plans are replaced on next prefetch

## How to Test

After changes, restart rag-api and run:

```bash
# Clear cached plans (old wrong plans)
curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans

# Re-run ingest (rebuilds graph + prefetches new plans)
docker compose -f infra/docker-compose.local.yaml up rag-ingest

# Test via chat
# Ask: "какие есть личные проекты" → expect: AI-Portfolio, HyperKeeper, ReAct-Agent
# Ask: "какие есть проекты с LLM" → expect: t2, AI-Portfolio, HyperKeeper, ReAct-Agent (NOT F3 TAIL, СКИО)
# Ask: "коммерческие проекты" → expect: t2, АЛОР БРОКЕР, F3 TAIL, СКИО
# Ask: "какие есть проекты" → expect: all 7 projects
# Ask: "ML проекты" → expect: same as "проекты с LLM" (uses project_list now, not technology_usage)
# Ask: "Где применялся RAG?" → expect: technology_usage intent (unchanged behavior)
```

## Key Design Decisions

1. **Shared helper** `_collect_projects_by_tech_category()` eliminates duplication between `_projects_by_tech_category_query()` and `_list_projects_query()`
2. **Two prompt examples REPLACED** (not just added): "Какие у тебя есть проекты?" and "ML проекты" — avoids conflicting guidance
3. **Semantic rule added** to prompt: "проекты с X" → project_list; "где применялся X" → technology_usage
4. **Deterministic answer** for project_list prevents LLM from hallucinating extra projects

## What Is NOT Changed

- All existing intent handlers (`_project_details_query`, `_profile_query`, etc.)
- `_projects_by_tech_category_query()` — refactored to use helper, but **external behavior identical**
- Router (greeting/cv/off-topic routing)
- Streaming, rate-limiting, cache infrastructure
- Frontend components
- Content API
- Docker configuration
- Normalizer rules (graph returns already-filtered data)
