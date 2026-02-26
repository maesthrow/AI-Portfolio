# Data Model: Fix Agent Answer Relevance

**Date**: 2026-02-26
**Feature**: [spec.md](spec.md)

## Entities

### Existing Entities (unchanged)

#### FactItem
- **Location**: `services/rag-api-new/app/agent/planner/schemas.py:201-226`
- **Fields**: `type: str`, `text: str`, `metadata: dict[str, Any]`, `source_id: str | None`
- **Role**: Atomic unit of retrieved information. Contains full document text in `text` field.
- **Note**: `text` field for `project`/`experience_project` types contains ALL achievements as bullet points (mixed technologies). This is the source of the relevance problem.

#### FactsPayload
- **Location**: `services/rag-api-new/app/agent/planner/schemas.py:236-297`
- **Fields**: `found`, `items: list[FactItem]`, `groups`, `meta`, `sources`, `query`, `intents`, `render_style`, `answer_style`, `warnings`
- **Role**: Container passed from PlanExecutor → Normalizer → AnswerLLM
- **Gap**: No `entities` field — plan entities not passed through. Fix does NOT add field (passed via normalizer param instead).

#### NormalizerOutput
- **Location**: `services/rag-api-new/app/agent/planner/schemas_v3.py:434-455`
- **Fields**: `filtered_facts: list[FactBundleItem]`, `removed_count: int`, `rules_applied: list[str]`, `rendered_text: str`
- **Role**: Output of normalizer with filtered facts and audit trail

#### QueryPlanV3.entities
- **Location**: `services/rag-api-new/app/agent/planner/schemas_v3.py:251-376`
- **Type**: `list[dict[str, Any]]`
- **Example**: `[{"type": "technology", "id": "technology:computer-vision", "name": "Computer Vision", "confidence": 0.95}]`
- **Role**: Extracted technology entity from planner. The `name` field provides the English entity name for keyword matching.

### Modified Entities

#### FactNormalizer.normalize() — Extended Signature

**Current**:
```python
def normalize(self, facts, intent, tech_filter=None, max_items=20) -> NormalizerOutput
```

**Proposed**:
```python
def normalize(self, facts, intent, tech_filter=None, max_items=20,
              entity_names=None, question=None) -> NormalizerOutput
```

New parameters:
- `entity_names: list[str] | None` — Technology entity names from planner (e.g., `["Computer Vision"]`)
- `question: str | None` — Original user question for keyword extraction

These are optional and only used when `intent == "technology_usage"`.

#### portfolio_rag_tool Return Dict — Conditional Fields

**Current** (always returns all fields):
```python
return {
    "answer": answer,
    "rendered_facts": rendered,
    "items": [item.model_dump() for item in payload.items],
    "sources": [...],
    "confidence": ..., "found": ..., "intents": ..., ...
}
```

**Proposed** (conditional surface reduction):
```python
result = {
    "answer": answer,
    "rendered_facts": rendered if not deterministic_used else "",
    "items": [item.model_dump() ...] if not deterministic_used else [],
    "sources": [...],
    "confidence": ..., "found": ..., "intents": ..., ...
}
```

When `deterministic_used=True`: `rendered_facts=""`, `items=[]` — prevents agent re-synthesis.
When `deterministic_used=False`: full context preserved for agent LLM to work with.

## Data Flow

### Content Filtering Flow (new)

```
FactItem.text (multi-bullet):                    Keywords (from 3 sources):
"Проект: t2 — Нейросети                          entity_names: ["Computer Vision"]
Компания: Aston                                   question_keywords: ["компьютерн", "зрени"]
Период: 2024 — 2025                               related_techs: ["Detectron2", "YOLO", "CV"]
Достижения:
- Внедрил сервис компьютерного зрения...  ✓ matches "компьютерн"
- Создал умного помощника с LLM + RAG...  ✗ no keyword match
- Разработал MVP бэкенда... CV-моделей.   ✓ matches "CV"
"
                    ↓
Filtered FactItem.text:
"Проект: t2 — Нейросети
Компания: Aston
Период: 2024 — 2025
Достижения:
- Внедрил сервис компьютерного зрения...
- Разработал MVP бэкенда... CV-моделей."
```

### Header vs Bullet Classification

Lines in `fact.text` are classified as:
- **Header lines**: Project name, company, period, description — ALWAYS preserved
- **Bullet lines**: Lines starting with `- ` or `• ` — filtered by keyword relevance

Heuristic: A line is a bullet if it starts with `- ` or `• ` (after trimming). Everything else is a header/context line.

## Validation Rules

1. Content filtering ONLY activates when `intent == "technology_usage"` AND `entity_names` is non-empty
2. If ALL bullets in a fact match keywords → return fact unchanged
3. If NO bullets in a fact match keywords → exclude fact entirely
4. If SOME bullets match → return fact with only matching bullets (headers preserved)
5. Empty `entity_names` or `question` → skip content filtering, fall back to type-only filter
6. Keyword matching is case-insensitive substring match (not exact word boundary)
