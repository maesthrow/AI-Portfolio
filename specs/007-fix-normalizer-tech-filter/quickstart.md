# Quickstart: Fix Normalizer technology_usage Filter

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-28

## Overview

This is a single-file bugfix in the normalizer module. The change expands the `technology_usage_filter` type whitelist, adds AI agent terms to `TECH_ABBREVIATIONS`, and makes the zero-result safety fallback explicit.

## Prerequisites

- Python 3.12+
- Repository cloned with `services/rag-api-new/` accessible
- pytest available (`pip install pytest` or via project's `pyproject.toml`)

## Files to Modify

| File | Change Type | Description |
|------|------------|-------------|
| `services/rag-api-new/app/agent/normalizer/normalizer.py` | MODIFY | Expand type filter, add TECH_ABBREVIATIONS entry, explicit fallback |
| `services/rag-api-new/tests/test_tz_v3_acceptance.py` | MODIFY | Add new normalizer tests |

## Implementation Steps

### Step 1: Add AI Agents to TECH_ABBREVIATIONS

In `normalizer.py`, add to the `TECH_ABBREVIATIONS` dict (after "Large Language Model" entry):

```python
"AI Agents": ["AI-агенты", "ИИ-агенты", "агентные системы", "агентн"],
```

### Step 2: Expand Type Filter

In `normalizer.py`, replace the type tuple in the `technology_usage` block (~line 112):

```python
# Before:
tech_facts = [f for f in filtered if f.type in (
    "technology_usage", "technology", "project",
    "experience", "experience_project",
)]

# After:
tech_facts = [f for f in filtered if f.type in (
    "technology_usage", "technology", "project",
    "experience", "experience_project",
    "profile", "focus_area", "tech_focus", "catalog",
)]
```

### Step 3: Make Zero-Result Fallback Explicit

The existing `if tech_facts:` guard already prevents zero-result scenarios. Add a log message for the fallback case:

```python
if tech_facts:
    filtered = tech_facts
    rules_applied.append("technology_usage_filter")
else:
    logger.warning(
        "technology_usage_filter: type filter removed all %d facts, keeping unfiltered",
        len(filtered),
    )
    rules_applied.append("technology_usage_filter_fallback")
```

### Step 4: Add Tests

Add test cases to `TestNormalizer` in `test_tz_v3_acceptance.py`:
1. Profile fact with matching keyword → retained
2. Profile fact without keyword → filtered out by Rule 2b
3. Focus_area/tech_focus/catalog facts retained when relevant
4. Zero-result fallback works
5. TECH_ABBREVIATIONS maps "AI Agents" correctly

## Verification

```bash
cd services/rag-api-new
pytest tests/test_tz_v3_acceptance.py -v -k "TestNormalizer"
```

All existing tests must pass. New tests must cover the 5 scenarios above.

## Manual Testing

After deploying to local Docker:

1. Ask: "какой опыт с ИИ агентами" → Should return substantive answer about AI agents work
2. Ask: "какой опыт с машинным обучением" → Should include PyTorch, YOLO, etc. from tech_focus
3. Ask: "где используется PostgreSQL" → Should NOT include profile (no false positives)
4. Ask: "расскажи про опыт с RAG" → Should include profile and focus_area data
