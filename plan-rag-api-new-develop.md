# План реализации rag-api-new

## Обзор

Создание нового сервиса `rag-api-new` — полной замены `rag-api`, интегрированного с `content-api-new`.

**Ключевые решения:**
- RAG Export: Расширить endpoint в content-api-new (новый `/api/v1/rag/export`)
- LLM Providers: GigaChat + LiteLLM (как в текущем rag-api)
- Порт: 8014 (параллельно со старым на 8004)
- Коллекция ChromaDB: `portfolio_new`

---

## Фаза 1: Подготовка инфраструктуры

### 1.1 Создать структуру директорий
```
services/rag-api-new/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── deps.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ask.py
│   │   ├── chat.py
│   │   ├── ingest.py
│   │   ├── ingest_batch.py
│   │   └── admin.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   ├── retrieval.py
│   │   ├── rank.py
│   │   ├── evidence.py
│   │   ├── prompting.py
│   │   ├── types.py
│   │   ├── nlp.py
│   │   └── utils.py
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── bm25.py
│   │   ├── persistence.py
│   │   ├── chunker.py
│   │   └── normalizer.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   └── tools.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── gigachat_adapter.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ask.py
│   │   ├── chat.py
│   │   ├── ingest.py
│   │   ├── export.py
│   │   └── admin.py
│   └── utils/
│       ├── __init__.py
│       └── metadata.py
├── pyproject.toml
├── Dockerfile
└── uv.lock
```

### 1.2 Файлы конфигурации
- [ ] `pyproject.toml` — скопировать из rag-api, изменить name на `rag-api-new`
- [ ] `Dockerfile` — скопировать as-is
- [ ] `settings.py` — изменить `chroma_collection` default на `portfolio_new`

---

## Фаза 2: Перенос модулей as-is

Эти файлы переносятся **без изменений** (только обновить импорты):

| Источник | Назначение |
|----------|------------|
| `rag-api/app/rag/types.py` | `rag-api-new/app/rag/types.py` |
| `rag-api/app/rag/nlp.py` | `rag-api-new/app/rag/nlp.py` |
| `rag-api/app/rag/utils.py` | `rag-api-new/app/rag/utils.py` |
| `rag-api/app/rag/rank.py` | `rag-api-new/app/rag/rank.py` |
| `rag-api/app/rag/evidence.py` | `rag-api-new/app/rag/evidence.py` |
| `rag-api/app/rag/prompting.py` | `rag-api-new/app/rag/prompting.py` |
| `rag-api/app/rag/retrieval.py` | `rag-api-new/app/rag/retrieval.py` |
| `rag-api/app/rag/core.py` | `rag-api-new/app/rag/core.py` |
| `rag-api/app/utils/bm25_index.py` | `rag-api-new/app/indexing/bm25.py` |
| `rag-api/app/rag/index.py` | `rag-api-new/app/indexing/persistence.py` |
| `rag-api/app/llm/gigachat_adapter.py` | `rag-api-new/app/llm/gigachat_adapter.py` |
| `rag-api/app/agent/graph.py` | `rag-api-new/app/agent/graph.py` |
| `rag-api/app/agent/tools.py` | `rag-api-new/app/agent/tools.py` |

---

## Фаза 3: Новые схемы (schemas/)

### 3.1 schemas/export.py — НОВЫЙ ExportPayload

Адаптировать под модели content-api-new:

```python
# Новые типы документов:
- ProfileExport (full_name, title, subtitle, summary_md, hero_headline, hero_description, current_position)
- CompanyExperienceExport (role, company_name, company_slug, start_date, end_date, is_current, kind, company_summary_md, company_role_md, projects: list[ExperienceProjectExport])
- ExperienceProjectExport (name, slug, period, description_md, achievements_md) — НОВЫЙ
- ProjectExport (name, slug, featured, domain, repo_url, demo_url, description_md, long_description_md, technologies: list[str])
- TechnologyExport (name, slug, category)
- PublicationExport (title, year, source, url, description_md)
- FocusAreaExport (title, is_primary, bullets: list[FocusAreaBulletExport]) — НОВЫЙ
- WorkApproachExport (title, icon, bullets: list[WorkApproachBulletExport]) — НОВЫЙ
- TechFocusExport (label, description, tags: list[TechFocusTagExport]) — НОВЫЙ
- StatExport (key, label, value, hint, group_name) — НОВЫЙ
- ContactExport (kind, label, value, url, is_primary) — НОВЫЙ

class ExportPayload:
    profile: ProfileExport | None
    experiences: list[CompanyExperienceExport]
    projects: list[ProjectExport]
    technologies: list[TechnologyExport]
    publications: list[PublicationExport]
    focus_areas: list[FocusAreaExport]
    work_approaches: list[WorkApproachExport]
    tech_focus: list[TechFocusExport]
    stats: list[StatExport]
    contacts: list[ContactExport]
```

### 3.2 schemas/ask.py, chat.py, ingest.py, admin.py
- Скопировать структуры из текущего rag-api
- Разделить по файлам для удобства

---

## Фаза 4: Normalizer (indexing/normalizer.py)

### 4.1 indexing/chunker.py
- Выделить `_split_text()` из `normalize_export_rich.py`

### 4.2 indexing/normalizer.py — НОВАЯ ВЕРСИЯ

Добавить обработчики для новых типов документов:

| Тип документа | Источник | Текст |
|---------------|----------|-------|
| `profile` | ProfileExport | full_name, title, subtitle, summary_md, current_position |
| `experience` | CompanyExperienceExport | role, company_name, period, company_summary_md, company_role_md |
| `experience_project` | ExperienceProjectExport | name, period, description_md, achievements_md + связь с компанией |
| `project` | ProjectExport | name, description_md, long_description_md, technologies, domain, repo_url, demo_url |
| `technology` | TechnologyExport | name, category + проекты где используется |
| `publication` | PublicationExport | title, year, source, url, description_md |
| `focus_area` | FocusAreaExport | title, is_primary, bullets |
| `work_approach` | WorkApproachExport | title, bullets |
| `tech_focus` | TechFocusExport | label, description, tags |
| `stat` | StatExport | key, label, value, hint |
| `contact` | ContactExport | kind, label, value, url |
| `catalog` | Агрегированные | Сводки технологий |

**Ключевое отличие от текущего normalizer:**
- Текущий использует `companies`, `achievements`, `documents` — старая структура
- Новый использует `experiences` с вложенными `projects` — структура content-api-new
- Добавить focus_areas, work_approaches, tech_focus, stats, contacts

---

## Фаза 5: Routers (routers/)

Все endpoints с префиксом `/api/v1`:

| Файл | Endpoints |
|------|-----------|
| `routers/ask.py` | POST `/api/v1/ask` |
| `routers/chat.py` | POST `/api/v1/agent/chat/stream` |
| `routers/ingest.py` | POST `/api/v1/ingest` |
| `routers/ingest_batch.py` | POST `/api/v1/ingest/batch` |
| `routers/admin.py` | DELETE `/api/v1/admin/collection`, GET `/api/v1/admin/stats` |

Адаптировать из текущих `api_*.py` файлов.

---

## Фаза 6: Main и deps

### 6.1 deps.py
- Скопировать структуру из текущего rag-api
- Изменить default collection на `portfolio_new`

### 6.2 main.py
- CORS middleware
- Health endpoints: `/healthz`, `/meta`
- Include routers с prefix `/api/v1`

---

## Фаза 7: Изменения в content-api-new

### 7.1 Новые схемы: `app/schemas/rag_export.py`
Создать ExportPayload и все *Export схемы для RAG.

### 7.2 Новый endpoint: `app/routers/rag.py`

**ВАЖНО:** В текущем `rag.py` импортируется `Experience`, но правильная модель — `CompanyExperience` из `models/experience.py`. Нужно исправить импорт.

```python
from app.models.experience import CompanyExperience  # НЕ Experience

@router.get("/export", response_model=ExportPayload)
def export_for_rag(db: Session = Depends(get_db)):
    # Загрузить все данные с joinedload для связей:
    # - Profile
    # - CompanyExperience + projects (joinedload)
    # - Project + technologies (joinedload)
    # - Technology
    # - Publication
    # - FocusArea + bullets (joinedload)
    # - WorkApproach + bullets (joinedload)
    # - TechFocus + tags (joinedload)
    # - Stat
    # - Contact
```

**Критические файлы для изменения:**
- `services/content-api-new/app/routers/rag.py`
- `services/content-api-new/app/schemas/rag.py` (или новый `rag_export.py`)

---

## Фаза 8: Docker конфигурация

### 8.1 infra/compose.apps.yaml — добавить сервис

```yaml
rag-api-new:
  build:
    context: ../services/rag-api-new
    dockerfile: Dockerfile
  restart: unless-stopped
  environment:
    litellm_base_url: http://litellm:4000/v1
    litellm_api_key: ${LITELLM_MASTER_KEY}
    chat_model: ${CHAT_MODEL}
    embedding_model: ${EMBEDDING_MODEL}
    giga_auth_data: ${GIGA_AUTH_DATA}
    CHROMA_HOST: chroma
    CHROMA_PORT: 8000
    chroma_collection: portfolio_new
    FRONTEND_ORIGIN: ${FRONTEND_ORIGIN}
    FRONTEND_LOCAL_IP: ${FRONTEND_LOCAL_IP}
    LOG_LEVEL: INFO
  depends_on:
    - chroma
    - litellm
  ports: ["${RAG_NEW_PORT:-8014}:8000"]
```

### 8.2 infra/.env.dev — добавить
```
RAG_NEW_PORT=8014
```

---

## Фаза 9: Тестирование

### Manual flow:
1. Запустить content-api-new
2. Получить `GET /api/v1/rag/export`
3. Запустить rag-api-new
4. Вызвать `POST /api/v1/ingest/batch` с ExportPayload
5. Проверить `GET /api/v1/admin/stats`
6. Проверить `POST /api/v1/ask`
7. Проверить `POST /api/v1/agent/chat/stream`

---

## Критические файлы

### Переносить as-is (обновить импорты):
- `services/rag-api/app/rag/*.py` (7 файлов)
- `services/rag-api/app/agent/*.py` (2 файла)
- `services/rag-api/app/llm/gigachat_adapter.py`
- `services/rag-api/app/utils/bm25_index.py`

### Создать новые:
- `services/rag-api-new/app/schemas/export.py` — новый ExportPayload
- `services/rag-api-new/app/indexing/normalizer.py` — новая версия normalizer
- `services/rag-api-new/app/routers/*.py` — 5 роутеров

### Изменить в content-api-new:
- `services/content-api-new/app/routers/rag.py` — добавить `/export`
- `services/content-api-new/app/schemas/rag.py` — добавить ExportPayload схемы

### Docker:
- `infra/compose.apps.yaml` — добавить rag-api-new сервис
- `infra/.env.dev` — добавить RAG_NEW_PORT

---

## Порядок выполнения (checklist)

### Блок 1: Инфраструктура rag-api-new
- [ ] Создать директорию services/rag-api-new/
- [ ] Скопировать pyproject.toml, Dockerfile
- [ ] Создать settings.py

### Блок 2: RAG pipeline (перенос as-is)
- [ ] Перенести rag/types.py, nlp.py, utils.py
- [ ] Перенести rag/rank.py, evidence.py, prompting.py
- [ ] Перенести rag/retrieval.py, core.py
- [ ] Создать indexing/bm25.py, persistence.py, chunker.py

### Блок 3: Схемы
- [ ] Создать schemas/export.py (новый ExportPayload)
- [ ] Создать schemas/ask.py, chat.py, ingest.py, admin.py

### Блок 4: Normalizer
- [ ] Создать indexing/normalizer.py с поддержкой всех типов

### Блок 5: Agent и LLM
- [ ] Перенести agent/graph.py, tools.py
- [ ] Перенести llm/gigachat_adapter.py

### Блок 6: Routers
- [ ] Создать routers/ask.py
- [ ] Создать routers/chat.py
- [ ] Создать routers/ingest.py, ingest_batch.py
- [ ] Создать routers/admin.py

### Блок 7: Main и deps
- [ ] Создать deps.py
- [ ] Создать main.py

### Блок 8: content-api-new изменения
- [ ] Добавить схемы в schemas/rag.py
- [ ] Добавить GET /api/v1/rag/export в routers/rag.py

### Блок 9: Docker
- [ ] Обновить compose.apps.yaml
- [ ] Обновить .env.dev

### Блок 10: Тестирование
- [ ] Manual тестирование полного flow
