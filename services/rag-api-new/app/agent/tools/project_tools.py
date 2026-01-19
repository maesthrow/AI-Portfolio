"""
Project Tools - specialized tool for project-related queries.

Provides get_project_details function for retrieving details
of a specific project including technologies and achievements.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_GET_PROJECT_DETAILS

logger = logging.getLogger(__name__)


def get_project_details(
    project_name: str,
    include_technologies: bool = True,
    include_achievements: bool = True,
) -> ToolResult:
    """
    Get detailed information about a specific project.

    Returns project description, technologies used, and achievements.

    Args:
        project_name: Project name or slug (e.g., "t2", "ai-portfolio", "alor-broker")
        include_technologies: Whether to include technology list
        include_achievements: Whether to include achievements

    Returns:
        ToolResult with project details

    Examples:
        - "расскажи о проекте t2" -> get_project_details("t2")
        - "какой стек в AI-Portfolio" -> get_project_details("ai-portfolio")
    """
    from ...graph.query import _project_details_query

    if not project_name:
        logger.warning("get_project_details called with empty project_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_DETAILS,
            params={"project_name": project_name},
            error="Project name is required",
        )

    # Normalize project name to slug-like format
    project_key = _normalize_project_name(project_name)

    logger.info(
        "get_project_details: project_name=%s, project_key=%s",
        project_name,
        project_key,
    )

    try:
        result = _project_details_query(project_key)

        # Convert items to FactItem
        facts = []
        for item in result.items:
            fact = _item_to_fact(item, include_technologies, include_achievements)
            if fact:
                facts.append(fact)

        logger.info(
            "get_project_details: found=%s for project '%s'",
            result.found,
            project_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_PROJECT_DETAILS,
            params={
                "project_name": project_name,
                "project_key": project_key,
                "include_technologies": include_technologies,
                "include_achievements": include_achievements,
            },
        )

    except Exception as e:
        logger.error("get_project_details error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_DETAILS,
            params={"project_name": project_name},
            error=str(e),
        )


def _normalize_project_name(name: str) -> str:
    """
    Normalize project name to slug-like format.

    Handles common variations:
    - "t2" -> "t2"
    - "AI-Portfolio" -> "ai-portfolio"
    - "ALOR Broker" -> "alor-broker"
    """
    name_lower = name.lower().strip()

    # Known project mappings
    project_mappings = {
        # T2 variations
        "t2": "t2",
        "tier2": "t2",
        "т2": "t2",
        "tier-2": "t2",
        # AI-Portfolio variations
        "ai-portfolio": "ai-portfolio",
        "ai portfolio": "ai-portfolio",
        "портфолио": "ai-portfolio",
        # ALOR Broker variations
        "alor-broker": "alor-broker",
        "alor broker": "alor-broker",
        "алор брокер": "alor-broker",
        "alor": "alor-broker",
        # HyperKeeper variations
        "hyperkeeper": "hyperkeeper",
        "hyper-keeper": "hyperkeeper",
        "гиперкипер": "hyperkeeper",
    }

    # Check for direct match
    if name_lower in project_mappings:
        return project_mappings[name_lower]

    # Check for partial match
    for pattern, slug in project_mappings.items():
        if pattern in name_lower or name_lower in pattern:
            return slug

    # Fallback: simple normalization
    return name_lower.replace(" ", "-")


def _item_to_fact(
    item: dict[str, Any],
    include_technologies: bool,
    include_achievements: bool,
) -> FactItem | None:
    """Convert a project details item to FactItem."""
    if not isinstance(item, dict):
        return None

    name = item.get("name")
    if not name:
        return None

    # Build comprehensive text representation
    text_parts = []

    # Project name and company
    company = item.get("company_name")
    if company:
        text_parts.append(f"{name} ({company})")
    else:
        text_parts.append(str(name))

    # Domain and period
    domain = item.get("domain")
    period = item.get("period")
    if domain or period:
        meta = []
        if domain:
            meta.append(f"домен: {domain}")
        if period:
            meta.append(f"период: {period}")
        text_parts.append(" | ".join(meta))

    # Description
    description = item.get("long_description") or item.get("description")
    if description:
        text_parts.append(str(description))

    # Technologies
    if include_technologies:
        technologies = item.get("technologies", [])
        if technologies and isinstance(technologies, list):
            tech_str = ", ".join(str(t) for t in technologies)
            text_parts.append(f"Технологии: {tech_str}")

    # Achievements
    if include_achievements:
        achievements = item.get("achievements", [])
        if achievements and isinstance(achievements, list):
            ach_list = [f"• {a}" for a in achievements]
            text_parts.append("Достижения:\n" + "\n".join(ach_list))

    # URLs
    repo_url = item.get("repo_url")
    demo_url = item.get("demo_url")
    if repo_url or demo_url:
        urls = []
        if repo_url:
            urls.append(f"GitHub: {repo_url}")
        if demo_url:
            urls.append(f"Demo: {demo_url}")
        text_parts.append(" | ".join(urls))

    text = "\n\n".join(text_parts)

    return FactItem(
        type="project",
        text=text,
        metadata={
            **item,
            "project_slug": item.get("slug"),
            "company_slug": _extract_company_slug(item),
        },
        source_id=item.get("slug") or item.get("id"),
    )


def _extract_company_slug(item: dict[str, Any]) -> str | None:
    """Extract company slug from project item."""
    company_name = item.get("company_name")
    if not company_name:
        return None

    # Simple slug extraction
    name_lower = company_name.lower()

    # Known mappings
    if "aston" in name_lower:
        return "aston"
    if "spargo" in name_lower:
        return "spargo"
    if "alor" in name_lower:
        return "alor"
    if "freelance" in name_lower:
        return "freelance"

    return name_lower.replace(" ", "-")
