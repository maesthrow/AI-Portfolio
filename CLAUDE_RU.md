# CLAUDE_RU.md

Этот файл содержит инструкции для Claude Code (claude.ai/code) при работе с кодом в этом репозитории.

---

## ⚠️ CRITICAL: Активные директории сервисов

**ВСЕГДА используйте эти директории:**
- ✅ `frontend-new/` - Активный Next.js фронтенд (киберпанк-тема)
- ✅ `services/content-api-new/` - Активный Content API с версионными эндпоинтами
- ✅ `services/rag-api-new/` - **НОВЫЙ** Активный RAG & Agent API (многослойный пайплайн, LLM планировщик)
- ✅ `infra/docker-compose.local.yaml` - Актуальная конфигурация Docker Compose (локальная разработка)

**Legacy сервис (доступен, но для новой разработки используйте rag-api-new):**
- ⚠️ `services/rag-api/` - Legacy RAG API (упрощенная архитектура, порт 8004)

**НИКОГДА не используйте эти директории (удалены из кодовой базы):**
- ❌ `frontend/` - Старый фронтенд (удален)
- ❌ `services/content-api/` - Старый Content API (удален)
- ❌ `infra/docker-compose.yaml` - Старый Docker Compose (deprecated)

Если случайно начали работать в устаревших директориях, **ОСТАНОВИТЕСЬ** и сразу переключитесь на правильные.

---

## Обзор проекта

**AI-Portfolio** — микросервисное киберпанк-портфолио с возможностями RAG (Retrieval-Augmented Generation). Система состоит из фронтенда на Next.js, базы данных PostgreSQL, бэкенд-сервисов на FastAPI и векторной БД ChromaDB для семантического поиска с агентом на LangGraph.

**Технологический стек:**
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Framer Motion, react-markdown
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic
- RAG: LangChain, LangGraph, ChromaDB, sentence-transformers, rank-bm25
- LLM-инфраструктура: LiteLLM proxy, vLLM (Qwen2.5-7B-Instruct-AWQ), TEI (multilingual-e5-base embeddings)
- База данных: PostgreSQL 16
- Инфраструктура: Docker Compose

---

## Архитектура

Проект построен на микросервисной архитектуре с ключевыми сервисами:

### 1. **Content API** (`services/content-api-new/`)
**ВАЖНО: Используйте `content-api-new`, НЕ `content-api` (старая версия)**

- Управляет структурированными данными портфолио через версионированный REST API
- SQLAlchemy ORM с Alembic миграциями
- Версия API: все эндпоинты имеют префикс `/api/v1/`
- Точка входа: `app/main.py`
- Порт: 8003

Основные модули:
- `app/models/` - модели SQLAlchemy:
  - `profile.py` - Profile (full_name, title, subtitle, summary_md, hero_headline, hero_description, current_position)
  - `experience.py` - CompanyExperience (role, company_name, company_slug, start_date, end_date, is_current, kind, company_summary_md, company_role_md, description_md)
  - `experience_project.py` - ExperienceProject (проекты внутри опыта с achievements_md)
  - `project.py` - Project (личные/featured проекты; slug, technologies, featured, domain, repo_url, demo_url, long_description_md)
  - `publication.py` - Publication (статьи/посты)
  - `contact.py` - Contact (email, telegram, github, linkedin, hh, leetcode)
  - `stats.py` - Stat (ключевые метрики)
  - `tech_focus.py` - TechFocus (технологические направления)
  - `technology.py` - Technology (элементы стека)
  - `hero_tag.py` - HeroTag (теги в hero-секции)
  - `focus_area.py` - FocusArea, FocusAreaBullet (фокусные направления с буллетами)
  - `work_approach.py` - WorkApproach, WorkApproachBullet (подходы к работе с буллетами и иконками)
  - `section_meta.py` - SectionMeta (метаданные секций: title, subtitle)
- `app/routers/` - API эндпоинты:
  - `profile.py` - GET `/api/v1/profile`
  - `experience.py` - GET `/api/v1/experience`, GET `/api/v1/experience/{slug}`
  - `stats.py` - GET `/api/v1/stats`
  - `tech_focus.py` - GET `/api/v1/tech-focus`
  - `projects.py` - GET `/api/v1/projects`, GET `/api/v1/projects/{slug}`
  - `publications.py` - GET `/api/v1/publications`
  - `contacts.py` - GET `/api/v1/contacts`
  - `rag.py` - GET `/api/v1/rag/documents` (legacy плоский список), GET `/api/v1/rag/export` (структурированный ExportPayload для RAG-индексации)
  - `hero_tags.py` - GET `/api/v1/hero-tags`
  - `focus_areas.py` - GET `/api/v1/focus-areas`
  - `work_approaches.py` - GET `/api/v1/work-approaches`
  - `section_meta.py` - GET `/api/v1/section-meta`, GET `/api/v1/section-meta/{section_key}`
- `app/schemas/` - Pydantic-схемы (включая `rag_export.py` — ExportPayload для RAG)
- `app/settings.py` - настройки приложения
- `alembic/` - миграции базы данных

### 2. **RAG API New** (`services/rag-api-new/`) ⭐ РЕКОМЕНДУЕТСЯ
**Многослойный RAG пайплайн с LLM-планировщиком и детерминированной генерацией ответов**

- Продвинутый семантический поиск с LLM-планированием запросов
- Knowledge Graph для структурированных запросов
- Scope Guard для детекции off-topic вопросов
- Детерминированная нормализация фактов и генерация ответов
- Точка входа: `app/main.py`
- Порт: 8004 (Docker compose через `RAG_NEW_PORT`), 8000 (default uvicorn)
- Документация: `/api/swagger`

**Архитектура многослойного пайплайна:**
```
Вопрос пользователя
    ↓
[ScopeGuard] - Детекция off-topic (сказки, генерация кода и т.д.)
    ↓
[PlannerLLM] - Генерация QueryPlanV3 (intents, entities, tool_calls)
    ↓
[PlanExecutor] - Оркестрация выполнения тулзов
    ├─ [graph_query_tool] - Запросы к графу знаний
    └─ [portfolio_search_tool] - Гибридный поиск (dense + BM25 + rerank)
    ↓
[FactNormalizer] - Детерминированная фильтрация фактов по intent
    ↓
[AnswerLLM] - Генерация ответа со строгим промптингом (без галлюцинаций)
    ↓
[RenderEngine] - Форматирование в целевой стиль (BULLETS, TABLE, GROUPED_BULLETS и др.)
    ↓
Ответ пользователю (стриминг или прямой)
```

**Основные модули:**
- `app/main.py` - FastAPI приложение с роутерами, health endpoints (`/healthz`, `/meta`)
- `app/settings.py` - Pydantic настройки с температурами LLM
- `app/deps.py` - Общие зависимости (инстансы LLM, vectorstore, reranker)
- `app/prefetch.py` - Прогрев кэша для популярных вопросов
  - `POPULAR_QUESTIONS` - Список частых вопросов в user-style и agent-style формулировках
  - `prefetch_popular_plans()` - Прогревает Redis кэш после ingest (~60-70% cache hit rate)

**API роутеры** (`app/routers/`):
- `chat.py` - POST `/api/v1/agent/chat/stream` - Стриминговый чат с NDJSON (status-события через unified asyncio.Queue)
- `ingest.py` - POST `/api/v1/ingest` - Загрузка одного документа
- `ingest_batch.py` - POST `/api/v1/ingest/batch` - Пакетный импорт ExportPayload
- `admin.py` - Админские эндпоинты:
  - DELETE `/api/v1/admin/collection` - Очистка коллекции ChromaDB
  - GET `/api/v1/admin/stats` - Статистика коллекции и графа
  - GET `/api/v1/admin/cache/stats` - Статистика кэша (Redis)
  - DELETE `/api/v1/admin/cache/plans` - Очистка plan cache
  - DELETE `/api/v1/admin/cache/embeddings` - Очистка embedding cache
  - DELETE `/api/v1/admin/cache` - Очистка всех кэшей
  - GET `/api/v1/rate-limit/status` - Статус rate limit для текущего IP

**Агентная система** (`app/agent/`):
- `graph.py` - LangGraph агент с ReAct паттерном и памятью
- `rag_tool.py` - Async RAG тулза для агента с эмиссией статусов пайплайна
  - `_emit_status(stage, text, config)` - Отправляет status-события на фронтенд через `asyncio.Queue` из `config["configurable"]["_status_queue"]`
  - Этапы: `planning`, `searching`, `verifying`, `answering`
  - Тяжёлые sync-операции обёрнуты в `asyncio.to_thread()` (planner, executor, critic, search, answer)

**Identity** (`app/agent/identity/`):
- `classifier.py` - Двухуровневая детекция identity-вопросов:
  1. **Лингвистическая проверка** (детерминированная): Обнаруживает местоимения 2-го лица (ты, себя, твой и т.д.) → confidence=1.0
  2. **Семантическое сравнение** (embedding similarity): Сравнение с референсными вопросами → confidence=similarity score
  - `SIMILARITY_THRESHOLD = 0.92` для консервативного matching (избежание false positive)
  - `is_identity_question(question)` возвращает `(is_identity, max_similarity)`
  - `generate_identity_response(question)` генерирует LLM-ответ о возможностях агента
- `prompts.py` - Промпты и список возможностей
  - `CAPABILITIES` - Список возможностей агента (легко расширяемый)
  - `IDENTITY_REFERENCE_QUESTIONS` - Референсные вопросы для semantic matching (курированы для избежания false positive с вопросами о проектах)
  - `get_identity_system_prompt()` - Генерирует системный промпт с актуальными возможностями

**Планировщик** (`app/agent/planner/`):
- `planner_llm.py` - LLM-планировщик запросов со structured output
- `schemas_v3.py` - QueryPlanV3, IntentV3, TechCategory, ToolCallV3, RenderStyleV3, AnswerStyleV3, InfoNeed, ScopeLevel, TechFilter, Scope, EntitiesV3, AnswerFormatV3, LimitsConfigV3, FallbackConfigV3, FactBundleItem, FactBundle, NormalizerOutput, GroundingResult
- `schemas.py` - Legacy QueryPlan схема (совместимость с V2)
- `prompts.py` - Системные промпты для планировщика (intents, tools, entity extraction)
- `shortcuts.py` - Шорткаты планов для однозначных вопросов (контакты, текущая работа, кто разработчик)
  - `SAFE_SHORTCUTS` - Dict regex-паттернов к готовым QueryPlanV3
  - `try_shortcut(question)` - Возвращает план если shortcut подходит, иначе None (fallback на LLM)

**TechCategory** (для фильтрации технологий):
- `language` - Языки программирования (Python, C#, JavaScript, SQL)
- `database` - Базы данных (PostgreSQL, MongoDB, Redis)
- `vector_store` - Векторные БД (ChromaDB, Qdrant, pgvector)
- `framework` - Фреймворки (FastAPI, React, Django)
- `ml_framework` - ML-фреймворки (LangChain, LangGraph, vLLM)
- `mlops` - MLOps-инструменты (MLFlow, LiteLLM)
- `concept` - Концепции (RAG, LLM, ReAct)
- `tool` - Инструменты (Docker, Git)
- `message_broker` - Брокеры сообщений (RabbitMQ, Kafka)
- `library` - Библиотеки (SQLAlchemy, Alembic, pytest)
- `cloud` - Облачные сервисы
- `other` - Прочие технологии

**Интенты (IntentV3):**
- `CURRENT_JOB` - Текущая позиция
- `PROJECT_DETAILS` - Информация о проекте
- `PROJECT_ACHIEVEMENTS` - Достижения в проектах
- `PROJECT_TECH_STACK` - Технологии в проектах
- `TECHNOLOGY_OVERVIEW` - Описание технологии
- `TECHNOLOGY_USAGE` - Где использовалась технология
- `EXPERIENCE_SUMMARY` - Опыт работы
- `PROFILE` - Информация о разработчике (PERSON node: имя, должность, описание, локация)
- `CONTACTS` - Контактная информация
- `GENERAL_UNSTRUCTURED` - Fallback для общих вопросов

**Scope Guard** (`app/agent/scope_guard/`):
- `scope_guard.py` - Детекция off-topic (сказки, шутки, генерация кода и т.д.)
- `schemas.py` - ScopeDecision с suggested_prompts для перенаправления пользователя

**Executor** (`app/agent/executor/`):
- `execute_plan.py` - PlanExecutor для оркестрации тулзов с fallback handling

**Normalizer** (`app/agent/normalizer/`):
- `normalizer.py` - FactNormalizer с intent-специфичными правилами фильтрации
- `fact_bundle.py` - Группировка фактов по типу/проекту

**Генерация ответов** (`app/agent/answer/`):
- `answer_llm.py` - AnswerLLM со строгим промптингом для предотвращения галлюцинаций
  - Детерминированная (без LLM) генерация для: `contacts`, `publications`, `project_details`, `technology_usage`
  - `_deterministic_render()` - Общий метод для детерминированного рендеринга фактов с преамбулой
  - Fallback на LLM только когда детерминированный путь недоступен для интента
- `prompts.py` - Системные промпты и инструкции по стилю

**Render** (`app/agent/render/`):
- `renderer.py` - RenderEngine (BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH)
  - `_format_fact_with_metadata()` - Централизованное форматирование с поддержкой URL/метаданных (контакты, проекты, публикации, технологии)
  - `_format_fact_inline()` - Инлайн-форматирование для стилей SHORT и PARAGRAPH

**Critic** (`app/agent/critic/`):
- `critic_llm.py` - CriticLLM для оценки ответов
- `prompts.py` - Системные промпты критика
- `schemas.py` - Схемы FactSufficiency

**Grounding** (`app/agent/grounding/`):
- `grounding_verifier.py` - Проверка, что ответ основан на evidence

**Tools** (`app/agent/tools/`):
- `portfolio_search_tool.py` - Гибридный поиск с полным RAG пайплайном
- `graph_query_tool.py` - Структурированные запросы к графу (project_details, technologies, experience)

**RAG Pipeline** (`app/rag/`):
- `search.py` - Оркестрация `portfolio_search()`
- `retrieval.py` - `HybridRetriever` (dense + BM25 + RRF merge + MMR dedup)
- `rank.py` - Cross-encoder реранкинг
- `evidence.py` - Отбор evidence и упаковка контекста (без технических метаданных для естественного чтения)
- `entities.py` - EntityRegistry для matching сущностей
- `nlp.py` - NLP утилиты (ключевые слова, поддержка RU)
- `formatter.py` - FormatRenderer для пост-обработки
- `search_types.py` - SearchResult, Intent, EntityType
- `types.py` - Doc, ScoredDoc, SourceInfo
- `utils.py` - Вспомогательные утилиты RAG пайплайна

**Knowledge Graph** (`app/graph/`):
- `schema.py` - NodeType (PERSON, COMPANY, PROJECT, ACHIEVEMENT, TECHNOLOGY, CONTACT), EdgeType
  - PROJECT = личный или experience-based (не "standalone")
- `builder.py` - Построение графа из ExportPayload (включает поле `kind` для проектов из опыта)
- `query.py` - Выполнение запросов к графу (классифицирует проекты как "коммерческий" или "личный проект" по наличию company_name)
- `store.py` - In-memory GraphStore singleton

**Indexing** (`app/indexing/`):
- `normalizer.py` - Нормализация документов из ExportPayload
- `chunker.py` - Чанкинг текста (~900 chars, поддержка RU)
- `bm25.py` - BM25Index реализация
- `persistence.py` - Персистентность BM25 (`~/.bm25.{collection}.pkl`)

**Cache** (`app/cache/`):
- `cache_service.py` - CacheService с graceful degradation для Redis
- `plan_cache.py` - Кэширование планов (shortcut → cache → LLM)
- `embedding_cache.py` - Кэширование embeddings запросов
- Возможности:
  - Redis-кэширование с настраиваемым TTL
  - Автоинвалидация plan cache при изменении content hash
  - Нормализация вопросов для консистентности ключей кэша
  - Graceful degradation при недоступности Redis

**Rate Limiting** (`app/rate_limit/`):
- `limiter.py` - Класс RateLimiter для токен-лимитов по IP с Redis
- `schemas.py` - Схемы RateLimitBucket, RateLimitInfo, RateLimitStatus
- Возможности:
  - Токен-лимиты по IP-адресу (не по сессии)
  - Настраиваемый лимит токенов и временное окно
  - Порог предупреждения при приближении к лимиту (по умолчанию 80%)
  - Redis-хранилище с graceful degradation
  - Информация о лимите возвращается в событии `end` стриминга
  - Фронтенд показывает предупреждение при приближении к лимиту, блокирует при превышении

**LLM Factory** (`app/llm/`):
- `factory.py` - класс `LLMFactory`, `parse_llm_id()`, `get_llm_factory()`, `get_provider_info()`
- `providers.py` - `LLMProvider` enum (GIGACHAT, DEEPSEEK, QWEN), `ProviderConfig`
- `exceptions.py` - `LLMConfigError`, `LLMProviderError`
- `validation.py` - `validate_llm_config()` для валидации при старте
- `gigachat_adapter.py` - GigaChat адаптер для LangChain (legacy)

**Schemas** (`app/schemas/`):
- `chat.py` - ChatRequest, ChatMessage (стриминговые типы)
- `ingest.py` - IngestItem, IngestRequest, IngestResult
- `export.py` - ExportPayload со всеми типами сущностей
- `admin.py` - AdminStats
- `ask.py` - AskRequest, AskResponse

**Utilities** (`app/utils/`):
- `logging_utils.py` - Компактный JSON, truncation текста
- `metadata.py` - Генерация Document ID, хэширование контента

### 3. **RAG API Legacy** (`services/rag-api/`) ⚠️ LEGACY
**Упрощенная RAG архитектура - доступна, но для новых фич используйте rag-api-new**

- Базовый семантический поиск и ответы на вопросы
- Агент на LangGraph с памятью (паттерн ReAct)
- Гибридный поиск: dense embeddings + BM25
- Реранкинг cross-encoder
- Стриминговый чат
- Точка входа: `app/main.py`
- Порт: 8004

См. документацию legacy в предыдущих версиях CLAUDE.md.

### 4. **Frontend** (`frontend-new/`)
**ВАЖНО: Используйте `frontend-new`, НЕ `frontend` (старая версия)**

- Next.js 14 с App Router
- Server-side rendering (SSR)
- Киберпанк UI с анимациями на Framer Motion
- react-markdown для рендера markdown
- Точка входа: `app/page.tsx`
- Порт: 3000

**Страницы:**
- `app/page.tsx` - главная страница (фетчит все данные, включает ParticlesBackground)
- `app/layout.tsx` - корневой layout с AgentDock и CustomCursor
- `app/projects/[slug]/page.tsx` - страница проекта (long_description_md)
- `app/experience/[company_slug]/page.tsx` - страница опыта с проектами и достижениями
- `app/globals.css` - глобальные стили и анимации hero

**Компоненты:**
- `components/agent/` - чат с RAG-агентом:
  - `AgentDock.tsx` - глобальный плавающий чат (управляет состоянием `thinkingStatus`)
  - `AgentChatWindow.tsx` - UI окна чата (прокидывает thinkingStatus в список сообщений)
  - `AgentInput.tsx` - инпут сообщений
  - `AgentMessageList.tsx` - вывод сообщений со стримингом и авто-скроллом при thinking status
  - `ThinkingStatus.tsx` - индикатор этапа пайплайна с очередью min-duration (800мс) и crossfade-анимацией (200мс)
  - `RateLimitWarning.tsx` - предупреждение при приближении к лимиту (анимация Framer Motion)
  - `RateLimitBlocked.tsx` - блокировка UI при превышении лимита или недоступности сервиса
- `components/hero/` - Hero-секция:
  - `HeroIntro.tsx` - контент hero с анимациями Framer Motion
  - `HeroScrollHint.tsx` - кнопка скролла вниз с анимацией
  - `ParticlesBackground.tsx` - канвас-анимация киберпанк-частиц
- `components/about/` - секция About:
  - `AboutMeSection.tsx` - контейнер секции
  - `StatsGrid.tsx` - сетка статистики с CountUp и IntersectionObserver
- `components/experience/` - секция опыта:
  - `ExperienceSection.tsx` - таймлайн опыта
  - `ExperienceCard.tsx` - карточка опыта (memoized)
- `components/tech/` - Tech-секция:
  - `TechFocusSection.tsx` - технологические фокусы
- `components/projects/` - проекты:
  - `ProjectsSection.tsx` - грид избранных проектов
  - `ProjectCard.tsx` - карточка проекта (memoized)
- `components/publications/` - публикации:
  - `PublicationsSection.tsx` - список статей/публикаций
  - `PublicationCard.tsx` - карточка публикации (memoized)
- `components/contacts/` - контакты:
  - `ContactsSection.tsx` - контакты
  - `ContactCard.tsx` - карточка контакта (memoized)
- `components/how/` - секция How I Work:
  - `HowIWorkSection.tsx` - отображение подходов к работе
- `components/layout/` - layout-компоненты:
  - `Shell.tsx` - оболочка страницы
  - `Footer.tsx` - футер
  - `Section.tsx` - реюзабельный компонент секции с анимацией заголовков
- `components/ui/` - общие UI-компоненты:
  - `CustomCursor.tsx` - кастомный курсор (trail, ripple, breathing, velocity)
  - `SocialBadge.tsx` - бейдж соцсетей
  - `TechTag.tsx` - тег технологии

**Библиотека:**
- `lib/api.ts` - API-клиент:
  - `getProfile()` - профиль
  - `getExperience()` - список опыта
  - `getExperienceDetail(slug)` - опыт с проектами
  - `getStats()` - статистика
  - `getTechFocus()` - технологические фокусы
  - `getProjects()` - проекты
  - `getProjectBySlug(slug)` - проект по slug
  - `getFeaturedProjects()` - избранные проекты
  - `getPublications()` - публикации
  - `getContacts()` - контакты
  - `getHeroTags()` - теги hero
  - `getFocusAreas()` - фокусные области
  - `getWorkApproaches()` - подходы к работе
  - `getSectionMeta(key)` - метаданные секции
  - `getAllSectionMeta()` - метаданные всех секций
  - `askAgent(question, sessionId)` - вопрос агенту
  - `callAgentStream(body, opts)` - стриминг чата (обрабатывает 429/503 как RateLimitError, `ChatStreamEvent` union включает тип `status`)
  - `getRateLimitStatus()` - текущий статус rate limit для IP
  - `isRateLimitError(error)` - type guard для RateLimitError
- `lib/types.ts` - типы TypeScript:
  - `Profile`, `ExperienceItem`, `ExperienceProject`, `ExperienceDetail`
  - `StatItem`, `TechFocusItem`, `Project`, `ProjectDetail`
  - `Publication`, `Contact`, `AgentMessage`
  - `HeroTag`, `FocusArea`, `FocusAreaBullet`
  - `WorkApproach`, `WorkApproachBullet`, `SectionMeta`
  - `RateLimitBucket`, `RateLimitInfo`, `RateLimitStatus`, `RateLimitError`

### 5. **Инфраструктура** (`infra/`)
- Docker Compose оркестрация
- Compose-файлы:
  - `docker-compose.local.yaml` — **основной** (локальная разработка, все сервисы)
  - `docker-compose-prod.yaml` — продакшен конфигурация
- Сервисы (`docker-compose.local.yaml`):
  - `frontend` (порт 3000) — Next.js фронтенд, собирается из frontend-new/
  - `postgres` (порт 5433) — PostgreSQL 16
  - `content-api` (порт 8003) — собирается из content-api-new/
  - `chroma` (порт 8001 внешний / 8000 внутренний) — ChromaDB
  - `tei` (порт 8006) — Text Embeddings Inference (multilingual-e5-base)
  - `litellm` (порт 8005 внешний / 4000 внутренний) — прокси LLM/embeddings
  - `redis` (порт 6379) — Redis для кэша и rate limit
  - `rag-api` (порт 8004) — **собирается из rag-api-new/** (не из rag-api/)
  - `rag-ingest` — одноразовый контейнер: экспорт из content-api → инжест в rag-api
- Другие файлы:
  - `.env.dev`, `.env.local`, `.env.prod`, `.env.example` — переменные окружения
  - `DOCKER-LOCAL.md`, `DOCKER-PROD.md` — руководства по Docker
  - `caddy/Caddyfile` — reverse proxy (продакшен)
  - `init/postgres-init.sql` — инициализация БД (uuid-ossp)
  - `scripts/ingest.py` — скрипт для RAG-индексации
  - `litellm/config.yaml` — алиасы моделей LiteLLM
  - `models/intfloat/multilingual-e5-base/` — модель для TEI

**Важно:** В compose сервис `rag-api` собирается из `../services/rag-api-new`. Отдельного сервиса `rag-api-new` в compose нет.

### 6. **Техническая документация** (`discource/`)
**Хранилище технических заданий и спецификаций проекта**

Папка `discource/` содержит всю техническую документацию для реализации фич:

**Структура:**
```
discource/
├── docs/                            # Технические задания (ТЗ)
│   ├── TZ_MULTI_LLM_PROVIDERS.md   # Мультипровайдерная LLM архитектура (v1.3)
│   ├── TZ_RATE_LIMIT.md            # Реализация rate limiting (v1.0)
│   ├── TZ_RAG_OPTIMIZATION.md      # Оптимизация RAG (v1.1)
│   └── TZ_AI-Portfolio_RAG_Agent_Hardening.md  # Hardening агента (v3)
├── specs/                           # Спецификации реализации
│   └── agent-identity-vs-profile-detection.md  # Детекция Identity vs Profile вопросов
└── planning-with-files-archive/     # Архив сессий планирования
```

**Типы документов:**
- **ТЗ (Технические Задания)** в `docs/`: Высокоуровневые требования и архитектурные решения
- **Спецификации** в `specs/`: Детальные спецификации реализации с примерами кода

**Ключевые спецификации:**

1. **Мультипровайдерные LLM** (`TZ_MULTI_LLM_PROVIDERS.md`):
   - Архитектура провайдеров GigaChat, DeepSeek, Qwen
   - 5 ролей LLM (identity, planner, answer, critic, agent)
   - LLMFactory с кэшированием и валидацией

2. **Rate Limiting** (`TZ_RATE_LIMIT.md`):
   - Токен-лимиты по IP
   - Redis-хранилище с graceful degradation
   - TokenUsageCollector для агрегации usage от всех ролей

3. **Оптимизация RAG** (`TZ_RAG_OPTIMIZATION.md`):
   - Гибридный поиск (dense + BM25 + rerank)
   - Кэширование планов и шорткаты
   - Стратегии embedding cache

4. **Hardening агента** (`TZ_AI-Portfolio_RAG_Agent_Hardening.md`):
   - Scope Guard для детекции off-topic
   - Fact Normalizer для фильтрации по intent
   - Grounding verification

5. **Identity vs Profile** (`specs/agent-identity-vs-profile-detection.md`):
   - Лингвистический паттерн: местоимения 2-го лица → Identity вопросы
   - 3-е лицо / имя → Profile вопросы
   - Реализация intent PROFILE

**Когда использовать:**
- Перед реализацией новой фичи проверьте, есть ли спецификация в `discource/`
- Создайте новую спецификацию в `specs/` перед началом сложных реализаций
- Используйте ТЗ как референс для архитектурных решений

---

## Команды разработки

### Frontend (frontend-new)

```bash
cd frontend-new

npm run dev          # запуск dev-сервера (по умолчанию порт 3000)
npm run build        # сборка прод-версии
npm start            # запуск прод-сервера
npm run lint         # запуск ESLint
```

Переменные окружения (`.env.local`):
```bash
NEXT_PUBLIC_CONTENT_API_BASE=http://localhost:8003/api/v1
NEXT_PUBLIC_AGENT_API_BASE=http://localhost:8004  # rag-api в Docker compose (RAG_NEW_PORT)
# Серверные варианты (переопределяют NEXT_PUBLIC_ при SSR):
CONTENT_API_BASE=http://localhost:8003/api/v1
AGENT_API_BASE=http://localhost:8004
# Настройки анимации стриминга текста:
NEXT_PUBLIC_CHARS_PER_SECOND=60
NEXT_PUBLIC_MAX_CHARS_PER_TICK=4
# Валидация пользовательского ввода:
NEXT_PUBLIC_MAX_INPUT_TOKENS=100
NEXT_PUBLIC_CHARS_PER_TOKEN=4
```

### Content API (content-api-new)

```bash
cd services/content-api-new

# запуск API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# миграции базы данных
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# проверка состояния миграций
alembic current
alembic history

# наполнить БД примером данных
python -m app.seed.seed_ai_portfolio_new
```

Переменные окружения:
```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5433/ai_portfolio_new
FRONTEND_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO
APP_ENV=dev
```

### RAG API New (rag-api-new) ⭐ РЕКОМЕНДУЕТСЯ

```bash
cd services/rag-api-new

# запуск API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Документация API
# Откройте http://localhost:8000/api/swagger

# Загрузка документов в ChromaDB (после наполнения content-api)
# 1. Экспорт из content-api: GET http://localhost:8003/api/v1/rag/export
# 2. Импорт в rag-api: POST http://localhost:8004/api/v1/ingest/batch
# Или используйте docker compose сервис rag-ingest для автоматического экспорта+импорта
```

Переменные окружения:
```bash
litellm_base_url=http://localhost:8005/v1
litellm_api_key=dev-secret-123
tei_base_url=http://localhost:8006/v1      # TEI embeddings (прямой доступ)
embedding_model=intfloat/multilingual-e5-base  # модель embeddings
embedding_batch_size=4                     # размер батча для embeddings
reranker_model=BAAI/bge-reranker-base
max_rerank_candidates=80                   # макс. кандидатов на реранкинг
CHROMA_HOST=localhost
CHROMA_PORT=8001
chroma_collection=portfolio_new            # отличается от legacy
FRONTEND_ORIGIN=http://localhost:3000
frontend_local_ip=http://localhost:3000
LOG_LEVEL=INFO
max_user_input_tokens=250                  # макс. длина сообщения в токенах

# Роли LLM (все по умолчанию в коде: gigachat:GigaChat-2)
IDENTITY_LLM=gigachat:GigaChat-2
PLANNER_LLM=gigachat:GigaChat-2
ANSWER_LLM=gigachat:GigaChat-2
CRITIC_LLM=gigachat:GigaChat-2
AGENT_LLM=gigachat:GigaChat-2

# Температуры
planner_temperature=0.0   # детерминированное планирование
answer_temperature=0.2    # сбалансированная генерация

# Креды провайдеров (опционально)
giga_auth_data=           # Base64 креды GigaChat
DEEPSEEK_API_KEY=         # API ключ DeepSeek
```

### RAG API Legacy (rag-api)

```bash
cd services/rag-api

# запуск API (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Переменные окружения (те же, что и rag-api-new, но с `chroma_collection=portfolio`).

### Docker инфраструктура

```bash
cd infra

# запустить все сервисы (рекомендуется)
docker compose -f docker-compose.local.yaml up -d

# запустить отдельные сервисы
docker compose -f docker-compose.local.yaml up -d chroma tei litellm
docker compose -f docker-compose.local.yaml up -d content-api rag-api

# одноразовый импорт данных (экспорт из content-api → инжест в rag-api)
docker compose -f docker-compose.local.yaml run --rm rag-ingest

# проверить состояние
docker compose -f docker-compose.local.yaml ps

# посмотреть логи
docker compose -f docker-compose.local.yaml logs -f content-api
docker compose -f docker-compose.local.yaml logs -f rag-api

# пересобрать и перезапустить
docker compose -f docker-compose.local.yaml up -d --build rag-api
```

### Запуск тестов

RAG API New имеет тесты в `services/rag-api-new/tests/`:
```bash
cd services/rag-api-new
pytest tests/
```

---

## Критические правила

### Кодировка (СТРОГО)
- **Все файлы ДОЛЖНЫ быть UTF-8 без BOM**
- Никогда не используйте Windows-1251/ANSI и ломанный кириллический текст
- Python-строки: используйте обычные строки `text = "Правильный кириллический текст"`
- AI-инструменты должны проверять корректность кодировки перед коммитом

### Миграции БД
- **Всегда создавайте Alembic миграцию** при изменении моделей SQLAlchemy
- **Не правьте старые миграции** — создавайте новые
- Генерация: `alembic revision --autogenerate -m "message"`
- Путь миграций: `services/content-api-new/alembic/versions/`

### Соглашения об именовании
- Python: `snake_case` для функций/переменных, `PascalCase` для классов, `snake_case.py` для файлов
- TypeScript/React: `PascalCase.tsx` для компонентов, `useX.ts` для хуков, `camelCase.ts` для утилит

### Изменения кода
- Всегда соблюдайте принципы чистого кода: SOLID, DRY, KISS
- Меняйте только явные файлы из задачи
- Соблюдайте текущую структуру проекта
- Не допускайте циклических импортов в backend
- Разделяйте бизнес-логику и контроллеры
- Используйте SQLAlchemy ORM и Pydantic схемы

### Системный подход к решению проблем (КРИТИЧЕСКИ ВАЖНО)
- **Всегда ищите корневые причины** — не чините симптомы, находите и устраняйте первопричину
- **Никаких костылей и временных заплаток** — если что-то не работает, разберитесь почему и исправьте правильно
- **Чистые архитектурные решения** — предпочитайте хорошо спроектированный, поддерживаемый код быстрым хакам
- **Без лишних конструкций** — избегайте оверхеда, лишних абстракций и кода "на всякий случай"
- **Методичный дебаггинг** — трассируйте проблему системно, не гадайте и не добавляйте случайные фиксы
- **Чини один раз, чини правильно** — потратьте время на понимание проблемы, чтобы избежать повторных правок
- **Проверяйте предположения** — если поведение неожиданное, верифицируйте своё понимание системы
- При обнаружении багов:
  1. Надёжно воспроизведите проблему
  2. Проследите выполнение, чтобы найти реальную причину
  3. Поймите ПОЧЕМУ это происходит, а не только ГДЕ
  4. Спроектируйте правильный фикс, устраняющий корневую причину
  5. Убедитесь, что фикс не создаёт новых проблем

### Frontend
- Компоненты должны быть детерминированными
- Используйте классы Tailwind CSS в JSX
- Не применяйте inline-стили, кроме анимаций
- Не используйте эмодзи без явного запроса

---

## Поток данных

1. Управление контентом: админ/скрипты → PostgreSQL (через content-api-new)
2. RAG-индексация: content-api-new `/api/v1/rag/export` → rag-api-new `/api/v1/ingest/batch` → ChromaDB + BM25 + Knowledge Graph (или через docker-сервис `rag-ingest` для автоматизации)
3. Frontend SSR: Next.js → content-api-new `/api/v1/*` → PostgreSQL → JSON
4. Чат агента: пользователь → frontend-new AgentDock → rag-api-new `/api/v1/agent/chat/stream` → многослойный пайплайн
5. Запрос RAG (rag-api-new):
   - ScopeGuard → PlannerLLM → PlanExecutor
   - → HybridRetriever (dense + BM25) → Rerank → Evidence
   - → FactNormalizer → AnswerLLM → RenderEngine → Ответ
6. Thinking Status события: rag_tool.py `_emit_status()` → `asyncio.Queue` через config → chat.py unified queue → NDJSON `status` event → фронтенд ThinkingStatus компонент

### NDJSON Streaming Events (`/api/v1/agent/chat/stream`)

Стриминговый эндпоинт отправляет NDJSON-события следующих типов:

| Тип события | Поля | Описание |
|-------------|------|----------|
| `start` | `message_id`, `created_at` | Стрим открыт, сразу за ним идёт начальный status |
| `status` | `stage`, `text` | Индикатор этапа пайплайна (thinking, planning, searching, verifying, answering, identity) |
| `tool_start` | `tool` | Вызов инструмента агента начат |
| `tool_end` | — | Вызов инструмента завершён |
| `delta` | `content` | Инкрементальный чанк текста от LLM |
| `error` | `message` | Ошибка обработки |
| `end` | `message_id`, `usage`, `rate_limit` | Стрим завершён |

**Этапы status-событий:**

| Stage | Текст | Источник |
|-------|-------|----------|
| `thinking` | Анализирую вопрос... | chat.py (немедленно, после `start`) |
| `planning` | Составляю план поиска... | rag_tool.py |
| `searching` | Ищу в базе знаний... | rag_tool.py |
| `verifying` | Проверяю полноту данных... | rag_tool.py (условный, critic) |
| `answering` | Формирую ответ... | rag_tool.py |
| `identity` | Формирую ответ... | chat.py (identity fast-path) |

**Механизм доставки статусов:** `rag_tool.py` использует `_emit_status()`, которая помещает события в `asyncio.Queue` из `config["configurable"]["_status_queue"]`. `chat.py` запускает две конкурентные задачи — `_run_agent` (LangGraph события) и `_relay_status` (consumer очереди) — объединённые в unified queue для упорядоченной NDJSON эмиссии.

---

## Ключевые архитектурные особенности

### Многослойный RAG Pipeline (rag-api-new)

Новая RAG система использует продвинутую многослойную архитектуру:

1. **Scope Guard**: Детектирует off-topic вопросы (сказки, генерация кода, общие знания)
   - Возвращает вежливый отказ с 5 предложенными вопросами о портфолио
   - См. `app/agent/scope_guard/scope_guard.py`

2. **LLM Planner**: Генерирует структурированный план запроса с intents, entities, tool calls
   - Использует `with_structured_output()` для надежного парсинга JSON
   - Поддерживает retry с repair prompt при ошибке валидации
   - См. `app/agent/planner/planner_llm.py:PlannerLLM.plan()`

3. **Plan Executor**: Оркестрирует выполнение тулзов с fallback handling
   - Выполняет graph_query_tool или portfolio_search_tool на основе плана
   - См. `app/agent/executor/execute_plan.py:PlanExecutor.execute()`

4. **Fact Normalizer**: Фильтрует факты по intent и tech category
   - Удаляет дубликаты, факты с низкой confidence
   - См. `app/agent/normalizer/normalizer.py:FactNormalizer.normalize()`

5. **Answer LLM**: Генерирует ответ со строгим промптингом
   - Детерминированные (без LLM) ответы для: contacts, publications, project_details, technology_usage
   - LLM-генерация для остальных интентов со строгим промптингом (без галлюцинаций)
   - Механизм восстановления: fallback на детерминированную генерацию, если LLM выдал "не найдено", но evidence есть
   - См. `app/agent/answer/answer_llm.py:AnswerLLM.generate()`

6. **Render Engine**: Форматирует ответ в целевой стиль
   - BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH
   - См. `app/agent/render/renderer.py:RenderEngine.render()`

### Мультипровайдерная архитектура LLM (rag-api-new)

Система поддерживает несколько LLM-провайдеров с независимым выбором модели для каждой роли:

**Поддерживаемые провайдеры:**
- `gigachat` - GigaChat API (Сбер) через `langchain_gigachat` — силён в русском языке
- `deepseek` - DeepSeek API через `ChatOpenAI` — силён в reasoning (модель R1)
- `qwen` - Qwen через LiteLLM → vLLM (локальный) — экономичный для простых задач

**Роли LLM (5 независимых конфигураций):**

| Роль | Назначение | Умолч. в коде | Умолч. в compose | Температура |
|------|------------|---------------|-------------------|-------------|
| `identity` | Ответы на "кто ты?" | `gigachat:GigaChat-2` | `deepseek:deepseek-chat` | 0.3 |
| `planner` | Генерация QueryPlanV3 | `gigachat:GigaChat-2` | `gigachat:GigaChat-2` | 0.0 |
| `answer` | Генерация ответов пользователю | `gigachat:GigaChat-2` | `deepseek:deepseek-chat` | 0.2 |
| `critic` | Оценка достаточности фактов | `gigachat:GigaChat-2` | `deepseek:deepseek-reasoner` | 0.2 |
| `agent` | ReAct-оркестрация | `gigachat:GigaChat-2` | `gigachat:GigaChat-2` | 0.2 |

**Примечание:** В `settings.py` все роли по умолчанию `gigachat:GigaChat-2`. В `docker-compose.local.yaml` env-переменные переопределяют на конфигурацию выше.

**Формат LLM ID:** `provider:model` (например, `gigachat:GigaChat-2`, `deepseek:deepseek-reasoner`)

**⚠️ Ограничение DeepSeek Reasoner:**
Модель `deepseek-reasoner` (R1) **НЕ поддерживает** tool calling в LangChain/LangGraph из-за отсутствия поля `reasoning_content` в ответе.

| Роль | DeepSeek Reasoner | DeepSeek Chat | Причина |
|------|-------------------|---------------|---------|
| `IDENTITY_LLM` | ⚠️ Избыточно | ✅ | Простые ответы |
| `PLANNER_LLM` | ✅ | ✅ | Только structured output |
| `ANSWER_LLM` | ⚠️ Избыточно | ✅ | Генерация текста |
| `CRITIC_LLM` | ✅ | ✅ | Без tool calls |
| `AGENT_LLM` | ❌ **НЕЛЬЗЯ** | ✅ | Требует tool calling |

**Рекомендация:** Для `AGENT_LLM` используйте `gigachat:GigaChat-2` или `deepseek:deepseek-chat`, НЕ `deepseek:deepseek-reasoner`.

**Архитектура:**
```
┌─────────────────────────────────────────────────────────────────┐
│  gigachat:model ──► GigaChat() ─────────────► GigaChat API     │
│                     (langchain_gigachat)       (напрямую)       │
│                                                                 │
│  deepseek:model ──► ChatOpenAI() ───────────► DeepSeek API     │
│                     (base_url=api.deepseek)    (напрямую)       │
│                                                                 │
│  qwen:model ──────► ChatOpenAI() ──► LiteLLM ──► vLLM          │
│                     (base_url=litellm)         (локальный)      │
└─────────────────────────────────────────────────────────────────┘
```

**Ключевые файлы:**
- `app/llm/factory.py` - `LLMFactory` с кэшированием по (provider, model, temperature)
- `app/llm/providers.py` - `LLMProvider` enum, `ProviderConfig`
- `app/llm/exceptions.py` - `LLMConfigError`, `LLMProviderError`
- `app/llm/validation.py` - `validate_llm_config()` для валидации при старте
- `app/deps.py` - Функции для ролей: `identity_llm()`, `planner_llm()`, `answer_llm()`, `critic_llm()`, `agent_llm()`

**Конфигурация (переменные окружения):**
```bash
# Креды провайдеров
GIGA_AUTH_DATA=base64_credentials      # GigaChat
DEEPSEEK_API_KEY=sk-xxx                # DeepSeek
LITELLM_BASE_URL=http://localhost:8005/v1  # Qwen через LiteLLM

# Роли LLM (формат: "provider:model", умолч. в коде: gigachat:GigaChat-2)
IDENTITY_LLM=deepseek:deepseek-chat          # compose default
PLANNER_LLM=gigachat:GigaChat-2              # compose default
ANSWER_LLM=deepseek:deepseek-chat            # compose default
CRITIC_LLM=deepseek:deepseek-reasoner        # compose default
AGENT_LLM=gigachat:GigaChat-2                # compose default

# Температуры
IDENTITY_TEMPERATURE=0.3
PLANNER_TEMPERATURE=0.0
ANSWER_TEMPERATURE=0.2
CRITIC_TEMPERATURE=0.2
AGENT_TEMPERATURE=0.2
```

**TokenUsageCollector (интеграция с Rate Limiting):**

Система агрегирует usage токенов от ВСЕХ LLM-ролей для точного rate limiting:

```
Поток запроса:
Identity LLM ─────┐
Planner LLM ──────┤
Critic LLM ───────┼──► TokenUsageCollector ──► rate_limiter.record_usage()
Answer LLM ───────┤
Agent LLM ────────┘
```

- `app/rate_limit/usage_collector.py` - `TokenUsageCollector`, `RoleUsage`
- Каждый LLM-класс возвращает `(result, usage)` tuple
- `chat.py` агрегирует usage от agent + rag_tool
- Суммарные токены записываются в Redis для rate limiting

**Логирование usage:**
```
INFO: TokenUsage summary: message_id=abc123 total=3847 breakdown=[planner=1200, critic=650, answer=1500, agent=497]
```

### Knowledge Graph (rag-api-new)

Система строит граф знаний из данных портфолио:
- **Node Types**: PERSON, COMPANY, PROJECT (личный или experience-based), ACHIEVEMENT, TECHNOLOGY, CONTACT
- **Edge Types**: WORKS_AT, WORKED_AT, CREATED, ACHIEVED, USES, KNOWS, BELONGS_TO, HAS_CONTACT
- Проекты с `company_name` классифицируются как "коммерческий", без — "личный проект"
- Узлы проектов из опыта включают поле `kind` из CompanyExperience
- Используется для структурированных запросов (project_details, technologies, experience)
- См. `app/graph/builder.py:build_graph()`

### Гибридный поиск

Оба RAG сервиса используют гибридный поиск:
1. **Dense Search**: ChromaDB similarity search с embeddings
2. **BM25 Search**: Лексический keyword matching
3. **RRF Merge**: Reciprocal Rank Fusion для объединения результатов
4. **MMR Dedup**: Удаление похожих документов
5. **Expand by Project**: Добавление связанных project/experience документов
6. **Cross-encoder Reranking**: Оценка кандидатов с `BAAI/bge-reranker-base`

### Типы документов в RAG

RAG система создает несколько типов документов:
- `profile` - информация профиля разработчика
- `experience`, `experience_project` - опыт работы
- `project` - личные/featured проекты
- `technology` - элементы tech стека
- `publication` - статьи/блог-посты
- `contact` - контактная информация
- `stat` - ключевые метрики
- `focus_area`, `work_approach` - информация о карьере
- `item` - атомарные документы (achievements, bullets, stats, contacts)

### Персистентность BM25

BM25 индекс хранится на диске:
- Локация: `~/.bm25.{collection}.pkl`
- Загружается на старте через `bm25_try_load()`
- Сохраняется после индексации через `bm25_try_save()`
- Сбрасывается при очистке коллекции

### Анимации Hero

**Particles Background** (`frontend-new/components/hero/ParticlesBackground.tsx`):
- Рендер на canvas с оптимизациями
- Desktop: 60fps, 35-80 частиц с glow
- Mobile: 30fps, 25-50 частиц, без glow
- 8 форм частиц: pulseRing, dataNode, scanLine, hexagon, crosshair, diamond, circuit, orb
- Реакция на мышь (вихревой отталкивающий эффект)
- IntersectionObserver для паузы вне экрана
- Постепенный спаун на загрузке
- Зацикленное движение с оберткой по краям

**Hero Intro** (`frontend-new/components/hero/HeroIntro.tsx`):
- Последовательные анимации Framer Motion:
  1. Заголовок "AI-Portfolio" появляется снизу (0s)
  2. Линия проходит слева направо (задержка 0.4s)
  3. Теглайн появляется и запускается typing-эффект (0.8s, CSS typing с 1.1s)
  4. Карточка появляется (0.5s)
  5. Контент карточки (0.7s)
  6. Аватар (0.85s)
- Ширина линии подстраивается под текст теглайна
- Используется `next/image` для оптимизации
- `will-change` подсказки для GPU

**Custom Cursor** (`frontend-new/components/ui/CustomCursor.tsx`):
- Динамический хвост с затуханием
- Ripple-эффекты по клику
- Анимации, зависящие от скорости
- Эффект "breathing"
- Автоотключение на touch-устройствах
- Учитывает `prefers-reduced-motion`
- Использует requestAnimationFrame (60fps)

**CSS анимации** (`frontend-new/app/globals.css`):
- `hero-grid-pan` — движущаяся сетка
- `hero-line-sweep` — пробегающий свет
- `hero-typing` + `hero-caret` — печатающий эффект
- `glowDrift` — плавающие градиентные пятна
- `hero-bounce-slow` — прыгающая кнопка скролла
- `cursor-breathe` — дыхание курсора
- `animate-cursor-ripple` — ripple при клике
- `breathe` — пульсирующее свечение индикатора thinking status (box-shadow с accent-soft)
- `pulse-slow` — медленная пульсация (2s, 50-100% opacity)
- `@media (prefers-reduced-motion)` — поддержка предпочтений
- Мобильные оптимизации: меньше blur, медленнее анимации

### Оптимизации производительности (frontend)
- **React.memo** на карточках (ProjectCard, ExperienceCard, ContactCard, PublicationCard)
- **useMemo/useCallback** в HeroIntro и AgentDock
- **next/image** с корректными `sizes`
- **IntersectionObserver** в ParticlesBackground и StatsGrid
- **CountUp** в StatsGrid только при видимости
- Троттлинг ресайза и мыши
- Ограничение FPS на мобилках (30fps vs 60fps)
- CSS `will-change` для GPU
- Поддержка `prefers-reduced-motion`

### Модели базы данных (`services/content-api-new/app/models/`)

**Profile** (`profile.py`):
- Одна запись с персональной информацией
- Поля: full_name, title, subtitle, location, status, avatar_url, summary_md
- Новые поля: hero_headline, hero_description, current_position

**CompanyExperience** (`experience.py`):
- Опыт работы в компаниях
- Поля: role, company_name, company_slug, start_date, end_date, is_current
- `kind`: "commercial" | "personal"
- Markdown-поля: `company_summary_md`, `company_role_md`, `description_md`
- One-to-many с `ExperienceProject`

**ExperienceProject** (`experience_project.py`):
- Проекты внутри опыта
- Поля: name, slug, period, description_md, achievements_md, order_index
- `technologies` - массив технологий
- Many-to-one к CompanyExperience (CASCADE delete)

**Project** (`project.py`):
- Личные избранные проекты (не привязаны к опыту работы в компании)
- Поля: name, slug, featured, period, company_name, company_website
- Новые поля: domain ("cv" | "rag" | "backend" | "mlops" | "other"), repo_url, demo_url
- Markdown: `description_md`, `long_description_md`
- Many-to-many с Technology через `project_technology`

**Technology** (`technology.py`):
- Элементы стека (name, slug, category, order_index)
- Many-to-many с Project

**Publication** (`publication.py`):
- Статьи/посты (title, year, source, url, badge)
- Источники: "Habr" | "GitHub" | "Blog" | "Other"

**Contact** (`contact.py`):
- Контакты
- Типы: email, telegram, github, linkedin, hh, leetcode, other
- Поля: label, value, url

**Stat** (`stats.py`):
- Метрики для отображения (key, label, value, hint, group_name)

**TechFocus** (`tech_focus.py`):
- Технологические направления

**HeroTag** (`hero_tag.py`):
- Теги hero (name, url, icon, order_index)

**FocusArea** (`focus_area.py`):
- Фокусные области с буллетами (`FocusAreaBullet`)
- Поля: title, is_primary, order_index

**WorkApproach** (`work_approach.py`):
- Подходы к работе с буллетами (`WorkApproachBullet`)
- Поля: title, icon, order_index

**SectionMeta** (`section_meta.py`):
- Метаданные секций (section_key, title, subtitle)
- Используются для заголовков в UI

---

## Переменные окружения

Ключевые переменные (см. `infra/.env.dev`):

**База данных:**
- `POSTGRES_DB` - имя БД (например, `ai_portfolio_new`)
- `POSTGRES_USER` - пользователь БД
- `POSTGRES_PASSWORD` - пароль БД
- `POSTGRES_PORT` - порт PostgreSQL (по умолчанию 5433)
- `DATABASE_URL` - строка подключения (например, `postgresql+psycopg://user:pass@host:5433/db`)

**Frontend:**
- `FRONTEND_ORIGIN` - разрешенный CORS origin (например, `http://localhost:3001`)
- `FRONTEND_LOCAL_IP` - дополнительный CORS origin (например, `http://192.168.1.36:3001`)
- `NEXT_PUBLIC_CONTENT_API_BASE` - базовый URL Content API (frontend env)
- `NEXT_PUBLIC_AGENT_API_BASE` - базовый URL Agent API (frontend env)

**LLM-инфраструктура:**
- `LITELLM_BASE_URL` - URL LiteLLM (например, `http://litellm:4000/v1`)
- `LITELLM_MASTER_KEY` - ключ LiteLLM
- `LITELLM_API_KEY` - API ключ для аутентификации в LiteLLM
- `CHAT_MODEL` - alias чат-модели (legacy, например, `Qwen2.5` или `GigaChat`)
- `EMBEDDING_MODEL` - alias embedding-модели (например, `embedding-default`)
- `GIGA_AUTH_DATA` - Base64 креды GigaChat (если используется)
- `DEEPSEEK_API_KEY` - API ключ DeepSeek (если используется)
- `DEEPSEEK_BASE_URL` - URL DeepSeek API (по умолчанию: `https://api.deepseek.com/v1`)
- `HF_TOKEN` - токен HuggingFace для загрузки моделей

**Роли LLM (мультипровайдерная архитектура):**
- `IDENTITY_LLM` - LLM для identity-вопросов (формат: `provider:model`, умолч. в коде: `gigachat:GigaChat-2`, в compose: `deepseek:deepseek-chat`)
- `PLANNER_LLM` - LLM для планирования запросов (умолч. в коде: `gigachat:GigaChat-2`, в compose: `gigachat:GigaChat-2`)
- `ANSWER_LLM` - LLM для генерации ответов (умолч. в коде: `gigachat:GigaChat-2`, в compose: `deepseek:deepseek-chat`)
- `CRITIC_LLM` - LLM для оценки фактов (умолч. в коде: `gigachat:GigaChat-2`, в compose: `deepseek:deepseek-reasoner`)
- `AGENT_LLM` - LLM для ReAct-агента (умолч. в коде: `gigachat:GigaChat-2`, в compose: `gigachat:GigaChat-2`)

**Температуры LLM:**
- `IDENTITY_TEMPERATURE` - температура Identity LLM (по умолчанию: 0.3)
- `PLANNER_TEMPERATURE` - температура Planner LLM (по умолчанию: 0.0)
- `ANSWER_TEMPERATURE` - температура Answer LLM (по умолчанию: 0.2)
- `CRITIC_TEMPERATURE` - температура Critic LLM (по умолчанию: 0.2)
- `AGENT_TEMPERATURE` - температура Agent LLM (по умолчанию: 0.2)

**RAG API:**
- `reranker_model` - модель реранкера (по умолчанию `BAAI/bge-reranker-base`)
- `chroma_collection` - имя коллекции ChromaDB (по умолчанию `portfolio` для legacy, `portfolio_new` для нового)
- `tei_base_url` - URL TEI для прямого доступа к embeddings (по умолчанию `http://tei:80/v1`)
- `embedding_model` - модель embeddings (по умолчанию `intfloat/multilingual-e5-base`)
- `embedding_batch_size` - размер батча для embeddings (по умолчанию 4)
- `max_rerank_candidates` - макс. кандидатов для реранкинга (по умолчанию 80)
- `max_user_input_tokens` - макс. длина сообщения пользователя в токенах (по умолчанию 250)
- `planner_temperature` - температура LLM для планировщика (по умолчанию 0.0 для детерминизма)
- `answer_temperature` - температура LLM для генерации ответов (по умолчанию 0.2)

**Rate Limiting:**
- `rate_limit_enabled` - включить/выключить rate limiting (по умолчанию true)
- `rate_limit_ip_tokens` - лимит токенов на IP за окно (в коде: 15000 для локального тестирования, в compose: 50000)
- `rate_limit_window_seconds` - окно rate limit в секундах (в коде: 60, в compose: 3600 = 1 час)
- `rate_limit_warning_threshold` - порог предупреждения в долях (по умолчанию 0.8 = 80%)
- `rate_limit_log_ip_mode` - режим логирования IP (по умолчанию `masked`)

**Critic (ленивый критик):**
- `critic_enabled` - включить/выключить CriticLLM (по умолчанию true)
- `critic_confidence_threshold` - порог уверенности для пропуска критика (по умолчанию 0.7)
- `critic_min_facts_threshold` - мин. количество фактов для пропуска критика (по умолчанию 2)
- `critic_skip_intents` - интенты, для которых критик не нужен (по умолчанию: `["contacts", "current_job"]`)

**Redis Cache:**
- `REDIS_URL` - URL подключения Redis (например, `redis://localhost:6379/0`)
- `CACHE_ENABLED` - включить/выключить кэширование (по умолчанию true)
- `PLAN_CACHE_TTL` - TTL plan cache в секундах (по умолчанию 604800 = 7 дней)
- `EMBEDDING_CACHE_TTL` - TTL embedding cache в секундах (по умолчанию 604800 = 7 дней)

**Векторная БД:**
- `CHROMA_HOST` - хост ChromaDB
- `CHROMA_PORT` - порт ChromaDB (по умолчанию 8001 внешний / 8000 внутренний)

**Порты сервисов (docker-compose.local.yaml):**
- `frontend` - 3000 (Next.js)
- `postgres` - 5433 (PostgreSQL)
- `content-api` - 8003 (Content API)
- `chroma` - 8001 (ChromaDB)
- `tei` - 8006 (Text Embeddings Inference)
- `litellm` - 8005 (LiteLLM proxy)
- `redis` - 6379 (Redis)
- `rag-api` - 8004 (RAG API, собирается из rag-api-new/)

---

## Частые ошибки

1. **Неверные директории сервисов**:
   - ✅ Используйте `content-api-new`, `frontend-new`, `rag-api-new`
   - ⚠️ `rag-api` - legacy, используйте только для поддержки
   - ❌ `content-api`, `frontend` директории удалены

2. **Версионирование API**:
   - Эндпоинты content-api-new имеют префикс `/api/v1/`
   - Эндпоинты rag-api-new имеют префикс `/api/v1/`
   - Frontend должен использовать базовый URL с этим префиксом

3. **Циклические импорты**: храните общие зависимости в `deps.py`, избегайте перекрестных импортов роутеров

4. **Конфликты миграций**:
   - Всегда проверяйте `alembic current` перед созданием миграции
   - Миграции: `services/content-api-new/alembic/versions/`

5. **Проблемы с кодировкой**: проверяйте UTF-8, особенно для кириллицы

6. **Использование инструментов агента**: RAG-агент обязан вызывать тулзы для вопросов о портфолио

7. **CORS**:
   - `FRONTEND_ORIGIN` должен совпадать с URL фронта
   - Все API строго проверяют CORS

8. **Сетевое взаимодействие Docker**:
   - PostgreSQL доступен через `host.docker.internal` (внешняя БД)
   - Внутри Docker используйте имена сервисов (`chroma:8000`, `litellm:4000`)

9. **Алиасы моделей LiteLLM**:
   - Названия моделей должны совпадать с алиасами в `infra/litellm/config.yaml`
   - По умолчанию: `CHAT_MODEL=Qwen2.5` (или `GigaChat`), `EMBEDDING_MODEL=embedding-default`

10. **Markdown-поля**:
    - Многие поля используют markdown (`summary_md`, `description_md`, `achievements_md`, `long_description_md`)
    - Frontend рендерит через `react-markdown`

11. **Состояние BM25**:
    - Индекс BM25 хранится в `~/.bm25.{collection}.pkl`
    - Очищайте ChromaDB и BM25 при ресете коллекции `/api/v1/admin/collection`

12. **Разные коллекции**:
    - `rag-api` использует `chroma_collection=portfolio`
    - `rag-api-new` использует `chroma_collection=portfolio_new`
    - Данные нужно загружать отдельно в каждую

13. **Инвалидация кэша**:
    - Plan cache автоинвалидируется при изменении content hash (после ingest)
    - Embedding cache НЕ автоинвалидируется (зависит только от текста запроса)
    - После изменения `prompts.py` или логики планировщика: очистить plan cache через `/api/v1/admin/cache/plans`
    - После смены embedding модели: очистить embedding cache через `/api/v1/admin/cache/embeddings`

14. **Потребление токенов Rate Limit**:
    - Каждый запрос агенту потребляет ~6000-9000 токенов из-за многослойного пайплайна
    - Стадии пайплайна: системный промпт агента (~2000), Planner LLM (~1500), RAG Tool (~1500), Answer LLM (~2000), ответ (~1500)
    - При лимите 50000 токенов/час пользователь может сделать ~5-8 запросов в час
    - Для тестирования используйте меньший лимит (например, 4500), но учтите, что даже один запрос может его превысить
    - Rate limit по IP, не по сессии — все пользователи с одного IP делят лимит

15. **Техспецификации в `discource/`**:
    - Всегда проверяйте `discource/docs/` на наличие ТЗ перед реализацией новых фич
    - Проверяйте `discource/specs/` для детальных спецификаций реализации
    - Создавайте новую спецификацию перед началом сложных реализаций
    - Примечание: папка называется `discource` (опечатка сохранена для консистентности)

---

## Структура проекта (справочно)

```
AI-Portfolio/
├── frontend-new/                    # ✅ АКТИВНЫЙ Next.js фронтенд (киберпанк)
│   ├── app/
│   │   ├── page.tsx                # Главная страница
│   │   ├── layout.tsx              # Корневой layout с AgentDock и CustomCursor
│   │   ├── globals.css             # Глобальные стили и анимации
│   │   ├── projects/[slug]/        # Страница проекта
│   │   └── experience/[company_slug]/ # Страница опыта
│   ├── components/
│   │   ├── agent/                  # Чат с RAG-агентом (AgentDock, AgentChatWindow, ThinkingStatus и др.)
│   │   ├── hero/                   # Hero (HeroIntro, HeroScrollHint, ParticlesBackground)
│   │   ├── about/                  # About (AboutMeSection, StatsGrid)
│   │   ├── experience/             # Опыт (ExperienceSection, ExperienceCard)
│   │   ├── tech/                   # TechFocusSection
│   │   ├── projects/               # ProjectsSection, ProjectCard
│   │   ├── publications/           # PublicationsSection, PublicationCard
│   │   ├── contacts/               # ContactsSection, ContactCard
│   │   ├── how/                    # HowIWorkSection
│   │   ├── ui/                     # Общие UI (CustomCursor, SocialBadge, TechTag)
│   │   └── layout/                 # Shell, Footer, Section
│   ├── lib/
│   │   ├── api.ts                  # API-клиент (SSR)
│   │   └── types.ts                # Типы TypeScript
│   ├── package.json
│   └── .env.local                  # Переменные окружения
│
├── services/
│   ├── content-api-new/            # ✅ АКТИВНЫЙ Content API (версионные эндпоинты)
│   │   ├── app/
│   │   │   ├── main.py             # Точка входа FastAPI
│   │   │   ├── settings.py         # Настройки приложения
│   │   │   ├── db.py               # Подключение БД
│   │   │   ├── models/             # Модели SQLAlchemy (см. выше)
│   │   │   ├── routers/            # Эндпоинты (/api/v1/*)
│   │   │   ├── schemas/            # Pydantic-схемы (включая rag_export.py)
│   │   │   ├── core/config.py      # Базовые настройки
│   │   │   └── seed/               # Наполнение БД (seed_ai_portfolio_new.py)
│   │   ├── alembic/                # Миграции
│   │   │   └── versions/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── rag-api-new/                # ✅ АКТИВНЫЙ RAG & Agent API (многослойный пайплайн)
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI с роутерами
│   │   │   ├── settings.py         # Pydantic-настройки (температуры и др.)
│   │   │   ├── deps.py             # Общие зависимости (LLMs, vectorstore)
│   │   │   ├── prefetch.py         # Прогрев кэша для популярных вопросов
│   │   │   ├── agent/              # Агентная система
│   │   │   │   ├── graph.py        # LangGraph агент
│   │   │   │   ├── rag_tool.py     # RAG тулза
│   │   │   │   ├── identity/       # Identity-вопросы (classifier.py, prompts.py)
│   │   │   │   ├── planner/        # LLM планировщик (planner_llm.py, schemas_v3.py, schemas.py, prompts.py, shortcuts.py)
│   │   │   │   ├── scope_guard/    # Off-topic детекция (scope_guard.py, schemas.py)
│   │   │   │   ├── executor/       # Plan executor (execute_plan.py)
│   │   │   │   ├── normalizer/     # Fact normalizer (normalizer.py, fact_bundle.py)
│   │   │   │   ├── answer/         # Генерация ответов (answer_llm.py, prompts.py)
│   │   │   │   ├── render/         # Рендеринг ответов (renderer.py)
│   │   │   │   ├── critic/         # Оценка ответов (critic_llm.py, prompts.py, schemas.py)
│   │   │   │   ├── grounding/      # Evidence grounding (grounding_verifier.py)
│   │   │   │   └── tools/          # Тулзы агента (portfolio_search_tool.py, graph_query_tool.py)
│   │   │   ├── rag/                # RAG пайплайн
│   │   │   │   ├── search.py       # Оркестрация поиска
│   │   │   │   ├── retrieval.py    # HybridRetriever
│   │   │   │   ├── rank.py         # Реранкинг
│   │   │   │   ├── evidence.py     # Отбор evidence
│   │   │   │   ├── entities.py     # Entity registry
│   │   │   │   ├── nlp.py          # NLP утилиты
│   │   │   │   ├── formatter.py    # Format rendering
│   │   │   │   ├── search_types.py # Типы поиска (SearchResult, Intent, EntityType)
│   │   │   │   ├── types.py        # Базовые типы (Doc, ScoredDoc, SourceInfo)
│   │   │   │   └── utils.py        # Утилиты RAG пайплайна
│   │   │   ├── graph/              # Knowledge graph
│   │   │   │   ├── schema.py       # NodeType, EdgeType
│   │   │   │   ├── builder.py      # Построение графа
│   │   │   │   ├── query.py        # Запросы к графу
│   │   │   │   └── store.py        # Хранилище графа
│   │   │   ├── indexing/           # Индексация документов
│   │   │   │   ├── normalizer.py   # Нормализация документов
│   │   │   │   ├── chunker.py      # Чанкинг текста
│   │   │   │   ├── bm25.py         # BM25 индекс
│   │   │   │   └── persistence.py  # Персистентность BM25
│   │   │   ├── cache/              # Redis-кэширование
│   │   │   │   ├── cache_service.py # CacheService с graceful degradation
│   │   │   │   ├── plan_cache.py   # Кэш планов (shortcut → cache → LLM)
│   │   │   │   └── embedding_cache.py # Кэш embeddings запросов
│   │   │   ├── rate_limit/         # Rate limiting
│   │   │   │   ├── limiter.py      # Класс RateLimiter
│   │   │   │   ├── schemas.py      # Схемы rate limit
│   │   │   │   └── usage_collector.py # TokenUsageCollector для агрегации usage от всех ролей
│   │   │   ├── llm/                # Мультипровайдерная LLM фабрика
│   │   │   │   ├── factory.py      # LLMFactory, parse_llm_id(), get_provider_info()
│   │   │   │   ├── providers.py    # LLMProvider enum, ProviderConfig
│   │   │   │   ├── exceptions.py   # LLMConfigError, LLMProviderError
│   │   │   │   ├── validation.py   # validate_llm_config() для валидации при старте
│   │   │   │   └── gigachat_adapter.py # Legacy адаптер
│   │   │   ├── routers/            # API роутеры
│   │   │   │   ├── chat.py         # /api/v1/agent/chat/stream
│   │   │   │   ├── ingest.py       # /api/v1/ingest
│   │   │   │   ├── ingest_batch.py # /api/v1/ingest/batch
│   │   │   │   └── admin.py        # /api/v1/admin/*, /api/v1/rate-limit/status
│   │   │   ├── schemas/            # Pydantic схемы
│   │   │   │   ├── chat.py, ingest.py, export.py, admin.py, ask.py
│   │   │   └── utils/              # Утилиты
│   │   │       ├── logging_utils.py
│   │   │       └── metadata.py
│   │   ├── tests/                  # Тесты
│   │   │   ├── test_smoke.py       # Smoke-тесты
│   │   │   ├── test_tz_v3_acceptance.py  # Приёмочные тесты QueryPlanV3
│   │   │   ├── test_answer_llm_usage.py  # Отслеживание токенов Answer LLM
│   │   │   ├── test_llm_factory.py       # Тесты LLM фабрики
│   │   │   ├── test_usage_collector.py   # Тесты TokenUsageCollector
│   │   │   └── llm/test_providers.py     # Тесты провайдеров
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── Dockerfile.prod         # Docker-образ для продакшена
│   │
│   └── rag-api/                    # ⚠️ LEGACY RAG API (упрощенная архитектура)
│       └── app/
│           ├── main.py
│           ├── settings.py
│           ├── deps.py
│           ├── api_ask.py, api_ingest.py, api_ingest_batch.py, api_admin.py
│           ├── rag/                # Legacy RAG пайплайн
│           ├── agent/              # Legacy агент (graph.py, tools.py)
│           ├── llm/
│           ├── utils/
│           └── schemas/
│
├── scripts/
│   ├── ingest.py                   # Legacy-ингест RAG
│   └── settings.py
│
├── infra/
│   ├── docker-compose.local.yaml   # ✅ Основной compose (локальная разработка)
│   ├── docker-compose-prod.yaml    # Продакшен compose
│   ├── .env.dev                    # Переменные окружения (dev)
│   ├── .env.local                  # Переменные окружения (local)
│   ├── .env.prod                   # Переменные окружения (prod)
│   ├── .env.example                # Шаблон переменных окружения
│   ├── DOCKER-LOCAL.md             # Руководство по локальному Docker
│   ├── DOCKER-PROD.md              # Руководство по продакшен Docker
│   ├── caddy/Caddyfile             # Reverse proxy (продакшен)
│   ├── init/postgres-init.sql      # Инициализация БД (uuid-ossp)
│   ├── scripts/ingest.py           # Скрипт RAG-индексации
│   ├── litellm/
│   │   └── config.yaml             # Алиасы моделей LiteLLM
│   └── models/
│       └── intfloat/multilingual-e5-base/  # Модель TEI
│
├── discource/                       # 📋 Техническая документация и спецификации
│   ├── docs/                        # Технические задания (ТЗ)
│   │   ├── TZ_MULTI_LLM_PROVIDERS.md    # Мультипровайдерная LLM архитектура
│   │   ├── TZ_RATE_LIMIT.md             # Спецификация rate limiting
│   │   ├── TZ_RAG_OPTIMIZATION.md       # Оптимизация RAG
│   │   └── TZ_AI-Portfolio_RAG_Agent_Hardening.md  # Hardening агента
│   ├── specs/                       # Спецификации реализации
│   │   └── agent-identity-vs-profile-detection.md  # Identity vs Profile детекция
│   └── planning-with-files-archive/ # Архив сессий планирования
│
├── CLAUDE.md                       # Эта инструкция (EN)
├── CLAUDE_RU.md                    # Эта инструкция (RU)
├── AGENTS.md                       # Документация по агентам
└── tech-task-rag-api-new-develop.md  # Техническое задание на RAG API new
```

**Ключевые пункты:**
- ✅ Активные сервисы: `frontend-new`, `content-api-new`, `rag-api-new`
- ⚠️ Legacy: `rag-api` (доступен, упрощенная архитектура)
- 🐳 Docker: используйте `infra/docker-compose.local.yaml`
- 📝 В compose сервис `rag-api` собирается из `rag-api-new/` — отдельного `rag-api-new` сервиса нет

---

## При внесении изменений

**Всегда:**
1. Проверяйте директории сервисов: используйте `content-api-new`, `frontend-new`, `rag-api-new`
2. Убедитесь, что кодировка UTF-8 (особенно для кириллицы/markdown)
3. Создайте Alembic миграцию при изменении моделей в `content-api-new`
4. Тестируйте локально перед коммитом
5. Следуйте существующим паттернам и соглашениям
6. Для всех API используйте префикс `/api/v1/`
7. Используйте markdown-поля (`*_md`) для контента, рендерящегося на фронте
8. **Проверьте `discource/`** на наличие спецификаций перед реализацией новых фич

**Никогда:**
1. Не используйте удаленные директории (`content-api`, `frontend`)
2. Не меняйте кодировку с UTF-8
3. Не трогайте старые миграции Alembic
4. Не создавайте циклические импорты
5. Не смешивайте бизнес-логику с контроллерами
6. Не нарушайте структуру проекта без явного разрешения
7. Не убирайте префикс `/api/v1/` у эндпоинтов
8. Не хардкодьте URL API (используйте переменные окружения)
9. **Не добавляйте костыли и хаки** — всегда устраняйте корневые причины, а не симптомы
10. **Не добавляйте "временные" фиксы** — нет ничего более постоянного, чем временное решение

**Перед коммитом:**
1. ✅ Убедитесь, что меняли правильный сервис (`*-new`)
2. ✅ Проверьте, что нет битой кириллицы (`????` или `\u041f`)
3. ✅ Выполните миграцию Alembic, если меняли модели
4. ✅ Протестируйте API с префиксом `/api/v1/`
5. ✅ Проверьте CORS, если фронт не может достучаться до бэкенда
