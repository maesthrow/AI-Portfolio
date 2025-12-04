# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ CRITICAL: Active Service Directories

**ALWAYS use these directories:**
- ✅ `frontend-new/` - Active Next.js frontend (cyberpunk theme)
- ✅ `services/content-api-new/` - Active Content API with versioned endpoints
- ✅ `services/rag-api/` - Active RAG & Agent API
- ✅ `infra/compose.apps.yaml` - Active Docker Compose configuration

**NEVER use these directories (deprecated):**
- ❌ `frontend/` - Old frontend (deprecated)
- ❌ `services/content-api/` - Old Content API (deprecated)
- ❌ `infra/docker-compose.yaml` - Old Docker Compose (deprecated)

If you accidentally work with deprecated directories, **STOP** and switch to the correct active directories immediately.

---

## Project Overview

**AI-Portfolio** is a microservices-based cyberpunk-themed portfolio application with RAG (Retrieval-Augmented Generation) capabilities. The system consists of a Next.js frontend, PostgreSQL database, FastAPI backend services, and ChromaDB vector database for semantic search with LangGraph-powered agent.

**Tech Stack:**
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Framer Motion, react-markdown
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic
- RAG: LangChain, LangGraph, ChromaDB, sentence-transformers
- LLM Infrastructure: LiteLLM proxy, vLLM (Qwen2.5-7B-Instruct-AWQ), TEI (multilingual-e5-base embeddings)
- Database: PostgreSQL 16
- Infrastructure: Docker Compose

---

## Architecture

The project follows a microservices architecture with these key services:

### 1. **Content API** (`services/content-api-new/`)
**IMPORTANT: Use `content-api-new`, NOT `content-api` (old version)**

- Manages structured portfolio data with versioned REST API
- SQLAlchemy ORM with Alembic migrations
- Versioned API: all endpoints prefixed with `/api/v1/`
- Entry point: `app/main.py`
- Port: 8003

Key modules:
- `app/models/` - SQLAlchemy models:
  - `profile.py` - Profile (full_name, title, subtitle, summary_md)
  - `experience.py` - CompanyExperience (role, company, dates, kind, projects)
  - `experience_project.py` - ExperienceProject (projects within company experience)
  - `project.py` - Project (standalone projects with slug, technologies, featured flag)
  - `publication.py` - Publication (articles, blog posts)
  - `contact.py` - Contact (email, telegram, github, linkedin)
  - `stats.py` - Stat (key metrics for display)
  - `tech_focus.py` - TechFocus (technology focus areas)
  - `technology.py` - Technology (tech stack items)
- `app/routers/` - API endpoints:
  - `profile.py` - GET `/api/v1/profile`
  - `experience.py` - GET `/api/v1/experience`, GET `/api/v1/experience/{slug}`
  - `stats.py` - GET `/api/v1/stats`
  - `tech_focus.py` - GET `/api/v1/tech-focus`
  - `projects.py` - GET `/api/v1/projects`
  - `publications.py` - GET `/api/v1/publications`
  - `contacts.py` - GET `/api/v1/contacts`
  - `rag.py` - GET `/api/v1/rag/documents` (exports data for RAG indexing)
- `alembic/` - Database migrations

### 2. **RAG API** (`services/rag-api/`)
- Semantic search and question answering over portfolio data
- LangGraph agent with memory (ReAct pattern)
- Hybrid retrieval: dense embeddings + BM25
- Cross-encoder reranking
- Streaming chat interface
- Entry point: `app/main.py`
- Port: 8004

Key modules:
- `app/rag/core.py` - Main RAG pipeline (`portfolio_rag_answer`)
- `app/rag/retrieval.py` - `HybridRetriever` (dense + BM25)
- `app/rag/rank.py` - Cross-encoder reranking
- `app/rag/evidence.py` - Evidence selection and context packing
- `app/agent/graph.py` - LangGraph agent with tools
- `app/agent/tools.py` - RAG tools for the agent
- Agent endpoints:
  - POST `/api/v1/agent/chat/stream` - Streaming chat with agent

### 3. **Frontend** (`frontend-new/`)
**IMPORTANT: Use `frontend-new`, NOT `frontend` (old version)**

- Next.js 14 with App Router
- Server-side rendering (SSR)
- Cyberpunk-themed UI with Framer Motion animations
- react-markdown for rendering markdown content
- Entry point: `app/page.tsx`
- Port: 3000

Key structure:
- `app/page.tsx` - Main landing page (fetches all data via API)
- `app/layout.tsx` - Root layout with AgentDock
- `components/` - Modular components:
  - `agent/AgentDock.tsx` - Global floating chat with RAG agent
  - `agent/AgentChatWindow.tsx` - Chat window UI
  - `agent/AgentInput.tsx` - Message input
  - `agent/AgentMessageList.tsx` - Message display with streaming
  - `hero/HeroIntro.tsx` - Hero section
  - `about/AboutMeSection.tsx` - About section with stats
  - `experience/ExperienceSection.tsx` - Experience timeline
  - `tech/TechFocusSection.tsx` - Technology focus areas
  - `projects/ProjectsSection.tsx` - Featured projects
  - `publications/PublicationsSection.tsx` - Articles/publications
  - `contacts/ContactsSection.tsx` - Contact information
  - `layout/Shell.tsx`, `layout/Footer.tsx` - Layout components
- `lib/api.ts` - API client functions
- `lib/types.ts` - TypeScript type definitions

### 4. **Infrastructure** (`infra/`)
- Docker Compose orchestration (compose.apps.yaml)
- Services:
  - PostgreSQL (external, accessed via host.docker.internal)
  - ChromaDB (vector database)
  - vLLM (Qwen2.5-7B-Instruct-AWQ via OpenAI-compatible API)
  - TEI (Text Embeddings Inference for multilingual-e5-base)
  - LiteLLM (unified proxy for LLM/embeddings)
  - content-api-new (port 8003)
  - rag-api (port 8004)

---

## Development Commands

### Frontend (frontend-new)

```bash
cd frontend-new

npm run dev          # Start development server (default port 3000)
npm run build        # Build for production
npm start            # Start production server
npm run lint         # Run ESLint
```

Environment variables (`.env.local`):
```bash
NEXT_PUBLIC_CONTENT_API_BASE=http://localhost:8003/api/v1
NEXT_PUBLIC_AGENT_API_BASE=http://localhost:8004
```

### Content API (content-api-new)

```bash
cd services/content-api-new

# Run the API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

Environment variables:
```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5433/ai_portfolio_new
FRONTEND_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO
APP_ENV=dev
```

### RAG API

```bash
cd services/rag-api

# Run the API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ingest documents into ChromaDB (after content-api is populated)
# Use the /api/v1/rag/documents endpoint from content-api
```

Environment variables:
```bash
litellm_base_url=http://localhost:8005/v1
litellm_api_key=dev-secret-123
chat_model=GigaChat
embedding_model=embedding-default
CHROMA_HOST=localhost
CHROMA_PORT=8001
FRONTEND_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO
```

### Docker Infrastructure

```bash
cd infra

# Start all services (recommended)
docker compose -f compose.apps.yaml up -d

# Start specific services
docker compose -f compose.apps.yaml up -d chroma tei litellm
docker compose -f compose.apps.yaml up -d content-api rag-api

# Check service health
docker compose -f compose.apps.yaml ps

# View logs
docker compose -f compose.apps.yaml logs -f content-api
docker compose -f compose.apps.yaml logs -f rag-api

# Rebuild and restart
docker compose -f compose.apps.yaml up -d --build content-api
```

### Running Tests

Currently no test suite is configured. When adding tests, use:
- Backend: `pytest` (to be added to pyproject.toml)
- Frontend: Jest/React Testing Library (to be added)

---

## Critical Rules (from CONTRIBUTING.md)

### Encoding (STRICT)
- **All files MUST be UTF-8 without BOM**
- Never use Windows-1251, ANSI, or broken Cyrillic encoding
- Python strings: use plain strings `text = "Корректный русский текст"`
- AI tools MUST verify encoding correctness before committing changes

### Database Migrations
- **Always create Alembic migration** when modifying SQLAlchemy models
- **Never modify old migrations** - create new ones
- Generate: `alembic revision --autogenerate -m "message"`
- Location: `services/content-api/app/alembic/versions/`

### Naming Conventions
- Python: `snake_case` for functions/variables, `PascalCase` for classes, `snake_case.py` for files
- TypeScript/React: `PascalCase.tsx` for components, `useX.ts` for hooks, `camelCase.ts` for utilities

### Code Changes
- Only modify files explicitly mentioned in the task
- Maintain existing project structure
- No circular imports in backend
- Separate business logic from controllers
- Use SQLAlchemy ORM and Pydantic schemas

### Frontend
- Components must be deterministic
- Use Tailwind CSS classes in JSX
- Avoid inline styles except for animations
- No emojis unless explicitly requested

---

## Data Flow

1. **Content Management**: Admin/scripts → PostgreSQL (via content-api-new)
2. **RAG Ingestion**: content-api-new `/api/v1/rag/documents` → ChromaDB indexing
3. **Frontend SSR**: Next.js → content-api-new `/api/v1/*` → PostgreSQL → JSON response
4. **Agent Chat**: User → frontend-new AgentDock → rag-api `/api/v1/agent/chat/stream` → LangGraph agent
5. **RAG Query Flow**: Agent tool call → Hybrid retrieval (dense + BM25) → Rerank → Evidence selection → LLM generation

---

## Key Architectural Patterns

### RAG Pipeline
The RAG system uses a sophisticated retrieval pipeline:
1. **Hybrid Retrieval**: Combines dense embeddings (semantic) with BM25 (keyword-based)
2. **Reranking**: Cross-encoder scores candidates for relevance
3. **Evidence Selection**: Picks top-k documents with diversity
4. **Context Packing**: Fits selected evidence into token budget
5. **LLM Generation**: Uses packed context to generate answer

See `services/rag-api/app/rag/core.py:portfolio_rag_answer()`

### Agent System
The LangGraph agent (`services/rag-api/app/agent/graph.py`) uses ReAct pattern:
- System prompt enforces RAG tool usage for portfolio questions
- Memory via `MemorySaver` checkpointer (thread_id based)
- Tools: `portfolio_rag_tool`, `list_projects_tool`
- Agent MUST call RAG tool for any portfolio-related questions

### Database Models
Key models and relationships (`services/content-api-new/app/models/`):

**Profile** (`profile.py`):
- Single instance storing personal info (full_name, title, subtitle, location, status, avatar_url, summary_md)

**CompanyExperience** (`experience.py`):
- Work experience at companies (role, company_name, company_slug, start_date, end_date, is_current)
- Has `kind` field: "commercial" | "personal"
- Contains markdown fields: `company_summary_md`, `company_role_md`, `description_md`
- One-to-many relationship with `ExperienceProject`

**ExperienceProject** (`experience_project.py`):
- Projects within a specific company experience
- Fields: name, slug, period, description_md, achievements_md
- Many-to-one with CompanyExperience (CASCADE delete)

**Project** (`project.py`):
- Standalone featured projects (not tied to experience)
- Has slug, featured flag, repo_url, demo_url
- Many-to-many with Technology via `project_technology` junction table
- Contains `long_description_md` and `description_md`

**Technology** (`technology.py`):
- Tech stack items (name, slug, category, order_index)
- Many-to-many with Project

**Publication** (`publication.py`):
- Articles, blog posts (title, year, source, url, badge)

**Contact** (`contact.py`):
- Contact methods (kind: email/telegram/github/linkedin, label, value, url)

**Stat** (`stats.py`):
- Key metrics for display (key, label, value, hint, group_name)

**TechFocus** (`tech_focus.py`):
- Technology focus areas grouping

---

## Environment Variables

Key variables (see `infra/.env.dev`):

**Database:**
- `POSTGRES_DB` - Database name (e.g., `ai_portfolio_new`)
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_PORT` - PostgreSQL port (default: 5433)
- `DATABASE_URL` - Full connection string (e.g., `postgresql+psycopg://user:pass@host:5433/db`)

**Frontend:**
- `FRONTEND_ORIGIN` - CORS allowed origin (e.g., `http://localhost:3001`)
- `FRONTEND_LOCAL_IP` - Additional CORS origin (e.g., `http://192.168.1.36:3001`)
- `NEXT_PUBLIC_CONTENT_API_BASE` - Content API base URL (frontend env)
- `NEXT_PUBLIC_AGENT_API_BASE` - Agent API base URL (frontend env)

**LLM Infrastructure:**
- `LITELLM_BASE_URL` - LiteLLM proxy URL (e.g., `http://litellm:4000/v1`)
- `LITELLM_MASTER_KEY` - LiteLLM authentication key
- `CHAT_MODEL` - Chat model alias (e.g., `GigaChat`, mapped in litellm/config.yaml)
- `EMBEDDING_MODEL` - Embedding model alias (e.g., `embedding-default`)
- `GIGA_AUTH_DATA` - GigaChat base64 credentials (if using GigaChat)
- `HF_TOKEN` - HuggingFace token for model downloads

**Vector Database:**
- `CHROMA_HOST` - ChromaDB host
- `CHROMA_PORT` - ChromaDB port (default: 8001 external, 8000 internal)

**Service Ports:**
- `CHROMA_PORT` - 8001 (ChromaDB)
- `VLLM_PORT` - 8002 (vLLM inference)
- `CONTENT_PORT` - 8003 (content-api-new)
- `RAG_PORT` - 8004 (rag-api)
- `LITELLM_PORT` - 8005 (LiteLLM proxy)
- `TEI_PORT` - 8006 (Text Embeddings Inference)

---

## Common Pitfalls

1. **Wrong Service Directories**:
   - ✅ Use `content-api-new` and `frontend-new`
   - ❌ Do NOT use `content-api` or `frontend` (old versions)

2. **API Versioning**:
   - content-api-new endpoints are prefixed with `/api/v1/`
   - Frontend must use correct base URL with version prefix

3. **Circular Imports**: Keep `deps.py` for shared dependencies, avoid importing between API routers

4. **Migration Conflicts**:
   - Always check `alembic current` before creating migrations
   - Migration location: `services/content-api-new/alembic/versions/`

5. **Encoding Issues**: Verify UTF-8 encoding, especially when working with Cyrillic text (MANDATORY from CONTRIBUTING.md)

6. **Agent Tool Usage**: The RAG agent MUST call `portfolio_rag_tool` for portfolio questions - don't let LLM answer directly

7. **CORS Configuration**:
   - Ensure `FRONTEND_ORIGIN` matches frontend URL
   - content-api-new checks CORS strictly

8. **Docker Networking**:
   - PostgreSQL accessed via `host.docker.internal` (external database)
   - Internal service communication uses service names (e.g., `chroma:8000`, `litellm:4000`)

9. **LiteLLM Model Aliases**:
   - Model names must match aliases in `infra/litellm/config.yaml`
   - Default: `CHAT_MODEL=GigaChat`, `EMBEDDING_MODEL=embedding-default`

10. **Markdown Fields**:
    - Many fields support markdown (e.g., `summary_md`, `description_md`, `achievements_md`)
    - Frontend renders with `react-markdown`

---

## File Structure Reference

```
AI-Portfolio/
├── frontend-new/                    # ✅ ACTIVE Next.js frontend (cyberpunk theme)
│   ├── app/
│   │   ├── page.tsx                # Main landing page
│   │   ├── layout.tsx              # Root layout with AgentDock
│   │   └── experience/[company_slug]/ # Experience detail page
│   ├── components/
│   │   ├── agent/                  # RAG agent chat components
│   │   ├── hero/                   # Hero section
│   │   ├── about/                  # About section with stats
│   │   ├── experience/             # Experience timeline
│   │   ├── tech/                   # Tech focus areas
│   │   ├── projects/               # Projects showcase
│   │   ├── publications/           # Publications list
│   │   ├── contacts/               # Contact cards
│   │   └── layout/                 # Shell, Footer
│   ├── lib/
│   │   ├── api.ts                  # API client (SSR)
│   │   └── types.ts                # TypeScript types
│   ├── package.json
│   └── .env.local                  # Environment variables
│
├── frontend/                        # ❌ OLD VERSION (deprecated)
│
├── services/
│   ├── content-api-new/            # ✅ ACTIVE Content API (versioned API)
│   │   ├── app/
│   │   │   ├── main.py            # FastAPI app entry
│   │   │   ├── models/            # SQLAlchemy models
│   │   │   │   ├── profile.py
│   │   │   │   ├── experience.py
│   │   │   │   ├── experience_project.py
│   │   │   │   ├── project.py
│   │   │   │   ├── publication.py
│   │   │   │   ├── contact.py
│   │   │   │   ├── stats.py
│   │   │   │   ├── tech_focus.py
│   │   │   │   └── technology.py
│   │   │   ├── routers/           # API endpoints (/api/v1/*)
│   │   │   │   ├── profile.py
│   │   │   │   ├── experience.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── publications.py
│   │   │   │   ├── contacts.py
│   │   │   │   ├── stats.py
│   │   │   │   ├── tech_focus.py
│   │   │   │   └── rag.py         # RAG document export
│   │   │   ├── schemas/           # Pydantic schemas
│   │   │   ├── core/config.py     # Settings
│   │   │   └── db.py              # Database setup
│   │   ├── alembic/               # Database migrations
│   │   │   └── versions/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── content-api/                # ❌ OLD VERSION (deprecated)
│   │
│   └── rag-api/                    # ✅ ACTIVE RAG & Agent API
│       └── app/
│           ├── main.py             # FastAPI app entry
│           ├── rag/                # RAG pipeline modules
│           │   ├── core.py         # Main RAG function
│           │   ├── retrieval.py    # Hybrid retriever
│           │   ├── rank.py         # Reranking
│           │   ├── evidence.py     # Evidence selection
│           │   └── prompting.py    # Prompt templates
│           ├── agent/              # LangGraph agent
│           │   ├── graph.py        # Agent graph definition
│           │   └── tools.py        # Agent tools
│           └── deps.py             # Shared dependencies
│
├── scripts/
│   ├── ingest.py                   # RAG document ingestion (legacy)
│   └── settings.py
│
├── infra/
│   ├── compose.apps.yaml           # ✅ Main docker compose (ACTIVE)
│   ├── docker-compose.yaml         # ❌ Old compose (deprecated)
│   ├── .env.dev                    # Environment variables template
│   ├── litellm/
│   │   └── config.yaml             # LiteLLM model aliases
│   └── models/
│       └── intfloat/multilingual-e5-base/  # TEI embedding model
│
├── CONTRIBUTING.md                 # ⚠️ MANDATORY rules for AI tools
└── CLAUDE.md                       # This file
```

**Key Points:**
- ✅ **Active services**: `frontend-new`, `content-api-new`, `rag-api`
- ❌ **Deprecated**: `frontend`, `content-api` (old versions, do not use)
- 🐳 **Docker**: Use `infra/compose.apps.yaml` for orchestration
- 📝 **Rules**: Always read `CONTRIBUTING.md` before making changes

---

## When Making Changes

**Always:**
1. **Verify service directories**: Use `content-api-new` and `frontend-new`, NOT old versions
2. Read `CONTRIBUTING.md` first (mandatory UTF-8 encoding rules)
3. Check encoding is UTF-8 (especially for Cyrillic text in markdown fields)
4. Create Alembic migration if modifying SQLAlchemy models in `content-api-new`
5. Test locally before committing
6. Follow existing code patterns and naming conventions
7. Ensure API endpoints include `/api/v1/` prefix for content-api-new
8. Use markdown fields (`*_md`) for rich content that will be rendered with `react-markdown`

**Never:**
1. Use `content-api` or `frontend` directories (old versions)
2. Change file encoding from UTF-8
3. Modify old Alembic migrations
4. Create circular imports
5. Mix business logic with API controllers
6. Change project structure without explicit permission
7. Skip API versioning (`/api/v1/` prefix)
8. Hardcode API URLs (use environment variables)

**Before Committing:**
1. ✅ Verify you modified the correct service (`*-new` versions)
2. ✅ Check no broken Cyrillic characters (`????` or `\u041f`)
3. ✅ Run Alembic migration if models changed
4. ✅ Test API endpoints with correct `/api/v1/` prefix
5. ✅ Verify CORS settings if frontend can't reach backend
