# Research: Fix Normalizer technology_usage Filter

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-28

## Research Summary

All technical unknowns resolved. This is a targeted bugfix with minimal scope — the research confirms the approach is safe and sufficient.

## Research Items

### 1. Normalizer Type Filter — Current Behavior

**Decision**: Expand the type whitelist from 5 to 9 types.

**Current code** (`normalizer.py:112-115`):
```python
tech_facts = [f for f in filtered if f.type in (
    "technology_usage", "technology", "project",
    "experience", "experience_project",
)]
```

**Proposed change**: Add `"profile"`, `"focus_area"`, `"tech_focus"`, `"catalog"` to the tuple.

**Rationale**: These 4 types contain technology competency data that is directly relevant to "what experience with X?" queries:
- `profile` — subtitle, current_position, summary mention technologies
- `focus_area` — bullet-point descriptions of skill areas (e.g., "LLM / AI-Agents / RAG")
- `tech_focus` — structured tech category + tool tags (e.g., "ML и CV: PyTorch, YOLO")
- `catalog` — `technologies_all` and `technologies_by_company` summaries

**Alternatives considered**:
- Remove type filter entirely → Rejected: would pass `stat`, `work_approach` types which add noise
- Add types dynamically based on keyword matching → Rejected: over-engineering for a 4-element addition
- Use a blocklist instead of allowlist → Rejected: allowlist is safer against future unknown types

### 2. Content-Level Filtering (Rule 2b) — False Positive Prevention

**Decision**: Rely on existing Rule 2b (`_filter_fact_bullets` + `_build_content_keywords`) — no new filtering needed.

**Rationale**: Rule 2b already runs after the type filter and performs keyword matching:
- For bullet-type facts: keeps only bullets containing the queried keyword
- For non-bullet facts (profile, catalog): checks if ANY line contains a keyword; returns `None` (reject) if not

This means a `profile` fact about "AI-агенты" survives when querying "AI agents" but is rejected when querying "PostgreSQL". Verified by reading `_filter_fact_bullets()` at lines 340-389.

**Alternatives considered**:
- Add separate content filter for new types → Rejected: Rule 2b already handles this
- Add minimum score threshold for new types → Rejected: scores are set by the retriever, not normalizer

### 3. TECH_ABBREVIATIONS — AI Agent Terms

**Decision**: Add `"AI Agents"` entry with Russian equivalents.

**Proposed entry**:
```python
"AI Agents": ["AI-агенты", "ИИ-агенты", "агентные системы", "агентн"],
```

**Rationale**: The planner generates entity name "AI agents" (English). The profile contains "AI-агенты" (Russian). Without this mapping, `_build_content_keywords` would only have "ai", "agents" as keywords — "ai" is too short (2 chars, filtered), and "agents" doesn't substring-match "агенты". The abbreviation mapping bridges this gap.

**Alternatives considered**:
- Use fuzzy matching → Rejected: TECH_ABBREVIATIONS is the established pattern (7 entries already)
- Add to planner entity extraction → Rejected: wrong layer, planner already works correctly

### 4. Zero-Result Safety Fallback

**Decision**: Add explicit fallback when type-filtering removes all facts.

**Current code** (`normalizer.py:116-118`):
```python
if tech_facts:
    filtered = tech_facts
    rules_applied.append("technology_usage_filter")
```

The `if tech_facts:` guard already prevents zero-result scenarios — if filtering removes everything, `filtered` keeps its pre-filter value. FR-003 makes this explicit and adds a log message.

**Rationale**: The existing guard is correct but implicit. Making it explicit improves maintainability and makes the safety behavior visible in logs.

**Alternatives considered**:
- Remove the guard (type filter is always applied) → Rejected: loses safety net
- Raise an exception on zero results → Rejected: violates YAGNI, zero-result is a valid degenerate case

### 5. FactItem Metadata Structure by Type

**Decision**: No metadata changes needed. New types are read-only through the normalizer.

Research into `indexing/normalizer.py` confirmed metadata structures:
- `profile` → `{name, full_name, title, subtitle, current_position, location, priority}`
- `focus_area` → `{title, is_primary, bullet_count}`
- `tech_focus` → `{label, tags}`
- `catalog` → `{catalog_kind, technology_names, technology_counts}`

None of these have `technology`/`project` keys expected by the deterministic answer path (`_answer_technology_usage`). They are safely ignored by the deterministic path and used as context by the LLM fallback.

### 6. Existing Test Infrastructure

**Decision**: Add tests to existing `TestNormalizer` class in `test_tz_v3_acceptance.py`.

Research found:
- `TestNormalizer` class at line 212 with helper `_make_facts()` for creating test FactItems
- Existing tests: `test_technology_usage_filters_to_tech_facts` (line 225), `test_experience_summary_prioritizes_experience` (line 244), `test_empty_facts_handled` (line 279)
- Pattern: create FactItems with specific types → call `normalize()` → assert filtered results

New tests needed:
1. Profile fact with matching keyword is retained for technology_usage
2. Profile fact WITHOUT matching keyword is filtered out
3. Focus_area/tech_focus facts are retained when relevant
4. Zero-result fallback preserves unfiltered facts
5. TECH_ABBREVIATIONS correctly maps "AI Agents" ↔ "AI-агенты"

### 7. Deterministic Answer Path Compatibility

**Decision**: No changes to `answer_llm.py`. New fact types are handled correctly.

Research into `answer_llm.py:_answer_technology_usage()` (line 266):
- Iterates facts looking for `metadata.get("technology")` or `metadata.get("name")` with `metadata.get("project_names")`
- Profile/focus_area/tech_focus facts don't have these keys → safely skipped
- If deterministic path yields nothing, falls back to LLM which benefits from seeing the additional context

No code changes needed in the answer layer.
