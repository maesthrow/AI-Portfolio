# CLAUDE_RU.md

Этот файл содержит инструкции для Claude Code (claude.ai/code) при работе с кодом в этом репозитории.

---

## ⚠️ CRITICAL: Активные директории сервисов

**ВСЕГДА используйте эти директории:**
- ✅ `frontend-new/` - Активный Next.js фронтенд (киберпанк-тема)
- ✅ `services/content-api-new/` - Активный Content API с версионными эндпоинтами
- ✅ `services/rag-api-new/` - **НОВЫЙ** Активный RAG & Agent API (многослойный пайплайн, LLM планировщик)
- ✅ `infra/compose.apps.yaml` - Актуальная конфигурация Docker Compose

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
  - `project.py` - Project (slug, technologies, featured, domain, repo_url, demo_url, long_description_md)
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
  - `rag.py` - GET `/api/v1/rag/documents` (экспорт данных для RAG)
  - `hero_tags.py` - GET `/api/v1/hero-tags`
  - `focus_areas.py` - GET `/api/v1/focus-areas`
  - `work_approaches.py` - GET `/api/v1/work-approaches`
  - `section_meta.py` - GET `/api/v1/section-meta`, GET `/api/v1/section-meta/{section_key}`
- `app/schemas/` - Pydantic-схемы
- `app/settings.py` - настройки приложения
- `alembic/` - миграции базы данных

### 2. **RAG API New** (`services/rag-api-new/`) ⭐ РЕКОМЕНДУЕТСЯ
**Многослойный RAG пайплайн с LLM-планировщиком и детерминированной генерацией ответов**

- Продвинутый семантический поиск с LLM-планированием запросов
- Knowledge Graph для структурированных запросов
- Scope Guard для детекции off-topic вопросов
- Детерминированная нормализация фактов и генерация ответов
- Точка входа: `app/main.py`
- Порт: 8014
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

**API роутеры** (`app/routers/`):
- `chat.py` - POST `/api/v1/agent/chat/stream` - Стриминговый чат с NDJSON
- `ingest.py` - POST `/api/v1/ingest` - Загрузка одного документа
- `ingest_batch.py` - POST `/api/v1/ingest/batch` - Пакетный импорт ExportPayload
- `admin.py` - Админские эндпоинты:
  - DELETE `/api/v1/admin/collection` - Очистка коллекции ChromaDB
  - GET `/api/v1/admin/stats` - Статистика коллекции и графа
  - DELETE `/api/v1/admin/cache/plans` - Очистка plan cache
  - DELETE `/api/v1/admin/cache/embeddings` - Очистка embedding cache
  - DELETE `/api/v1/admin/cache` - Очистка всех кэшей

**Агентная система** (`app/agent/`):
- `graph.py` - LangGraph агент с ReAct паттерном и памятью
- `rag_tool.py` - RAG тулза для агента

**Планировщик** (`app/agent/planner/`):
- `planner_llm.py` - LLM-планировщик запросов со structured output
- `schemas_v3.py` - QueryPlanV3, IntentV3, TechCategory, ToolCall, RenderStyleV3, AnswerStyleV3
- `prompts.py` - Системные промпты для планировщика (intents, tools, entity extraction)

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
- `prompts.py` - Системные промпты и инструкции по стилю

**Render** (`app/agent/render/`):
- `renderer.py` - RenderEngine (BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH)

**Critic** (`app/agent/critic/`):
- `critic_llm.py` - CriticLLM для оценки ответов
- `prompts.py`, `schemas.py` - Промпты и схемы критика

**Grounding** (`app/agent/grounding/`):
- `grounding_verifier.py` - Проверка, что ответ основан на evidence

**Tools** (`app/agent/tools/`):
- `portfolio_search_tool.py` - Гибридный поиск с полным RAG пайплайном
- `graph_query_tool.py` - Структурированные запросы к графу (project_details, technologies, experience)

**RAG Pipeline** (`app/rag/`):
- `search.py` - Оркестрация `portfolio_search()`
- `retrieval.py` - `HybridRetriever` (dense + BM25 + RRF merge + MMR dedup)
- `rank.py` - Cross-encoder реранкинг
- `evidence.py` - Отбор evidence и упаковка контекста
- `entities.py` - EntityRegistry для matching сущностей
- `nlp.py` - NLP утилиты (ключевые слова, поддержка RU)
- `formatter.py` - FormatRenderer для пост-обработки
- `search_types.py` - SearchResult, Intent, EntityType
- `types.py` - Doc, ScoredDoc, SourceInfo

**Knowledge Graph** (`app/graph/`):
- `schema.py` - NodeType (PERSON, COMPANY, PROJECT, ACHIEVEMENT, TECHNOLOGY, CONTACT), EdgeType
- `builder.py` - Построение графа из ExportPayload
- `query.py` - Выполнение запросов к графу
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

**LLM адаптеры** (`app/llm/`):
- `gigachat_adapter.py` - GigaChat адаптер для LangChain

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
  - `AgentDock.tsx` - глобальный плавающий чат
  - `AgentChatWindow.tsx` - UI окна чата
  - `AgentInput.tsx` - инпут сообщений
  - `AgentMessageList.tsx` - вывод сообщений со стримингом
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
  - `GithubBadgeIcon.tsx` - SVG-иконка GitHub для бейджей
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
  - `callAgentStream(body, opts)` - стриминг чата
- `lib/types.ts` - типы TypeScript:
  - `Profile`, `ExperienceItem`, `ExperienceProject`, `ExperienceDetail`
  - `StatItem`, `TechFocusItem`, `Project`, `ProjectDetail`
  - `Publication`, `Contact`, `AgentMessage`
  - `HeroTag`, `FocusArea`, `FocusAreaBullet`
  - `WorkApproach`, `WorkApproachBullet`, `SectionMeta`

### 5. **Инфраструктура** (`infra/`)
- Docker Compose оркестрация (compose.apps.yaml — основной файл)
- Альтернативные compose-файлы: `compose.db.yaml`
- Сервисы:
  - PostgreSQL (внешний, доступ через host.docker.internal)
  - ChromaDB (векторная БД, порт 8001 внешний / 8000 внутренний)
  - vLLM (Qwen2.5-7B-Instruct-AWQ через OpenAI-совместимый API, порт 8002)
  - TEI (Text Embeddings Inference для multilingual-e5-base, порт 8006)
  - LiteLLM (прокси LLM/embeddings, порт 8005 внешний / 4000 внутренний)
  - content-api (порт 8003) — собирается из content-api-new/
  - rag-api (порт 8004) — legacy RAG сервис
  - rag-api-new (порт 8014) — новый многослойный RAG сервис

**Примечание:** Compose-файлы:
- `compose.apps.yaml` - основной со всеми сервисами
- `compose.db.yaml` - конфигурация БД

Используйте `compose.apps.yaml` как основной.

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
NEXT_PUBLIC_AGENT_API_BASE=http://localhost:8014  # Используйте rag-api-new
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
# 1. Экспорт из content-api: GET http://localhost:8003/api/v1/rag/documents
# 2. Импорт в rag-api-new: POST http://localhost:8014/api/v1/ingest/batch
```

Переменные окружения:
```bash
litellm_base_url=http://localhost:8005/v1
litellm_api_key=dev-secret-123
chat_model=Qwen2.5  # модель LLM (или GigaChat)
embedding_model=embedding-default
reranker_model=BAAI/bge-reranker-base
CHROMA_HOST=localhost
CHROMA_PORT=8001
chroma_collection=portfolio_new  # отличается от legacy
FRONTEND_ORIGIN=http://localhost:3000
frontend_local_ip=http://localhost:3000
LOG_LEVEL=INFO
planner_temperature=0.0   # детерминированное планирование
answer_temperature=0.2    # сбалансированная генерация
giga_auth_data=  # Base64 креды GigaChat (опционально)
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
docker compose -f compose.apps.yaml up -d

# запустить отдельные сервисы
docker compose -f compose.apps.yaml up -d chroma tei litellm
docker compose -f compose.apps.yaml up -d content-api rag-api rag-api-new

# проверить состояние
docker compose -f compose.apps.yaml ps

# посмотреть логи
docker compose -f compose.apps.yaml logs -f content-api
docker compose -f compose.apps.yaml logs -f rag-api-new

# пересобрать и перезапустить
docker compose -f compose.apps.yaml up -d --build rag-api-new
```

### Запуск тестов

RAG API New имеет тесты в `services/rag-api-new/tests/`:
```bash
cd services/rag-api-new
pytest tests/
```

---

## Критические правила (из CONTRIBUTING.md)

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

### Frontend
- Компоненты должны быть детерминированными
- Используйте классы Tailwind CSS в JSX
- Не применяйте inline-стили, кроме анимаций
- Не используйте эмодзи без явного запроса

---

## Поток данных

1. Управление контентом: админ/скрипты → PostgreSQL (через content-api-new)
2. RAG-индексация: content-api-new `/api/v1/rag/documents` → rag-api-new `/api/v1/ingest/batch` → ChromaDB + BM25 + Knowledge Graph
3. Frontend SSR: Next.js → content-api-new `/api/v1/*` → PostgreSQL → JSON
4. Чат агента: пользователь → frontend-new AgentDock → rag-api-new `/api/v1/agent/chat/stream` → многослойный пайплайн
5. Запрос RAG (rag-api-new):
   - ScopeGuard → PlannerLLM → PlanExecutor
   - → HybridRetriever (dense + BM25) → Rerank → Evidence
   - → FactNormalizer → AnswerLLM → RenderEngine → Ответ

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
   - Предотвращает "вероятно", "возможно" галлюцинации
   - Использует только предоставленные факты
   - См. `app/agent/answer/answer_llm.py:AnswerLLM.generate()`

6. **Render Engine**: Форматирует ответ в целевой стиль
   - BULLETS, GROUPED_BULLETS, SHORT, TABLE, PARAGRAPH
   - См. `app/agent/render/renderer.py:RenderEngine.render()`

### Knowledge Graph (rag-api-new)

Система строит граф знаний из данных портфолио:
- **Node Types**: PERSON, COMPANY, PROJECT, ACHIEVEMENT, TECHNOLOGY, CONTACT
- **Edge Types**: WORKS_AT, WORKED_AT, CREATED, ACHIEVED, USES, KNOWS, BELONGS_TO, HAS_CONTACT
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
- `project` - отдельные проекты (featured)
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
- Отдельные избранные проекты
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
- `CHAT_MODEL` - alias чат-модели (например, `Qwen2.5` или `GigaChat`, алиасы в `infra/litellm/config.yaml`)
- `EMBEDDING_MODEL` - alias embedding-модели (например, `embedding-default`)
- `GIGA_AUTH_DATA` - Base64 креды GigaChat (если используется)
- `HF_TOKEN` - токен HuggingFace для загрузки моделей

**RAG API:**
- `reranker_model` - модель реранкера (по умолчанию `BAAI/bge-reranker-base`)
- `chroma_collection` - имя коллекции ChromaDB (по умолчанию `portfolio` для legacy, `portfolio_new` для нового)
- `planner_temperature` - температура LLM для планировщика (по умолчанию 0.0 для детерминизма)
- `answer_temperature` - температура LLM для генерации ответов (по умолчанию 0.2)

**Redis Cache:**
- `REDIS_URL` - URL подключения Redis (например, `redis://localhost:6379/0`)
- `CACHE_ENABLED` - включить/выключить кэширование (по умолчанию true)
- `PLAN_CACHE_TTL` - TTL plan cache в секундах (по умолчанию 3600)
- `EMBEDDING_CACHE_TTL` - TTL embedding cache в секундах (по умолчанию 86400)

**Векторная БД:**
- `CHROMA_HOST` - хост ChromaDB
- `CHROMA_PORT` - порт ChromaDB (по умолчанию 8001 внешний / 8000 внутренний)

**Порты сервисов:**
- `CHROMA_PORT` - 8001 (ChromaDB)
- `VLLM_PORT` - 8002 (vLLM)
- `CONTENT_PORT` - 8003 (content-api-new)
- `RAG_PORT` - 8004 (rag-api legacy)
- `RAG_NEW_PORT` - 8014 (rag-api-new)
- `LITELLM_PORT` - 8005 (LiteLLM proxy)
- `TEI_PORT` - 8006 (Text Embeddings Inference)

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

5. **Проблемы с кодировкой**: проверяйте UTF-8, особенно для кириллицы (обязательно из CONTRIBUTING.md)

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
│   │   ├── agent/                  # Чат с RAG-агентом (AgentDock, AgentChatWindow и др.)
│   │   ├── hero/                   # Hero (HeroIntro, HeroScrollHint, ParticlesBackground)
│   │   ├── about/                  # About (AboutMeSection, StatsGrid)
│   │   ├── experience/             # Опыт (ExperienceSection, ExperienceCard)
│   │   ├── tech/                   # TechFocusSection
│   │   ├── projects/               # ProjectsSection, ProjectCard, GithubBadgeIcon
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
│   │   │   ├── schemas/            # Pydantic-схемы
│   │   │   └── core/config.py      # Базовые настройки
│   │   ├── seed/                   # Наполнение БД
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
│   │   │   ├── agent/              # Агентная система
│   │   │   │   ├── graph.py        # LangGraph агент
│   │   │   │   ├── rag_tool.py     # RAG тулза
│   │   │   │   ├── planner/        # LLM планировщик (planner_llm.py, schemas_v3.py, prompts.py)
│   │   │   │   ├── scope_guard/    # Off-topic детекция (scope_guard.py, schemas.py)
│   │   │   │   ├── executor/       # Plan executor (execute_plan.py)
│   │   │   │   ├── normalizer/     # Fact normalizer (normalizer.py, fact_bundle.py)
│   │   │   │   ├── answer/         # Генерация ответов (answer_llm.py, prompts.py)
│   │   │   │   ├── render/         # Рендеринг ответов (renderer.py)
│   │   │   │   ├── critic/         # Оценка ответов (critic_llm.py)
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
│   │   │   │   ├── search_types.py # Типы поиска
│   │   │   │   └── types.py        # Базовые типы
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
│   │   │   ├── llm/                # LLM адаптеры
│   │   │   │   └── gigachat_adapter.py
│   │   │   ├── routers/            # API роутеры
│   │   │   │   ├── chat.py         # /api/v1/agent/chat/stream
│   │   │   │   ├── ingest.py       # /api/v1/ingest
│   │   │   │   ├── ingest_batch.py # /api/v1/ingest/batch
│   │   │   │   └── admin.py        # /api/v1/admin/*
│   │   │   ├── schemas/            # Pydantic схемы
│   │   │   │   ├── chat.py, ingest.py, export.py, admin.py, ask.py
│   │   │   └── utils/              # Утилиты
│   │   │       ├── logging_utils.py
│   │   │       └── metadata.py
│   │   ├── tests/                  # Тесты
│   │   ├── pyproject.toml
│   │   └── Dockerfile
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
│   ├── compose.apps.yaml           # ✅ Основной docker compose
│   ├── compose.db.yaml             # Compose для БД
│   ├── .env.dev                    # Пример переменных окружения
│   ├── litellm/
│   │   └── config.yaml             # Алиасы моделей LiteLLM
│   └── models/
│       └── intfloat/multilingual-e5-base/  # Модель TEI
│
├── CONTRIBUTING.md                 # ⚠️ Обязательные правила для AI-инструментов
├── CLAUDE.md                       # Эта инструкция (EN)
└── CLAUDE_RU.md                    # Эта инструкция (RU)
```

**Ключевые пункты:**
- ✅ Активные сервисы: `frontend-new`, `content-api-new`, `rag-api-new`
- ⚠️ Legacy: `rag-api` (доступен, упрощенная архитектура)
- 🐳 Docker: используйте `infra/compose.apps.yaml`
- 📑 Правила: всегда читайте `CONTRIBUTING.md` перед изменениями

---

## При внесении изменений

**Всегда:**
1. Проверяйте директории сервисов: используйте `content-api-new`, `frontend-new`, `rag-api-new`
2. Прочитайте `CONTRIBUTING.md` (обязательные правила UTF-8 и прочее)
3. Убедитесь, что кодировка UTF-8 (особенно для кириллицы/markdown)
4. Создайте Alembic миграцию при изменении моделей в `content-api-new`
5. Тестируйте локально перед коммитом
6. Следуйте существующим паттернам и соглашениям
7. Для всех API используйте префикс `/api/v1/`
8. Используйте markdown-поля (`*_md`) для контента, рендерящегося на фронте

**Никогда:**
1. Не используйте удаленные директории (`content-api`, `frontend`)
2. Не меняйте кодировку с UTF-8
3. Не трогайте старые миграции Alembic
4. Не создавайте циклические импорты
5. Не смешивайте бизнес-логику с контроллерами
6. Не нарушайте структуру проекта без явного разрешения
7. Не убирайте префикс `/api/v1/` у эндпоинтов
8. Не хардкодьте URL API (используйте переменные окружения)

**Перед коммитом:**
1. ✅ Убедитесь, что меняли правильный сервис (`*-new`)
2. ✅ Проверьте, что нет битой кириллицы (`????` или `\u041f`)
3. ✅ Выполните миграцию Alembic, если меняли модели
4. ✅ Протестируйте API с префиксом `/api/v1/`
5. ✅ Проверьте CORS, если фронт не может достучаться до бэкенда
