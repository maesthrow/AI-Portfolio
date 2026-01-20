"""
Summary Tools - tools for entity definition queries.

Provides get_project_summary and get_company_summary
for "что такое X" / "что за компания X" questions.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import (
    ToolResult,
    TOOL_GET_PROJECT_SUMMARY,
    TOOL_GET_COMPANY_SUMMARY,
)
from .normalize import normalize_project_name, normalize_company_name

logger = logging.getLogger(__name__)


def get_project_summary(project_name: str) -> ToolResult:
    """
    Get summary of a project for "что такое X" questions.

    Returns description-first text without leading technical fields
    (domain/period/stack should NOT be first).

    Args:
        project_name: Project name or slug

    Returns:
        ToolResult with project summary

    Examples:
        - "что такое t2" -> get_project_summary("t2")
        - "что за проект AI-Portfolio" -> get_project_summary("ai-portfolio")
    """
    from ...graph.query import _project_summary_query

    if not project_name:
        logger.warning("get_project_summary called with empty project_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_SUMMARY,
            params={"project_name": project_name},
            error="Project name is required",
        )

    project_key = normalize_project_name(project_name)

    logger.info(
        "get_project_summary: project_name=%s, project_key=%s",
        project_name,
        project_key,
    )

    try:
        result = _project_summary_query(project_key)

        facts = []
        for item in result.items:
            fact = _project_summary_to_fact(item)
            if fact:
                facts.append(fact)

        logger.info(
            "get_project_summary: found=%s for '%s'",
            result.found,
            project_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_PROJECT_SUMMARY,
            params={"project_name": project_name, "project_key": project_key},
        )

    except Exception as e:
        logger.error("get_project_summary error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_PROJECT_SUMMARY,
            params={"project_name": project_name},
            error=str(e),
        )


def get_company_summary(company_name: str) -> ToolResult:
    """
    Get summary of a company for "что за компания X" questions.

    Returns company description, role, and period.

    Args:
        company_name: Company name or slug

    Returns:
        ToolResult with company summary

    Examples:
        - "что за компания АЛОР" -> get_company_summary("alor")
        - "расскажи о компании Aston" -> get_company_summary("aston")
    """
    from ...graph.query import _company_summary_query

    if not company_name:
        logger.warning("get_company_summary called with empty company_name")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_SUMMARY,
            params={"company_name": company_name},
            error="Company name is required",
        )

    company_key = normalize_company_name(company_name)

    logger.info(
        "get_company_summary: company_name=%s, company_key=%s",
        company_name,
        company_key,
    )

    try:
        result = _company_summary_query(company_key)

        facts = []
        for item in result.items:
            fact = _company_summary_to_fact(item)
            if fact:
                facts.append(fact)

        logger.info(
            "get_company_summary: found=%s for '%s'",
            result.found,
            company_name,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_COMPANY_SUMMARY,
            params={"company_name": company_name, "company_key": company_key},
        )

    except Exception as e:
        logger.error("get_company_summary error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_COMPANY_SUMMARY,
            params={"company_name": company_name},
            error=str(e),
        )


def _project_summary_to_fact(item: dict[str, Any]) -> FactItem | None:
    """Convert project summary item to FactItem.

    IMPORTANT: Description FIRST, technical fields LAST.
    """
    if not isinstance(item, dict):
        return None

    name = item.get("name")
    if not name:
        return None

    description = item.get("description") or ""
    company = item.get("company_name")
    domain = item.get("domain")
    period = item.get("period")

    # Human-friendly text: description FIRST, NOT domain/period
    text_parts = []

    # 1. Name with context
    if company:
        text_parts.append(f"{name} — проект в компании {company}.")
    else:
        text_parts.append(f"{name} — личный проект.")

    # 2. Description (main content)
    if description:
        # Truncate if too long
        desc = description[:400] if len(description) > 400 else description
        text_parts.append(desc)

    # 3. Domain and period at the end
    if domain:
        text_parts.append(f"Домен: {domain}.")
    if period:
        text_parts.append(f"Период: {period}.")

    text = " ".join(text_parts)

    return FactItem(
        type="project_summary",
        text=text,
        metadata={
            "name": name,
            "slug": item.get("slug"),
            "description": description,
            "company_name": company,
            "domain": domain,
            "period": period,
        },
        source_id=item.get("slug"),
    )


def _company_summary_to_fact(item: dict[str, Any]) -> FactItem | None:
    """Convert company summary item to FactItem."""
    if not isinstance(item, dict):
        return None

    company = item.get("company")
    if not company:
        return None

    role = item.get("role") or ""
    summary = item.get("summary") or ""
    role_desc = item.get("role_description") or ""
    period = item.get("period") or ""
    is_current = item.get("is_current", False)

    # Human-friendly text
    text_parts = [company]

    if summary:
        text_parts.append(f"— {summary}")

    if role:
        text_parts.append(f"Роль Дмитрия: {role}.")

    if role_desc:
        text_parts.append(role_desc)

    if period:
        text_parts.append(f"Период: {period}.")

    if is_current:
        text_parts.append("[текущее место работы]")

    text = " ".join(text_parts)

    return FactItem(
        type="company_summary",
        text=text,
        metadata={
            "company_name": company,
            "company_slug": item.get("company_slug"),
            "role": role,
            "period": period,
            "summary": summary,
            "role_description": role_desc,
            "is_current": is_current,
        },
        source_id=item.get("company_slug"),
    )
