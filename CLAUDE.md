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
- RAG: LangChain, LangGraph, ChromaDB, sentence-transformers, rank-bm25
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
  - `profile.py` - Profile (full_name, title, subtitle, summary_md, hero_headline, hero_description, current_position)
  - `experience.py` - CompanyExperience (role, company, dates, kind, company_summary_md, company_role_md)
  - `experience_project.py` - ExperienceProject (projects within company experience with achievements_md)
  - `project.py` - Project (standalone projects with slug, technologies, featured, domain, repo_url, demo_url, long_description_md)
  - `publication.py` - Publication (articles, blog posts)
  - `contact.py` - Contact (email, telegram, github, linkedin, hh, leetcode)
  - `stats.py` - Stat (key metrics for display)
  - `tech_focus.py` - TechFocus (technology focus areas)
  - `technology.py` - Technology (tech stack items)
  - `hero_tag.py` - HeroTag (tags displayed in hero section)
  - `focus_area.py` - FocusArea, FocusAreaBullet (focus areas with bullet points)
  - `work_approach.py` - WorkApproach, WorkApproachBullet (work approaches with bullets and icons)
  - `section_meta.py` - SectionMeta (metadata for sections like titles, subtitles)
- `app/routers/` - API endpoints:
  - `profile.py` - GET `/api/v1/profile`
  - `experience.py` - GET `/api/v1/experience`, GET `/api/v1/experience/{slug}`
  - `stats.py` - GET `/api/v1/stats`
  - `tech_focus.py` - GET `/api/v1/tech-focus`
  - `projects.py` - GET `/api/v1/projects`, GET `/api/v1/projects/{slug}`
  - `publications.py` - GET `/api/v1/publications`
  - `contacts.py` - GET `/api/v1/contacts`
  - `rag.py` - GET `/api/v1/rag/documents` (exports data for RAG indexing)
  - `hero_tags.py` - GET `/api/v1/hero-tags`
  - `focus_areas.py` - GET `/api/v1/focus-areas`
  - `work_approaches.py` - GET `/api/v1/work-approaches`
  - `section_meta.py` - GET `/api/v1/section-meta`, GET `/api/v1/section-meta/{section_key}`
- `app/schemas/` - Pydantic schemas for each model
- `app/settings.py` - Application settings
- `alembic/` - Database migrations

### 2. **RAG API** (`services/rag-api/`)
- Semantic search and question answering over portfolio data
- LangGraph agent with memory (ReAct pattern)
- Hybrid retrieval: dense embeddings + BM25
- Cross-encoder reranking
- Streaming chat interface
- Entry point: `app/main.py`
- Port: 8004

**Architecture** (modular design):
- `app/main.py` - FastAPI app with routers
- `app/settings.py` - Pydantic settings with environment variables
- `app/deps.py` - Shared dependencies (LLM, vectorstore, reranker, agent)

**API Routers:**
- `app/api_ask.py` - Question answering endpoints:
  - POST `/ask` - Single question with session memory support
  - POST `/api/v1/agent/chat/stream` - Streaming chat with LLM
- `app/api_ingest.py` - Single document ingestion:
  - POST `/ingest` - Add individual documents
- `app/api_ingest_batch.py` - Batch ingestion:
  - POST `/ingest/batch` - Batch import from ExportPayload
- `app/api_admin.py` - Admin endpoints:
  - DELETE `/admin/collection` - Clear ChromaDB collection and BM25 index
  - GET `/admin/stats` - Get collection statistics with type breakdown

**RAG Pipeline** (`app/rag/`):
- `core.py` - Main RAG function `portfolio_rag_answer()`
- `retrieval.py` - `HybridRetriever` combining dense and BM25 search
- `rank.py` - Cross-encoder reranking
- `evidence.py` - Evidence selection and context packing
- `prompting.py` - Prompt templates and message building
- `types.py` - Type definitions (Doc, ScoredDoc, Retriever, ReRanker, SourceInfo)
- `nlp.py` - NLP utilities (keywords extraction, sentence filtering with Russian support)
- `index.py` - BM25 index persistence (load/save to pickle)

**Utilities** (`app/utils/`):
- `bm25_index.py` - BM25 index implementation using rank_bm25.BM25Okapi
- `normalize.py` - Basic normalization utilities
- `normalize_export_rich.py` - Rich document normalization for batch ingestion:
  - Creates document chunks with smart text splitting
  - Generates multiple document types: project, achievement, technology, company, document, catalog
  - Uses SHA1 hashing for change tracking
  - Supports chunking with max_chars=900

**Agent System** (`app/agent/`):
- `graph.py` - LangGraph agent with tools and memory
- `tools.py` - RAG tools for the agent (portfolio_rag_tool, list_projects_tool)

**LLM Adapters** (`app/llm/`):
- `gigachat_adapter.py` - GigaChat adapter implementing LangChain BaseChatModel:
  - Supports tool binding for LangGraph agent
  - Streaming responses support
  - Uses official GigaChat SDK

**Schemas** (`app/schemas/`):
- `ingest_schema.py` - Ingestion schemas:
  - `IngestItem` - Base item for ingestion
  - `IngestRequest` - Request for adding documents
  - `ProjectExport` - Project structure (with kind, weight, repo_url, demo_url)
  - `TechnologyExport` - Technology structure
  - `CompanyExport` - Company structure
  - `AchievementExport` - Achievement structure
  - `DocumentExport` - External document structure
  - `ExportPayload` - Full export structure for batch ingestion

### 3. **Frontend** (`frontend-new/`)
**IMPORTANT: Use `frontend-new`, NOT `frontend` (old version)**

- Next.js 14 with App Router
- Server-side rendering (SSR)
- Cyberpunk-themed UI with Framer Motion animations
- react-markdown for rendering markdown content
- Entry point: `app/page.tsx`
- Port: 3000

**Pages:**
- `app/page.tsx` - Main landing page (fetches all data via API, includes ParticlesBackground)
- `app/layout.tsx` - Root layout with AgentDock and CustomCursor
- `app/projects/[slug]/page.tsx` - Project detail page with long_description_md
- `app/experience/[company_slug]/page.tsx` - Experience detail page with projects and achievements
- `app/globals.css` - Global styles including hero animations

**Components:**
- `components/agent/` - RAG agent chat:
  - `AgentDock.tsx` - Global floating chat with RAG agent
  - `AgentChatWindow.tsx` - Chat window UI
  - `AgentInput.tsx` - Message input
  - `AgentMessageList.tsx` - Message display with streaming
- `components/hero/` - Hero section:
  - `HeroIntro.tsx` - Hero content with Framer Motion animations
  - `HeroScrollHint.tsx` - Scroll down button with animation
  - `ParticlesBackground.tsx` - Canvas-based animated cyberpunk particles
- `components/about/` - About section:
  - `AboutMeSection.tsx` - About section container
  - `StatsGrid.tsx` - Statistics grid with CountUp animation and IntersectionObserver
- `components/experience/` - Experience section:
  - `ExperienceSection.tsx` - Experience timeline
  - `ExperienceCard.tsx` - Individual experience card (memoized)
- `components/tech/` - Technology section:
  - `TechFocusSection.tsx` - Technology focus areas
- `components/projects/` - Projects section:
  - `ProjectsSection.tsx` - Featured projects grid
  - `ProjectCard.tsx` - Individual project card (memoized)
  - `GithubBadgeIcon.tsx` - GitHub SVG icon for project badges
- `components/publications/` - Publications section:
  - `PublicationsSection.tsx` - Articles/publications list
  - `PublicationCard.tsx` - Individual publication card (memoized)
- `components/contacts/` - Contacts section:
  - `ContactsSection.tsx` - Contact information
  - `ContactCard.tsx` - Individual contact card (memoized)
- `components/how/` - How I Work section:
  - `HowIWorkSection.tsx` - Work approaches display
- `components/layout/` - Layout components:
  - `Shell.tsx` - Page shell/wrapper
  - `Footer.tsx` - Site footer
  - `Section.tsx` - Reusable section component with title animations
- `components/ui/` - Shared UI components:
  - `CustomCursor.tsx` - Custom cursor with effects (trail, ripple, breathing, velocity-based)
  - `SocialBadge.tsx` - Social media badge
  - `TechTag.tsx` - Technology tag

**Library:**
- `lib/api.ts` - API client functions:
  - `getProfile()` - Fetch profile
  - `getExperience()` - Fetch experience list
  - `getExperienceDetail(slug)` - Fetch experience with projects
  - `getStats()` - Fetch statistics
  - `getTechFocus()` - Fetch tech focus areas
  - `getProjects()` - Fetch projects
  - `getProjectBySlug(slug)` - Fetch project detail
  - `getFeaturedProjects()` - Fetch featured projects
  - `getPublications()` - Fetch publications
  - `getContacts()` - Fetch contacts
  - `getHeroTags()` - Fetch hero tags
  - `getFocusAreas()` - Fetch focus areas
  - `getWorkApproaches()` - Fetch work approaches
  - `getSectionMeta(key)` - Fetch section metadata
  - `getAllSectionMeta()` - Fetch all section metadata
  - `askAgent(question, sessionId)` - Ask agent question
  - `callAgentStream(body, opts)` - Streaming chat with agent
- `lib/types.ts` - TypeScript type definitions:
  - `Profile`, `ExperienceItem`, `ExperienceProject`, `ExperienceDetail`
  - `StatItem`, `TechFocusItem`, `Project`, `ProjectDetail`
  - `Publication`, `Contact`, `AgentMessage`
  - `HeroTag`, `FocusArea`, `FocusAreaBullet`
  - `WorkApproach`, `WorkApproachBullet`, `SectionMeta`

### 4. **Infrastructure** (`infra/`)
- Docker Compose orchestration (compose.apps.yaml - primary compose file)
- Alternative compose files: `compose.apps.new.yaml`, `compose.db.yaml`, `compose.ml.yaml`
- Services:
  - PostgreSQL (external, accessed via host.docker.internal)
  - ChromaDB (vector database, port 8001 external / 8000 internal)
  - vLLM (Qwen2.5-7B-Instruct-AWQ via OpenAI-compatible API, port 8002)
  - TEI (Text Embeddings Inference for multilingual-e5-base, port 8006)
  - LiteLLM (unified proxy for LLM/embeddings, port 8005 external / 4000 internal)
  - content-api (port 8003) - builds from content-api-new/
  - rag-api (port 8004)

**Note:** There are multiple compose files:
- `compose.apps.yaml` - Main file (service: `content-api` builds from content-api-new/)
- `compose.apps.new.yaml` - Alternative (service: `content-api-new`, port 8013)
- `compose.db.yaml` - Database configuration
- `compose.ml.yaml` - ML services configuration
- `docker-compose.yaml` - Old file (DEPRECATED)

Use `compose.apps.yaml` as the primary configuration.

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

# Seed database with sample data
python -m app.seed.seed_ai_portfolio_new
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
# Then POST to /ingest/batch endpoint on rag-api
```

Environment variables:
```bash
litellm_base_url=http://localhost:8005/v1
litellm_api_key=dev-secret-123
chat_model=Qwen2.5  # Default LLM model (or GigaChat if configured)
embedding_model=embedding-default
reranker_model=BAAI/bge-reranker-base
CHROMA_HOST=localhost
CHROMA_PORT=8001
chroma_collection=portfolio
FRONTEND_ORIGIN=http://localhost:3000
frontend_local_ip=http://localhost:3000
LOG_LEVEL=INFO
giga_auth_data=  # Base64 GigaChat credentials (optional)
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
- Location: `services/content-api-new/alembic/versions/`

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
2. **RAG Ingestion**: content-api-new `/api/v1/rag/documents` → rag-api `/ingest/batch` → ChromaDB + BM25 indexing
3. **Frontend SSR**: Next.js → content-api-new `/api/v1/*` → PostgreSQL → JSON response
4. **Agent Chat**: User → frontend-new AgentDock → rag-api `/api/v1/agent/chat/stream` → LangGraph agent
5. **RAG Query Flow**: Agent tool call → Hybrid retrieval (dense + BM25) → Rerank → Evidence selection → LLM generation

---

## Key Architectural Patterns

### RAG Pipeline
The RAG system uses a sophisticated retrieval pipeline:
1. **Hybrid Retrieval**: Combines dense embeddings (semantic) with BM25 (keyword-based) via `HybridRetriever`
2. **Reranking**: Cross-encoder scores candidates for relevance using `BAAI/bge-reranker-base`
3. **Evidence Selection**: Picks top-k documents with diversity
4. **Context Packing**: Fits selected evidence into token budget (900 tokens default)
5. **LLM Generation**: Uses packed context to generate answer

See `services/rag-api/app/rag/core.py:portfolio_rag_answer()`

### Document Types in RAG
The RAG system creates multiple document types from portfolio data:
- `project` - Project information with technologies and links
- `achievement` - Individual achievements from experience projects
- `technology` - Technologies with projects where they were used
- `company` - Company information from experience
- `document` - External documents
- `catalog` - Catalogs (all technologies, technologies by company)

### Agent System
The LangGraph agent (`services/rag-api/app/agent/graph.py`) uses ReAct pattern:
- System prompt enforces RAG tool usage for portfolio questions
- Memory via `MemorySaver` checkpointer (thread_id based)
- Tools: `portfolio_rag_tool`, `list_projects_tool`
- Agent MUST call RAG tool for any portfolio-related questions

### BM25 Index Persistence
The BM25 index is persisted to disk:
- Location: `~/.bm25.{collection}.pkl`
- Loaded on startup via `bm25_try_load()`
- Saved after ingestion via `bm25_try_save()`
- Reset when collection is cleared

### Hero Section Animations
The hero section includes sophisticated animations:

**Particles Background** (`frontend-new/components/hero/ParticlesBackground.tsx`):
- Canvas-based rendering with performance optimizations
- Desktop: 60fps, 35-80 particles with glow effects
- Mobile: 30fps, 25-50 particles, no glow (for performance)
- 8 cyberpunk-themed particle shapes: pulseRing, dataNode, scanLine, hexagon, crosshair, diamond, circuit, orb
- Mouse interaction: particles are repelled by cursor movement (vortex effect)
- IntersectionObserver for visibility detection (pauses when scrolled away)
- Gradual particle spawn on page load
- Particles wrap around screen edges

**Hero Intro Animations** (`frontend-new/components/hero/HeroIntro.tsx`):
- Sequential entrance animations using Framer Motion:
  1. "AI-Portfolio" title fades in from below (0s)
  2. Animated line sweeps across (0.4s delay)
  3. Tagline appears and typing animation starts (0.8s delay, CSS typing at 1.1s)
  4. Main card fades in (0.5s delay)
  5. Card content appears (0.7s delay)
  6. Avatar image appears (0.85s delay)
- Line width auto-adjusts to match tagline text width
- Uses `next/image` for optimized avatar loading
- `will-change` hints for GPU acceleration

**Custom Cursor** (`frontend-new/components/ui/CustomCursor.tsx`):
- Dynamic trail with fade effect
- Click ripple effects
- Velocity-based animations
- Breathing animation effect
- Touch device detection with auto-disable on mobile
- Respects `prefers-reduced-motion`
- Uses requestAnimationFrame for smooth 60fps

**CSS Animations** (`frontend-new/app/globals.css`):
- `hero-grid-pan` - Moving grid background
- `hero-line-sweep` - Running light effect on line
- `hero-typing` + `hero-caret` - Typewriter effect for tagline
- `glowDrift` - Floating gradient blobs
- `hero-bounce-slow` - Scroll button bounce
- `cursor-breathe` - Cursor breathing animation
- `animate-cursor-ripple` - Click ripple effect
- `@media (prefers-reduced-motion)` - Respects user preferences
- Mobile optimizations: reduced blur, slower animations

### Performance Optimizations
The frontend includes several performance optimizations:
- **React.memo** on card components (ProjectCard, ExperienceCard, ContactCard, PublicationCard)
- **useMemo/useCallback** in HeroIntro and AgentDock for memoized values and callbacks
- **next/image** for optimized image loading with proper sizes attribute
- **IntersectionObserver** in ParticlesBackground and StatsGrid for visibility-based behavior
- **CountUp animation** in StatsGrid triggered only when visible
- **Throttled event handlers** for resize and mouse events
- **Frame rate limiting** on mobile devices (30fps vs 60fps)
- **will-change CSS hints** for GPU-accelerated animations
- **prefers-reduced-motion** media query support

### Database Models
Key models and relationships (`services/content-api-new/app/models/`):

**Profile** (`profile.py`):
- Single instance storing personal info
- Fields: full_name, title, subtitle, location, status, avatar_url, summary_md
- New fields: hero_headline, hero_description, current_position

**CompanyExperience** (`experience.py`):
- Work experience at companies
- Fields: role, company_name, company_slug, start_date, end_date, is_current
- `kind` field: "commercial" | "personal"
- Markdown fields: `company_summary_md`, `company_role_md`, `description_md`
- One-to-many relationship with `ExperienceProject`

**ExperienceProject** (`experience_project.py`):
- Projects within a specific company experience
- Fields: name, slug, period, description_md, achievements_md, order_index
- Field `technologies` - array of technology names
- Many-to-one with CompanyExperience (CASCADE delete)

**Project** (`project.py`):
- Standalone featured projects (not tied to experience)
- Fields: name, slug, featured, period, company_name, company_website
- New fields: domain ("cv" | "rag" | "backend" | "mlops" | "other"), repo_url, demo_url
- Markdown fields: description_md, long_description_md
- Many-to-many with Technology via `project_technology` junction table

**Technology** (`technology.py`):
- Tech stack items (name, slug, category, order_index)
- Many-to-many with Project

**Publication** (`publication.py`):
- Articles, blog posts (title, year, source, url, badge)
- Source types: "Habr" | "GitHub" | "Blog" | "Other"

**Contact** (`contact.py`):
- Contact methods
- Kind types: email, telegram, github, linkedin, hh, leetcode, other
- Fields: label, value, url

**Stat** (`stats.py`):
- Key metrics for display (key, label, value, hint, group_name)

**TechFocus** (`tech_focus.py`):
- Technology focus areas grouping

**HeroTag** (`hero_tag.py`):
- Tags displayed in hero section
- Fields: name, url, icon, order_index

**FocusArea** (`focus_area.py`):
- Focus areas with nested bullet points
- Fields: title, is_primary, order_index
- One-to-many with `FocusAreaBullet`

**WorkApproach** (`work_approach.py`):
- Work approaches with nested bullet points
- Fields: title, icon, order_index
- One-to-many with `WorkApproachBullet`

**SectionMeta** (`section_meta.py`):
- Metadata for sections (section_key, title, subtitle)
- Used for customizing section headers throughout the UI

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
- `CHAT_MODEL` - Chat model alias (e.g., `Qwen2.5` or `GigaChat`, mapped in litellm/config.yaml)
- `EMBEDDING_MODEL` - Embedding model alias (e.g., `embedding-default`)
- `GIGA_AUTH_DATA` - GigaChat base64 credentials (if using GigaChat)
- `HF_TOKEN` - HuggingFace token for model downloads

**RAG API Specific:**
- `reranker_model` - Reranker model (default: `BAAI/bge-reranker-base`)
- `chroma_collection` - ChromaDB collection name (default: `portfolio`)

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
   - content-api-new and rag-api check CORS strictly

8. **Docker Networking**:
   - PostgreSQL accessed via `host.docker.internal` (external database)
   - Internal service communication uses service names (e.g., `chroma:8000`, `litellm:4000`)

9. **LiteLLM Model Aliases**:
   - Model names must match aliases in `infra/litellm/config.yaml`
   - Default models: `CHAT_MODEL=Qwen2.5` (or `GigaChat`), `EMBEDDING_MODEL=embedding-default`
   - Check `infra/litellm/config.yaml` for available model aliases

10. **Markdown Fields**:
    - Many fields support markdown (e.g., `summary_md`, `description_md`, `achievements_md`, `long_description_md`)
    - Frontend renders with `react-markdown`

11. **BM25 Index State**:
    - BM25 index is stored in pickle files (`~/.bm25.{collection}.pkl`)
    - Clear both ChromaDB and BM25 when resetting collection via `/admin/collection`

---

## File Structure Reference

```
AI-Portfolio/
├── frontend-new/                    # ✅ ACTIVE Next.js frontend (cyberpunk theme)
│   ├── app/
│   │   ├── page.tsx                # Main landing page
│   │   ├── layout.tsx              # Root layout with AgentDock, CustomCursor
│   │   ├── globals.css             # Global styles and animations
│   │   ├── projects/[slug]/        # Project detail page
│   │   └── experience/[company_slug]/ # Experience detail page
│   ├── components/
│   │   ├── agent/                  # RAG agent chat (AgentDock, AgentChatWindow, etc.)
│   │   ├── hero/                   # Hero section (HeroIntro, HeroScrollHint, ParticlesBackground)
│   │   ├── about/                  # About section (AboutMeSection, StatsGrid)
│   │   ├── experience/             # Experience section (ExperienceSection, ExperienceCard)
│   │   ├── tech/                   # Tech focus (TechFocusSection)
│   │   ├── projects/               # Projects (ProjectsSection, ProjectCard, GithubBadgeIcon)
│   │   ├── publications/           # Publications (PublicationsSection, PublicationCard)
│   │   ├── contacts/               # Contacts (ContactsSection, ContactCard)
│   │   ├── how/                    # How I Work (HowIWorkSection)
│   │   ├── ui/                     # Shared UI (CustomCursor, SocialBadge, TechTag)
│   │   └── layout/                 # Layout (Shell, Footer, Section)
│   ├── lib/
│   │   ├── api.ts                  # API client (SSR) - all fetch functions
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
│   │   │   ├── settings.py        # Application settings
│   │   │   ├── db.py              # Database setup
│   │   │   ├── models/            # SQLAlchemy models (all listed above)
│   │   │   ├── routers/           # API endpoints (/api/v1/*)
│   │   │   ├── schemas/           # Pydantic schemas
│   │   │   ├── core/config.py     # Core settings
│   │   │   └── seed/              # Database seeding
│   │   ├── alembic/               # Database migrations
│   │   │   └── versions/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── content-api/                # ❌ OLD VERSION (deprecated)
│   │
│   └── rag-api/                    # ✅ ACTIVE RAG & Agent API
│       └── app/
│           ├── main.py             # FastAPI app entry with routers
│           ├── settings.py         # Pydantic settings
│           ├── deps.py             # Shared dependencies
│           ├── api_ask.py          # /ask and /api/v1/agent/chat/stream
│           ├── api_ingest.py       # /ingest endpoint
│           ├── api_ingest_batch.py # /ingest/batch endpoint
│           ├── api_admin.py        # /admin/* endpoints
│           ├── rag/                # RAG pipeline modules
│           │   ├── core.py         # Main RAG function
│           │   ├── retrieval.py    # HybridRetriever
│           │   ├── rank.py         # Reranking
│           │   ├── evidence.py     # Evidence selection
│           │   ├── prompting.py    # Prompt templates
│           │   ├── types.py        # Type definitions
│           │   ├── nlp.py          # NLP utilities
│           │   └── index.py        # BM25 index persistence
│           ├── agent/              # LangGraph agent
│           │   ├── graph.py        # Agent graph definition
│           │   └── tools.py        # Agent tools
│           ├── llm/                # LLM adapters
│           │   └── gigachat_adapter.py # GigaChat LangChain adapter
│           ├── utils/              # Utilities
│           │   ├── bm25_index.py   # BM25 implementation
│           │   ├── normalize.py    # Basic normalization
│           │   └── normalize_export_rich.py # Rich export normalization
│           └── schemas/            # Pydantic schemas
│               └── ingest_schema.py # Ingestion schemas
│
├── scripts/
│   ├── ingest.py                   # RAG document ingestion (legacy)
│   └── settings.py
│
├── infra/
│   ├── compose.apps.yaml           # ✅ Main docker compose (ACTIVE)
│   ├── compose.apps.new.yaml       # Alternative compose
│   ├── compose.db.yaml             # Database compose
│   ├── compose.ml.yaml             # ML services compose
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
