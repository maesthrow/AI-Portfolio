"""
Типы данных для Query Planning и Graph-RAG.

Эпик 1 & 2: Все структуры данных для поиска, планирования запросов
и результатов графовых запросов.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Intent(str, Enum):
    """Намерения пользователя для классификации запросов."""
    ACHIEVEMENTS = "achievements"
    CURRENT_JOB = "current_job"
    LANGUAGES = "languages"
    RAG_USAGE = "rag_usage"
    CONTACTS = "contacts"
    PROJECT_DETAILS = "project_details"
    TECHNOLOGIES = "technologies"
    EXPERIENCE = "experience"
    GENERAL = "general"


class EntityType(str, Enum):
    """Типы сущностей в портфолио."""
    PROJECT = "project"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    PERSON = "person"


class EntityPolicy(str, Enum):
    """Политика применения сущностей при поиске."""
    STRICT = "strict"    # Фильтровать только по найденной сущности
    BOOST = "boost"      # Повышать релевантность найденной сущности
    NONE = "none"        # Не применять фильтрацию по сущностям


@dataclass
class Entity:
    """Извлечённая сущность из вопроса."""
    type: EntityType
    slug: str
    name: str
    confidence: float = 1.0


@dataclass
class QueryPlan:
    """
    План выполнения запроса.

    Определяет стратегию поиска: какие типы документов искать,
    какую политику применять к сущностям, использовать ли граф.
    """
    intent: Intent
    entities: list[Entity] = field(default_factory=list)
    allowed_types: set[str] | None = None
    entity_policy: EntityPolicy = EntityPolicy.NONE
    use_graph: bool = False
    k_dense: int = 40
    k_bm: int = 40
    k_final: int = 24
    style_hint: str | None = None


@dataclass
class GraphQueryResult:
    """
    Результат запроса к графу знаний.

    Содержит структурированные факты (items) и метаинформацию.
    """
    items: list[dict[str, Any]]
    found: bool
    sources: list[dict[str, Any]]
    confidence: float
    intent: Intent
    entity_key: str | None = None


@dataclass
class SearchResult:
    """
    Унифицированный результат поиска.

    Возвращается из portfolio_search() независимо от того,
    использовался граф или гибридный поиск.
    """
    query: str
    intent: Intent
    entities: list[Entity]
    items: list[Any]  # Структурированные факты или ScoredDoc
    evidence: str  # Упакованный контекст для LLM
    sources: list[dict[str, Any]]
    confidence: float
    found: bool
    used_graph: bool = False
