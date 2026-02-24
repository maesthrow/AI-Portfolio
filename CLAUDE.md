# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ CRITICAL: Active Service Directories

**ALWAYS use these directories:**
- ✅ `frontend-new/` - Active Next.js frontend (cyberpunk theme)
- ✅ `services/content-api-new/` - Active Content API with versioned endpoints
- ✅ `services/rag-api-new/` - **NEW** Active RAG & Agent API (multi-layer pipeline, LLM planner)
- ✅ `infra/docker-compose.local.yaml` - Active Docker Compose configuration (local dev)

**NEVER use these directories (removed from codebase):**
- ❌ `frontend/` - Old frontend (deleted)
- ❌ `services/content-api/` - Old Content API (deleted)
- ❌ `services/rag-api/` - Legacy RAG API (deleted from disk)
- ❌ `infra/docker-compose.yaml` - Old Docker Compose (deprecated)

If you accidentally work with deprecated directories, **STOP** and switch to the correct active directories immediately.

---

## Project Overview

**AI-Portfolio** is a microservices-based cyberpunk-themed portfolio application with RAG (Retrieval-Augmented Generation) capabilities. The system consists of a Next.js frontend, PostgreSQL database with pgvector extension for semantic search, FastAPI backend services, and a LangGraph-powered agent.

**Tech Stack:**
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Framer Motion, react-markdown, remark-gfm, lucide-react
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic
- RAG: LangChain 1.x, LangGraph 1.x, pgvector (PostgreSQL extension), sentence-transformers, rank-bm25
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
  - `project.py` - Project (personal/featured projects with slug, technologies, featured, domain, repo_url, demo_url, long_description_md)
  - `publication.py` - Publication (articles, blog posts; title, year, source, url, badge, description_md, order_index)
  - `contact.py` - Contact (email, telegram, github, linkedin, hh, leetcode; label, value, url, order_index, is_primary)
  - `stats.py` - Stat (key metrics for display)
  - `tech_focus.py` - TechFocus (technology focus areas)
  - `technology.py` - Technology (tech stack items)
  - `hero_tag.py` - HeroTag (tags displayed in hero section)
  - `focus_area.py` - FocusArea, FocusAreaBullet (focus areas with bullet points)
  - `work_approach.py` - WorkApproach, WorkApproachBullet (work approaches with bullets and icons)
  - `section_meta.py` - SectionMeta (metadata for sections like titles, subtitles)
- `app/routers/` - API endpoints:
  - `profile.py` - GET `/api/v1/profile`
  - `experience.py` - GET `/api/v1/experience` (optional `kind` filter, default: `"commercial"`), GET `/api/v1/experience/{slug}`
  - `stats.py` - GET `/api/v1/stats`
  - `tech_focus.py` - GET `/api/v1/tech-focus`
  - `projects.py` - GET `/api/v1/projects`, GET `/api/v1/projects/{slug}`
  - `publications.py` - GET `/api/v1/publications`
  - `contacts.py` - GET `/api/v1/contacts`
  - `rag.py` - GET `/api/v1/rag/documents` (legacy flat list for RAG), GET `/api/v1/rag/export` (structured ExportPayload for RAG ingestion)
  - `hero_tags.py` - GET `/api/v1/hero-tags`
  - `focus_areas.py` - GET `/api/v1/focus-areas`
  - `work_approaches.py` - GET `/api/v1/work-approaches`
  - `section_meta.py` - GET `/api/v1/section-meta`, GET `/api/v1/section-meta/{section_key}`
- `app/schemas/` - Pydantic schemas for each model (includes `rag_export.py` for comprehensive RAG export structures)
- `app/settings.py` - Application settings
- `alembic/` - Database migrations

### 2. **RAG API New** (`services/rag-api-new/`) ⭐ RECOMMENDED
**Multi-layer RAG pipeline with LLM-based planning and deterministic answer generation**

- Advanced semantic search with LLM-based query planning
- Knowledge Graph for structured data queries
- Scope Guard for off-topic detection
- Deterministic fact normalization and answer generation
- Entry point: `app/main.py`
- Port: 8014 (Docker compose local via `RAG_NEW_PORT`), 8000 (default uvicorn)
- Docs: `/api/swagger`

**Agent Graph Architecture (StateGraph with hybrid routing):**
```
User Message
    ↓
[RouterNode] - Hybrid regex fast-path → LLM fallback intent classification
    ├─ "greeting"/"thanks"/"farewell" → [SmallTalkNode] → END (deterministic, no LLM)
    ├─ "off_topic"  → [OffTopicNode]  → END (deterministic refusal with suggestions)
    ├─ "cv_start"   → [CvStartNode]   → END (start CV send flow)
    ├─ "cv_process" → [CvProcessNode]  → END (process email in CV flow)
    ├─ "cv_cancel"  → [CvCancelNode]   → END (adaptive LLM cancel response)
    └─ "rag"        → [RAG ReAct Subgraph]
                         ↓
                    [AGENT_SYSTEM_PROMPT] - Off-topic safety net (primary guard is RouterNode)
                         ↓
                    [PlannerLLM] - QueryPlanV3 generation
                         ↓
                    [PlanExecutor]
                         ├─ [graph_query_tool]
                         └─ [portfolio_search_tool]
                         ↓
                    [FactNormalizer] → [AnswerLLM] → [RenderEngine]
                         ↓
                    [ClearPending] - Resets pending_action state
                         ↓
                    User Response (streaming NDJSON)
```

**Core Modules:**
- `app/main.py` - FastAPI app with routers, health endpoints (`/healthz`, `/meta`)
- `app/settings.py` - Pydantic settings with LLM temperatures
- `app/deps.py` - Shared dependencies (LLM instances, PGVectorStore via `pg_engine()`, reranker)
- `app/prefetch.py` - Cache warmup for popular questions
  - `POPULAR_QUESTIONS` - List of common questions in both user-style and agent-style
  - `prefetch_popular_plans()` - Warms up Redis cache after ingest (~60-70% cache hit rate)

**API Routers** (`app/routers/`):
- `chat.py` - POST `/api/v1/agent/chat/stream` - Streaming chat with NDJSON (status events via unified asyncio.Queue)
- `ingest.py` - POST `/api/v1/ingest` - Single document ingestion
- `ingest_batch.py` - POST `/api/v1/ingest/batch` - Batch import from ExportPayload
- `admin.py` - Admin and utility endpoints:
  - DELETE `/api/v1/admin/collection` - Clear pgvector collection
  - GET `/api/v1/admin/stats` - Collection and graph statistics
  - GET `/api/v1/admin/cache/stats` - Cache statistics
  - DELETE `/api/v1/admin/cache/plans` - Clear plan cache
  - DELETE `/api/v1/admin/cache/embeddings` - Clear embedding cache
  - DELETE `/api/v1/admin/cache` - Clear all caches
  - GET `/api/v1/rate-limit/status` - Rate limit status for current IP

**Agent System** (`app/agent/`):
- `graph.py` - Top-level `StateGraph` with hybrid router dispatching to branches (RAG subgraph, CV, smalltalk, off-topic)
- `graph_state.py` - `AgentState` TypedDict: `messages`, `pending_action` (`""` | `"cv_awaiting_email"`), `_route_intent`
- `router.py` - `router_node(state, config)`: regex fast-path → LLM fallback; `route_edge(state)` conditional edge
- `router_llm.py` - `classify_intent(text, llm)` → `greeting/thanks/farewell/cv_request/off_topic/rag`; `is_cv_continuation(text, llm)` → `"yes"/"cancel"/"change"` for multi-turn CV flow
- `cv_nodes.py` - CV send graph nodes:
  - `cv_start_node(state, config)` - starts CV send: extracts email or asks for it, sets `pending_action="cv_awaiting_email"`
  - `cv_process_node(state, config)` - processes email input in multi-turn flow
  - `_check_cv_rate_limit(ip, email)` / `_record_cv_send(ip, email)` - per-IP and per-email Redis rate limiting
  - `_emit_status("sending_cv", "Отправляю резюме...", config)`
- `cv_cancel_node.py` - Adaptive LLM response (via `answer_llm`) when user cancels CV sending; resets `pending_action`
- `smalltalk_node.py` - Deterministic canned responses for `greeting`, `thanks`, `farewell` (no LLM calls)
- `offtopic_node.py` - Deterministic off-topic refusal with suggested on-topic questions (no LLM calls)
- `rag_tool.py` - Async RAG tool for ReAct subgraph with pipeline status emission
  - `_emit_status(stage, text, config)` - Sends status events to frontend via `asyncio.Queue` from `config["configurable"]["_status_queue"]`
  - Stages emitted: `planning`, `searching`, `verifying`, `answering`
  - Heavy sync operations wrapped in `asyncio.to_thread()` (planner, executor, critic, search, answer)

**Identity** (`app/agent/identity/`):
- `classifier.py` - Two-level identity question detection:
  1. **Linguistic check** (deterministic): Detects 2nd person pronouns (ты, себя, твой, etc.) → confidence=1.0
  2. **Semantic matching** (embedding similarity): Compares with reference questions → confidence=similarity score
  - `SIMILARITY_THRESHOLD = 0.92` for conservative matching (avoids false positives)
  - `is_identity_question(question)` returns `(is_identity, max_similarity)`
  - `generate_identity_response(question)` generates LLM response about agent capabilities
- `prompts.py` - Identity prompts and capabilities list
  - `CAPABILITIES` - List of agent capabilities (easily extensible)
  - `IDENTITY_REFERENCE_QUESTIONS` - Reference questions for semantic matching (curated to avoid false positives with project questions)
  - `get_identity_system_prompt()` - Generates system prompt with current capabilities

**Planner** (`app/agent/planner/`):
- `planner_llm.py` - LLM-based query plan generator with structured output
- `schemas_v3.py` - QueryPlanV3, IntentV3, TechCategory, ToolCallV3, RenderStyleV3, AnswerStyleV3, InfoNeed, ScopeLevel, TechFilter, Scope, EntitiesV3, AnswerFormatV3, LimitsConfigV3, FallbackConfigV3, FactBundleItem, FactBundle, NormalizerOutput, GroundingResult
- `schemas.py` - Legacy QueryPlan schema (V2 compatibility)
- `prompts.py` - System prompts for planner (intents, tools, entity extraction)
- `shortcuts.py` - Plan shortcuts for unambiguous questions (4 patterns):
  1. Contacts (`контакты|связаться|...`) → `CONTACTS` intent
  2. Current job (`где работает|текущая работа|...`) → `CURRENT_JOB` intent
  3. Who is developer (`кто такой|кто это|о разработчике|...`) → `PROFILE` intent
  4. Location (`где живет|в каком городе|местоположение|...`) → `PROFILE` intent
  - `SAFE_SHORTCUTS` - Dict of regex patterns to pre-built QueryPlanV3
  - `try_shortcut(question)` - Returns plan if shortcut matches, else None (falls back to LLM)

**TechCategory** (for technology filtering):
- `language` - Programming languages (Python, C#, JavaScript, SQL)
- `database` - Databases (PostgreSQL, MongoDB, Redis)
- `vector_store` - Vector databases (pgvector, Qdrant, ChromaDB)
- `framework` - Frameworks (FastAPI, React, Django)
- `ml_framework` - ML frameworks (LangChain, LangGraph, vLLM)
- `mlops` - MLOps tools (MLFlow, LiteLLM)
- `concept` - Concepts (RAG, LLM, ReAct)
- `tool` - Tools (Docker, Git)
- `message_broker` - Message brokers (RabbitMQ, Kafka)
- `library` - Libraries (SQLAlchemy, Alembic, pytest)
- `cloud` - Cloud services
- `other` - Other technologies

**Intents (IntentV3):**
- `CURRENT_JOB` - Current position
- `PROJECT_DETAILS` - Project information
- `PROJECT_ACHIEVEMENTS` - Achievements in projects
- `PROJECT_TECH_STACK` - Technologies in projects
- `TECHNOLOGY_OVERVIEW` - Technology description
- `TECHNOLOGY_USAGE` - Where technology was used
- `EXPERIENCE_SUMMARY` - Work experience
- `PROFILE` - Developer profile information (PERSON node: name, title, summary, location)
- `CONTACTS` - Contact information
- `GENERAL_UNSTRUCTURED` - Fallback for general questions

**Scope Guard** (`app/agent/scope_guard/`) — **NOT active in pipeline**:
- `scope_guard.py` - Off-topic detection module (fairy tales, jokes, code generation, etc.)
- `schemas.py` - ScopeDecision with suggested_prompts for redirecting user
- **Note**: ScopeGuard is NOT called from the main RAG pipeline. Off-topic is handled at **router level** via `classify_intent()` → `off_topic` → `offtopic_node` (deterministic refusal). `AGENT_SYSTEM_PROMPT` serves as a secondary safety net

**Executor** (`app/agent/executor/`):
- `execute_plan.py` - PlanExecutor for tool orchestration with fallback handling

**Normalizer** (`app/agent/normalizer/`):
- `normalizer.py` - FactNormalizer with intent-specific filtering rules
- `fact_bundle.py` - Fact grouping by type/project

**Answer Generation** (`app/agent/answer/`):
- `answer_llm.py` - AnswerLLM with strict prompting to prevent hallucinations
  - Deterministic (non-LLM) answering for: `contacts`, `publications`, `project_details`, `technology_usage`
  - `_deterministic_render()` - Shared method for deterministic fact rendering with optional preamble
  - Falls back to LLM only when deterministic path is not available for the intent
- `prompts.py` - Answer system prompts and style instructions

**Render** (`app/agent/render/`):
- `renderer.py` - RenderEngine (BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH)
  - `_format_fact_with_metadata()` - Centralized formatting with URL/metadata support (contacts, projects, publications, technologies)
  - `_format_fact_inline()` - Inline formatting for SHORT and PARAGRAPH styles

**Critic** (`app/agent/critic/`):
- `critic_llm.py` - CriticLLM for answer evaluation
- `prompts.py` - Critic system prompts
- `schemas.py` - FactSufficiency schemas

**Grounding** (`app/agent/grounding/`):
- `grounding_verifier.py` - Verifies answer is grounded in evidence

**Tools** (`app/agent/tools/`):
- `portfolio_search_tool.py` - Hybrid search with full RAG pipeline
- `graph_query_tool.py` - Structured graph queries (project_details, technologies, experience)

**Email Module** (`app/email/`):
- `service.py` - `EmailService` class: `send_cv(to_email)` via `smtplib` (STARTTLS), multipart MIME with HTML body + PDF attachment
- `templates.py` - `CV_EMAIL_SUBJECT`, `cv_email_body_html(site_url)`, `cv_email_body_plain(site_url)`
- `validation.py` - `validate_email(email)` (with blocklist of 16 disposable domains), `extract_email(text)` for parsing email from free text

**RAG Pipeline** (`app/rag/`):
- `search.py` - `portfolio_search()` orchestration
- `retrieval.py` - `HybridRetriever` (dense + BM25 + RRF merge + MMR dedup)
- `rank.py` - Cross-encoder reranking
- `evidence.py` - Evidence selection and context packing (strips technical metadata for natural reading)
- `entities.py` - EntityRegistry for entity matching
- `nlp.py` - NLP utilities (keywords, Russian support)
- `formatter.py` - FormatRenderer for post-processing
- `search_types.py` - SearchResult, Intent, EntityType
- `types.py` - Doc, ScoredDoc, SourceInfo
- `utils.py` - Utility functions

**Knowledge Graph** (`app/graph/`):
- `schema.py` - NodeType (PERSON, COMPANY, PROJECT, ACHIEVEMENT, TECHNOLOGY, CONTACT), EdgeType
  - PROJECT = personal or experience-based (not "standalone")
- `builder.py` - Build graph from ExportPayload (includes `kind` field for experience projects)
- `query.py` - Graph query execution (classifies projects as "коммерческий" or "личный проект" based on company_name)
- `store.py` - In-memory GraphStore singleton

**Indexing** (`app/indexing/`):
- `normalizer.py` - Document normalization from ExportPayload
- `chunker.py` - Text chunking (~1800 chars max, Russian-aware)
- `bm25.py` - BM25Index implementation
- `persistence.py` - BM25 persistence (`.bm25.{collection}.pkl` (CWD-relative))

**Cache** (`app/cache/`):
- `cache_service.py` - CacheService with Redis graceful degradation
- `plan_cache.py` - Plan caching with shortcuts and LLM fallback
- `embedding_cache.py` - Embedding caching for query vectors
- Features:
  - Redis-based caching with configurable TTL (default: `0` = **infinite**, manual clear only)
  - Automatic plan cache invalidation on content hash change
  - Question normalization for cache key consistency
  - Graceful degradation when Redis is unavailable

**Rate Limiting** (`app/rate_limit/`):
- `limiter.py` - RateLimiter class for token-based IP rate limiting with Redis
- `schemas.py` - RateLimitBucket, RateLimitInfo, RateLimitStatus schemas
- Features:
  - Token-based rate limiting per IP address (not per session)
  - Configurable token limit and time window
  - Warning threshold for approaching limit (default 80%)
  - Redis-based storage — **fail-closed** (unlike CacheService which is fail-open): if Redis unavailable, returns 503 blocking ALL requests
  - Rate limit info returned in streaming response `end` event
  - Frontend displays warning when approaching limit, blocks when exceeded

**LLM Factory** (`app/llm/`):
- `factory.py` - `LLMFactory` class, `parse_llm_id()`, `get_llm_factory()`, `get_provider_info()`
- `providers.py` - `LLMProvider` enum (GIGACHAT, DEEPSEEK, QWEN), `ProviderConfig`
- `exceptions.py` - `LLMConfigError`, `LLMProviderError`
- `validation.py` - `validate_llm_config()` for startup validation (validates 5 roles: identity, planner, answer, critic, agent; excludes router_llm)
- `gigachat_adapter.py` - GigaChat adapter for LangChain (legacy, not used by LLMFactory)

**Schemas** (`app/schemas/`):
- `chat.py` - ChatRequest, ChatMessage (streaming types)
- `ingest.py` - IngestItem, IngestRequest, IngestResult
- `export.py` - ExportPayload with all entity types
- `admin.py` - AdminStats
- `ask.py` - AskRequest, AskResponse

**Utilities** (`app/utils/`):
- `logging_utils.py` - Compact JSON, text truncation
- `metadata.py` - Document ID generation, content hashing

### 3. **Frontend** (`frontend-new/`)
**IMPORTANT: Use `frontend-new`, NOT `frontend` (deleted)**

- Next.js 14 with App Router
- Server-side rendering (SSR)
- Cyberpunk-themed UI with Framer Motion animations
- react-markdown + remark-gfm for rendering markdown content with clickable links
- Entry point: `app/page.tsx`
- Port: 3000

**Pages:**
- `app/page.tsx` - Main landing page (fetches all data via API, includes neural network background)
- `app/layout.tsx` - Root layout with AgentDock and CustomCursor
- `app/projects/[slug]/page.tsx` - Project detail page with long_description_md
- `app/experience/[company_slug]/page.tsx` - Experience detail page with projects and achievements
- `app/globals.css` - Global styles including hero animations

**Components:**
- `components/agent/` - RAG agent chat:
  - `AgentDock.tsx` - Global floating chat with RAG agent (manages `thinkingStatus` state)
  - `AgentChatWindow.tsx` - Chat window UI (passes thinkingStatus to message list)
  - `AgentInput.tsx` - Message input
  - `AgentMessageList.tsx` - Message display with streaming, auto-scroll on thinking status, clickable markdown links (remark-gfm)
  - `ThinkingStatus.tsx` - Pipeline stage indicator with min-duration queue (800ms) and crossfade animation (200ms)
  - `RateLimitWarning.tsx` - Warning banner when approaching rate limit (Framer Motion animated)
  - `RateLimitBlocked.tsx` - Block UI when rate limit exceeded or service unavailable
- `components/hero/` - Hero section:
  - `HeroIntro.tsx` - Hero content with Framer Motion animations
  - `HeroScrollHint.tsx` - Scroll down button with animation
  - `ParticlesBackground.tsx` - Canvas-based neural network visualization (neurons, synapses, signal pulses)
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
  - `callAgentStream(body, opts)` - Streaming chat with agent (handles 429/503 as RateLimitError, `ChatStreamEvent` union includes `status` type)
  - `getRateLimitStatus()` - Get current rate limit status for IP
  - `isRateLimitError(error)` - Type guard for RateLimitError
- `lib/types.ts` - TypeScript type definitions:
  - `Profile`, `ExperienceItem`, `ExperienceProject`, `ExperienceDetail`
  - `StatItem`, `TechFocusItem`, `Project`, `ProjectDetail`
  - `Publication`, `Contact`, `AgentMessage`
  - `HeroTag`, `FocusArea`, `FocusAreaBullet`
  - `WorkApproach`, `WorkApproachBullet`, `SectionMeta`
  - `RateLimitBucket`, `RateLimitInfo`, `RateLimitStatus`, `RateLimitError`

### 4. **Infrastructure** (`infra/`)
- Docker Compose orchestration
- Compose files:
  - `docker-compose.local.yaml` - **Primary** local development compose (all services)
  - `docker-compose-prod.yaml` - Production deployment
- Services (in `docker-compose.local.yaml`):
  - frontend (port 3000) - Next.js dev server
  - postgres (port 5433) - PostgreSQL 16 database with pgvector extension (shared by content-api and rag-api)
  - content-api (port 8003) - builds from content-api-new/
  - tei (port 8006) - Text Embeddings Inference for multilingual-e5-base
  - litellm (port 8005 external / 4000 internal) - unified proxy for LLM/embeddings
  - redis (port 6379) - Redis for caching and rate limiting
  - rag-api (port 8014) - builds from rag-api-new/ (service name kept, builds new codebase; volume mounts `../data/cv.pdf:/app/data/cv.pdf:ro`)
  - rag-ingest - one-shot service: exports from content-api → ingests into rag-api
- Additional:
  - `caddy/Caddyfile` - Reverse proxy configuration (production)
  - `init/postgres-init.sql` - Database initialization (uuid-ossp, pgvector)
  - `scripts/ingest.py` - RAG document ingestion script
  - `.env.dev`, `.env.local`, `.env.prod`, `.env.example` - Environment variable templates
  - `DOCKER-LOCAL.md`, `DOCKER-PROD.md` - Docker setup guides

### 5. **Technical Documentation** (`discource/`)
**Project specifications and technical requirements storage**

The `discource/` folder contains all technical documentation for feature implementation:

**Structure:**
```
discource/
├── docs/                            # Technical Requirements (ТЗ)
│   ├── TZ_MULTI_LLM_PROVIDERS.md   # Multi-provider LLM architecture (v1.3)
│   ├── TZ_RATE_LIMIT.md            # Rate limiting implementation (v1.0)
│   ├── TZ_RAG_OPTIMIZATION.md      # RAG optimization techniques (v1.1)
│   └── TZ_AI-Portfolio_RAG_Agent_Hardening.md  # Agent hardening (v3)
├── specs/                           # Implementation Specifications
│   └── agent-identity-vs-profile-detection.md  # Identity vs Profile question detection
└── planning-with-files-archive/     # Historical planning session archives
```

**Document Types:**
- **ТЗ (Technical Requirements)** in `docs/`: High-level requirements and architecture decisions
- **Specs** in `specs/`: Detailed implementation specifications with code examples

**Key Specifications:**

1. **Multi-LLM Providers** (`TZ_MULTI_LLM_PROVIDERS.md`):
   - GigaChat, DeepSeek, Qwen provider architecture
   - 5 LLM roles documented (identity, planner, answer, critic, agent); 6th role `router` added later
   - LLMFactory with caching and validation

2. **Rate Limiting** (`TZ_RATE_LIMIT.md`):
   - Token-based IP rate limiting
   - Redis-based storage with graceful degradation
   - TokenUsageCollector for multi-role aggregation

3. **RAG Optimization** (`TZ_RAG_OPTIMIZATION.md`):
   - Hybrid retrieval (dense + BM25 + rerank)
   - Plan caching and shortcuts
   - Embedding cache strategies

4. **Agent Hardening** (`TZ_AI-Portfolio_RAG_Agent_Hardening.md`):
   - Scope Guard for off-topic detection
   - Fact Normalizer for intent-based filtering
   - Grounding verification

5. **Identity vs Profile Detection** (`specs/agent-identity-vs-profile-detection.md`):
   - Linguistic pattern for 2nd person pronouns → Identity questions
   - 3rd person / name → Profile questions
   - PROFILE intent implementation

**When to Use:**
- Before implementing a new feature, check if a spec exists in `discource/`
- Create a new spec in `specs/` before starting complex implementations
- Reference ТЗ documents for architectural decisions

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
NEXT_PUBLIC_AGENT_API_BASE=http://localhost:8014  # rag-api in Docker compose (RAG_NEW_PORT=8014)
# Server-side variants (override NEXT_PUBLIC_ in SSR context):
CONTENT_API_BASE=http://localhost:8003/api/v1
AGENT_API_BASE=http://localhost:8014
# Streaming text animation settings:
NEXT_PUBLIC_CHARS_PER_SECOND=60
NEXT_PUBLIC_MAX_CHARS_PER_TICK=4
# User input validation:
NEXT_PUBLIC_MAX_INPUT_TOKENS=100
NEXT_PUBLIC_CHARS_PER_TOKEN=4
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

### RAG API New (rag-api-new) ⭐ RECOMMENDED

```bash
cd services/rag-api-new

# Run the API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API Documentation
# Visit http://localhost:8000/api/swagger

# Ingest documents into pgvector (after content-api is populated)
# 1. Export from content-api: GET http://localhost:8003/api/v1/rag/export
# 2. Import to rag-api: POST http://localhost:8014/api/v1/ingest/batch
# Or use the rag-ingest service: docker compose -f docker-compose.local.yaml up rag-ingest
```

Environment variables (see `infra/.env.dev` and `infra/.env.example` for full list):
```bash
litellm_base_url=http://localhost:8005/v1
litellm_api_key=dev-secret-123
TEI_BASE_URL=http://tei:80/v1         # Direct TEI access for embeddings
embedding_model=text-embedding-3-large
reranker_model=BAAI/bge-reranker-base
MAX_RERANK_CANDIDATES=80              # Limits CPU usage (~1.3s)
DATABASE_URL=postgresql+psycopg://user:password@localhost:5433/ai_portfolio_new
COLLECTION_NAME=portfolio_new
FRONTEND_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO
# LLM Roles (format: provider:model)
IDENTITY_LLM=deepseek:deepseek-chat
PLANNER_LLM=gigachat:GigaChat-2
ANSWER_LLM=deepseek:deepseek-chat
CRITIC_LLM=deepseek:deepseek-reasoner
AGENT_LLM=gigachat:GigaChat-2
ROUTER_LLM=deepseek:deepseek-chat
giga_auth_data=  # Base64 GigaChat credentials (optional)
DEEPSEEK_API_KEY=  # DeepSeek API key (optional)
# Cache (TTL=0 means infinite, manual clear only)
REDIS_URL=redis://localhost:6379/0
PLAN_CACHE_TTL=0
EMBEDDING_CACHE_TTL=0
# Rate Limiting (production values — compose overrides)
RATE_LIMIT_IP_TOKENS=50000
RATE_LIMIT_WINDOW_SECONDS=3600        # 1 hour
MAX_USER_INPUT_TOKENS=250             # ~1000 chars
# CV sending via email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=secret
SMTP_FROM_EMAIL=noreply@example.com
DOMAIN=https://ai-folio.ru
CV_FILE_PATH=/app/data/cv.pdf
```

### Docker Infrastructure

```bash
cd infra

# Start all services (recommended)
docker compose -f docker-compose.local.yaml up -d

# Start specific services
docker compose -f docker-compose.local.yaml up -d postgres tei litellm redis
docker compose -f docker-compose.local.yaml up -d content-api rag-api

# Run ingestion (one-shot, exports content-api data → rag-api)
docker compose -f docker-compose.local.yaml up rag-ingest

# Check service health
docker compose -f docker-compose.local.yaml ps

# View logs
docker compose -f docker-compose.local.yaml logs -f content-api
docker compose -f docker-compose.local.yaml logs -f rag-api

# Rebuild and restart
docker compose -f docker-compose.local.yaml up -d --build rag-api
```

### Running Tests

RAG API New has tests in `services/rag-api-new/tests/`:
```bash
cd services/rag-api-new
pytest tests/
```

---

## Critical Rules

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
- Always follow the principles of clean code: SOLID, DRY, KISS
- Only modify files explicitly mentioned in the task
- Maintain existing project structure
- No circular imports in backend
- Separate business logic from controllers
- Use SQLAlchemy ORM and Pydantic schemas

### Systematic Problem Solving (CRITICAL)
- **Always find root causes** - never fix symptoms, find and fix the underlying problem
- **No workarounds or temporary patches** - if something doesn't work, investigate why and fix it properly
- **Clean architectural solutions** - prefer well-designed, maintainable code over quick hacks
- **No unnecessary constructs** - avoid overhead, extra abstractions, or code "just in case"
- **Methodical debugging** - trace the problem systematically, don't guess or add random fixes
- **Fix once, fix right** - spend time understanding the issue to avoid repeated fixes
- **Question assumptions** - if behavior is unexpected, verify your understanding of the system
- When encountering bugs:
  1. Reproduce the issue reliably
  2. Trace execution to find the actual cause
  3. Understand WHY it happens, not just WHERE
  4. Design a proper fix that addresses the root cause
  5. Verify the fix doesn't introduce new issues

### Frontend
- Components must be deterministic
- Use Tailwind CSS classes in JSX
- Avoid inline styles except for animations
- No emojis unless explicitly requested

---

## Data Flow

1. **Content Management**: Admin/scripts → PostgreSQL (via content-api-new)
2. **RAG Ingestion**: content-api-new `/api/v1/rag/export` → rag-api-new `/api/v1/ingest/batch` → pgvector + BM25 + Knowledge Graph (automated via `rag-ingest` service in compose)
3. **Frontend SSR**: Next.js → content-api-new `/api/v1/*` → PostgreSQL → JSON response
4. **Agent Chat**: User → frontend-new AgentDock → rag-api-new `/api/v1/agent/chat/stream` → `RouterNode` → branch dispatch
5. **RAG Query Flow (rag-api-new)**:
   - RouterNode (regex/LLM) → "rag" branch → ReAct Agent → PlannerLLM → PlanExecutor
   - → HybridRetriever (dense + BM25) → Rerank → Evidence
   - → FactNormalizer → AnswerLLM → RenderEngine → Response
6. **CV Sending Flow**: User asks for CV → RouterNode → "cv_start" → CvStartNode (ask for email) → User sends email → "cv_process" → CvProcessNode → EmailService (SMTP) → PDF attachment sent
7. **CV Cancel Flow**: User refuses in CV flow → RouterNode (3-way LLM: YES/CANCEL/CHANGE) → "cv_cancel" → CvCancelNode (adaptive LLM response via answer_llm, resets pending_action)
8. **Smalltalk Flow**: User says greeting/thanks/farewell → RouterNode → SmallTalkNode → canned response (no LLM)
9. **Off-topic Flow**: User asks off-topic (fairy tales, code generation, etc.) → RouterNode (LLM classify_intent → off_topic) → OffTopicNode → deterministic refusal with suggested questions
8. **Thinking Status Events**: rag_tool.py / cv_nodes.py `_emit_status()` → `asyncio.Queue` via config → chat.py unified queue → NDJSON `status` event → frontend ThinkingStatus component

### NDJSON Streaming Events (`/api/v1/agent/chat/stream`)

The streaming endpoint emits NDJSON events with the following types:

| Event type | Fields | Description |
|------------|--------|-------------|
| `start` | `message_id`, `created_at` | Stream opened, immediately followed by initial status |
| `status` | `stage`, `text` | Pipeline stage indicator (thinking, planning, searching, verifying, answering, identity) |
| `tool_start` | `tool` | Agent tool invocation started |
| `tool_end` | — | Agent tool invocation completed |
| `delta` | `content` | Incremental text chunk from LLM |
| `error` | `message` | Error during processing |
| `end` | `message_id`, `usage`, `rate_limit` | Stream finished |

**Status event stages:**

| Stage | Text | Source |
|-------|------|--------|
| `thinking` | Анализирую вопрос... | chat.py (immediate, after `start`) |
| `planning` | Составляю план поиска... | rag_tool.py |
| `searching` | Ищу в базе знаний... | rag_tool.py |
| `verifying` | Проверяю полноту данных... | rag_tool.py (conditional, critic) |
| `answering` | Формирую ответ... | rag_tool.py |
| `identity` | Формирую ответ... | chat.py (identity fast-path) |
| `sending_cv` | Отправляю резюме... | cv_nodes.py (CV send flow) |

**Status delivery mechanism:** `rag_tool.py` and `cv_nodes.py` use `_emit_status()` which puts events into an `asyncio.Queue` stored in `config["configurable"]["_status_queue"]`. `chat.py` runs two concurrent tasks — `_run_agent` (LangGraph events) and `_relay_status` (queue consumer) — merged into a unified queue for ordered NDJSON emission. Events from the internal `router` node are filtered out and never streamed to the user.

---

## Key Architectural Patterns

### Hybrid Router (rag-api-new)

Before any RAG processing, the agent graph runs a hybrid router (`app/agent/router.py`) that dispatches messages to different branches:

1. **Regex fast-path**: Checks for greeting (`привет`, `hello`), thanks (`спасибо`), farewell (`пока`), CV request (`пришли резюме`, `send cv`) patterns — instant dispatch without LLM
2. **Multi-turn CV state**: If `pending_action == "cv_awaiting_email"`: extract email → 3-way LLM classification (`is_cv_continuation()` → `YES/CANCEL/CHANGE`)
3. **LLM fallback**: For ambiguous inputs, calls `router_llm` (`classify_intent()`) to classify as `greeting/thanks/farewell/cv_request/off_topic/rag`

**Branches:**
- `greeting/thanks/farewell` → `smalltalk_node` (deterministic canned responses, 0 LLM calls)
- `off_topic` → `offtopic_node` (deterministic refusal with suggested questions, 0 LLM calls)
- `cv_start` → `cv_start_node` (extract/ask for email, trigger CV send)
- `cv_process` → `cv_process_node` (process email in ongoing CV flow)
- `cv_cancel` → `cv_cancel_node` (adaptive LLM response via `answer_llm`, resets `pending_action`)
- `rag` → full ReAct subgraph with RAG pipeline

Router events are filtered from NDJSON stream and never shown to users.

### CV Sending Feature (rag-api-new)

Multi-turn flow for sending CV via email:
1. User asks for CV → `cv_start_node`: extracts email from text or sets `pending_action="cv_awaiting_email"` and asks user
2. User responds in CV flow → router runs 3-way LLM (`is_cv_continuation()`):
   - `YES` → `cv_process_node`: validates email, checks rate limits, calls `EmailService.send_cv()`
   - `CANCEL` → `cv_cancel_node`: adaptive LLM response (via `answer_llm`), resets `pending_action`
   - `CHANGE` → `rag`: topic change, `clear_pending` resets `pending_action`
3. `EmailService` (stdlib `smtplib`): builds multipart MIME message (HTML body + PDF attachment), sends via STARTTLS
4. Rate limiting: 3 sends per IP per hour, 2 sends per email address per hour (Redis keys `cv:ip:{ip}` and `cv:email:{email}`)
5. Email validation: regex + disposable domain blocklist (16 providers blocked), `extract_email()` parses free text

CV PDF must exist at `CV_FILE_PATH` (default `/app/data/cv.pdf`). Configure SMTP via env vars.

### Multi-Layer RAG Pipeline (rag-api-new)

The RAG system (triggered via "rag" routing branch) uses a sophisticated multi-layer architecture:

1. **Off-topic handling**: Primary guard is **router-level** LLM classification (`classify_intent()` → `off_topic` → `offtopic_node` with deterministic refusal). `AGENT_SYSTEM_PROMPT` serves as secondary safety net
   - The `ScopeGuard` module exists in `app/agent/scope_guard/` but is **NOT called** from the main pipeline

2. **LLM Planner**: Generates structured query plan with intents, entities, tool calls
   - Uses `with_structured_output()` for reliable JSON parsing
   - Supports retry with repair prompt on validation failure
   - See `app/agent/planner/planner_llm.py:PlannerLLM.plan()`

3. **Plan Executor**: Orchestrates tool execution with fallback handling
   - Executes graph_query_tool or portfolio_search_tool based on plan
   - See `app/agent/executor/execute_plan.py:PlanExecutor.execute()`

4. **Fact Normalizer**: Filters facts by intent and tech category
   - Removes duplicates, low-confidence facts
   - See `app/agent/normalizer/normalizer.py:FactNormalizer.normalize()`

5. **Answer LLM**: Generates response with strict prompting
   - Deterministic (non-LLM) answers for: contacts, publications, project_details, technology_usage
   - LLM-based answers for remaining intents with strict prompting (no hallucinations)
   - Recovery mechanism: falls back to deterministic generation if LLM produces "not found" but evidence exists
   - See `app/agent/answer/answer_llm.py:AnswerLLM.generate()`

6. **Render Engine**: Formats answer to target style
   - BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH
   - See `app/agent/render/renderer.py:RenderEngine.render()`

### Multi-Provider LLM Architecture (rag-api-new)

The system supports multiple LLM providers with role-based model selection:

**Supported Providers:**
- `gigachat` - GigaChat API (Sber) via `langchain_gigachat` - excels at Russian language
- `deepseek` - DeepSeek API via `ChatOpenAI` - excels at reasoning (R1 model)
- `qwen` - Qwen via LiteLLM → vLLM (local) - cost-effective for simple tasks

**LLM Roles (6 independent configurations):**

| Role | Purpose | Compose Default | Code Default | Temperature |
|------|---------|-----------------|--------------|-------------|
| `identity` | "Who are you?" responses | `deepseek:deepseek-chat` | `gigachat:GigaChat-2` | 0.3 |
| `planner` | QueryPlanV3 generation | `gigachat:GigaChat-2` | `gigachat:GigaChat-2` | 0.0 |
| `answer` | User-facing responses | `deepseek:deepseek-chat` | `gigachat:GigaChat-2` | 0.2 |
| `critic` | Fact sufficiency evaluation | `deepseek:deepseek-reasoner` | `gigachat:GigaChat-2` | 0.2 |
| `agent` | ReAct orchestration | `gigachat:GigaChat-2` | `gigachat:GigaChat-2` | 0.2 |
| `router` | Intent classification (greeting/cv/rag) | `deepseek:deepseek-chat` | `deepseek:deepseek-chat` | 0.0 |

**LLM ID Format:** `provider:model` (e.g., `gigachat:GigaChat-2`, `deepseek:deepseek-reasoner`)

**⚠️ DeepSeek Reasoner Limitation:**
`deepseek-reasoner` (R1 model) does NOT support tool calling in LangChain/LangGraph due to missing `reasoning_content` field.

| Role | DeepSeek Reasoner | DeepSeek Chat | Reason |
|------|-------------------|---------------|--------|
| `IDENTITY_LLM` | ⚠️ Overkill | ✅ | Simple responses |
| `PLANNER_LLM` | ✅ | ✅ | Structured output only |
| `ANSWER_LLM` | ⚠️ Overkill | ✅ | Text generation |
| `CRITIC_LLM` | ✅ | ✅ | No tool calls |
| `AGENT_LLM` | ❌ **CANNOT USE** | ✅ | Requires tool calling |
| `ROUTER_LLM` | ⚠️ Overkill | ✅ | Fast classification (max_tokens=32) |

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│  gigachat:model ──► GigaChat() ─────────────► GigaChat API     │
│                     (langchain_gigachat)       (direct)         │
│                                                                 │
│  deepseek:model ──► ChatOpenAI() ───────────► DeepSeek API     │
│                     (base_url=api.deepseek)    (direct)         │
│                                                                 │
│  qwen:model ──────► ChatOpenAI() ──► LiteLLM ──► vLLM          │
│                     (base_url=litellm)         (local)          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `app/llm/factory.py` - `LLMFactory` with caching by (provider, model, temperature)
- `app/llm/providers.py` - `LLMProvider` enum, `ProviderConfig`
- `app/llm/exceptions.py` - `LLMConfigError`, `LLMProviderError`
- `app/llm/validation.py` - `validate_llm_config()` for startup validation
- `app/deps.py` - Role-specific LLM getters: `identity_llm()`, `planner_llm()`, `answer_llm()`, `critic_llm()`, `agent_llm()`, `router_llm()`, `email_service()`

**Configuration (environment variables):**
```bash
# Provider credentials
GIGA_AUTH_DATA=base64_credentials      # GigaChat
DEEPSEEK_API_KEY=sk-xxx                # DeepSeek
LITELLM_BASE_URL=http://localhost:8005/v1  # Qwen via LiteLLM

# LLM roles (format: "provider:model") — compose defaults:
IDENTITY_LLM=deepseek:deepseek-chat
PLANNER_LLM=gigachat:GigaChat-2
ANSWER_LLM=deepseek:deepseek-chat
CRITIC_LLM=deepseek:deepseek-reasoner
AGENT_LLM=gigachat:GigaChat-2
ROUTER_LLM=deepseek:deepseek-chat

# Temperatures
IDENTITY_TEMPERATURE=0.3
PLANNER_TEMPERATURE=0.0
ANSWER_TEMPERATURE=0.2
CRITIC_TEMPERATURE=0.2
AGENT_TEMPERATURE=0.2
ROUTER_TEMPERATURE=0.0
```

**TokenUsageCollector (Rate Limiting Integration):**

The system aggregates token usage from ALL LLM roles for accurate rate limiting:

```
Request Flow:
Router LLM ───────┐
Identity LLM ─────┤
Planner LLM ──────┤
Critic LLM ───────┼──► TokenUsageCollector ──► rate_limiter.record_usage()
Answer LLM ───────┤
Agent LLM ────────┘
```

- `app/rate_limit/usage_collector.py` - `TokenUsageCollector`, `RoleUsage`
- Each LLM class returns `(result, usage)` tuple
- `chat.py` aggregates usage from agent + rag_tool
- Total tokens recorded in Redis for rate limiting

**Usage Logging:**
```
INFO: TokenUsage summary: message_id=abc123 total=3847 breakdown=[planner=1200, critic=650, answer=1500, agent=497]
```

### Knowledge Graph (rag-api-new)

The system builds a knowledge graph from portfolio data:
- **Node Types**: PERSON, COMPANY, PROJECT (personal or experience-based), ACHIEVEMENT, TECHNOLOGY, CONTACT
- **Edge Types**: WORKS_AT, WORKED_AT, CREATED, ACHIEVED, USES, KNOWS, BELONGS_TO, HAS_CONTACT
- Projects with `company_name` are classified as "коммерческий" (commercial), without — "личный проект" (personal)
- Experience project nodes include `kind` field from CompanyExperience
- Used for structured queries (project_details, technologies, experience)
- See `app/graph/builder.py:build_graph()`

### Hybrid Retrieval
1. **Dense Search**: pgvector similarity search with embeddings
2. **BM25 Search**: Lexical keyword matching
3. **RRF Merge**: Reciprocal Rank Fusion to combine results
4. **MMR Dedup**: Remove similar documents
5. **Expand by Project**: Add related project/experience documents
6. **Cross-encoder Reranking**: Score candidates with `BAAI/bge-reranker-base`

### Document Types in RAG

The RAG system creates multiple document types:
- `profile` - Developer profile information
- `experience`, `experience_project` - Work experience
- `project` - Personal/featured projects
- `technology` - Tech stack items
- `publication` - Articles/blog posts
- `contact` - Contact information
- `stat` - Key metrics
- `focus_area`, `work_approach` - Career information
- `catalog` - Summary documents (technologies_all, technologies_by_company)
- `item` - Atomic documents (achievements, bullets, stats, contacts)

### BM25 Index Persistence

The BM25 index is persisted to disk:
- Location: `.bm25.{collection}.pkl` (CWD-relative)
- Loaded on startup via `bm25_try_load()`
- Saved after ingestion via `bm25_try_save()`
- Reset when collection is cleared

### Hero Section Animations

The hero section includes sophisticated animations:

**Neural Network Background** (`frontend-new/components/hero/ParticlesBackground.tsx`):
- Canvas-based neural network visualization with neurons, synapses, and signal pulses
- **Neurons**: Glowing circular nodes with concentric layers (glow halo, membrane ring, filled core, bright center dot). 3 depth layers (far/mid/near) for parallax. 15% are larger "hub" neurons
- **Synapses**: Thin lines connecting nearby neurons (max 180px desktop, 120px mobile). Opacity scales with distance and neuron activation. Topology rebuilt every ~1 second
- **Signal pulses**: Bright dots (80% green, 20% purple) traveling along connections. On arrival activate target neuron with 50% cascade chance, creating chain reactions
- **Activation system**: Neurons have activation level (0-1) controlling brightness/glow. Decays toward base level, boosted by mouse proximity and signal arrival
- Desktop: 60fps, 88-200 neurons with glow effects, max 31 signals, 5 connections per neuron
- Mobile: 30fps, 50-100 neurons, no glow, max 15 signals, 3 connections per neuron
- Mouse interaction: cursor activates nearby neurons (glow brighter) and triggers signal cascades; gentle push/repulsion physics
- `CONFIG` object with all tunable parameters (neuron count, connection distance, signal spawn rate, etc.)
- IntersectionObserver for visibility detection (pauses when scrolled away)
- Gradual neuron spawn on page load
- Edge wrapping for neurons

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
- `pulse-slow` - Slow pulse opacity animation (2.5s)
- `breathe` - Thinking status indicator glow pulse (box-shadow with accent-soft color)
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
- Personal featured projects (not tied to company experience)
- Fields: name, slug, short_title, featured, is_active, period, company_name, company_website, order_index
- Fields: domain ("cv" | "rag" | "backend" | "mlops" | "other"), repo_url, demo_url
- Markdown fields: description_md, long_description_md
- Many-to-many with Technology via `project_technology` junction table

**Technology** (`technology.py`):
- Tech stack items (name, slug, category, order_index)
- Many-to-many with Project

**Publication** (`publication.py`):
- Articles, blog posts
- Fields: title, year, source, url, badge, description_md, order_index
- Source types: "Habr" | "GitHub" | "Blog" | "Other"

**Contact** (`contact.py`):
- Contact methods
- Kind types: email, telegram, github, linkedin, hh, leetcode, other
- Fields: label, value, url, order_index, is_primary

**Stat** (`stats.py`):
- Key metrics for display (key, label, value, hint, group_name, order_index)

**TechFocus** (`tech_focus.py`):
- Technology focus areas grouping (label, description, order_index)
- One-to-many with `TechFocusTag` (name, order_index)

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
- `LITELLM_API_KEY` - LiteLLM API key for authentication
- `CHAT_MODEL` - Chat model alias (legacy, e.g., `Qwen2.5` or `GigaChat`)
- `EMBEDDING_MODEL` - Embedding model alias (e.g., `embedding-default`)
- `GIGA_AUTH_DATA` - GigaChat base64 credentials (if using GigaChat)
- `DEEPSEEK_API_KEY` - DeepSeek API key (if using DeepSeek)
- `DEEPSEEK_BASE_URL` - DeepSeek API URL (default: `https://api.deepseek.com/v1`)
- `HF_TOKEN` - HuggingFace token for model downloads

**LLM Roles (Multi-Provider Architecture):**
- `IDENTITY_LLM` - LLM for identity questions (format: `provider:model`, compose default: `deepseek:deepseek-chat`)
- `PLANNER_LLM` - LLM for query planning (compose default: `gigachat:GigaChat-2`)
- `ANSWER_LLM` - LLM for answer generation (compose default: `deepseek:deepseek-chat`)
- `CRITIC_LLM` - LLM for fact evaluation (compose default: `deepseek:deepseek-reasoner`)
- `AGENT_LLM` - LLM for ReAct agent (compose default: `gigachat:GigaChat-2`)
- `ROUTER_LLM` - LLM for intent classification in router (default: `deepseek:deepseek-chat`, max_tokens=32)

**LLM Temperatures:**
- `IDENTITY_TEMPERATURE` - Identity LLM temperature (default: 0.3)
- `PLANNER_TEMPERATURE` - Planner LLM temperature (default: 0.0)
- `ANSWER_TEMPERATURE` - Answer LLM temperature (default: 0.2)
- `CRITIC_TEMPERATURE` - Critic LLM temperature (default: 0.2)
- `AGENT_TEMPERATURE` - Agent LLM temperature (default: 0.2)
- `ROUTER_TEMPERATURE` - Router LLM temperature (default: 0.0)

**RAG API Specific:**
- `DATABASE_URL` - PostgreSQL connection string for pgvector (shared with content-api, e.g., `postgresql+psycopg://user:pass@host:5433/db`)
- `COLLECTION_NAME` - pgvector collection name (default: `portfolio_new`)
- `TEI_BASE_URL` - Direct TEI access URL (default: `http://tei:80/v1`)
- `EMBEDDING_MODEL` - Embedding model (default: `text-embedding-3-large`)
- `EMBEDDING_BATCH_SIZE` - Batch size for embeddings (default: 4, small to avoid TEI 413)
- `reranker_model` - Reranker model (default: `BAAI/bge-reranker-base`)
- `MAX_RERANK_CANDIDATES` - Max docs for reranker (default: 80, limits CPU to ~1.3s)
- `MAX_USER_INPUT_TOKENS` - Approximate token limit for user input (default: 250, ~1000 chars)

**Critic Settings:**
- `CRITIC_ENABLED` - Enable/disable Critic LLM (default: true)
- `CRITIC_CONFIDENCE_THRESHOLD` - Skip critic if plan confidence >= threshold (default: 0.7)
- `CRITIC_MIN_FACTS_THRESHOLD` - Skip critic if facts >= threshold (default: 2)
- `CRITIC_SKIP_INTENTS` - Intents where critic is always skipped (default: `["contacts", "current_job"]`)

**Rate Limiting:**
- `RATE_LIMIT_ENABLED` - Enable/disable rate limiting (default: true)
- `RATE_LIMIT_IP_TOKENS` - Token limit per IP per window (compose default: 50000)
- `RATE_LIMIT_WINDOW_SECONDS` - Rate limit window in seconds (compose default: 3600 = 1 hour)
- `RATE_LIMIT_WARNING_THRESHOLD` - Warning threshold as decimal (default: 0.8 = 80%)
- `RATE_LIMIT_LOG_IP_MODE` - IP logging mode: `masked` or `full` (default: `masked`)

**Redis Cache:**
- `REDIS_URL` - Redis connection URL (e.g., `redis://localhost:6379/0`)
- `CACHE_ENABLED` - Enable/disable caching (default: true)
- `PLAN_CACHE_TTL` - Plan cache TTL in seconds (default: `0` = **infinite**, manual clear only)
- `EMBEDDING_CACHE_TTL` - Embedding cache TTL in seconds (default: `0` = **infinite**, manual clear only)

**CV Sending (Email):**
- `SMTP_HOST` - SMTP server host
- `SMTP_PORT` - SMTP port (default: 587, STARTTLS)
- `SMTP_USER` - SMTP username
- `SMTP_PASSWORD` - SMTP password
- `SMTP_FROM_EMAIL` - Sender email address
- `SMTP_FROM_NAME` - Sender display name (default: `"AI-Portfolio | Dmitry"`)
- `SMTP_USE_TLS` - Use STARTTLS (default: true)
- `DOMAIN` - Site domain for email templates (e.g., `https://ai-folio.ru`)
- `CV_FILE_PATH` - Path to CV PDF in container (default: `/app/data/cv.pdf`)
- `CV_ATTACHMENT_NAME` - Attachment filename in email
- `CV_SEND_LIMIT_PER_IP` - Max CV sends per IP per window (default: 3)
- `CV_SEND_LIMIT_PER_EMAIL` - Max CV sends per email per window (default: 2)
- `CV_SEND_LIMIT_WINDOW_SECONDS` - CV rate limit window (default: 3600 = 1 hour)

**Vector Database:**
- pgvector runs inside the shared PostgreSQL instance (no separate service)
- `DATABASE_URL` - Same connection string as content-api (see Database section above)
- `COLLECTION_NAME` - pgvector collection name (default: `portfolio_new`)

**Service Ports (docker-compose.local.yaml defaults):**
- Frontend - 3000
- `POSTGRES_PORT` - 5433 (PostgreSQL with pgvector)
- `CONTENT_PORT` - 8003 (content-api)
- `TEI_PORT` - 8006 (Text Embeddings Inference)
- `LITELLM_PORT` - 8005 (LiteLLM proxy)
- `REDIS_PORT` - 6379 (Redis)
- `RAG_NEW_PORT` - 8014 (rag-api, builds from rag-api-new/; compose YAML fallback is `:-8004` but `.env.dev`/`.env.example` set it to `8014`)

---

## Common Pitfalls

1. **Wrong Service Directories**:
   - ✅ Use `content-api-new`, `frontend-new`, `rag-api-new`
   - ❌ `content-api`, `frontend`, `rag-api` directories were deleted (do not reference them)

2. **API Versioning**:
   - content-api-new endpoints are prefixed with `/api/v1/`
   - rag-api-new endpoints are prefixed with `/api/v1/`
   - Frontend must use correct base URL with version prefix

3. **Circular Imports**: Keep `deps.py` for shared dependencies, avoid importing between API routers

4. **Migration Conflicts**:
   - Always check `alembic current` before creating migrations
   - Migration location: `services/content-api-new/alembic/versions/`

5. **Encoding Issues**: Verify UTF-8 encoding, especially when working with Cyrillic text (MANDATORY)

6. **Agent Tool Usage**: The RAG agent MUST call tools for portfolio questions - don't let LLM answer directly

7. **CORS Configuration**:
   - Ensure `FRONTEND_ORIGIN` matches frontend URL
   - All APIs check CORS strictly

8. **Docker Networking**:
   - PostgreSQL accessed via `postgres:5432` (internal Docker service, shared by content-api and rag-api for pgvector)
   - Internal service communication uses service names (e.g., `litellm:4000`, `tei:80`)

9. **LiteLLM Model Aliases**:
   - Model names must match aliases in `infra/litellm/config.yaml`
   - Default models: `CHAT_MODEL=Qwen2.5` (or `GigaChat`), `EMBEDDING_MODEL=embedding-default`
   - Check `infra/litellm/config.yaml` for available model aliases

10. **Markdown Fields**:
    - Many fields support markdown (e.g., `summary_md`, `description_md`, `achievements_md`, `long_description_md`)
    - Frontend renders with `react-markdown`

11. **BM25 Index State**:
    - BM25 index is stored in pickle files (`.bm25.{collection}.pkl` (CWD-relative))
    - Clear both pgvector collection and BM25 when resetting collection via `/api/v1/admin/collection`

12. **pgvector Collection**:
    - `rag-api-new` uses `COLLECTION_NAME=portfolio_new`
    - pgvector stores embeddings in the shared PostgreSQL database (no separate vector DB service)
    - The old ChromaDB-based `portfolio` collection (from deleted rag-api) is no longer used

13. **Cache Invalidation**:
    - Plan cache auto-invalidates when content hash changes (after ingest)
    - Embedding cache does NOT auto-invalidate (depends only on query text)
    - After changing `prompts.py` or planner logic: clear plan cache via `/api/v1/admin/cache/plans`
    - After changing embedding model: clear embedding cache via `/api/v1/admin/cache/embeddings`
    - Default TTL is `0` (infinite) — caches persist until manually cleared

14. **Rate Limit Token Consumption**:
    - Each agent request consumes ~6000-9000 tokens due to multi-stage pipeline (6 LLM roles)
    - Pipeline stages: Router LLM (~50), Agent system prompt (~2000), Planner LLM (~1500), RAG Tool (~1500), Answer LLM (~2000), Response (~1500)
    - With production limit of 50000 tokens/hour, users can make ~5-8 requests per hour
    - Rate limit is per IP, not per session - all users from same IP share the limit
    - CV send has a separate Redis-based rate limit: 3/IP and 2/email per hour

15. **CV Sending Setup**:
    - CV PDF must be placed at path defined by `CV_FILE_PATH` (default `/app/data/cv.pdf` in container)
    - `data/` directory at project root is volume-mounted into the container
    - SMTP credentials must be configured via env vars for CV sending to work
    - If SMTP not configured, `EmailService` logs a warning and CV send will fail gracefully

16. **ScopeGuard Module**:
    - The `app/agent/scope_guard/` module exists but is **NOT called** from the main pipeline
    - Off-topic detection is handled at **router level** via `classify_intent()` → `off_topic` → `offtopic_node`
    - `AGENT_SYSTEM_PROMPT` serves as secondary safety net
    - Do not add ScopeGuard calls to the RAG pipeline

17. **Technical Specs in `discource/`**:
    - Always check `discource/docs/` for existing ТЗ before implementing new features
    - Check `discource/specs/` for detailed implementation specifications
    - Create a new spec before starting complex implementations
    - Note: folder is named `discource` (typo preserved for consistency)

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
│   │   ├── agent/                  # RAG agent chat (AgentDock, AgentChatWindow, ThinkingStatus, etc.)
│   │   ├── hero/                   # Hero section (HeroIntro, HeroScrollHint, neural network background)
│   │   ├── about/                  # About section (AboutMeSection, StatsGrid)
│   │   ├── experience/             # Experience section (ExperienceSection, ExperienceCard)
│   │   ├── tech/                   # Tech focus (TechFocusSection)
│   │   ├── projects/               # Projects (ProjectsSection, ProjectCard)
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
├── services/
│   ├── content-api-new/            # ✅ ACTIVE Content API (versioned API)
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI app entry
│   │   │   ├── settings.py         # Application settings
│   │   │   ├── db.py               # Database setup
│   │   │   ├── models/             # SQLAlchemy models (all listed above)
│   │   │   ├── routers/            # API endpoints (/api/v1/*)
│   │   │   ├── schemas/            # Pydantic schemas
│   │   │   ├── core/config.py      # Core settings
│   │   │   └── seed/               # Database seeding (seed_ai_portfolio_new.py)
│   │   ├── alembic/                # Database migrations
│   │   │   └── versions/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── rag-api-new/                # ✅ ACTIVE RAG & Agent API (multi-layer pipeline)
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI app with routers
│   │   │   ├── settings.py         # Pydantic settings (temperatures, etc.)
│   │   │   ├── deps.py             # Shared dependencies (LLMs, PGVectorStore, reranker)
│   │   │   ├── prefetch.py         # Cache warmup for popular questions
│   │   │   ├── agent/              # Agent system
│   │   │   │   ├── graph.py        # StateGraph: hybrid router + ReAct subgraph + CV + smalltalk + off-topic
│   │   │   │   ├── graph_state.py  # AgentState TypedDict (messages, pending_action, _route_intent)
│   │   │   │   ├── router.py       # router_node (regex→LLM), route_edge conditional
│   │   │   │   ├── router_llm.py   # classify_intent() (6 intents incl. off_topic), is_cv_continuation() (YES/CANCEL/CHANGE)
│   │   │   │   ├── cv_nodes.py     # cv_start_node, cv_process_node, CV rate limiting
│   │   │   │   ├── cv_cancel_node.py # Adaptive LLM cancel response (answer_llm), resets pending_action
│   │   │   │   ├── smalltalk_node.py # Deterministic responses for greeting/thanks/farewell
│   │   │   │   ├── offtopic_node.py  # Deterministic off-topic refusal with suggestions
│   │   │   │   ├── rag_tool.py     # RAG tool (ReAct subgraph)
│   │   │   │   ├── identity/       # Identity questions (classifier.py, prompts.py)
│   │   │   │   ├── planner/        # LLM planner (planner_llm.py, schemas_v3.py, schemas.py, prompts.py, shortcuts.py)
│   │   │   │   ├── scope_guard/    # Off-topic detection — NOT active in pipeline (scope_guard.py, schemas.py)
│   │   │   │   ├── executor/       # Plan executor (execute_plan.py)
│   │   │   │   ├── normalizer/     # Fact normalizer (normalizer.py, fact_bundle.py)
│   │   │   │   ├── answer/         # Answer generation (answer_llm.py, prompts.py)
│   │   │   │   ├── render/         # Response rendering (renderer.py)
│   │   │   │   ├── critic/         # Answer evaluation (critic_llm.py, prompts.py, schemas.py)
│   │   │   │   ├── grounding/      # Evidence grounding (grounding_verifier.py)
│   │   │   │   └── tools/          # Agent tools (portfolio_search_tool.py, graph_query_tool.py)
│   │   │   ├── rag/                # RAG pipeline
│   │   │   │   ├── search.py       # Main search orchestration
│   │   │   │   ├── retrieval.py    # HybridRetriever
│   │   │   │   ├── rank.py         # Reranking
│   │   │   │   ├── evidence.py     # Evidence selection
│   │   │   │   ├── entities.py     # Entity registry
│   │   │   │   ├── nlp.py          # NLP utilities
│   │   │   │   ├── formatter.py    # Format rendering
│   │   │   │   ├── search_types.py # Search types
│   │   │   │   ├── types.py        # Core types
│   │   │   │   └── utils.py        # RAG utility functions
│   │   │   ├── graph/              # Knowledge graph
│   │   │   │   ├── schema.py       # NodeType, EdgeType
│   │   │   │   ├── builder.py      # Graph construction
│   │   │   │   ├── query.py        # Graph queries
│   │   │   │   └── store.py        # Graph storage
│   │   │   ├── indexing/           # Document indexing
│   │   │   │   ├── normalizer.py   # Document normalization
│   │   │   │   ├── chunker.py      # Text chunking
│   │   │   │   ├── bm25.py         # BM25 index
│   │   │   │   └── persistence.py  # BM25 persistence
│   │   │   ├── email/              # CV sending via SMTP (NEW)
│   │   │   │   ├── service.py      # EmailService (smtplib, multipart MIME + PDF)
│   │   │   │   ├── templates.py    # CV email HTML/plain body templates
│   │   │   │   └── validation.py   # validate_email, extract_email (disposable domain blocklist)
│   │   │   ├── cache/              # Redis caching
│   │   │   │   ├── cache_service.py # CacheService with graceful degradation
│   │   │   │   ├── plan_cache.py   # Plan caching (shortcut → cache → LLM)
│   │   │   │   └── embedding_cache.py # Query embedding cache
│   │   │   ├── rate_limit/         # Rate limiting
│   │   │   │   ├── limiter.py      # RateLimiter class
│   │   │   │   ├── schemas.py      # Rate limit schemas
│   │   │   │   └── usage_collector.py # TokenUsageCollector for multi-role aggregation
│   │   │   ├── llm/                # Multi-provider LLM factory
│   │   │   │   ├── factory.py      # LLMFactory, parse_llm_id(), get_provider_info()
│   │   │   │   ├── providers.py    # LLMProvider enum, ProviderConfig
│   │   │   │   ├── exceptions.py   # LLMConfigError, LLMProviderError
│   │   │   │   ├── validation.py   # validate_llm_config() for startup
│   │   │   │   └── gigachat_adapter.py # Legacy adapter
│   │   │   ├── routers/            # API routers
│   │   │   │   ├── chat.py         # /api/v1/agent/chat/stream
│   │   │   │   ├── ingest.py       # /api/v1/ingest
│   │   │   │   ├── ingest_batch.py # /api/v1/ingest/batch
│   │   │   │   └── admin.py        # /api/v1/admin/* + /api/v1/rate-limit/status
│   │   │   ├── schemas/            # Pydantic schemas
│   │   │   │   ├── chat.py, ingest.py, export.py, admin.py, ask.py
│   │   │   └── utils/              # Utilities
│   │   │       ├── logging_utils.py
│   │   │       └── metadata.py
│   │   ├── tests/                  # Tests
│   │   │   ├── test_smoke.py       # Smoke tests
│   │   │   ├── test_tz_v3_acceptance.py  # QueryPlanV3 acceptance
│   │   │   ├── test_answer_llm_usage.py  # Answer LLM token tracking
│   │   │   ├── test_llm_factory.py       # LLM factory tests
│   │   │   ├── test_usage_collector.py   # TokenUsageCollector tests
│   │   │   └── llm/test_providers.py     # Provider-specific tests
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── Dockerfile.prod         # Production Docker image
│   │
│
├── data/                            # Static files volume-mounted into containers (gitignored)
│   └── cv.pdf                       # CV PDF for email sending (CV_FILE_PATH=/app/data/cv.pdf)
│
├── infra/
│   ├── docker-compose.local.yaml   # ✅ Primary local dev compose
│   ├── docker-compose-prod.yaml    # Production compose
│   ├── .env.dev                    # Development env variables
│   ├── .env.local                  # Local env variables
│   ├── .env.prod                   # Production env variables
│   ├── .env.example                # Comprehensive env example
│   ├── DOCKER-LOCAL.md             # Local Docker setup guide
│   ├── DOCKER-PROD.md              # Production Docker setup guide
│   ├── caddy/Caddyfile             # Reverse proxy (production)
│   ├── init/postgres-init.sql      # DB init (uuid-ossp, pgvector)
│   ├── scripts/ingest.py           # RAG ingestion script
│   ├── litellm/
│   │   └── config.yaml             # LiteLLM model aliases
│   └── models/
│       └── intfloat/multilingual-e5-base/  # TEI embedding model
│
├── discource/                       # 📋 Technical specifications and specs
│   ├── docs/                        # Technical requirements (ТЗ)
│   │   ├── TZ_MULTI_LLM_PROVIDERS.md    # Multi-provider LLM architecture spec
│   │   ├── TZ_RATE_LIMIT.md             # Rate limiting implementation spec
│   │   ├── TZ_RAG_OPTIMIZATION.md       # RAG optimization techniques spec
│   │   └── TZ_AI-Portfolio_RAG_Agent_Hardening.md  # Agent hardening spec
│   ├── specs/                       # Implementation specifications
│   │   └── agent-identity-vs-profile-detection.md  # Identity vs Profile detection
│   └── planning-with-files-archive/ # Historical planning session archives
│
├── CLAUDE.md                       # This file (EN)
├── CLAUDE_RU.md                    # This file (RU)
├── AGENTS.md                       # Agent-related documentation
└── tech-task-rag-api-new-develop.md  # RAG API new technical task specification
```

**Key Points:**
- ✅ **Active services**: `frontend-new`, `content-api-new`, `rag-api-new`
- ❌ **Deleted**: `rag-api`, `content-api`, `frontend` — do not reference
- 🐳 **Docker**: Use `infra/docker-compose.local.yaml` for local development
- 📝 **Rules**: Follow encoding and architecture rules in Critical Rules section
- 📋 In Docker compose, service `rag-api` builds from `rag-api-new/` — there is no separate `rag-api-new` service in compose
- 📁 `data/cv.pdf` at project root is volume-mounted into rag-api container for CV sending

---

## When Making Changes

**Always:**
1. **Verify service directories**: Use `content-api-new`, `frontend-new`, `rag-api-new`
2. Ensure all files are UTF-8 without BOM (mandatory encoding rule)
3. Check encoding is UTF-8 (especially for Cyrillic text in markdown fields)
4. Create Alembic migration if modifying SQLAlchemy models in `content-api-new`
5. Test locally before committing
6. Follow existing code patterns and naming conventions
7. Ensure API endpoints include `/api/v1/` prefix
8. Use markdown fields (`*_md`) for rich content that will be rendered with `react-markdown`
9. **Check `discource/` for specs** before implementing new features - specs may already exist

**Never:**
1. Use deleted directories (`content-api`, `frontend`, `rag-api`)
2. Change file encoding from UTF-8
3. Modify old Alembic migrations
4. Create circular imports
5. Mix business logic with API controllers
6. Change project structure without explicit permission
7. Skip API versioning (`/api/v1/` prefix)
8. Hardcode API URLs (use environment variables)
9. **Add workarounds or hacks** - always fix root causes, not symptoms
10. **Add "temporary" fixes** - there's nothing more permanent than a temporary solution

**Before Committing:**
1. ✅ Verify you modified the correct service (`*-new` versions)
2. ✅ Check no broken Cyrillic characters (`????` or `\u041f`)
3. ✅ Run Alembic migration if models changed
4. ✅ Test API endpoints with correct `/api/v1/` prefix
5. ✅ Verify CORS settings if frontend can't reach backend
