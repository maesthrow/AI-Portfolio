"""
GraphSchema - типы узлов и рёбер для графа знаний портфолио.

Определяет структуру графа: какие сущности представлены узлами,
какие отношения - рёбрами.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class NodeType(str, Enum):
    """Типы узлов в графе знаний."""
    PERSON = "person"           # Профиль (владелец портфолио)
    COMPANY = "company"         # Компания/организация
    PROJECT = "project"         # Проект (standalone или experience)
    ACHIEVEMENT = "achievement" # Достижение
    TECHNOLOGY = "technology"   # Технология/навык
    CONTACT = "contact"         # Контакт (email, github, etc.)


class EdgeType(str, Enum):
    """Типы рёбер (отношений) в графе."""
    WORKS_AT = "works_at"       # Person -> Company (текущая работа)
    WORKED_AT = "worked_at"     # Person -> Company (прошлая работа)
    CREATED = "created"         # Person -> Project
    ACHIEVED = "achieved"       # Person -> Achievement
    USES = "uses"               # Project -> Technology
    KNOWS = "knows"             # Person -> Technology (навык)
    BELONGS_TO = "belongs_to"   # Achievement -> Project/Company
    HAS_CONTACT = "has_contact" # Person -> Contact


@dataclass
class GraphNode:
    """
    Узел графа знаний.

    Attributes:
        id: Уникальный идентификатор (например, "project:alor-broker")
        type: Тип узла
        name: Человекочитаемое название
        slug: Короткий идентификатор для URL/поиска
        data: Дополнительные данные узла
    """
    id: str
    type: NodeType
    name: str
    slug: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """
    Ребро (отношение) графа знаний.

    Attributes:
        source_id: ID исходного узла
        target_id: ID целевого узла
        type: Тип отношения
        data: Дополнительные данные ребра
    """
    source_id: str
    target_id: str
    type: EdgeType
    data: Dict[str, Any] = field(default_factory=dict)
