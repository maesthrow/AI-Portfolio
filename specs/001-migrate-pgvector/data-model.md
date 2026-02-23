# Data Model: Migrate ChromaDB to pgvector

**Date**: 2026-02-23
**Branch**: `001-migrate-pgvector`

## Entity: Vector Embedding Table (`portfolio_new`)

Единственная таблица, создаваемая PGVectorStore. Заменяет две таблицы
deprecated PGVector (`langchain_pg_collection` + `langchain_pg_embedding`)
и внешний ChromaDB-сервис.

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `langchain_id` | UUID | NOT NULL | `gen_random_uuid()` | PK, auto-generated |
| `content` | TEXT | NOT NULL | — | Текст документа (page_content) |
| `embedding` | vector(768) | NOT NULL | — | Вектор от multilingual-e5-base через TEI |
| `type` | TEXT | NULL | — | Dedicated metadata column: тип документа |
| `project_id` | TEXT | NULL | — | Dedicated metadata column: ID проекта |
| `ref_id` | TEXT | NULL | — | Dedicated metadata column: reference ID |
| `doc_id` | TEXT | NULL | — | Dedicated metadata column: document ID |
| `langchain_metadata` | JSON | NULL | — | Overflow: остальные метаданные (JSONB) |

### Dedicated Metadata Columns

Поля, вынесенные в отдельные колонки для быстрой SQL-фильтрации:

| Field | Reason | Used In |
|-------|--------|---------|
| `type` | Фильтр `{"type": {"$in": [...]}}` в каждом поисковом запросе | `HybridRetriever.retrieve()`, `expand_by_project()` |
| `project_id` | Compound-фильтр в `expand_by_project()` | `retrieval.py:107-110` |
| `ref_id` | Стандартное поле всех документов для идентификации | Нормализация, дедупликация |
| `doc_id` | Получение документов по ID (`fetch_by_ids`) | `retrieval.py:13-39` |

### Overflow Metadata (langchain_metadata)

Поля, хранящиеся в JSONB-колонке `langchain_metadata`:

| Field | Type | Example | Document Types |
|-------|------|---------|----------------|
| `name` | string | "AI-Portfolio" | profile, project, experience, technology |
| `slug` | string | "ai-portfolio" | project, experience |
| `company_name` | string | "Company X" | experience, experience_project |
| `company_slug` | string | "company-x" | experience, experience_project |
| `content_hash` | string | "sha1:abc123" | all |
| `technologies` | array | ["FastAPI", "Python"] | project, experience_project |
| `project_ids` | array | [1, 2, 3] | experience, technology |
| `project_slugs` | array | ["proj-a"] | experience |
| `project_names` | array | ["Proj A"] | technology |
| `start_date` | string | "2023-01" | experience |
| `end_date` | string | "2024-06" | experience |
| `is_current` | boolean | true | experience |
| `kind` | string | "commercial" | experience |
| `domain` | string | "rag" | project |
| `featured` | boolean | true | project |
| `repo_url` | string | "https://..." | project |
| `demo_url` | string | "https://..." | project |
| `period` | string | "2023-2024" | experience_project |
| `title` | string | "Article Title" | publication |
| `year` | integer | 2024 | publication |
| `source` | string | "Habr" | publication |
| `url` | string | "https://..." | publication, contact |
| `badge` | string | "Featured" | publication |
| `label` | string | "Email" | contact, stat |
| `value` | string | "user@example.com" | contact, stat |
| `is_primary` | boolean | true | contact, focus_area |
| `category` | string | "framework" | technology |
| `parent_id` | string | "experience:3" | chunked documents |
| `part` | integer | 1 | chunked documents |
| `priority` | integer | 1 | profile, experience |
| `catalog_kind` | string | "technologies_all" | catalog |

### Document Types

| Type Value | Source Entity | Typical Count |
|-----------|---------------|---------------|
| `profile` | ProfileExport | 1 |
| `experience` | CompanyExperienceExport | ~5-10 |
| `experience_project` | ExperienceProjectExport | ~10-20 |
| `project` | ProjectExport | ~5-10 |
| `technology` | TechnologyExport | ~30-50 |
| `publication` | PublicationExport | ~5-10 |
| `focus_area` | FocusAreaExport | ~3-5 |
| `work_approach` | WorkApproachExport | ~3-5 |
| `tech_focus` | TechFocusExport | ~3-5 |
| `stat` | StatExport | ~5-10 |
| `contact` | ContactExport | ~5-8 |
| `catalog` | Aggregated | ~5-10 |
| `item` | Atomic (achievements, bullets) | ~30-50 |
| **Total** | | **~120-200** |

### Document ID Format

Формат ID не меняется:
- Одночанковый: `"{type}:{ref_id}"` (e.g., `"project:5"`)
- Многочанковый: `"{type}:{ref_id}:c{idx}"` (e.g., `"experience:3:c1"`)

ID хранится в dedicated column `doc_id` для быстрого поиска.
`langchain_id` (UUID) — внутренний PK PGVectorStore, не используется
в бизнес-логике.

## Entity: Settings Changes

### Removed Fields

| Field | Old Default | Notes |
|-------|-------------|-------|
| `chroma_host` | `"localhost"` | ChromaDB HTTP host |
| `chroma_port` | `8001` | ChromaDB HTTP port |
| `chroma_collection` | `"portfolio_new"` | ChromaDB collection name |

### Added/Modified Fields

| Field | Default | Notes |
|-------|---------|-------|
| `database_url` | `"postgresql+psycopg://..."` | PostgreSQL connection (shared with content-api) |
| `collection_name` | `"portfolio_new"` | PGVectorStore table name |

### Removed Property

| Property | Notes |
|----------|-------|
| `chroma_client_kwargs` | Was unused, ChromaDB-specific |

## Relationships

```
PostgreSQL (ai_portfolio_new)
├── Content API tables (existing, unchanged)
│   ├── profiles
│   ├── company_experiences
│   ├── experience_projects
│   ├── projects
│   ├── technologies
│   ├── publications
│   ├── contacts
│   ├── stats
│   ├── tech_focuses
│   ├── hero_tags
│   ├── focus_areas
│   ├── work_approaches
│   └── section_meta
│
└── RAG API table (NEW)
    └── portfolio_new          ← PGVectorStore table
        ├── langchain_id (PK)
        ├── content
        ├── embedding (vector)
        ├── type, project_id, ref_id, doc_id (dedicated metadata)
        └── langchain_metadata (JSONB overflow)
```

Таблицы Content API и RAG API не имеют FK-связей между собой.
Связь — логическая (через `ref_id` и `project_id` в метаданных).
