"""
Achievements Tools - tools for querying achievements.

Provides get_company_achievements and get_project_achievements
for retrieving specific achievements from portfolio.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import (
    ToolResult,
    TOOL_GET_COMPANY_ACHIEVEMENTS,
    TOOL_GET_PROJECT_ACHIEVEMENTS,
)
from .normalize import normalize_company_name, normalize_project_name

logger = logging.getLogger(__name__)


def get_company_achievements(company_name: str) -> ToolResult:
    """
    Get achievements for a specific company.

    Collects achievements from all projects in the company.
    Used for questions like "достижения в Спарго", "чего добился в АЛОР".

    Args:
        company_name: Company name or slug

    Returns:
        ToolResult with list of achievements

    Examples:
        - "достижения в Спарго" -> get_company_achievements("spargo")
        - "результаты в АЛОР" -> get_company_achievements("alor")
    """
    from ...graph.query import _company_achievements_query

    if not company_name:
        logger.warning("get_company_achievements called with empty company_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_ACHIEVEMENTS,
            params={"company_name": company_name},
            error="Company name is required",
        )

    company_key = normalize_company_name(company_name)

    logger.info(
        "get_company_achievements: company_name=%s, company_key=%s",
        company_name,
        company_key,
    )

    try:
        result = _company_achievements_query(company_key)

        facts = []
        for item in result.items:
            fact = _achievement_to_fact(item)
            if fact:
                facts.append(fact)

        logger.info(
            "get_company_achievements: found %d achievements for '%s'",
            len(facts),
            company_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_COMPANY_ACHIEVEMENTS,
            params={"company_name": company_name, "company_key": company_key},
        )

    except Exception as e:
        logger.error("get_company_achievements error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_ACHIEVEMENTS,
            params={"company_name": company_name},
            error=str(e),
        )


def get_project_achievements(project_name: str) -> ToolResult:
    """
    Get achievements for a specific project.

    Used for questions like "достижения в t2", "результаты проекта AI-Portfolio".

    Args:
        project_name: Project name or slug

    Returns:
        ToolResult with list of achievements

    Examples:
        - "достижения в t2" -> get_project_achievements("t2")
        - "результаты AI-Portfolio" -> get_project_achievements("ai-portfolio")
    """
    from ...graph.query import _project_achievements_query

    if not project_name:
        logger.warning("get_project_achievements called with empty project_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_ACHIEVEMENTS,
            params={"project_name": project_name},
            error="Project name is required",
        )

    project_key = normalize_project_name(project_name)

    logger.info(
        "get_project_achievements: project_name=%s, project_key=%s",
        project_name,
        project_key,
    )

    try:
        result = _project_achievements_query(project_key)

        facts = []
        for item in result.items:
            fact = _achievement_to_fact(item)
            if fact:
                facts.append(fact)

        logger.info(
            "get_project_achievements: found %d achievements for '%s'",
            len(facts),
            project_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_PROJECT_ACHIEVEMENTS,
            params={"project_name": project_name, "project_key": project_key},
        )

    except Exception as e:
        logger.error("get_project_achievements error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_ACHIEVEMENTS,
            params={"project_name": project_name},
            error=str(e),
        )


def _achievement_to_fact(item: dict[str, Any]) -> FactItem | None:
    """Convert achievement item to FactItem."""
    if not isinstance(item, dict):
        return None

    text = item.get("text")
    if not text:
        return None

    project = item.get("project")
    company = item.get("company")

    # Human-friendly text - just the achievement text
    # Context (project/company) is in metadata
    display_text = text
    if project:
        display_text = f"{text} (проект: {project})"

    # BUGFIX: Use unique source_id for each achievement
    # Old code used project_slug, which caused all achievements from same project
    # to be deduplicated to 1 fact (tool returns 3, but only 1 passes dedup).
    # Now use hash of text + project for uniqueness.
    import hashlib
    unique_key = f"{item.get('project_slug', '')}-{text[:50]}"
    source_id = f"achievement-{hashlib.md5(unique_key.encode()).hexdigest()[:8]}"

    return FactItem(
        type="achievement",
        text=display_text,
        metadata={
            "achievement_text": text,
            "project_name": project,
            "project_slug": item.get("project_slug"),
            "company_name": company,
            "company_slug": item.get("company_slug"),
        },
        source_id=source_id,
    )
