"""
Technology Tools - specialized tool for technology-related queries.

Provides get_technologies function for retrieving technologies
by project or by category.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_GET_TECHNOLOGIES
from .normalize import normalize_project_name

logger = logging.getLogger(__name__)


def get_technologies(
    project_name: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> ToolResult:
    """
    Get technologies by project or by category.

    Can return:
    1. Technologies used in a specific project
    2. All technologies in a category (language, database, ml_framework, etc.)
    3. All technologies (if neither project nor category specified)

    Args:
        project_name: Optional project name/slug to get technologies for
        category: Optional category filter (language, database, ml_framework, tool, etc.)
        limit: Maximum number of technologies to return

    Returns:
        ToolResult with technologies

    Examples:
        - "какие технологии в t2" -> get_technologies(project_name="t2")
        - "какие языки знает" -> get_technologies(category="language")
        - "какие базы данных использует" -> get_technologies(category="database")
    """
    from ...graph.query import (
        _technologies_query,
        _technologies_by_category_query,
    )

    logger.info(
        "get_technologies: project_name=%s, category=%s, limit=%d",
        project_name,
        category,
        limit,
    )

    try:
        if project_name:
            # Get technologies for specific project
            project_key = normalize_project_name(project_name)
            result = _technologies_query(project_key)
            context = {"project_name": project_name, "project_key": project_key}
        elif category:
            # Get technologies by category
            category_key = _normalize_category(category)
            result = _technologies_by_category_query(category_key, limit)
            context = {"category": category, "category_key": category_key}
        else:
            # Get all technologies
            result = _technologies_query(None)
            context = {}

        # Convert items to FactItem
        facts = []
        for item in result.items:
            fact = _item_to_fact(item, project_name, category)
            if fact:
                facts.append(fact)

        # Apply limit
        if limit and len(facts) > limit:
            facts = facts[:limit]

        logger.info(
            "get_technologies: found %d technologies",
            len(facts),
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_TECHNOLOGIES,
            params={
                "project_name": project_name,
                "category": category,
                "limit": limit,
                **context,
            },
        )

    except Exception as e:
        logger.error("get_technologies error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_TECHNOLOGIES,
            params={"project_name": project_name, "category": category},
            error=str(e),
        )


def _normalize_category(category: str) -> str:
    """
    Normalize category name to standard format.

    Handles Russian variations and common aliases.
    """
    category_lower = category.lower().strip()

    # Category mappings (including Russian)
    category_mappings = {
        # Language variations
        "language": "language",
        "languages": "language",
        "язык": "language",
        "языки": "language",
        "языков": "language",
        "programming": "language",
        "программирование": "language",
        # Database variations
        "database": "database",
        "databases": "database",
        "db": "database",
        "база": "database",
        "базы": "database",
        "базы данных": "database",
        "бд": "database",
        "субд": "database",
        # ML/AI variations
        "ml_framework": "ml_framework",
        "ml": "ml_framework",
        "ai": "ml_framework",
        "machine_learning": "ml_framework",
        "machine learning": "ml_framework",
        "машинное обучение": "ml_framework",
        "нейросети": "ml_framework",
        "нейросеть": "ml_framework",
        # Framework variations
        "framework": "framework",
        "frameworks": "framework",
        "фреймворк": "framework",
        "фреймворки": "framework",
        # Tool variations
        "tool": "tool",
        "tools": "tool",
        "инструмент": "tool",
        "инструменты": "tool",
        # Cloud variations
        "cloud": "cloud",
        "облако": "cloud",
        "облачные": "cloud",
        # Library variations
        "library": "library",
        "libraries": "library",
        "библиотека": "library",
        "библиотеки": "library",
        # Concept variations
        "concept": "concept",
        "концепт": "concept",
        "концепция": "concept",
    }

    if category_lower in category_mappings:
        return category_mappings[category_lower]

    for pattern, standard in category_mappings.items():
        if pattern in category_lower or category_lower in pattern:
            return standard

    return category_lower


def _item_to_fact(
    item: dict[str, Any],
    project_name: str | None,
    category: str | None,
) -> FactItem | None:
    """Convert a technology item to FactItem."""
    if not isinstance(item, dict):
        return None

    name = item.get("name")
    if not name:
        return None

    # Build text representation
    text_parts = [str(name)]

    item_category = item.get("category")
    if item_category:
        text_parts.append(f"категория: {item_category}")

    # If this is technology usage (has project info)
    project = item.get("project")
    if project:
        company = item.get("company_name")
        if company:
            text_parts.append(f"используется в: {project} ({company})")
        else:
            text_parts.append(f"используется в: {project}")

    # Project count for category queries
    project_count = item.get("project_count")
    if project_count is not None:
        text_parts.append(f"проектов: {project_count}")

    text = " — ".join(text_parts)

    return FactItem(
        type="technology",
        text=text,
        metadata={
            **item,
            "technology_name": name,
            "category": item_category or category,
        },
        source_id=item.get("id") or name.lower().replace(" ", "-"),
    )
