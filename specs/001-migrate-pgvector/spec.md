# Feature Specification: Migrate Vector Store from ChromaDB to pgvector

**Feature Branch**: `001-migrate-pgvector`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "Выполнить миграцию с ChromaDB на pgvector для упрощения инфраструктуры, унификации хранения и использования возможностей SQL-фильтрации"

## Clarifications

### Session 2026-02-23

- Q: Docker-образ PostgreSQL — специализированный pgvector или стандартный postgres? → A: `pgvector/pgvector:pg16` — специализированный образ с предустановленным pgvector
- Q: Обработка метаданных — убрать flattening `_filter_complex_metadata()` или оставить? → A: Убрать — хранить списки/словари нативно в JSONB
- Q: Стратегия подключения RAG API к PostgreSQL — общий DATABASE_URL или отдельный? → A: Общий `DATABASE_URL` — та же БД `ai_portfolio_new`, что и Content API

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI-агент отвечает на вопросы после миграции (Priority: P1)

Посетитель портфолио открывает чат с AI-агентом и задаёт вопросы о проектах,
технологиях, опыте работы. Агент находит релевантные документы через
векторный поиск (теперь через pgvector вместо ChromaDB), комбинирует
с BM25-результатами, ранжирует и формирует ответ. Качество ответов
и скорость остаются на прежнем уровне или улучшаются.

**Why this priority**: Это core-функциональность проекта. Если после миграции
агент перестанет корректно отвечать — проект сломан. Всё остальное вторично.

**Independent Test**: Задать агенту 10 типовых вопросов (из `POPULAR_QUESTIONS`)
и сравнить качество ответов с результатами до миграции. Все вопросы должны
получить содержательные, фактологически корректные ответы.

**Acceptance Scenarios**:

1. **Given** векторы проиндексированы в pgvector, **When** пользователь спрашивает "Какие проекты использовали FastAPI?", **Then** агент находит релевантные документы и перечисляет проекты с FastAPI
2. **Given** векторы проиндексированы в pgvector, **When** пользователь спрашивает "Где сейчас работает разработчик?", **Then** агент возвращает актуальную информацию о текущей позиции
3. **Given** векторы проиндексированы в pgvector, **When** пользователь задаёт вопрос с фильтрацией по типу документа, **Then** метаданные-фильтры корректно ограничивают поиск
4. **Given** гибридный поиск (dense + BM25) активен, **When** пользователь задаёт вопрос, **Then** результаты объединяются через RRF так же, как при ChromaDB

---

### User Story 2 - Batch-ингест данных из Content API (Priority: P2)

Администратор (или CI-пайплайн) запускает сервис `rag-ingest`, который
экспортирует данные из Content API и загружает их в RAG API. Документы
нормализуются, чанкуются, эмбеддинги вычисляются через TEI и сохраняются
в pgvector-таблицу внутри существующей PostgreSQL-базы. BM25-индекс
обновляется синхронно. Knowledge Graph строится из тех же данных.
Метаданные хранятся нативно в JSONB без flattening — списки и словари
сохраняются как есть.

**Why this priority**: Без корректного ингеста векторный поиск невозможен.
Это prerequisite для Story 1, но тестируется независимо — можно проверить
запись и чтение данных без запуска полного RAG-пайплайна.

**Independent Test**: Запустить `rag-ingest`, затем проверить через
`/api/v1/admin/stats`, что количество документов, разбивка по типам
и контрольная хеш-сумма совпадают с ожидаемыми значениями.

**Acceptance Scenarios**:

1. **Given** Content API содержит данные портфолио, **When** запускается `rag-ingest`, **Then** все документы сохраняются в pgvector с корректными эмбеддингами и метаданными
2. **Given** в pgvector уже есть данные, **When** запускается повторный ингест с теми же данными, **Then** документы обновляются (upsert), дубликатов не появляется
3. **Given** ингест завершён, **When** вызывается `/api/v1/admin/stats`, **Then** отображается корректное количество документов и разбивка по типам
4. **Given** контент изменился в Content API, **When** запускается ингест, **Then** кеши планов и эмбеддингов инвалидируются автоматически
5. **Given** документ с метаданными-списками (technologies, project_ids), **When** ингестируется в pgvector, **Then** списки сохраняются как нативные JSONB-массивы без flattening

---

### User Story 3 - Упрощённая инфраструктура без ChromaDB (Priority: P3)

DevOps/разработчик поднимает локальное окружение через
`docker compose -f docker-compose.local.yaml up -d`. В составе сервисов
больше нет ChromaDB — векторы хранятся в том же PostgreSQL, что и контент.
PostgreSQL использует образ `pgvector/pgvector:pg16` с предустановленным
расширением. RAG API подключается к той же БД через общий `DATABASE_URL`.
Бэкап всего состояния выполняется одним `pg_dump`.

**Why this priority**: Основная мотивация миграции — упрощение инфраструктуры.
Но это вторично по отношению к сохранению работоспособности агента.

**Independent Test**: Поднять окружение с нуля через Docker Compose, убедиться
что сервис `chroma` отсутствует, все остальные сервисы стартуют корректно,
ингест и поиск работают.

**Acceptance Scenarios**:

1. **Given** обновлённый `docker-compose.local.yaml`, **When** разработчик запускает `docker compose up -d`, **Then** сервис `chroma` отсутствует, PostgreSQL использует образ `pgvector/pgvector:pg16`, расширение `vector` активно
2. **Given** PostgreSQL с расширением pgvector, **When** выполняется `pg_dump`, **Then** дамп содержит и контентные таблицы, и таблицу векторных эмбеддингов
3. **Given** production compose, **When** развёрнут на сервере, **Then** ChromaDB-сервис отсутствует, все RAG-операции работают через PostgreSQL
4. **Given** файлы `.env.dev`, `.env.local`, `.env.prod`, `.env.example`, **When** разработчик проверяет переменные, **Then** переменные `CHROMA_*` удалены, `DATABASE_URL` доступен для RAG API

---

### User Story 4 - Администрирование коллекции (Priority: P4)

Администратор использует API-эндпоинты для управления коллекцией:
очистка, просмотр статистики, управление кешами. Все операции, ранее
работавшие через ChromaDB HTTP API, теперь работают через прямые
SQL-запросы к PostgreSQL.

**Why this priority**: Вспомогательная функциональность, но необходимая
для отладки и операционного управления.

**Independent Test**: Вызвать каждый admin-эндпоинт и проверить, что ответы
соответствуют ожидаемой схеме и данные корректны.

**Acceptance Scenarios**:

1. **Given** коллекция содержит документы, **When** вызывается `GET /api/v1/admin/stats`, **Then** возвращается количество документов и разбивка по типам
2. **Given** коллекция содержит документы, **When** вызывается `DELETE /api/v1/admin/collection`, **Then** все векторы и документы удаляются, BM25-индекс сбрасывается
3. **Given** коллекция очищена, **When** вызывается `GET /api/v1/admin/stats`, **Then** возвращается 0 документов

---

### User Story 5 - Использование SQL-возможностей pgvector (Priority: P5)

Система использует преимущества pgvector, недоступные в ChromaDB:
получение документов по ID через прямой SQL-запрос (вместо хака с
`vs._collection.get()`), использование стандартных SQL WHERE-фильтров,
нативное хранение JSONB-метаданных без flattening,
потенциальная возможность JOIN с таблицами Content API в будущем.

**Why this priority**: Это "бонусные" улучшения, которые открывает pgvector.
Не блокируют миграцию, но повышают качество решения.

**Independent Test**: Выполнить `fetch_by_ids()` и проверить, что документы
возвращаются по ID напрямую из PostgreSQL без обращения к внутренним
атрибутам LangChain-обёртки.

**Acceptance Scenarios**:

1. **Given** документы проиндексированы, **When** запрашивается `fetch_by_ids([id1, id2])`, **Then** документы возвращаются через SQL-запрос к pgvector-таблице (без `vs._collection`)
2. **Given** гибридный поиск, **When** BM25 находит ID, отсутствующие в dense-результатах, **Then** недостающие документы получаются через SQL SELECT по ID

---

### User Story 6 - Обновление документации и конфигурации (Priority: P6)

Разработчик читает документацию проекта (CLAUDE.md, CLAUDE_RU.md,
DOCKER-LOCAL.md, DOCKER-PROD.md) и находит актуальную информацию о pgvector
вместо устаревших ссылок на ChromaDB. Все файлы конфигурации (.env.*),
Docker Compose файлы и документация согласованы между собой.

**Why this priority**: Документация — последний шаг, но критически важна
для поддерживаемости. Устаревшие ссылки на ChromaDB будут вводить в заблуждение.

**Independent Test**: Grep по всему репозиторию на "chroma" / "ChromaDB" —
не должно быть активных ссылок (кроме git-истории и возможных комментариев
о миграции).

**Acceptance Scenarios**:

1. **Given** миграция завершена, **When** разработчик читает `CLAUDE.md`, **Then** все упоминания ChromaDB заменены на pgvector, архитектурные диаграммы обновлены
2. **Given** миграция завершена, **When** разработчик читает `CLAUDE_RU.md`, **Then** документация синхронизирована с `CLAUDE.md`
3. **Given** миграция завершена, **When** разработчик читает `DOCKER-LOCAL.md`, **Then** сервис `chroma` удалён из таблицы сервисов, команды curl обновлены
4. **Given** миграция завершена, **When** разработчик читает `DOCKER-PROD.md`, **Then** сервис `chroma` удалён, health-check примеры обновлены
5. **Given** файлы `.env.example`, **When** разработчик настраивает окружение, **Then** секция ChromaDB удалена, `DATABASE_URL` документирован для RAG API

---

### Edge Cases

- Что происходит при ингесте, если PostgreSQL недоступен? Ожидание: ингест
  завершается с ошибкой, данные не теряются (транзакционность)
- Что происходит, если расширение `vector` не установлено в PostgreSQL?
  Ожидание: сервис не стартует, понятное сообщение об ошибке
- Что происходит при одновременном ингесте и поиске? Ожидание: MVCC
  PostgreSQL обеспечивает изоляцию, поиск видит консистентные данные
- Что происходит при ингесте документа с метаданными, содержащими
  вложенные объекты? Ожидание: метаданные сохраняются нативно в JSONB
  (flattening удалён, JSONB поддерживает вложенные структуры)
- Что происходит с существующей базой content-api при добавлении
  pgvector-таблиц? Ожидание: таблицы `langchain_pg_collection` и
  `langchain_pg_embedding` создаются автоматически, не конфликтуют
  с таблицами Content API
- Что происходит, если Docker volume `pg_data` содержит старую БД
  без расширения `vector`? Ожидание: `postgres-init.sql` выполняет
  `CREATE EXTENSION IF NOT EXISTS "vector"` при первом запуске;
  для существующих БД — выполнить вручную или пересоздать volume

## Requirements *(mandatory)*

### Functional Requirements

**Ядро RAG-пайплайна:**

- **FR-001**: Система MUST хранить векторные эмбеддинги документов в PostgreSQL с расширением pgvector вместо ChromaDB
- **FR-002**: Система MUST поддерживать все существующие операции поиска: `similarity_search_by_vector` с метаданными-фильтрами (`type $in`, `project_id $in`)
- **FR-003**: Система MUST поддерживать upsert-семантику при ингесте: удаление по ID + добавление новых документов
- **FR-004**: Система MUST сохранять метаданные документов нативно в JSONB без flattening (списки и словари как есть)
- **FR-005**: Система MUST поддерживать batch-ингест из ExportPayload с вычислением эмбеддингов через TEI
- **FR-006**: Система MUST предоставлять admin-эндпоинты для очистки коллекции и получения статистики
- **FR-007**: Система MUST получать документы по списку ID через прямой SQL-запрос (замена `vs._collection.get()`)
- **FR-008**: Система MUST расширять результаты по project_id (`expand_by_project`) с compound-фильтрами
- **FR-009**: Система MUST синхронно обновлять BM25-индекс при каждом ингесте (поведение не меняется)
- **FR-010**: Система MUST автоматически инвалидировать кеши при изменении контент-хеша (поведение не меняется)
- **FR-011**: Система MUST сохранять формат NDJSON-стримов и pipeline status events без изменений
- **FR-012**: Система MUST использовать `langchain_postgres.PGVector` как замену `langchain_chroma.Chroma`
- **FR-013**: Система MUST удалить функцию `_filter_complex_metadata()` из ингеста (ChromaDB-специфичный хак)

**Инфраструктура и подключение:**

- **FR-014**: Система MUST использовать ту же PostgreSQL-базу `ai_portfolio_new`, что и Content API (общий `DATABASE_URL`)
- **FR-015**: Docker-образ PostgreSQL MUST быть заменён на `pgvector/pgvector:pg16` (local и production)
- **FR-016**: Скрипт `postgres-init.sql` MUST содержать `CREATE EXTENSION IF NOT EXISTS "vector"`
- **FR-017**: Система MUST удалить ChromaDB-сервис из Docker Compose (local и production)
- **FR-018**: Система MUST удалить Docker volume `chroma_data` из Docker Compose (local и production)
- **FR-019**: Система MUST удалить зависимость `depends_on: chroma` у сервиса rag-api (local и production)

**Конфигурация (.env файлы):**

- **FR-020**: Файлы `.env.dev`, `.env.local`, `.env.prod`, `.env.example` MUST удалить все переменные `CHROMA_*` (`CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_COLLECTION`)
- **FR-021**: Файлы `.env.*` MUST добавить `DATABASE_URL` в окружение rag-api (или передавать через compose)
- **FR-022**: Файл `.env.example` MUST документировать новую конфигурацию pgvector-подключения

**Зависимости Python:**

- **FR-023**: `pyproject.toml` MUST заменить `langchain-chroma` и `chromadb` на `langchain-postgres` и `psycopg[binary]`
- **FR-024**: Код MUST удалить все импорты `chromadb` и `langchain_chroma`

**Настройки приложения:**

- **FR-025**: `settings.py` MUST удалить поля `chroma_host`, `chroma_port`, `chroma_collection` и свойство `chroma_client_kwargs`
- **FR-026**: `settings.py` MUST добавить поле `database_url` для подключения к PostgreSQL
- **FR-027**: `settings.py` MUST сохранить поле `collection_name` (имя коллекции pgvector, default: `portfolio_new`)

**Документация:**

- **FR-028**: `CLAUDE.md` MUST быть обновлён: все упоминания ChromaDB заменены на pgvector, архитектура, env-переменные, файловая структура, Docker-сервисы, Common Pitfalls
- **FR-029**: `CLAUDE_RU.md` MUST быть синхронизирован с обновлённым `CLAUDE.md`
- **FR-030**: `infra/DOCKER-LOCAL.md` MUST быть обновлён: удалён `chroma` из таблицы сервисов, обновлены примеры команд
- **FR-031**: `infra/DOCKER-PROD.md` MUST быть обновлён: удалён `chroma` из таблицы сервисов, удалены примеры `docker inspect ai-folio-chroma-1`

### Key Entities

- **Embedding Record**: Векторный эмбеддинг документа. Содержит: ID документа, текст, вектор (размерность 768, определяется TEI-моделью multilingual-e5-base), метаданные (JSONB, нативные вложенные структуры), ID коллекции
- **Collection**: Логическая группировка эмбеддингов (аналог коллекции ChromaDB). Имя: `portfolio_new`. Хранится как запись в таблице `langchain_pg_collection`
- **Document Metadata**: Структурированные метаданные в JSONB. Ключевые поля: `type`, `ref_id`, `doc_id`, `content_hash`, `name`, `slug`, `company_name`, `technologies` (массив), `project_id`, `project_ids` (массив)

### Assumptions

- Docker-образ `pgvector/pgvector:pg16` содержит предустановленное расширение pgvector — достаточно `CREATE EXTENSION vector`
- RAG API и Content API используют общий `DATABASE_URL` к одной БД `ai_portfolio_new` — таблицы `langchain_pg_*` не конфликтуют с таблицами Content API
- Масштаб данных — ~200 документов/векторов — тривиальная нагрузка, HNSW-индекс не требуется (seq scan достаточен)
- Размерность эмбеддингов — 768 (multilingual-e5-base через TEI)
- `langchain_postgres.PGVector` поддерживает метаданные-фильтры в dict-формате `{"key": {"$in": [...]}}` — совместимо с текущим кодом retrieval
- JSONB-метаданные поддерживают вложенные списки и словари нативно — функция `_filter_complex_metadata()` больше не нужна
- BM25-индекс остаётся in-memory с pickle-персистенцией (не мигрируется в PostgreSQL)
- Миграция выполняется как clean cut: ChromaDB удаляется полностью, без fallback-режима

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: AI-агент отвечает на все вопросы из `POPULAR_QUESTIONS` с качеством не ниже текущего уровня (экспертная оценка: все ответы содержательны и фактологически корректны)
- **SC-002**: Время ответа агента на типовой вопрос не увеличивается более чем на 10% по сравнению с текущим
- **SC-003**: Batch-ингест всех документов портфолио завершается успешно с корректным количеством записей
- **SC-004**: Количество Docker-сервисов в production уменьшается на 1 (удалён ChromaDB)
- **SC-005**: Полный бэкап данных (контент + векторы) выполняется одной командой `pg_dump`
- **SC-006**: Все существующие тесты в `services/rag-api-new/tests/` проходят после миграции
- **SC-007**: Admin-эндпоинты (stats, clear collection) возвращают корректные данные
- **SC-008**: `fetch_by_ids()` работает через прямой SQL без обращения к внутренним атрибутам LangChain
- **SC-009**: Grep по репозиторию на `chroma` не выдаёт активных ссылок в коде, конфигурации и документации (кроме git-истории)
- **SC-010**: Файлы `.env.dev`, `.env.local`, `.env.prod`, `.env.example` не содержат переменных `CHROMA_*`
- **SC-011**: Документация (CLAUDE.md, CLAUDE_RU.md, DOCKER-LOCAL.md, DOCKER-PROD.md) не содержит устаревших ссылок на ChromaDB
