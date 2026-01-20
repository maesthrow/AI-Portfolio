"""
Company Tools - specialized tool for company-related queries.

Provides get_company_projects function for retrieving projects
of a specific company.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_GET_COMPANY_PROJECTS
from .normalize import normalize_company_name

logger = logging.getLogger(__name__)


def get_company_projects(
    company_name: str,
    include_achievements: bool = True,  # Always include achievements - users expect them
    limit: int = 10,
) -> ToolResult:
    """
    Get projects for a specific company.

    This tool returns ONLY projects that belong to the specified company,
    preventing mixing of projects from different companies.

    Args:
        company_name: Company name or slug (e.g., "aston", "spargo", "alor")
        include_achievements: Whether to include project achievements
        limit: Maximum number of projects to return

    Returns:
        ToolResult with company projects, sources, and confidence

    Examples:
        - "проекты в Aston" -> get_company_projects("aston")
        - "над чем работал в Спарго" -> get_company_projects("spargo")
    """
    from ...graph.query import _projects_by_company_query

    if not company_name:
        logger.warning("get_company_projects called with empty company_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_PROJECTS,
            params={"company_name": company_name},
            error="Company name is required",
        )

    # Normalize company name to slug-like format
    company_key = normalize_company_name(company_name)

    logger.info(
        "get_company_projects: company_name=%s, company_key=%s, limit=%d",
        company_name,
        company_key,
        limit,
    )

    try:
        result = _projects_by_company_query(company_key, limit)

        # Convert items to FactItem
        facts = []
        for item in result.items:
            fact = _item_to_fact(item, include_achievements)
            if fact:
                facts.append(fact)

        logger.info(
            "get_company_projects: found %d projects for company '%s'",
            len(facts),
            company_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_COMPANY_PROJECTS,
            params={
                "company_name": company_name,
                "company_key": company_key,
                "include_achievements": include_achievements,
                "limit": limit,
            },
        )

    except Exception as e:
        logger.error("get_company_projects error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_PROJECTS,
            params={"company_name": company_name},
            error=str(e),
        )


def _item_to_fact(item: dict[str, Any], include_achievements: bool) -> FactItem | None:
    """Convert a project item to FactItem."""
    if not isinstance(item, dict):
        return None

    name = item.get("name") or item.get("project")
    if not name:
        return None

    # Build text representation
    text_parts = [str(name)]

    company = item.get("company_name")
    if company:
        text_parts[0] = f"{name} ({company})"

    domain = item.get("domain")
    if domain:
        text_parts.append(f"домен: {domain}")

    period = item.get("period")
    if period:
        text_parts.append(f"период: {period}")

    description = item.get("description") or item.get("long_description")
    if description:
        # Truncate long descriptions
        desc = str(description)[:200]
        if len(str(description)) > 200:
            desc += "..."
        text_parts.append(desc)

    # Include technologies if available
    technologies = item.get("technologies", [])
    if technologies and isinstance(technologies, list):
        tech_str = ", ".join(str(t) for t in technologies[:5])
        if len(technologies) > 5:
            tech_str += f" и ещё {len(technologies) - 5}"
        text_parts.append(f"технологии: {tech_str}")

    # Include achievements (enabled by default)
    if include_achievements:
        achievements = item.get("achievements", [])
        if achievements and isinstance(achievements, list):
            # Include all achievements (up to 5) for completeness
            ach_str = "; ".join(str(a)[:100] for a in achievements[:5])
            if len(achievements) > 5:
                ach_str += f" и ещё {len(achievements) - 5}"
            text_parts.append(f"достижения: {ach_str}")

    text = " — ".join(text_parts)

    return FactItem(
        type="project",
        text=text,
        metadata={
            **item,
            "company_slug": item.get("company_slug"),
            "project_slug": item.get("slug"),
        },
        source_id=item.get("slug") or item.get("id"),
    )
