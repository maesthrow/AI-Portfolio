# Implementation Plan: Fix Normalizer technology_usage Filter

**Branch**: `007-fix-normalizer-tech-filter` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-fix-normalizer-tech-filter/spec.md`

## Summary

The normalizer's `technology_usage_filter` (Rule 2) drops `profile`, `focus_area`, `tech_focus`, and `catalog` document types, causing the RAG agent to miss crucial technology competency data. The fix expands the type whitelist, extends `TECH_ABBREVIATIONS` for AI agent terms, and adds a zero-result safety fallback. The existing content-level keyword filtering (Rule 2b) prevents false positives — no new filtering mechanism needed.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, LangChain 1.x, LangGraph 1.x, Pydantic
**Storage**: PostgreSQL 16 with pgvector (shared with content-api)
**Testing**: pytest (existing test suite in `services/rag-api-new/tests/`)
**Target Platform**: Linux Docker container (local dev on Windows)
**Project Type**: Web service (RAG API microservice)
**Performance Goals**: No performance impact — change is in-memory list filtering only
**Constraints**: Deterministic normalizer logic, no LLM calls in modified code paths
**Scale/Scope**: Single file modification (`normalizer.py`), ~15 lines of code changes + tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | No new files with Cyrillic. Russian strings in `TECH_ABBREVIATIONS` follow existing pattern. |
| II. Root-Cause Resolution | PASS | Fix targets the root cause (overly restrictive type filter), not symptoms. Regression analysis completed in spec. |
| III. Clean Architecture | PASS | Minimal change to existing code. No new abstractions, no new patterns. Extends existing tuple + existing dict. |
| IV. Service Directory Discipline | PASS | All changes in `services/rag-api-new/`. No deprecated directories touched. |
| V. API Versioning | N/A | No API endpoint changes. Internal normalizer logic only. |
| VI. Database Migration | N/A | No SQLAlchemy model changes. No Alembic migrations needed. |
| VII. Simplicity & YAGNI | PASS | Adds 4 types to a tuple, 1 entry to a dict, 1 safety guard. No over-engineering. |

**Gate result**: ALL PASS. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-fix-normalizer-tech-filter/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
services/rag-api-new/
├── app/
│   └── agent/
│       └── normalizer/
│           ├── normalizer.py        # PRIMARY: type filter + TECH_ABBREVIATIONS + safety fallback
│           └── fact_bundle.py       # NO CHANGES (read-only reference)
└── tests/
    └── test_tz_v3_acceptance.py     # ADD: new normalizer tests for expanded types
```

**Structure Decision**: Single-file bugfix in existing service. All changes confined to `normalizer.py` (production code) and `test_tz_v3_acceptance.py` (tests). No new files, no new modules, no structural changes.

## Complexity Tracking

> No violations. All changes align with Constitution Principle VII (Simplicity).
