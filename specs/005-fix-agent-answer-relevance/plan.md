# Implementation Plan: Fix Agent Answer Relevance

**Branch**: `005-fix-agent-answer-relevance` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-fix-agent-answer-relevance/spec.md`

## Summary

The RAG agent includes irrelevant facts in technology-specific answers (e.g., "LLM+RAG assistant for fines" appears when asking about "Computer Vision" experience). Three root causes: (1) normalizer filters by document type, not content; (2) GigaChat agent re-synthesizes from raw `rendered_facts` instead of using the pre-generated `answer` field; (3) deterministic answer for `technology_usage` is too brief (project names only, no achievements).

**Technical approach**: Add content-level bullet filtering in normalizer using multi-criteria keyword matching (entity name + question keywords + related technologies), enrich the deterministic answer generator to include filtered achievements, and conditionally strip raw data from tool return to prevent agent re-synthesis. All changes scoped to `technology_usage` intent only.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, LangChain 1.x, LangGraph 1.x, langchain_gigachat
**Storage**: PostgreSQL 16 with pgvector (shared), Redis (cache)
**Testing**: pytest (`services/rag-api-new/tests/`)
**Target Platform**: Linux server (Docker)
**Project Type**: Web service (RAG API microservice)
**Performance Goals**: Response latency for technology queries within 10% of current (~90s total including TEI embedding)
**Constraints**: No additional LLM calls for filtering (deterministic only), no schema changes to FactsPayload
**Scale/Scope**: 4 files modified in `services/rag-api-new/app/agent/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| UTF-8 encoding | PASS | No new files with Cyrillic content requiring encoding changes |
| Root-cause resolution | PASS | Addresses all 3 root causes (normalizer, surface reduction, answer enrichment) |
| Clean architecture | PASS | Changes are within existing module boundaries (normalizer, rag_tool, answer_llm) |
| Service directory discipline | PASS | All changes in `services/rag-api-new/` (active service) |
| API versioning | PASS | No new API endpoints — internal pipeline changes only |
| DB migration discipline | PASS | No database schema changes |
| Simplicity/YAGNI | PASS | Keyword matching is simplest viable approach; no LLM-based filtering or embedding comparison |

**Post-Phase 1 re-check**: PASS — no violations introduced by design decisions.

## Project Structure

### Documentation (this feature)

```text
specs/005-fix-agent-answer-relevance/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (completed)
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (files to modify)

```text
services/rag-api-new/app/agent/
├── normalizer/
│   └── normalizer.py        # Add content-level bullet filtering (Rule 2 enhancement)
├── answer/
│   └── answer_llm.py        # Rewrite _answer_technology_usage() for rich answers
├── rag_tool.py              # Pass entity names; conditional surface reduction
└── graph.py                 # Strengthen AGENT_SYSTEM_PROMPT relay instruction

```

**Structure Decision**: Existing microservice structure. All changes within `services/rag-api-new/app/agent/` — no new modules, no structural changes. No new test files — validation through existing test suite + manual acceptance testing.

## Implementation Layers

### Layer 1: Content-Level Filtering (normalizer.py) — P1

**What**: Add bullet-point level filtering within `fact.text` for `technology_usage` intent.

**Where**: `normalizer.py` Rule 2 section (lines 88-99), new helper methods.

**How**:
1. Add `entity_names: list[str] | None` and `question: str | None` params to `normalize()`
2. After existing type filter (Rule 2), add content filter:
   - Build keyword set from entity names + question tokens + related tech names
   - For each fact: split text into header lines and bullet lines
   - Keep bullets that match any keyword (case-insensitive substring)
   - Preserve header lines always (project name, company, period)
   - If no bullets match → exclude fact entirely
   - If all bullets match → keep fact unchanged
3. New rule name: `technology_usage_content_filter`
4. Also update convenience function `normalize_facts()` to pass through new params

**Keywords construction**:
- Entity names: split multi-word + keep full phrase → `["Computer", "Vision", "Computer Vision", "CV"]`
- Question tokens: significant words ≥ 3 chars → `["компьютерн", "зрени"]` (stemmed)
- Related techs from metadata: `fact.metadata.get("technologies", [])` → filter to known CV-family techs
- Add common abbreviations mapping: "Computer Vision" → also match "CV", "компьютерное зрение" → also match "компьютерн"

### Layer 2: Surface Reduction (rag_tool.py) — P1

**What**: Conditionally remove `rendered_facts` and `items` from tool return when deterministic answer was generated.

**Where**: `rag_tool.py` lines 296-343.

**How**:
1. Track `deterministic_used` flag from answer generation — currently `generate()` returns a 2-tuple `(answer, usage)` for both paths, so the flag must be added explicitly
2. Modify AnswerLLM.generate() to return a 3-tuple `(answer, usage, deterministic_used: bool)`
3. In rag_tool.py return dict: if `deterministic_used`, set `rendered_facts=""` and `items=[]`
4. Pass `entity_names` (from `plan.entities`) and `question` to normalizer call

### Layer 3: Rich Deterministic Answer (answer_llm.py) — P2

**What**: Rewrite `_answer_technology_usage()` to include specific achievements from filtered facts.

**Where**: `answer_llm.py` lines 265-362.

**How**:
1. Iterate filtered facts (which now contain only relevant bullets after Layer 1)
2. For each fact with type `project` or `experience_project`:
   - Extract project context: name, company, period from metadata
   - Extract bullet points from `fact.text` (lines starting with `- `)
   - Format as: `project_name (company, period):\n- bullet1\n- bullet2`
3. For `technology_usage` type facts (from graph): include as context line
4. Fallback: if no structured extraction possible, fall back to current behavior (project name listing)
5. `generate()` returns 3-tuple `(answer, usage, deterministic_used)` — see Layer 2

### Layer 4: Prompt Strengthening (graph.py) — P1

**What**: Strengthen AGENT_SYSTEM_PROMPT to more forcefully instruct answer relay.

**Where**: `graph.py` lines 81-83.

**How**: Update the existing instruction at line 81 to be more explicit:
```
- КРИТИЧЕСКИ ВАЖНО: Поле "answer" из результата portfolio_rag_tool — это ГОТОВЫЙ ФИНАЛЬНЫЙ ОТВЕТ.
  Верни его пользователю КАК ЕСТЬ. НЕ добавляй информацию из других полей (rendered_facts, items).
  НЕ перефразируй и НЕ дополняй ответ.
```

This is a belt-and-suspenders measure alongside the structural surface reduction.

## Complexity Tracking

> No Constitution Check violations — table not needed.

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Keyword matching too aggressive (removes relevant bullets) | Low | Medium | Err on inclusion: match ANY keyword, use substring not exact word |
| Keyword matching too loose (keeps irrelevant bullets) | Low | Low | Multi-criteria keywords cover most cases; remaining edge cases are acceptable |
| GigaChat still re-synthesizes despite surface reduction | Low | Medium | Prompt strengthening + empty rendered_facts makes re-synthesis impossible |
| Regression in other intents | Very Low | High | Content filter ONLY activates for technology_usage + non-empty entity_names |
| Performance degradation from text splitting | Very Low | Low | String operations are O(n) on small texts (~500 chars), negligible vs LLM calls |
