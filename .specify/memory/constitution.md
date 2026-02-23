<!--
  ============================================================
  SYNC IMPACT REPORT
  ============================================================
  Version change: N/A (initial) → 1.0.0
  Bump rationale: MAJOR — first ratification of project constitution

  Added principles:
    - I.   UTF-8 Encoding (NON-NEGOTIABLE)
    - II.  Root-Cause Resolution (NON-NEGOTIABLE)
    - III. Clean Architecture (SOLID / DRY / KISS)
    - IV.  Service Directory Discipline
    - V.   API Versioning & Contracts
    - VI.  Database Migration Discipline
    - VII. Simplicity & YAGNI

  Added sections:
    - Technology Stack & Constraints
    - Development Workflow

  Removed sections: none (initial constitution)

  Templates requiring updates:
    - .specify/templates/plan-template.md        ✅ compatible (Constitution Check generic)
    - .specify/templates/spec-template.md         ✅ compatible (no principle-specific refs)
    - .specify/templates/tasks-template.md        ✅ compatible (no principle-specific refs)
    - .specify/templates/checklist-template.md    ✅ compatible
    - .specify/templates/agent-file-template.md   ✅ compatible

  Deferred items: none
  ============================================================
-->

# AI-Portfolio Constitution

## Core Principles

### I. UTF-8 Encoding (NON-NEGOTIABLE)

All source files, configuration, templates, and documentation MUST be
encoded as UTF-8 **without BOM**. This is critical because the project
contains extensive Russian (Cyrillic) text in markdown fields, prompts,
seed data, and agent responses.

- NEVER use Windows-1251, ANSI, or any other encoding.
- Python strings MUST use plain literals: `text = "Корректный русский текст"`.
- Every tool and contributor MUST verify encoding correctness before
  committing. Broken Cyrillic (`????`, `\u041f` escapes, mojibake)
  is a blocking defect.

### II. Root-Cause Resolution (NON-NEGOTIABLE)

Every bug fix and behavioral change MUST address the **root cause**, not
the symptom.

- No workarounds, temporary patches, or "just in case" guards.
- Methodical debugging: reproduce → trace → understand WHY → design
  proper fix → verify no regressions.
- Question assumptions — if behavior is unexpected, verify your
  understanding of the system before adding code.
- Fix once, fix right. Time spent understanding the issue prevents
  repeated fixes.

### III. Clean Architecture (SOLID / DRY / KISS)

All code MUST follow clean-code principles:

- **SOLID**: Single responsibility, open/closed, Liskov substitution,
  interface segregation, dependency inversion.
- **DRY**: Eliminate meaningful duplication. Three similar lines are
  acceptable if an abstraction would be premature.
- **KISS**: Prefer the simplest correct solution. No unnecessary
  constructs, extra abstractions, or defensive code "just in case".
- Separate business logic from API controllers (routers).
- No circular imports in backend services.

### IV. Service Directory Discipline

The project uses a microservices layout with **active** service
directories. Contributors MUST use:

- `frontend-new/` — Active Next.js frontend
- `services/content-api-new/` — Active Content API
- `services/rag-api-new/` — Active RAG & Agent API

The following directories have been **deleted** and MUST NOT be
referenced: `frontend/`, `services/content-api/`, `services/rag-api/`.
If code accidentally targets a deleted directory, work MUST stop and
switch to the correct active directory immediately.

### V. API Versioning & Contracts

All HTTP endpoints MUST be versioned under the `/api/v1/` prefix.

- Pydantic schemas MUST validate all request/response payloads.
- CORS origins MUST be explicitly configured via environment variables
  (`FRONTEND_ORIGIN`). No wildcards in production.
- API URLs MUST NOT be hardcoded — use environment variables.
- Breaking changes MUST increment the version prefix.

### VI. Database Migration Discipline

When SQLAlchemy models in `content-api-new` are modified:

- An Alembic migration MUST be created:
  `alembic revision --autogenerate -m "description"`.
- Old migrations MUST NEVER be modified — create new ones.
- Run `alembic current` before generating to avoid conflicts.
- Migrations live in `services/content-api-new/alembic/versions/`.

### VII. Simplicity & YAGNI

Only make changes that are directly requested or clearly necessary.

- Do NOT add features, refactor surrounding code, or make
  "improvements" beyond the scope of the task.
- Do NOT add error handling, fallbacks, or validation for scenarios
  that cannot occur. Trust internal code and framework guarantees.
- Do NOT create helpers, utilities, or abstractions for one-time
  operations.
- Do NOT design for hypothetical future requirements.
- A bug fix does not need surrounding code cleaned up. A simple
  feature does not need extra configurability.

## Technology Stack & Constraints

The following technology choices are non-negotiable for the project:

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Frontend | Next.js 14 + React 18 + TypeScript | Tailwind CSS, Framer Motion |
| Backend API | FastAPI + SQLAlchemy 2.0 | Python 3.12+ |
| RAG Pipeline | LangChain 1.x + LangGraph 1.x | pgvector, sentence-transformers |
| LLM Infra | LiteLLM proxy, vLLM (Qwen), TEI | Multi-provider: GigaChat, DeepSeek, Qwen |
| Database | PostgreSQL 16 | Alembic migrations |
| Cache / Rate Limit | Redis | Fail-closed rate limiter, fail-open cache |
| Orchestration | Docker Compose | `infra/docker-compose.local.yaml` |

Additional constraints:

- Naming: Python `snake_case` functions/variables, `PascalCase` classes,
  `snake_case.py` files. TypeScript `PascalCase.tsx` components,
  `camelCase.ts` utilities.
- Frontend components MUST be deterministic. Tailwind classes in JSX.
  No inline styles except for animations.
- Markdown fields (`*_md`) rendered with `react-markdown` + `remark-gfm`.
- No emojis in code or UI unless explicitly requested.
- Docker internal networking: services communicate via service names
  (e.g., `postgres:5432`, `litellm:4000`, `tei:80`).

## Development Workflow

### Before Starting Work

1. Verify you are targeting the correct active service directories
   (`*-new` variants).
2. Check `discource/` for existing technical specs (ТЗ) before
   implementing new features.
3. Read existing code before proposing modifications.

### During Development

1. Only modify files explicitly required by the task.
2. Maintain existing project structure — no restructuring without
   explicit permission.
3. Use SQLAlchemy ORM and Pydantic schemas for all data operations.
4. Ensure all text is UTF-8 without BOM (especially Cyrillic).

### Before Committing

1. Verify modified files are in the correct `*-new` service directories.
2. Check for broken Cyrillic characters (`????` or `\u041f`).
3. Run Alembic migration if any SQLAlchemy models changed.
4. Test API endpoints with the correct `/api/v1/` prefix.
5. Verify CORS settings if frontend–backend communication is affected.
6. Test locally before committing.

### Technical Specs

- Technical requirements (ТЗ) live in `discource/docs/`.
- Implementation specifications live in `discource/specs/`.
- Create a new spec before starting complex implementations.

## Governance

This constitution is the authoritative source for project-wide
development principles. It supersedes ad-hoc conventions and informal
practices.

- **Compliance**: All code changes, reviews, and architectural
  decisions MUST verify compliance with these principles.
- **Amendments**: Any change to this constitution MUST be documented
  with a version bump, rationale, and sync impact report (see header
  comment). Amendments follow semantic versioning:
  - MAJOR: Principle removal or incompatible redefinition.
  - MINOR: New principle or materially expanded guidance.
  - PATCH: Clarification, wording, or typo fix.
- **Runtime guidance**: See `CLAUDE.md` at repository root for
  comprehensive development guidance and architectural documentation.
- **Complexity justification**: Any deviation from Principle VII
  (Simplicity) MUST be explicitly justified in the relevant spec
  or plan document.
- **Review cadence**: Constitution SHOULD be reviewed when major
  architectural changes are introduced (new services, new LLM
  providers, new deployment targets).

**Version**: 1.0.0 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
