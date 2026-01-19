"""
Search Tools - semantic search tool with filtering support.

Provides search_portfolio function for hybrid (semantic + BM25)
search across all portfolio data with optional filters.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_SEARCH_PORTFOLIO

logger = logging.getLogger(__name__)


def search_portfolio(
    query: str,
    company_filter: str | None = None,
    project_filter: str | None = None,
    type_filter: list[str] | None = None,
    k: int = 8,
) -> ToolResult:
    """
    Semantic search across portfolio data with optional filters.

    Uses hybrid retrieval (dense embeddings + BM25) for best results.
    Supports filtering by company, project, or document type.

    Args:
        query: Search query text
        company_filter: Optional company slug to filter results
        project_filter: Optional project slug to filter results
        type_filter: Optional list of document types to filter
                    (e.g., ["project", "technology", "achievement"])
        k: Number of results to return

    Returns:
        ToolResult with search results

    Examples:
        - "где применял RAG" -> search_portfolio("RAG применение")
        - "расскажи об ML-проектах" -> search_portfolio("ML проекты", type_filter=["project"])
        - "достижения в Aston" -> search_portfolio("достижения", company_filter="aston")
    """
    from ...rag.search import portfolio_search

    if not query or not query.strip():
        logger.warning("search_portfolio called with empty query")
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_SEARCH_PORTFOLIO,
            params={"query": query},
            error="Query is required",
        )

    # Build filters dict
    filters = {}
    if company_filter:
        filters["company_id"] = _normalize_company(company_filter)
    if project_filter:
        filters["project_id"] = _normalize_project(project_filter)

    logger.info(
        "search_portfolio: query=%r, company=%s, project=%s, types=%s, k=%d",
        query[:50],
        company_filter,
        project_filter,
        type_filter,
        k,
    )

    try:
        result = portfolio_search(
            question=query,
            k=k,
            allowed_types=type_filter,
            filters=filters if filters else None,
        )

        # Convert items to FactItem
        facts = []
        for item in result.items:
            fact = _item_to_fact(item)
            if fact:
                facts.append(fact)

        # If no facts from items, try parsing evidence text
        if not facts and result.evidence:
            facts = _evidence_to_facts(result.evidence)

        # Post-filter by company if graph didn't filter
        if company_filter and facts:
            company_key = _normalize_company(company_filter)
            facts = _filter_by_company(facts, company_key)

        logger.info(
            "search_portfolio: found %d facts for query '%s'",
            len(facts),
            query[:30],
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found and len(facts) > 0,
            confidence=result.confidence,
            tool_name=TOOL_SEARCH_PORTFOLIO,
            params={
                "query": query,
                "company_filter": company_filter,
                "project_filter": project_filter,
                "type_filter": type_filter,
                "k": k,
            },
            evidence_text=result.evidence,
        )

    except Exception as e:
        logger.error("search_portfolio error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_SEARCH_PORTFOLIO,
            params={"query": query},
            error=str(e),
        )


def _normalize_company(company: str) -> str:
    """Normalize company name to slug."""
    company_lower = company.lower().strip()

    mappings = {
        "aston": "aston",
        "астон": "aston",
        "spargo": "spargo",
        "спарго": "spargo",
        "alor": "alor",
        "алор": "alor",
        "freelance": "freelance",
        "фриланс": "freelance",
    }

    if company_lower in mappings:
        return mappings[company_lower]

    for pattern, slug in mappings.items():
        if pattern in company_lower:
            return slug

    return company_lower.replace(" ", "-")


def _normalize_project(project: str) -> str:
    """Normalize project name to slug."""
    project_lower = project.lower().strip()

    mappings = {
        "t2": "t2",
        "tier2": "t2",
        "ai-portfolio": "ai-portfolio",
        "alor-broker": "alor-broker",
        "hyperkeeper": "hyperkeeper",
    }

    if project_lower in mappings:
        return mappings[project_lower]

    for pattern, slug in mappings.items():
        if pattern in project_lower:
            return slug

    return project_lower.replace(" ", "-")


def _filter_by_company(facts: list[FactItem], company_key: str) -> list[FactItem]:
    """Post-filter facts by company."""
    filtered = []
    for fact in facts:
        md = fact.metadata or {}

        # Check various company fields
        company_slug = (md.get("company_slug") or "").lower()
        company_name = (md.get("company_name") or "").lower()

        if (company_key in company_slug or company_key in company_name or
            company_slug in company_key or company_name in company_key):
            filtered.append(fact)
            continue

        # If no company info, include by default (might be relevant)
        if not company_slug and not company_name:
            filtered.append(fact)

    return filtered


def _item_to_fact(item: Any) -> FactItem | None:
    """Convert a search result item to FactItem."""
    # Handle ScoredDoc objects
    if hasattr(item, "doc"):
        doc = item.doc
        text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        return FactItem(
            type=metadata.get("type", "document"),
            text=text,
            metadata=metadata,
            source_id=metadata.get("id"),
        )

    # Handle dict items
    if isinstance(item, dict):
        text = (
            item.get("text")
            or item.get("page_content")
            or item.get("content")
            or str(item)
        )
        return FactItem(
            type=item.get("type", "document"),
            text=str(text),
            metadata=item,
            source_id=item.get("id"),
        )

    # Handle string items
    if isinstance(item, str):
        return FactItem(
            type="text",
            text=item,
            metadata={},
        )

    return None


def _evidence_to_facts(evidence: str) -> list[FactItem]:
    """Parse evidence text into facts (fallback when items not available)."""
    import re

    text = (evidence or "").strip()
    if not text:
        return []

    facts: list[FactItem] = []
    blocks = re.split(r"\n\s*\n", text)

    for block in blocks:
        b = (block or "").strip()
        if not b:
            continue

        # Try to parse [type] title: body format
        m = re.match(
            r"^\[(?P<type>[^\]]+)\]\s*(?P<title>[^:]+)\s*:\s*(?P<body>.*)$",
            b,
            flags=re.DOTALL,
        )
        if m:
            fact_type = (m.group("type") or "text").strip()
            title = (m.group("title") or "").strip()
            body = (m.group("body") or "").strip()
            facts.append(
                FactItem(
                    type=fact_type,
                    text=body or title or b,
                    metadata={"name": title} if title else {},
                    source_id=None,
                )
            )
        else:
            facts.append(
                FactItem(
                    type="text",
                    text=b,
                    metadata={},
                    source_id=None,
                )
            )

    return facts
