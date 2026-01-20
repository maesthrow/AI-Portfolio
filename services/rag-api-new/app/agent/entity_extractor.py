"""
Entity Extractor - Deterministic extraction of entities from questions.

SYSTEMIC SOLUTION: Extract entities BEFORE calling Planner LLM.
This removes the burden from LLM to parse questions and decide
if explicit entities override session context.

Process:
1. Extract words from question
2. Match against known entities using fuzzy matching
3. Return extracted entities with confidence scores

The Planner receives extracted entities as EXPLICIT instruction,
so it just needs to choose the right tool - not parse the question.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Entity extracted from question."""
    type: Literal["project", "company", "technology"]
    value: str  # Normalized slug
    original: str  # Original text from question
    confidence: float  # 0.0-1.0


@dataclass
class ExtractionResult:
    """Result of entity extraction."""
    entities: list[ExtractedEntity]
    has_explicit_project: bool
    has_explicit_company: bool
    has_reference_words: bool  # "там", "этот", etc.


# Reference words that indicate using session context
REFERENCE_WORDS = {
    "там", "туда", "оттуда",
    "в ней", "в нём", "в них",
    "этой", "этого", "этом", "это",
    "той", "того", "том",
    "такой", "такого",
    "какие там", "что там", "а там",
    "а стек", "а достижения", "а технологии",
}

# Question patterns that indicate NEW entity (override session)
# Pattern: "что за X", "что такое X", "расскажи о X"
NEW_ENTITY_PATTERNS = [
    r"что (?:за|это за|такое)\s+([^\s?.,!]+)",
    r"расскажи (?:о|про|об)\s+([^\s?.,!]+)",
    r"что это за\s+([^\s?.,!]+)",
]


def extract_entities(question: str) -> ExtractionResult:
    """
    Extract entities from question deterministically.

    This function runs BEFORE Planner LLM to give it clear
    information about what entities are mentioned in the question.

    Args:
        question: User question text

    Returns:
        ExtractionResult with extracted entities and flags
    """
    question_lower = question.lower().strip()
    entities: list[ExtractedEntity] = []

    # Check for reference words (indicates session context should be used)
    has_reference_words = _has_reference_words(question_lower)

    # Try to extract explicit entities using patterns
    pattern_entities = _extract_from_patterns(question_lower)
    entities.extend(pattern_entities)

    # Try to match known projects
    project_entity = _try_match_project(question_lower)
    if project_entity and not _entity_exists(entities, project_entity):
        entities.append(project_entity)

    # Try to match known companies
    company_entity = _try_match_company(question_lower)
    if company_entity and not _entity_exists(entities, company_entity):
        entities.append(company_entity)

    # Determine flags
    has_explicit_project = any(e.type == "project" for e in entities)
    has_explicit_company = any(e.type == "company" for e in entities)

    logger.info(
        "EntityExtractor: question=%r, entities=%s, "
        "explicit_project=%s, explicit_company=%s, has_refs=%s",
        question[:50],
        [(e.type, e.value, e.confidence) for e in entities],
        has_explicit_project,
        has_explicit_company,
        has_reference_words,
    )

    return ExtractionResult(
        entities=entities,
        has_explicit_project=has_explicit_project,
        has_explicit_company=has_explicit_company,
        has_reference_words=has_reference_words,
    )


def _has_reference_words(text: str) -> bool:
    """Check if text contains reference words."""
    for ref in REFERENCE_WORDS:
        if ref in text:
            return True
    return False


def _extract_from_patterns(text: str) -> list[ExtractedEntity]:
    """Extract entities using regex patterns like 'что за X'."""
    entities = []

    for pattern in NEW_ENTITY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Try to resolve what this is (project or company)
            entity = _resolve_entity_type(match)
            if entity:
                entities.append(entity)

    return entities


def _resolve_entity_type(name: str) -> ExtractedEntity | None:
    """
    Try to resolve entity type by matching against known entities.

    Tries project first, then company.
    """
    # Try project match
    project_slug = _fuzzy_match_project(name)
    if project_slug:
        return ExtractedEntity(
            type="project",
            value=project_slug,
            original=name,
            confidence=0.9,
        )

    # Try company match
    company_slug = _fuzzy_match_company(name)
    if company_slug:
        return ExtractedEntity(
            type="company",
            value=company_slug,
            original=name,
            confidence=0.9,
        )

    # Unknown entity - still return as project (most common case)
    # This will be passed to get_project_details which can fail gracefully
    return ExtractedEntity(
        type="project",
        value=name.lower().replace(" ", "-"),
        original=name,
        confidence=0.5,  # Low confidence - may not exist
    )


def _try_match_project(text: str) -> ExtractedEntity | None:
    """
    Try to find a known project name in the text.

    Looks for project slugs or their variations in the question.
    """
    try:
        from app.graph.store import get_graph_store
        from app.graph.schema import NodeType

        store = get_graph_store()
        projects = store.get_nodes_by_type(NodeType.PROJECT)

        for project in projects:
            slug = project.slug.lower()
            name = (project.name or "").lower()

            # Check if slug appears in text
            if slug in text:
                return ExtractedEntity(
                    type="project",
                    value=slug,
                    original=slug,
                    confidence=0.95,
                )

            # Check if project name appears in text
            if name and len(name) > 2 and name in text:
                return ExtractedEntity(
                    type="project",
                    value=slug,
                    original=name,
                    confidence=0.90,
                )

        return None

    except Exception as e:
        logger.warning("Failed to match projects: %s", e)
        return None


def _try_match_company(text: str) -> ExtractedEntity | None:
    """
    Try to find a known company name in the text.

    Looks for company slugs or their variations in the question.
    """
    # Russian company name variations
    company_variations = {
        "aston": ["aston", "астон", "астоне", "астона"],
        "spargo": ["spargo", "спарго", "спарге"],
        "alor": ["alor", "алор", "алоре"],
        "freelance": ["freelance", "фриланс"],
        "t-bank": ["t-bank", "tbank", "тинькофф", "т-банк"],
    }

    for slug, variations in company_variations.items():
        for var in variations:
            if var in text:
                return ExtractedEntity(
                    type="company",
                    value=slug,
                    original=var,
                    confidence=0.95,
                )

    # Try matching from graph
    try:
        from app.graph.store import get_graph_store
        from app.graph.schema import NodeType

        store = get_graph_store()
        companies = store.get_nodes_by_type(NodeType.COMPANY)

        for company in companies:
            slug = company.slug.lower()
            name = (company.name or "").lower()

            if slug in text:
                return ExtractedEntity(
                    type="company",
                    value=slug,
                    original=slug,
                    confidence=0.95,
                )

            if name and len(name) > 2 and name in text:
                return ExtractedEntity(
                    type="company",
                    value=slug,
                    original=name,
                    confidence=0.90,
                )

        return None

    except Exception as e:
        logger.warning("Failed to match companies: %s", e)
        return None


def _fuzzy_match_project(name: str) -> str | None:
    """
    Fuzzy match a name against known project slugs.

    Uses the normalize module for consistent matching.
    """
    from app.agent.tools.normalize import normalize_project_name

    try:
        normalized = normalize_project_name(name)
        # Check if this is a real slug (not just the input back)
        if normalized != name.lower().replace(" ", "-"):
            return normalized
        return None
    except Exception:
        return None


def _fuzzy_match_company(name: str) -> str | None:
    """
    Fuzzy match a name against known company slugs.

    Uses the normalize module for consistent matching.
    """
    from app.agent.tools.normalize import normalize_company_name

    try:
        normalized = normalize_company_name(name)
        # Check if this is a real slug (not just the input back)
        if normalized != name.lower().replace(" ", "-"):
            return normalized
        return None
    except Exception:
        return None


def _entity_exists(entities: list[ExtractedEntity], new_entity: ExtractedEntity) -> bool:
    """Check if entity already exists in list."""
    for e in entities:
        if e.type == new_entity.type and e.value == new_entity.value:
            return True
    return False


def format_extraction_for_planner(
    extraction: ExtractionResult,
    last_company: str | None,
    last_project: str | None,
) -> str:
    """
    Format extraction result for Planner prompt.

    This gives Planner EXPLICIT information about:
    1. What entities are mentioned in the question
    2. What the session context is
    3. Clear instruction on what to use

    Args:
        extraction: Result from extract_entities()
        last_company: Session context company
        last_project: Session context project

    Returns:
        Formatted string to add to Planner prompt
    """
    parts = []

    # Session context
    session_parts = []
    if last_company:
        session_parts.append(f"Текущая компания в диалоге: {last_company}")
    if last_project:
        session_parts.append(f"Текущий проект в диалоге: {last_project}")

    if session_parts:
        parts.append("КОНТЕКСТ СЕССИИ:")
        parts.extend(session_parts)
        parts.append("")

    # Extracted entities (MOST IMPORTANT)
    if extraction.entities:
        parts.append("ОБНАРУЖЕНО В ВОПРОСЕ (используй ЭТИ сущности, игнорируй контекст сессии):")
        for entity in extraction.entities:
            type_ru = {"project": "проект", "company": "компания", "technology": "технология"}
            parts.append(f"  - {type_ru.get(entity.type, entity.type)}: {entity.value}")
        parts.append("")
    elif extraction.has_reference_words:
        parts.append("В вопросе есть слова-референции ('там', 'этот' и т.д.) - используй контекст сессии.")
        parts.append("")
    else:
        parts.append("Явных сущностей в вопросе не обнаружено - это ОБЩИЙ вопрос.")
        parts.append("")

    return "\n".join(parts)
