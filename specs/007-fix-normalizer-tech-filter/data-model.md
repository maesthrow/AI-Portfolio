# Data Model: Fix Normalizer technology_usage Filter

**Feature**: [spec.md](spec.md) | **Date**: 2026-02-28

## Entities

This bugfix does not introduce new entities or modify existing schemas. All changes operate on existing data structures.

### FactItem (existing, unchanged)

The normalizer's input/output entity. No schema changes.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Document type: `profile`, `experience`, `technology`, `project`, `experience_project`, `technology_usage`, `focus_area`, `tech_focus`, `catalog`, etc. |
| `text` | `str` | Main fact content (full document text) |
| `metadata` | `dict[str, Any]` | Type-specific structured data |
| `source_id` | `str \| None` | Source document/entity ID |

### TECH_ABBREVIATIONS (existing, extended)

Bidirectional mapping for cross-language keyword matching.

| Canonical Name | Current Abbreviations | Added by This Feature |
|---------------|----------------------|----------------------|
| Computer Vision | компьютерное зрение, компьютерн | — |
| Machine Learning | ML, машинное обучение, машинн | — |
| Natural Language Processing | NLP, обработка естественного языка | — |
| Artificial Intelligence | AI, ИИ, искусственный интеллект | — |
| Deep Learning | DL, глубокое обучение | — |
| Named Entity Recognition | NER | — |
| Optical Character Recognition | OCR | — |
| Large Language Model | LLM, языковая модель | — |
| **AI Agents** | — | **AI-агенты, ИИ-агенты, агентные системы, агентн** |

### Type Filter Whitelist (existing, expanded)

The `technology_usage_filter` allowed types tuple.

| Type | Status | Rationale |
|------|--------|-----------|
| `technology_usage` | Existing | Direct technology usage descriptions |
| `technology` | Existing | Technology entity details |
| `project` | Existing | Project descriptions with tech stacks |
| `experience` | Existing | Work experience with achievements |
| `experience_project` | Existing | Projects within company experience |
| **`profile`** | **Added** | Contains subtitle, current_position, summary with technology mentions |
| **`focus_area`** | **Added** | Skill area descriptions with bullet-point details |
| **`tech_focus`** | **Added** | Structured tech category + tool/framework tags |
| **`catalog`** | **Added** | Technology summary catalogs (technologies_all, technologies_by_company) |

### Types Intentionally Excluded

| Type | Reason for Exclusion |
|------|---------------------|
| `stat` | Too generic ("5+ лет, Python/.NET, Backend, ML") — adds noise |
| `work_approach` | Describes methodology, not technology usage |
| `contact` | Not technology-related |
| `publication` | May mention tech but not usage context |

## Metadata Structures by Document Type

No metadata changes. Reference for test construction:

| Type | Key Metadata Fields | Has `technology`/`project` keys? |
|------|-------------------|----------------------------------|
| `profile` | `name`, `title`, `subtitle`, `current_position`, `location` | No |
| `focus_area` | `title`, `is_primary`, `bullet_count` | No |
| `tech_focus` | `label`, `tags` | No |
| `catalog` | `catalog_kind`, `technology_names`, `technology_counts` | No |
| `technology` | `category`, `slug` | Yes (`category`) |
| `experience` | `company_name`, `start_date`, `end_date` | No |

## State Transitions

N/A — No state machines or lifecycle changes in this feature.

## Validation Rules

1. The type filter tuple MUST contain all 9 types (5 existing + 4 new)
2. `TECH_ABBREVIATIONS["AI Agents"]` MUST contain at least: `"AI-агенты"`, `"ИИ-агенты"`, `"агентные системы"`
3. Zero-result fallback MUST preserve original `filtered` list when `tech_facts` is empty
