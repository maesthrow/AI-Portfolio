# Research: Fix Agent Answer Relevance

**Date**: 2026-02-26
**Feature**: [spec.md](spec.md)

## Research Summary

Three root causes identified for irrelevant technology answers. All confirmed by code analysis.

---

## Decision 1: Content-Level Filtering Approach

**Decision**: Filter bullet points within `fact.text` using multi-criteria keyword matching inside the normalizer, only for `technology_usage` intent.

**Rationale**:
- Current normalizer (`normalizer.py:88-99`) only filters by document TYPE (e.g., `project`, `experience_project`), not by text CONTENT
- A single `experience_project` FactItem contains ALL achievements of a project in one text blob (CV + LLM+RAG + MLOps + Backend mixed together)
- The cheapest, most reliable fix is deterministic text splitting + keyword matching — no LLM call needed
- Scope limited to `technology_usage` intent only (other intents like `project_details` and `experience_summary` inherently want ALL achievements)

**Alternatives considered**:
1. **Separate documents per achievement in seeder** — rejected: too invasive, affects all intents, requires re-ingestion pipeline changes
2. **LLM-based content filtering** — rejected: adds latency, token cost, and non-determinism for a problem solvable with keyword matching
3. **Embedding-based bullet relevance** — rejected: overkill, embedding calls add latency, simple keyword match covers 95% of cases

**Implementation approach**:
- Split `fact.text` by newline + bullet markers (`\n-`, `\n•`, `\n*`)
- Build keyword set from: (a) plan entity name ("Computer Vision"), (b) user question keywords ("компьютерное зрение"), (c) related technologies from fact metadata (`technologies` list — e.g., "Detectron2", "YOLO" for CV)
- Keep a bullet if ANY keyword matches (case-insensitive, partial match for multi-word terms)
- Preserve project header lines (project name, company, period, description) always — they provide context
- If ALL bullets are relevant, return fact unchanged (no unnecessary modification)
- If NO bullets match, exclude the entire fact from results

---

## Decision 2: Entity Flow Gap — Passing Plan Entities to Normalizer

**Decision**: Add `entity_names: list[str]` parameter to `FactNormalizer.normalize()` and pass entity names + user question from `rag_tool.py`.

**Rationale**:
- `FactsPayload` has `query` and `intents` but NO `entities` field (confirmed in `schemas.py:236-297`)
- Plan's entities (e.g., `{"name": "Computer Vision"}`) are accessible in `rag_tool.py` as `plan.entities` but never passed downstream
- The normalizer needs entity names to build the keyword set for content filtering
- Adding a lightweight parameter to `normalize()` is simpler than modifying `FactsPayload` schema (which would affect all consumers)

**Alternatives considered**:
1. **Add `entities` field to FactsPayload** — rejected: wider change surface, not needed by answer_llm or renderer
2. **Parse entity from question text only** — rejected: entity name from planner is English ("Computer Vision") while question is Russian — both are needed
3. **Store entity in normalizer constructor** — rejected: normalizer is stateless by design, per-call params are cleaner

---

## Decision 3: Conditional Surface Reduction in Tool Return

**Decision**: When `portfolio_rag_tool` returns a result with a non-empty `answer` from deterministic path, strip `rendered_facts` and `items` from the return dict.

**Rationale**:
- Current return (`rag_tool.py:332-343`) exposes ALL fields to the GigaChat agent: `answer`, `rendered_facts`, `items`, `sources`, etc.
- GigaChat sees `rendered_facts` containing ALL project bullets (including irrelevant ones) and re-synthesizes from them, ignoring the `answer` field
- AGENT_SYSTEM_PROMPT line 81 already says "Извлекай поле 'answer'... возвращай его БЕЗ ИЗМЕНЕНИЙ" — but GigaChat ignores this with rich `rendered_facts` available
- Structural fix: remove the temptation — don't expose data that should not be used
- CONDITIONAL: only strip when deterministic answer was generated (non-None). When answer falls back to LLM, keep full context for the agent to work with

**Implementation approach**:
- Track whether deterministic answer was used (already logged: `answer_llm.py:95`)
- In `rag_tool.py`, after answer generation: if deterministic, set `rendered_facts=""` and `items=[]` in the return dict
- Keep `sources`, `confidence`, `found`, `intents` — these are metadata, not raw data for re-synthesis

**Alternatives considered**:
1. **Stronger prompt engineering only** — rejected: GigaChat behavioral tendency to re-synthesize is well-known, prompts alone don't reliably prevent it
2. **Remove `rendered_facts` always** — rejected: for LLM-generated answers (non-deterministic path), the agent needs raw facts as context for formatting
3. **Custom tool return wrapper** — rejected: over-engineering, simple conditional in return dict suffices

---

## Decision 4: Rich Deterministic Answer for technology_usage

**Decision**: Rewrite `_answer_technology_usage()` to extract and include specific achievements (bullet points) related to the queried technology, not just project names.

**Rationale**:
- Current output: `"Дмитрий применял Computer Vision в проектах:\n- t2 — Нейросети"` — just project names
- This is too brief → GigaChat thinks it needs to "improve" and adds details from `rendered_facts`
- With content-filtered facts (from Decision 1), the filtered `fact.text` already contains only relevant bullets
- The deterministic answer should include these filtered bullets under each project heading

**Implementation approach**:
- After normalizer content filtering, facts contain only relevant bullets
- In `_answer_technology_usage()`: iterate filtered facts, extract project context (name, company, period) from metadata + relevant bullets from text
- Format: `"Дмитрий применял Computer Vision в проекте t2 — Нейросети (Aston, 2024–2025):\n- Внедрил сервис компьютерного зрения для ребрендинга...\n- Разработал MVP бэкенда авто-обучения и инференса CV-моделей"`
- Fallback: if no bullets extracted, fall back to project name listing (current behavior)

**Alternatives considered**:
1. **LLM-based answer enrichment** — rejected: adds cost/latency, deterministic extraction from filtered facts is sufficient and hallucination-free
2. **Keep brief answer + remove rendered_facts** — rejected: brief answer alone is still poor UX for "what experience with X" questions

---

## Decision 5: Keyword Set Construction for Multilingual Matching

**Decision**: Build matching keywords from THREE sources: (1) entity name from plan, (2) tokens from user question, (3) technology names from fact metadata.

**Rationale**:
- Entity name from planner: English — "Computer Vision"
- User question: Russian — "компьютерное зрение"
- Related techs in fact metadata: "Detectron2", "YOLO", "Ultralytics", "OpenCV", "CV"
- A bullet like "MLOps: MLflow, Celery, RabbitMQ, пайплайн автообучения... ML-моделей компьютерного зрения" should match for CV query because it mentions "компьютерного зрения" (from question keywords) even though it doesn't mention "Computer Vision" entity name
- Cross-domain bullets like "MLOps pipeline for CV models" should match for BOTH MLOps and CV queries

**Implementation approach**:
- Entity names: split by space, keep multi-word as phrase too → `["Computer", "Vision", "Computer Vision"]`
- Question keywords: extract significant words (>= 3 chars, excluding stop words) → `["опыт", "компьютерным", "зрением", "компьютерное", "зрение"]`
- Add base forms: "компьютерн" (stem) for matching "компьютерного зрения" in text
- Related techs: extract from `fact.metadata.get("technologies", [])` — filter to CV-related using a lightweight category mapping (Detectron2/YOLO/OpenCV → CV family)
- Match: bullet text contains ANY keyword (case-insensitive substring match)

---

## Technical Findings

### Data Flow (current)
```
Plan (entities) → PlanExecutor → FactsPayload (NO entities) → Normalizer (type filter only)
                                                              → AnswerLLM (project names only)
                                                              → RenderEngine → rendered_facts
→ portfolio_rag_tool return: {answer, rendered_facts, items, sources, ...}
→ GigaChat agent sees ALL fields → re-synthesizes from rendered_facts
```

### Data Flow (proposed)
```
Plan (entities) → PlanExecutor → FactsPayload → Normalizer (type + CONTENT filter)
                  ↓ entity_names                  ↓ filtered facts (relevant bullets only)
                  + question                     → AnswerLLM (rich deterministic answer)
                                                 → RenderEngine → rendered_facts
→ portfolio_rag_tool return: {answer, rendered_facts="", items=[], ...}  ← conditional strip
→ GigaChat agent sees answer only → relays as-is
```

### Key Files to Modify
1. `normalizer.py` — add content-level bullet filtering for `technology_usage`
2. `rag_tool.py` — pass entity names + question to normalizer; conditional surface reduction in return
3. `answer_llm.py` — rewrite `_answer_technology_usage()` for rich deterministic answers
4. `graph.py` — minor: strengthen AGENT_SYSTEM_PROMPT relay instruction (belt + suspenders)
5. `schemas.py` — NO changes needed (FactsPayload unchanged)

### Non-Regression Considerations
- Only `technology_usage` intent affected — other intents pass through normalizer unchanged
- Normalizer's existing type filtering (Rule 2) still runs first — content filtering is additive
- Deterministic answer fallback preserved — if no bullets match, falls back to project name listing
- LLM answer path unaffected — surface reduction only applies when deterministic answer exists
- All existing tests should pass (content filtering only applies when entity_names are provided)
