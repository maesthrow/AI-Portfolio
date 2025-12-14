from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .entities import EntityMatch, extract_entities, get_entity_registry


class Intent(str, Enum):
    ACHIEVEMENTS = "ACHIEVEMENTS"
    CURRENT_JOB = "CURRENT_JOB"
    LANGUAGES = "LANGUAGES"
    RAG_USAGE = "RAG_USAGE"
    CONTACTS = "CONTACTS"
    PROJECT_DETAILS = "PROJECT_DETAILS"
    GENERAL = "GENERAL"


class EntityPolicy(str, Enum):
    NONE = "none"
    BOOST = "boost"
    STRICT = "strict"


class PackingStrategy(str, Enum):
    COMPACT = "COMPACT"
    ACHIEVEMENTS = "ACHIEVEMENTS"
    CONTACTS = "CONTACTS"
    STATS = "STATS"
    TECH_TAGS = "TECH_TAGS"
    PROJECT_DETAILS = "PROJECT_DETAILS"


@dataclass(frozen=True)
class QueryPlan:
    intent: Intent
    entities: list[EntityMatch] = field(default_factory=list)
    entity_policy: EntityPolicy = EntityPolicy.NONE
    entity_scope_types: set[str] | None = None

    # Retrieval constraints
    allowed_types: set[str] | None = None
    item_kinds: set[str] = field(default_factory=set)
    where: dict[str, Any] | None = None

    # Retrieval budgets
    k_dense: int = 40
    k_bm: int = 40
    k_final: int = 24
    evidence_k: int = 10

    # Answer/packing hints
    packing_strategy: PackingStrategy = PackingStrategy.COMPACT
    style_hint: str | None = None
    answer_instructions: str | None = None

    # Fallback tuning
    min_confidence_for_strict: float = 0.28


def _has_any(q: str, tokens: tuple[str, ...]) -> bool:
    return any(t in q for t in tokens)


def detect_intent(question: str) -> Intent:
    q = (question or "").lower()

    contacts = ("контакт", "как связ", "email", "e-mail", "почт", "телефон", "github", "telegram", "tg", "linkedin")
    if _has_any(q, contacts):
        return Intent.CONTACTS

    current_job = ("где сейчас", "сейчас работает", "текущ", "current job", "current position", "где работает")
    if _has_any(q, current_job):
        return Intent.CURRENT_JOB

    achievements = ("достижен", "achievement", "результат", "что реализ", "что сделал", "что удалось", "итог")
    if _has_any(q, achievements):
        return Intent.ACHIEVEMENTS

    rag = (" rag", "rag ", "rag?", "rag.", "retrieval", "langgraph", "langchain", "agent", "агент", "реакт-агент")
    if _has_any(q, rag) or "rag" in q:
        return Intent.RAG_USAGE

    languages = ("языки программ", "какие языки", "programming language", "programming languages", "languages")
    if _has_any(q, languages):
        return Intent.LANGUAGES

    project_details = ("проект", "project", "чем заним", "задач", "роль", "обязан", "стек", "архитектур", "описани")
    if _has_any(q, project_details):
        return Intent.PROJECT_DETAILS

    return Intent.GENERAL


def build_query_plan(question: str, *, collection: str, list_max_items: int) -> QueryPlan:
    """
    Строит план поиска: intent + entities + ограничения по типам + политика по сущностям.
    """
    intent = detect_intent(question)
    registry = get_entity_registry(collection)
    entities = extract_entities(question, registry)

    by_kind: dict[str, list[EntityMatch]] = {}
    for e in entities:
        by_kind.setdefault(e.kind, []).append(e)

    project_entities = by_kind.get("project", [])
    company_entities = by_kind.get("company", [])
    tech_entities = by_kind.get("technology", [])

    entity_policy = EntityPolicy.NONE
    scope_types: set[str] | None = None

    if intent in {Intent.ACHIEVEMENTS, Intent.PROJECT_DETAILS}:
        scope_types = {"item", "experience_project", "experience", "project", "technology"}
        if len(project_entities) == 1 or (len(project_entities) == 0 and len(company_entities) == 1):
            entity_policy = EntityPolicy.STRICT
        elif len(project_entities) > 1 or len(company_entities) > 1:
            entity_policy = EntityPolicy.BOOST

    if intent == Intent.CURRENT_JOB:
        scope_types = {"experience", "experience_project"}
        if len(company_entities) == 1:
            entity_policy = EntityPolicy.STRICT
        elif len(company_entities) > 1:
            entity_policy = EntityPolicy.BOOST

    # Defaults
    allowed_types: set[str] | None = None
    item_kinds: set[str] = set()
    packing = PackingStrategy.COMPACT
    style_hint: str | None = None
    answer_instructions: str | None = None
    where: dict[str, Any] | None = None

    if intent == Intent.ACHIEVEMENTS:
        allowed_types = {"experience", "experience_project", "project", "item"}
        item_kinds = {"achievement"}
        packing = PackingStrategy.ACHIEVEMENTS
        style_hint = "LIST"
    elif intent == Intent.CONTACTS:
        allowed_types = {"profile", "contact", "item"}
        item_kinds = {"contact"}
        packing = PackingStrategy.CONTACTS
        style_hint = "LIST"
    elif intent == Intent.CURRENT_JOB:
        allowed_types = {"profile", "experience", "experience_project"}
        packing = PackingStrategy.COMPACT
        style_hint = "ULTRASHORT"
    elif intent == Intent.LANGUAGES:
        allowed_types = {"technology"}
        style_hint = "LIST"
        # Точная фильтрация по категории, если в базе категория задана как 'language'.
        where = {"category": "language"}
        answer_instructions = (
            "Если вопрос про языки программирования: перечисли только языки. "
            "Фреймворки/инструменты не называй языками; при необходимости вынеси их отдельным коротким списком."
        )
    elif intent == Intent.RAG_USAGE:
        allowed_types = {"project", "experience_project", "tech_focus", "technology"}
        style_hint = "LIST"
        answer_instructions = (
            "Если вопрос про использование конкретного инструмента/технологии//фреймворка: перечисляй только те проекты/контексты, где есть данные об этом инструменте. "
            "Не добавляй фразы вида 'не удалось найти упоминание X', если пользователь не спрашивал про X."
        )
    elif intent == Intent.PROJECT_DETAILS:
        allowed_types = {"experience_project", "project", "technology", "experience", "item"}
        item_kinds = {"achievement"}
        packing = PackingStrategy.PROJECT_DETAILS
        style_hint = "LIST"

    evidence_k = max(8, int(list_max_items)) if style_hint == "LIST" else 8
    k_dense = max(evidence_k * 4, 40)
    k_bm = max(evidence_k * 4, 40)
    k_final = max(evidence_k * 3, evidence_k)

    return QueryPlan(
        intent=intent,
        entities=entities,
        entity_policy=entity_policy,
        entity_scope_types=scope_types,
        allowed_types=allowed_types,
        item_kinds=item_kinds,
        where=where,
        k_dense=k_dense,
        k_bm=k_bm,
        k_final=k_final,
        evidence_k=evidence_k,
        packing_strategy=packing,
        style_hint=style_hint,
        answer_instructions=answer_instructions,
    )
