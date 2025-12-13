# Техническое задание: RAG-API-NEW

## Миграция RAG-сервиса на новую архитектуру Content API

**Версия документа:** 1.0  
**Дата:** Декабрь 2025  
**Статус:** В разработке

---

## 1. Введение

### 1.1 Цель проекта

Создание нового модуля `rag-api-new` — полной замены текущего `rag-api`, адаптированного под новую структуру `content-api-new`. Новый сервис должен унаследовать лучшие архитектурные решения текущего `rag-api`, при этом полностью интегрироваться с обновлённой структурой данных.

### 1.2 Контекст

| Компонент | Текущее состояние | Целевое состояние |
|-----------|-------------------|-------------------|
| Content API | `content-api-new` (активный) | Без изменений |
| RAG API | `rag-api` (использует старые схемы) | `rag-api-new` (интеграция с content-api-new) |
| Frontend | `frontend-new` | Переключение на rag-api-new |

### 1.3 Ключевые требования

1. **Полная совместимость** с `content-api-new` и его схемами данных
2. **Сохранение функциональности** текущего `rag-api`
3. **Улучшение архитектуры** где это обосновано
4. **Обратная совместимость API** для frontend
5. **Качественная документация** и типизация

---

## 2. Анализ текущего RAG-API

### 2.1 Архитектура (сохранить)

```
rag-api/
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── settings.py          # Pydantic Settings
│   ├── deps.py              # DI: LLM, vectorstore, reranker, agent
│   │
│   ├── api_ask.py           # POST /ask, POST /api/v1/agent/chat/stream
│   ├── api_ingest.py        # POST /ingest
│   ├── api_ingest_batch.py  # POST /ingest/batch
│   ├── api_admin.py         # DELETE /admin/collection, GET /admin/stats
│   │
│   ├── rag/                  # RAG Pipeline
│   │   ├── core.py          # portfolio_rag_answer()
│   │   ├── retrieval.py     # HybridRetriever (dense + BM25)
│   │   ├── rank.py          # Cross-encoder reranking
│   │   ├── evidence.py      # Evidence selection
│   │   ├── prompting.py     # Prompt templates
│   │   ├── types.py         # Doc, ScoredDoc, SourceInfo
│   │   ├── nlp.py           # NLP utilities (Russian)
│   │   └── index.py         # BM25 persistence
│   │
│   ├── agent/               # LangGraph Agent
│   │   ├── graph.py         # ReAct agent
│   │   └── tools.py         # portfolio_rag_tool, list_projects_tool
│   │
│   ├── llm/                 # LLM Adapters
│   │   └── gigachat_adapter.py
│   │
│   ├── utils/               # Utilities
│   │   ├── bm25_index.py    # BM25Okapi wrapper
│   │   ├── normalize.py     # Basic normalization
│   │   └── normalize_export_rich.py  # Document chunking
│   │
│   └── schemas/
│       └── ingest_schema.py # ExportPayload, ProjectExport, etc.
```

### 2.2 Сильные стороны (перенести)

| Компонент | Описание | Статус |
|-----------|----------|--------|
| **HybridRetriever** | Dense + BM25 поиск | ✅ Перенести |
| **Cross-encoder reranking** | Переранжирование результатов | ✅ Перенести |
| **Evidence selection** | Умный отбор контекста | ✅ Перенести |
| **LangGraph Agent** | ReAct паттерн с memory | ✅ Перенести |
| **GigaChat Adapter** | LangChain-совместимый адаптер | ✅ Перенести |
| **BM25 persistence** | Сохранение индекса в pickle | ✅ Перенести |
| **Streaming responses** | SSE для чата | ✅ Перенести |
| **Document chunking** | Разбиение на чанки 900 символов | ✅ Перенести |

### 2.3 Текущие схемы rag-api (требуют адаптации)

```python
# Текущие схемы в rag-api/app/schemas/ingest_schema.py

class ProjectExport:
    id: int
    name: str
    kind: str           # "personal" | "commercial"
    weight: int
    repo_url: str | None
    demo_url: str | None
    technologies: list[str]
    description_md: str

class CompanyExport:
    id: int
    name: str
    slug: str

class AchievementExport:
    id: int
    project_id: int
    text: str
    order_idx: int

class TechnologyExport:
    id: int
    name: str
    category: str

class DocumentExport:
    id: int
    title: str
    url: str
    text_md: str

class ExportPayload:
    projects: list[ProjectExport]
    companies: list[CompanyExport]
    achievements: list[AchievementExport]
    technologies: list[TechnologyExport]
    documents: list[DocumentExport]
```

---

## 3. Структура Content-API-NEW

### 3.1 Модели данных

```python
# services/content-api-new/app/models/

# Profile
class Profile:
    full_name: str
    title: str
    subtitle: str
    summary_md: str
    hero_headline: str
    hero_description: str
    current_position: str

# Experience (CompanyExperience)
class CompanyExperience:
    id: int
    role: str
    company_name: str
    company_slug: str
    start_date: date
    end_date: date | None
    is_current: bool
    kind: str                  # "commercial" | "personal"
    company_summary_md: str
    company_role_md: str
    description_md: str
    projects: list[ExperienceProject]  # Relationship

# ExperienceProject (projects within company)
class ExperienceProject:
    id: int
    company_experience_id: int
    name: str
    slug: str
    period: str
    description_md: str
    achievements_md: str

# Project (standalone featured projects)
class Project:
    id: int
    name: str
    slug: str
    featured: bool
    domain: str | None
    repo_url: str | None
    demo_url: str | None
    description_md: str
    long_description_md: str | None
    technologies: list[Technology]  # M2M

# Technology
class Technology:
    id: int
    name: str
    slug: str
    category: str
    order_index: int

# Publication
class Publication:
    id: int
    title: str
    year: int
    source: str            # "Habr", etc.
    url: str
    badge: str | None

# Contact
class Contact:
    id: int
    kind: str              # email, telegram, github, linkedin, hh, leetcode
    label: str
    value: str
    url: str | None

# FocusArea
class FocusArea:
    id: int
    title: str
    description: str
    icon: str | None
    order_index: int
    bullets: list[FocusAreaBullet]

# WorkApproach
class WorkApproach:
    id: int
    title: str
    description: str
    icon: str | None
    order_index: int
    bullets: list[WorkApproachBullet]

# TechFocus
class TechFocus:
    id: int
    title: str
    badge: str
    order_index: int
    technologies: list[Technology]  # M2M

# Stat
class Stat:
    id: int
    key: str
    label: str
    value: str
    hint: str | None
    group_name: str | None

# HeroTag
class HeroTag:
    id: int
    text: str
    order_index: int

# SectionMeta
class SectionMeta:
    id: int
    section_key: str
    title: str
    subtitle: str | None
```

### 3.2 RAG Export Endpoint

```python
# GET /api/v1/rag/documents

# Текущая реализация экспортирует данные для RAG
# Необходимо проанализировать и адаптировать структуру
```

---

## 4. Архитектура RAG-API-NEW

### 4.1 Структура проекта

```
services/rag-api-new/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── settings.py             # Pydantic Settings v2
│   ├── deps.py                 # Dependency Injection
│   │
│   ├── routers/                # API Routers (новая структура)
│   │   ├── __init__.py
│   │   ├── ask.py              # POST /api/v1/ask
│   │   ├── chat.py             # POST /api/v1/agent/chat/stream
│   │   ├── ingest.py           # POST /api/v1/ingest
│   │   ├── ingest_batch.py     # POST /api/v1/ingest/batch
│   │   └── admin.py            # /api/v1/admin/*
│   │
│   ├── rag/                    # RAG Pipeline (перенос + улучшения)
│   │   ├── __init__.py
│   │   ├── core.py             # portfolio_rag_answer()
│   │   ├── retrieval.py        # HybridRetriever
│   │   ├── reranker.py         # Cross-encoder (переименован из rank.py)
│   │   ├── evidence.py         # Evidence selection
│   │   ├── prompts.py          # Prompt templates
│   │   ├── types.py            # Type definitions
│   │   └── nlp.py              # NLP utilities
│   │
│   ├── indexing/               # Indexing (выделен в отдельный модуль)
│   │   ├── __init__.py
│   │   ├── bm25.py             # BM25 index
│   │   ├── persistence.py      # Index persistence
│   │   └── chunker.py          # Document chunking
│   │
│   ├── agent/                  # LangGraph Agent
│   │   ├── __init__.py
│   │   ├── graph.py            # Agent definition
│   │   ├── tools.py            # Agent tools
│   │   └── prompts.py          # Agent prompts
│   │
│   ├── llm/                    # LLM Adapters
│   │   ├── __init__.py
│   │   ├── base.py             # Base adapter interface
│   │   ├── gigachat.py         # GigaChat adapter
│   │   └── litellm.py          # LiteLLM adapter (новый)
│   │
│   ├── schemas/                # Pydantic Schemas
│   │   ├── __init__.py
│   │   ├── ask.py              # Ask request/response
│   │   ├── chat.py             # Chat request/response
│   │   ├── ingest.py           # Ingest schemas
│   │   └── export.py           # Export schemas (адаптированные)
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── text.py             # Text utilities
│       └── logging.py          # Structured logging
│
├── tests/                      # Tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_retrieval.py
│   ├── test_reranker.py
│   └── test_agent.py
│
├── pyproject.toml
├── Dockerfile
└── README.md
```

### 4.2 Изменения по сравнению с rag-api

| Аспект | rag-api | rag-api-new | Причина |
|--------|---------|-------------|---------|
| API роутеры | В корне app/ | В routers/ | Лучшая организация |
| Все endpoints | Смешанные версии | `/api/v1/*` | Консистентность |
| rank.py | `rank.py` | `reranker.py` | Более понятное имя |
| BM25 | В utils/ | В indexing/ | Логическая группировка |
| Схемы | Одн файл | Раздельные | Масштабируемость |
| LLM | Только GigaChat | GigaChat + LiteLLM | Гибкость |
| Тесты | Отсутствуют | Есть | Качество |

---

## 5. Новые схемы данных

### 5.1 Export Schemas (адаптированные под content-api-new)

```python
# app/schemas/export.py

from pydantic import BaseModel
from datetime import date

# === Profile ===
class ProfileExport(BaseModel):
    full_name: str
    title: str
    subtitle: str
    summary_md: str
    hero_headline: str
    hero_description: str
    current_position: str

# === Experience ===
class ExperienceProjectExport(BaseModel):
    id: int
    name: str
    slug: str
    period: str
    description_md: str
    achievements_md: str

class CompanyExperienceExport(BaseModel):
    id: int
    role: str
    company_name: str
    company_slug: str
    start_date: date
    end_date: date | None
    is_current: bool
    kind: str  # "commercial" | "personal"
    company_summary_md: str
    company_role_md: str
    description_md: str
    projects: list[ExperienceProjectExport]

# === Projects ===
class TechnologyExport(BaseModel):
    id: int
    name: str
    slug: str
    category: str

class ProjectExport(BaseModel):
    id: int
    name: str
    slug: str
    featured: bool
    domain: str | None
    repo_url: str | None
    demo_url: str | None
    description_md: str
    long_description_md: str | None
    technologies: list[TechnologyExport]

# === Publications ===
class PublicationExport(BaseModel):
    id: int
    title: str
    year: int
    source: str
    url: str

# === Focus Areas ===
class FocusAreaBulletExport(BaseModel):
    id: int
    text: str
    order_index: int

class FocusAreaExport(BaseModel):
    id: int
    title: str
    description: str
    icon: str | None
    bullets: list[FocusAreaBulletExport]

# === Work Approaches ===
class WorkApproachBulletExport(BaseModel):
    id: int
    text: str
    order_index: int

class WorkApproachExport(BaseModel):
    id: int
    title: str
    description: str
    icon: str | None
    bullets: list[WorkApproachBulletExport]

# === Tech Focus ===
class TechFocusExport(BaseModel):
    id: int
    title: str
    badge: str
    technologies: list[TechnologyExport]

# === Stats ===
class StatExport(BaseModel):
    id: int
    key: str
    label: str
    value: str
    hint: str | None

# === Contacts ===
class ContactExport(BaseModel):
    id: int
    kind: str
    label: str
    value: str
    url: str | None

# === Full Export Payload ===
class ExportPayload(BaseModel):
    """Полный экспорт данных из content-api-new для RAG индексации"""
    profile: ProfileExport
    experiences: list[CompanyExperienceExport]
    projects: list[ProjectExport]
    publications: list[PublicationExport]
    focus_areas: list[FocusAreaExport]
    work_approaches: list[WorkApproachExport]
    tech_focus: list[TechFocusExport]
    stats: list[StatExport]
    contacts: list[ContactExport]
```

### 5.2 Document Types для индексации

```python
# app/schemas/ingest.py

from enum import Enum
from pydantic import BaseModel

class DocumentType(str, Enum):
    """Типы документов для RAG"""
    PROFILE = "profile"
    EXPERIENCE = "experience"
    EXPERIENCE_PROJECT = "experience_project"
    PROJECT = "project"
    PUBLICATION = "publication"
    FOCUS_AREA = "focus_area"
    WORK_APPROACH = "work_approach"
    TECH_FOCUS = "tech_focus"
    TECHNOLOGY = "technology"
    STAT = "stat"
    CONTACT = "contact"

class DocumentChunk(BaseModel):
    """Чанк документа для индексации"""
    id: str                    # SHA1 hash
    doc_type: DocumentType
    source_id: int             # ID в источнике
    title: str                 # Заголовок для отображения
    content: str               # Текст для индексации
    metadata: dict             # Дополнительные метаданные
    
class IngestRequest(BaseModel):
    """Запрос на индексацию одного документа"""
    doc_type: DocumentType
    source_id: int
    title: str
    content: str
    metadata: dict = {}

class IngestBatchRequest(BaseModel):
    """Запрос на batch-индексацию"""
    payload: ExportPayload
    clear_before: bool = False  # Очистить коллекцию перед индексацией
```

---

## 6. Алгоритм нормализации документов

### 6.1 Document Normalizer

```python
# app/indexing/normalizer.py

from hashlib import sha1
from app.schemas.export import ExportPayload
from app.schemas.ingest import DocumentChunk, DocumentType

class DocumentNormalizer:
    """Нормализация ExportPayload в DocumentChunks"""
    
    MAX_CHUNK_SIZE = 900  # символов
    
    def normalize(self, payload: ExportPayload) -> list[DocumentChunk]:
        """Преобразует ExportPayload в список DocumentChunk"""
        chunks = []
        
        # Profile
        chunks.extend(self._normalize_profile(payload.profile))
        
        # Experiences + их projects
        for exp in payload.experiences:
            chunks.extend(self._normalize_experience(exp))
        
        # Standalone Projects
        for proj in payload.projects:
            chunks.extend(self._normalize_project(proj))
        
        # Publications
        for pub in payload.publications:
            chunks.extend(self._normalize_publication(pub))
        
        # Focus Areas
        for fa in payload.focus_areas:
            chunks.extend(self._normalize_focus_area(fa))
        
        # Work Approaches
        for wa in payload.work_approaches:
            chunks.extend(self._normalize_work_approach(wa))
        
        # Tech Focus
        for tf in payload.tech_focus:
            chunks.extend(self._normalize_tech_focus(tf))
        
        # Stats
        for stat in payload.stats:
            chunks.extend(self._normalize_stat(stat))
        
        return chunks
    
    def _normalize_profile(self, profile: ProfileExport) -> list[DocumentChunk]:
        """Нормализация профиля"""
        content = f"""
{profile.full_name} — {profile.title}

{profile.subtitle}

{profile.summary_md}

Текущая позиция: {profile.current_position}
""".strip()
        
        return self._chunk_text(
            content=content,
            doc_type=DocumentType.PROFILE,
            source_id=0,
            title=profile.full_name,
            metadata={
                "current_position": profile.current_position,
            }
        )
    
    def _normalize_experience(self, exp: CompanyExperienceExport) -> list[DocumentChunk]:
        """Нормализация опыта работы"""
        chunks = []
        
        # Основной документ компании
        period = f"{exp.start_date} — {'н.в.' if exp.is_current else exp.end_date}"
        content = f"""
{exp.role} в {exp.company_name}
Период: {period}
Тип: {'Коммерческий' if exp.kind == 'commercial' else 'Личный проект'}

{exp.company_summary_md}

Роль:
{exp.company_role_md}

Описание:
{exp.description_md}
""".strip()
        
        chunks.extend(self._chunk_text(
            content=content,
            doc_type=DocumentType.EXPERIENCE,
            source_id=exp.id,
            title=f"{exp.role} @ {exp.company_name}",
            metadata={
                "company_slug": exp.company_slug,
                "is_current": exp.is_current,
                "kind": exp.kind,
                "start_date": str(exp.start_date),
                "end_date": str(exp.end_date) if exp.end_date else None,
            }
        ))
        
        # Проекты внутри опыта
        for proj in exp.projects:
            proj_content = f"""
Проект: {proj.name}
Компания: {exp.company_name}
Период: {proj.period}

{proj.description_md}

Достижения:
{proj.achievements_md}
""".strip()
            
            chunks.extend(self._chunk_text(
                content=proj_content,
                doc_type=DocumentType.EXPERIENCE_PROJECT,
                source_id=proj.id,
                title=f"{proj.name} ({exp.company_name})",
                metadata={
                    "company_id": exp.id,
                    "company_slug": exp.company_slug,
                    "project_slug": proj.slug,
                }
            ))
        
        return chunks
    
    def _normalize_project(self, proj: ProjectExport) -> list[DocumentChunk]:
        """Нормализация standalone проекта"""
        tech_names = ", ".join([t.name for t in proj.technologies])
        
        content = f"""
Проект: {proj.name}
{'⭐ Featured проект' if proj.featured else ''}
Домен: {proj.domain or 'Не указан'}
Технологии: {tech_names}

{proj.description_md}

{proj.long_description_md or ''}
""".strip()
        
        return self._chunk_text(
            content=content,
            doc_type=DocumentType.PROJECT,
            source_id=proj.id,
            title=proj.name,
            metadata={
                "slug": proj.slug,
                "featured": proj.featured,
                "domain": proj.domain,
                "repo_url": proj.repo_url,
                "demo_url": proj.demo_url,
                "technologies": [t.name for t in proj.technologies],
            }
        )
    
    def _normalize_publication(self, pub: PublicationExport) -> list[DocumentChunk]:
        """Нормализация публикации"""
        content = f"""
Публикация: {pub.title}
Источник: {pub.source}
Год: {pub.year}
URL: {pub.url}
""".strip()
        
        return [DocumentChunk(
            id=self._generate_id(DocumentType.PUBLICATION, pub.id, content),
            doc_type=DocumentType.PUBLICATION,
            source_id=pub.id,
            title=pub.title,
            content=content,
            metadata={
                "source": pub.source,
                "year": pub.year,
                "url": pub.url,
            }
        )]
    
    def _normalize_focus_area(self, fa: FocusAreaExport) -> list[DocumentChunk]:
        """Нормализация области фокуса"""
        bullets = "\n".join([f"• {b.text}" for b in fa.bullets])
        content = f"""
Область фокуса: {fa.title}

{fa.description}

{bullets}
""".strip()
        
        return [DocumentChunk(
            id=self._generate_id(DocumentType.FOCUS_AREA, fa.id, content),
            doc_type=DocumentType.FOCUS_AREA,
            source_id=fa.id,
            title=fa.title,
            content=content,
            metadata={"icon": fa.icon}
        )]
    
    def _normalize_work_approach(self, wa: WorkApproachExport) -> list[DocumentChunk]:
        """Нормализация подхода к работе"""
        bullets = "\n".join([f"• {b.text}" for b in wa.bullets])
        content = f"""
Подход к работе: {wa.title}

{wa.description}

{bullets}
""".strip()
        
        return [DocumentChunk(
            id=self._generate_id(DocumentType.WORK_APPROACH, wa.id, content),
            doc_type=DocumentType.WORK_APPROACH,
            source_id=wa.id,
            title=wa.title,
            content=content,
            metadata={"icon": wa.icon}
        )]
    
    def _normalize_tech_focus(self, tf: TechFocusExport) -> list[DocumentChunk]:
        """Нормализация технологического фокуса"""
        tech_names = ", ".join([t.name for t in tf.technologies])
        content = f"""
Технологический фокус: {tf.title}
Тип: {tf.badge}
Технологии: {tech_names}
""".strip()
        
        return [DocumentChunk(
            id=self._generate_id(DocumentType.TECH_FOCUS, tf.id, content),
            doc_type=DocumentType.TECH_FOCUS,
            source_id=tf.id,
            title=tf.title,
            content=content,
            metadata={
                "badge": tf.badge,
                "technologies": [t.name for t in tf.technologies],
            }
        )]
    
    def _normalize_stat(self, stat: StatExport) -> list[DocumentChunk]:
        """Нормализация статистики"""
        content = f"""
{stat.label}: {stat.value}
{stat.hint or ''}
""".strip()
        
        return [DocumentChunk(
            id=self._generate_id(DocumentType.STAT, stat.id, content),
            doc_type=DocumentType.STAT,
            source_id=stat.id,
            title=f"{stat.label}: {stat.value}",
            content=content,
            metadata={
                "key": stat.key,
                "group_name": stat.group_name,
            }
        )]
    
    def _chunk_text(
        self,
        content: str,
        doc_type: DocumentType,
        source_id: int,
        title: str,
        metadata: dict
    ) -> list[DocumentChunk]:
        """Разбивает текст на чанки если превышает MAX_CHUNK_SIZE"""
        if len(content) <= self.MAX_CHUNK_SIZE:
            return [DocumentChunk(
                id=self._generate_id(doc_type, source_id, content),
                doc_type=doc_type,
                source_id=source_id,
                title=title,
                content=content,
                metadata=metadata
            )]
        
        # Разбиение на чанки по предложениям
        chunks = []
        sentences = self._split_sentences(content)
        current_chunk = ""
        chunk_idx = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        id=self._generate_id(doc_type, source_id, current_chunk, chunk_idx),
                        doc_type=doc_type,
                        source_id=source_id,
                        title=f"{title} (часть {chunk_idx + 1})",
                        content=current_chunk.strip(),
                        metadata={**metadata, "chunk_idx": chunk_idx}
                    ))
                    chunk_idx += 1
                current_chunk = sentence
            else:
                current_chunk += " " + sentence
        
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                id=self._generate_id(doc_type, source_id, current_chunk, chunk_idx),
                doc_type=doc_type,
                source_id=source_id,
                title=f"{title} (часть {chunk_idx + 1})" if chunk_idx > 0 else title,
                content=current_chunk.strip(),
                metadata={**metadata, "chunk_idx": chunk_idx}
            ))
        
        return chunks
    
    def _split_sentences(self, text: str) -> list[str]:
        """Разбивает текст на предложения"""
        import re
        # Простое разбиение по точке, восклицательному, вопросительному
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _generate_id(
        self,
        doc_type: DocumentType,
        source_id: int,
        content: str,
        chunk_idx: int = 0
    ) -> str:
        """Генерирует уникальный ID документа"""
        raw = f"{doc_type.value}:{source_id}:{chunk_idx}:{content[:100]}"
        return sha1(raw.encode()).hexdigest()[:16]
```

---

## 7. RAG Pipeline

### 7.1 Core RAG Function

```python
# app/rag/core.py

from dataclasses import dataclass
from app.rag.retrieval import HybridRetriever
from app.rag.reranker import CrossEncoderReranker
from app.rag.evidence import EvidenceSelector
from app.rag.prompts import build_rag_prompt
from app.rag.types import ScoredDoc, SourceInfo

@dataclass
class RAGResponse:
    answer: str
    sources: list[SourceInfo]
    confidence: float

async def portfolio_rag_answer(
    question: str,
    retriever: HybridRetriever,
    reranker: CrossEncoderReranker,
    llm,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    max_context_tokens: int = 2000,
) -> RAGResponse:
    """
    Основная RAG функция для ответа на вопросы по портфолио.
    
    Pipeline:
    1. Hybrid retrieval (dense + BM25)
    2. Cross-encoder reranking
    3. Evidence selection
    4. LLM generation
    """
    
    # 1. Retrieve candidates
    candidates: list[ScoredDoc] = await retriever.retrieve(
        query=question,
        top_k=top_k_retrieve
    )
    
    if not candidates:
        return RAGResponse(
            answer="К сожалению, я не нашёл информации по вашему вопросу в портфолио.",
            sources=[],
            confidence=0.0
        )
    
    # 2. Rerank
    reranked: list[ScoredDoc] = await reranker.rerank(
        query=question,
        documents=candidates,
        top_k=top_k_rerank
    )
    
    # 3. Select evidence
    evidence_selector = EvidenceSelector(max_tokens=max_context_tokens)
    context, sources = evidence_selector.select(reranked)
    
    # 4. Generate answer
    prompt = build_rag_prompt(question=question, context=context)
    response = await llm.ainvoke(prompt)
    
    # Calculate confidence based on reranker scores
    avg_score = sum(d.score for d in reranked[:3]) / min(3, len(reranked))
    confidence = min(1.0, avg_score)
    
    return RAGResponse(
        answer=response.content,
        sources=sources,
        confidence=confidence
    )
```

### 7.2 Hybrid Retriever

```python
# app/rag/retrieval.py

from abc import ABC, abstractmethod
from typing import Protocol
from app.rag.types import ScoredDoc
from app.indexing.bm25 import BM25Index

class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int) -> list[ScoredDoc]: ...

class HybridRetriever:
    """
    Гибридный retriever: dense embeddings + BM25.
    
    Объединяет результаты через Reciprocal Rank Fusion (RRF).
    """
    
    def __init__(
        self,
        vectorstore,  # ChromaDB
        bm25_index: BM25Index,
        dense_weight: float = 0.6,
        bm25_weight: float = 0.4,
        rrf_k: int = 60,
    ):
        self.vectorstore = vectorstore
        self.bm25_index = bm25_index
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k
    
    async def retrieve(self, query: str, top_k: int = 20) -> list[ScoredDoc]:
        """Hybrid retrieval с RRF fusion"""
        
        # Dense retrieval
        dense_results = await self._dense_retrieve(query, top_k * 2)
        
        # BM25 retrieval
        bm25_results = self._bm25_retrieve(query, top_k * 2)
        
        # Reciprocal Rank Fusion
        fused = self._rrf_fusion(dense_results, bm25_results, top_k)
        
        return fused
    
    async def _dense_retrieve(self, query: str, top_k: int) -> list[ScoredDoc]:
        """Retrieval через векторный поиск"""
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=top_k
        )
        return [
            ScoredDoc(
                id=doc.metadata.get("id", ""),
                content=doc.page_content,
                metadata=doc.metadata,
                score=1.0 - score,  # Convert distance to similarity
            )
            for doc, score in results
        ]
    
    def _bm25_retrieve(self, query: str, top_k: int) -> list[ScoredDoc]:
        """Retrieval через BM25"""
        return self.bm25_index.search(query, top_k)
    
    def _rrf_fusion(
        self,
        dense: list[ScoredDoc],
        bm25: list[ScoredDoc],
        top_k: int
    ) -> list[ScoredDoc]:
        """Reciprocal Rank Fusion"""
        scores = {}
        doc_map = {}
        
        # Score from dense
        for rank, doc in enumerate(dense):
            rrf_score = self.dense_weight / (self.rrf_k + rank + 1)
            scores[doc.id] = scores.get(doc.id, 0) + rrf_score
            doc_map[doc.id] = doc
        
        # Score from BM25
        for rank, doc in enumerate(bm25):
            rrf_score = self.bm25_weight / (self.rrf_k + rank + 1)
            scores[doc.id] = scores.get(doc.id, 0) + rrf_score
            if doc.id not in doc_map:
                doc_map[doc.id] = doc
        
        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [
            ScoredDoc(
                id=doc_id,
                content=doc_map[doc_id].content,
                metadata=doc_map[doc_id].metadata,
                score=scores[doc_id]
            )
            for doc_id in sorted_ids[:top_k]
        ]
```

### 7.3 Prompts

```python
# app/rag/prompts.py

SYSTEM_PROMPT = """Ты — AI-ассистент портфолио Дмитрия Каргина, ML/LLM инженера.

Твоя задача — отвечать на вопросы о его опыте, проектах и технологиях, 
используя ТОЛЬКО предоставленный контекст.

Правила:
1. Отвечай ТОЛЬКО на основе контекста. Если информации нет — скажи об этом.
2. Будь конкретен, приводи факты из контекста.
3. Используй структурированные ответы для сложных вопросов.
4. Отвечай на русском языке.
5. Не придумывай информацию.

Если вопрос не относится к портфолио — вежливо перенаправь к релевантным темам."""

def build_rag_prompt(question: str, context: str) -> list[dict]:
    """Формирует промпт для RAG"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Контекст:
{context}

Вопрос: {question}

Ответь на вопрос, используя только информацию из контекста."""}
    ]

AGENT_SYSTEM_PROMPT = """Ты — AI-агент портфолио Дмитрия Каргина.

У тебя есть инструменты для поиска информации:
- portfolio_rag_tool: поиск по всему портфолио
- list_projects_tool: список всех проектов

ВАЖНО: Для любого вопроса о портфолио СНАЧАЛА используй инструменты, 
НЕ отвечай из своих знаний.

Отвечай кратко, по делу, на русском языке."""
```

---

## 8. Agent System

### 8.1 LangGraph Agent

```python
# app/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

from app.agent.tools import get_agent_tools
from app.rag.prompts import AGENT_SYSTEM_PROMPT

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def create_agent(llm, retriever, reranker):
    """Создаёт LangGraph агента с RAG tools"""
    
    tools = get_agent_tools(retriever, reranker, llm)
    llm_with_tools = llm.bind_tools(tools)
    
    def should_continue(state: AgentState) -> str:
        """Определяет, нужно ли вызывать инструменты"""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END
    
    def call_model(state: AgentState) -> dict:
        """Вызывает LLM"""
        messages = state["messages"]
        
        # Добавляем system prompt если его нет
        if not any(m.type == "system" for m in messages):
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + list(messages)
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Build graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
```

### 8.2 Agent Tools

```python
# app/agent/tools.py

from langchain_core.tools import tool
from app.rag.core import portfolio_rag_answer

def get_agent_tools(retriever, reranker, llm):
    """Возвращает инструменты для агента"""
    
    @tool
    async def portfolio_rag_tool(question: str) -> str:
        """
        Поиск информации в портфолио Дмитрия Каргина.
        Используй для любых вопросов об опыте, проектах, технологиях.
        
        Args:
            question: Вопрос для поиска
            
        Returns:
            Ответ на основе найденной информации
        """
        response = await portfolio_rag_answer(
            question=question,
            retriever=retriever,
            reranker=reranker,
            llm=llm
        )
        
        sources_text = ""
        if response.sources:
            sources_text = "\n\nИсточники:\n" + "\n".join(
                f"- {s.title}" for s in response.sources
            )
        
        return f"{response.answer}{sources_text}"
    
    @tool
    async def list_projects_tool() -> str:
        """
        Получить список всех проектов из портфолио.
        Используй когда нужен обзор проектов или их перечисление.
        
        Returns:
            Список проектов с краткими описаниями
        """
        # Поиск по типу документа
        results = retriever.vectorstore.get(
            where={"doc_type": "project"},
            include=["metadatas", "documents"]
        )
        
        if not results["documents"]:
            return "Проекты не найдены"
        
        projects = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            name = meta.get("title", "Без названия")
            featured = "⭐ " if meta.get("featured") else ""
            projects.append(f"{featured}{name}")
        
        return "Проекты в портфолио:\n" + "\n".join(f"- {p}" for p in projects)
    
    return [portfolio_rag_tool, list_projects_tool]
```

---

## 9. API Endpoints

### 9.1 Ask Router

```python
# app/routers/ask.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.deps import get_retriever, get_reranker, get_llm
from app.rag.core import portfolio_rag_answer, RAGResponse

router = APIRouter(prefix="/api/v1", tags=["ask"])

class AskRequest(BaseModel):
    question: str
    session_id: str | None = None

class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    retriever=Depends(get_retriever),
    reranker=Depends(get_reranker),
    llm=Depends(get_llm),
):
    """Ответ на вопрос по портфолио"""
    response = await portfolio_rag_answer(
        question=request.question,
        retriever=retriever,
        reranker=reranker,
        llm=llm,
    )
    
    return AskResponse(
        answer=response.answer,
        sources=[{"title": s.title, "type": s.doc_type} for s in response.sources],
        confidence=response.confidence,
    )
```

### 9.2 Chat Router (Streaming)

```python
# app/routers/chat.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from app.deps import get_agent

router = APIRouter(prefix="/api/v1/agent", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    agent=Depends(get_agent),
):
    """Streaming чат с агентом"""
    
    async def generate():
        config = {"configurable": {"thread_id": request.thread_id}}
        
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]
            
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            elif kind == "on_tool_start":
                tool_name = event["name"]
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"
            
            elif kind == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### 9.3 Ingest Batch Router

```python
# app/routers/ingest_batch.py

from fastapi import APIRouter, Depends, HTTPException
from app.deps import get_vectorstore, get_bm25_index
from app.schemas.export import ExportPayload
from app.schemas.ingest import IngestBatchRequest
from app.indexing.normalizer import DocumentNormalizer

router = APIRouter(prefix="/api/v1", tags=["ingest"])

@router.post("/ingest/batch")
async def ingest_batch(
    request: IngestBatchRequest,
    vectorstore=Depends(get_vectorstore),
    bm25_index=Depends(get_bm25_index),
):
    """Batch индексация из ExportPayload"""
    
    # Clear if requested
    if request.clear_before:
        vectorstore.delete_collection()
        bm25_index.clear()
    
    # Normalize documents
    normalizer = DocumentNormalizer()
    chunks = normalizer.normalize(request.payload)
    
    if not chunks:
        raise HTTPException(status_code=400, detail="No documents to index")
    
    # Index to ChromaDB
    documents = []
    metadatas = []
    ids = []
    
    for chunk in chunks:
        documents.append(chunk.content)
        metadatas.append({
            "id": chunk.id,
            "doc_type": chunk.doc_type.value,
            "source_id": chunk.source_id,
            "title": chunk.title,
            **chunk.metadata
        })
        ids.append(chunk.id)
    
    vectorstore.add_texts(
        texts=documents,
        metadatas=metadatas,
        ids=ids,
    )
    
    # Update BM25 index
    bm25_index.add_documents(chunks)
    bm25_index.save()
    
    return {
        "status": "success",
        "indexed_count": len(chunks),
        "types": {
            doc_type: len([c for c in chunks if c.doc_type.value == doc_type])
            for doc_type in set(c.doc_type.value for c in chunks)
        }
    }
```

### 9.4 Admin Router

```python
# app/routers/admin.py

from fastapi import APIRouter, Depends
from app.deps import get_vectorstore, get_bm25_index

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.delete("/collection")
async def clear_collection(
    vectorstore=Depends(get_vectorstore),
    bm25_index=Depends(get_bm25_index),
):
    """Очистка коллекции и BM25 индекса"""
    vectorstore.delete_collection()
    bm25_index.clear()
    bm25_index.save()
    
    return {"status": "cleared"}

@router.get("/stats")
async def get_stats(
    vectorstore=Depends(get_vectorstore),
    bm25_index=Depends(get_bm25_index),
):
    """Статистика коллекции"""
    collection = vectorstore._collection
    
    # Get all documents
    results = collection.get(include=["metadatas"])
    
    # Count by type
    type_counts = {}
    for meta in results["metadatas"]:
        doc_type = meta.get("doc_type", "unknown")
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
    
    return {
        "total_documents": len(results["ids"]),
        "bm25_documents": bm25_index.doc_count,
        "by_type": type_counts,
    }
```

---

## 10. Content-API-NEW Integration

### 10.1 RAG Export Endpoint (обновить в content-api-new)

```python
# services/content-api-new/app/routers/rag.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.schemas.rag import ExportPayload

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

@router.get("/documents", response_model=ExportPayload)
async def export_for_rag(session: AsyncSession = Depends(get_session)):
    """Экспорт всех данных для RAG индексации"""
    
    # Profile
    profile = await get_profile(session)
    
    # Experiences with projects
    experiences = await get_experiences_with_projects(session)
    
    # Standalone projects
    projects = await get_projects_with_technologies(session)
    
    # Publications
    publications = await get_publications(session)
    
    # Focus areas
    focus_areas = await get_focus_areas_with_bullets(session)
    
    # Work approaches
    work_approaches = await get_work_approaches_with_bullets(session)
    
    # Tech focus
    tech_focus = await get_tech_focus_with_technologies(session)
    
    # Stats
    stats = await get_stats(session)
    
    # Contacts
    contacts = await get_contacts(session)
    
    return ExportPayload(
        profile=profile,
        experiences=experiences,
        projects=projects,
        publications=publications,
        focus_areas=focus_areas,
        work_approaches=work_approaches,
        tech_focus=tech_focus,
        stats=stats,
        contacts=contacts,
    )
```

---

## 11. Dependencies & Configuration

### 11.1 Settings

```python
# app/settings.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    app_name: str = "RAG API NEW"
    app_env: str = "dev"
    log_level: str = "INFO"
    
    # CORS
    frontend_origin: str = "http://localhost:3000"
    
    # LLM
    litellm_base_url: str = "http://localhost:8005/v1"
    litellm_api_key: str = "dev-secret"
    chat_model: str = "Qwen2.5"
    embedding_model: str = "embedding-default"
    
    # GigaChat (optional)
    gigachat_credentials: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    
    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "portfolio_new"
    
    # BM25
    bm25_index_path: str = "~/.bm25.portfolio_new.pkl"
    
    # RAG
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    max_context_tokens: int = 2000
    dense_weight: float = 0.6
    bm25_weight: float = 0.4
    
    # Content API
    content_api_url: str = "http://localhost:8003/api/v1"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 11.2 Dependencies

```python
# app/deps.py

from functools import lru_cache
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.settings import get_settings
from app.indexing.bm25 import BM25Index
from app.rag.retrieval import HybridRetriever
from app.rag.reranker import CrossEncoderReranker
from app.agent.graph import create_agent
from app.llm.litellm import get_litellm_chat

settings = get_settings()

# Embeddings
@lru_cache
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-base"
    )

# VectorStore
@lru_cache
def get_vectorstore():
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        client_settings={
            "chroma_api_impl": "rest",
            "chroma_server_host": settings.chroma_host,
            "chroma_server_http_port": settings.chroma_port,
        }
    )

# BM25 Index
@lru_cache
def get_bm25_index():
    return BM25Index(path=settings.bm25_index_path)

# Retriever
@lru_cache
def get_retriever():
    return HybridRetriever(
        vectorstore=get_vectorstore(),
        bm25_index=get_bm25_index(),
        dense_weight=settings.dense_weight,
        bm25_weight=settings.bm25_weight,
    )

# Reranker
@lru_cache
def get_reranker():
    return CrossEncoderReranker(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

# LLM
@lru_cache
def get_llm():
    return get_litellm_chat(
        base_url=settings.litellm_base_url,
        api_key=settings.litellm_api_key,
        model=settings.chat_model,
    )

# Agent
@lru_cache
def get_agent():
    return create_agent(
        llm=get_llm(),
        retriever=get_retriever(),
        reranker=get_reranker(),
    )
```

---

## 12. Docker Configuration

### 12.1 Dockerfile

```dockerfile
# services/rag-api-new/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

COPY app ./app

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
```

### 12.2 Docker Compose Update

```yaml
# infra/compose.apps.yaml (добавить)

services:
  rag-api-new:
    build:
      context: ../services/rag-api-new
      dockerfile: Dockerfile
    ports:
      - "${RAG_NEW_PORT:-8014}:8004"
    environment:
      - LITELLM_BASE_URL=http://litellm:4000/v1
      - LITELLM_API_KEY=${LITELLM_MASTER_KEY}
      - CHAT_MODEL=${CHAT_MODEL:-Qwen2.5}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-embedding-default}
      - CHROMA_HOST=chroma
      - CHROMA_PORT=8000
      - CHROMA_COLLECTION=portfolio_new
      - FRONTEND_ORIGIN=${FRONTEND_ORIGIN}
      - CONTENT_API_URL=http://content-api:8000/api/v1
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - chroma
      - litellm
      - content-api
    networks:
      - ai-portfolio
    volumes:
      - bm25-data-new:/home/appuser/.bm25

volumes:
  bm25-data-new:
```

---

## 13. Миграция и тестирование

### 13.1 План миграции

| Этап | Действие | Проверка |
|------|----------|----------|
| 1 | Создать структуру rag-api-new | Файлы созданы |
| 2 | Реализовать schemas | Pydantic валидация |
| 3 | Реализовать normalizer | Unit tests |
| 4 | Реализовать RAG pipeline | Integration tests |
| 5 | Реализовать agent | Manual testing |
| 6 | Реализовать API endpoints | API tests |
| 7 | Обновить content-api-new export | Export endpoint |
| 8 | Docker интеграция | docker compose up |
| 9 | Frontend переключение | E2E test |
| 10 | Удаление старого rag-api | Cleanup |

### 13.2 Тесты

```python
# tests/test_normalizer.py

import pytest
from app.indexing.normalizer import DocumentNormalizer
from app.schemas.export import ExportPayload, ProfileExport

def test_normalize_profile():
    normalizer = DocumentNormalizer()
    profile = ProfileExport(
        full_name="Дмитрий Каргин",
        title="ML/LLM Engineer",
        subtitle="Backend Developer",
        summary_md="Опытный разработчик...",
        hero_headline="AI Engineer",
        hero_description="Создаю AI системы",
        current_position="Aston"
    )
    
    payload = ExportPayload(
        profile=profile,
        experiences=[],
        projects=[],
        publications=[],
        focus_areas=[],
        work_approaches=[],
        tech_focus=[],
        stats=[],
        contacts=[],
    )
    
    chunks = normalizer.normalize(payload)
    
    assert len(chunks) >= 1
    assert chunks[0].doc_type.value == "profile"
    assert "Дмитрий Каргин" in chunks[0].content
```

---

## 14. Чек-лист готовности

### 14.1 Код

- [ ] Структура проекта создана
- [ ] Settings с Pydantic v2
- [ ] Schemas адаптированы под content-api-new
- [ ] DocumentNormalizer реализован
- [ ] HybridRetriever перенесён
- [ ] CrossEncoderReranker перенесён
- [ ] Evidence selection перенесён
- [ ] Prompts обновлены
- [ ] LangGraph Agent перенесён
- [ ] Agent Tools обновлены
- [ ] GigaChat Adapter перенесён
- [ ] LiteLLM Adapter добавлен
- [ ] API Routers реализованы
- [ ] Dependencies настроены

### 14.2 Интеграция

- [ ] Content-API-NEW export endpoint обновлён
- [ ] Docker конфигурация готова
- [ ] Environment variables документированы
- [ ] CORS настроен
- [ ] Frontend переключён на rag-api-new

### 14.3 Тестирование

- [ ] Unit tests для normalizer
- [ ] Unit tests для retrieval
- [ ] Integration tests для RAG pipeline
- [ ] API endpoint tests
- [ ] Manual agent testing
- [ ] Performance testing

### 14.4 Документация

- [ ] README.md
- [ ] API documentation (OpenAPI)
- [ ] CLAUDE.md обновлён

---

## 15. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Несовместимость схем | Средняя | Высокое | Тщательное тестирование export |
| Потеря качества RAG | Низкая | Высокое | A/B тестирование с старым API |
| Performance деградация | Средняя | Среднее | Профилирование, оптимизация |
| Проблемы с памятью agent | Низкая | Среднее | Ограничение истории |

---

## 16. Приложения

### A. Маппинг старых типов на новые

| Старый тип (rag-api) | Новый тип (rag-api-new) |
|---------------------|------------------------|
| project | project |
| achievement | experience_project |
| company | experience |
| technology | technology |
| document | publication |
| catalog | tech_focus |
| - | profile |
| - | focus_area |
| - | work_approach |
| - | stat |
| - | contact |

### B. Список файлов для создания

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
│   │   ├── reranker.py
│   │   ├── evidence.py
│   │   ├── prompts.py
│   │   ├── types.py
│   │   └── nlp.py
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── bm25.py
│   │   ├── persistence.py
│   │   ├── normalizer.py
│   │   └── chunker.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── gigachat.py
│   │   └── litellm.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ask.py
│   │   ├── chat.py
│   │   ├── ingest.py
│   │   └── export.py
│   └── utils/
│       ├── __init__.py
│       ├── text.py
│       └── logging.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_normalizer.py
│   ├── test_retrieval.py
│   └── test_agent.py
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

**Конец документа**