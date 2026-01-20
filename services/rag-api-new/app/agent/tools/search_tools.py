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
from .normalize import normalize_project_name, normalize_company_name

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
        filters["company_id"] = normalize_company_name(company_filter)
    if project_filter:
        filters["project_id"] = normalize_project_name(project_filter)

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
            company_key = normalize_company_name(company_filter)
            facts = _filter_by_company(facts, company_key)

        # SYSTEMIC FIX: Post-filter by keywords from query
        # If query mentions specific technology, filter out results that don't mention it
        # This prevents "F3 TAIL: технология RAG не описана подробно" issues
        facts = _filter_by_query_keywords(facts, query)

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


# Known technology keywords for post-filtering
KNOWN_TECHNOLOGIES = {
    # ML/AI
    "rag", "llm", "langchain", "langgraph", "chromadb", "vector", "embedding",
    "ml", "machine learning", "deep learning", "neural", "нейросет",
    "gpt", "gigachat", "openai", "transformer", "bert", "vllm",
    # Languages
    "python", "javascript", "typescript", "c#", "java", "go", "rust", "sql",
    # Frameworks
    "fastapi", "django", "flask", "react", "next.js", "nextjs", "vue",
    "asp.net", "dotnet", ".net",
    # Databases
    "postgresql", "postgres", "mongodb", "redis", "mysql", "sqlite",
    # Tools
    "docker", "kubernetes", "k8s", "git", "ci/cd", "mlflow",
    # Concepts
    "microservice", "api", "rest", "graphql", "websocket",
}


def _filter_by_query_keywords(facts: list[FactItem], query: str) -> list[FactItem]:
    """
    Post-filter facts by technology keywords from query.

    CONTEXT: This is NOT related to state pollution (fixed by state_cleanup_node).
    This addresses a DIFFERENT issue: semantic search quality.

    PROBLEM: Dense embeddings (vector similarity) find semantically similar documents,
    but don't guarantee presence of query keywords. Example:
    - Query: "где применял RAG?"
    - Vector search might return "F3 TAIL" (semantically similar: ML, inference)
    - But F3 TAIL doesn't actually use RAG technology

    TODO: Better long-term solution:
    - Improve hybrid retrieval BM25 keyword weighting
    - Use ChromaDB metadata filtering by technologies array
    This post-filter is a pragmatic workaround until proper hybrid tuning.

    Args:
        facts: List of facts from search
        query: Original search query

    Returns:
        Filtered list - facts mentioning at least one query technology
    """
    if not facts:
        return facts

    query_lower = query.lower()

    # Find technology keywords in query
    query_techs = []
    for tech in KNOWN_TECHNOLOGIES:
        if tech in query_lower:
            query_techs.append(tech)

    # If no specific technology mentioned, return all facts
    if not query_techs:
        return facts

    logger.info(
        "_filter_by_query_keywords: found techs %s in query '%s'",
        query_techs,
        query[:50],
    )

    # Filter: keep facts that mention at least one of the query technologies
    filtered = []
    for fact in facts:
        # Check text content
        text_lower = (fact.text or "").lower()

        # Check metadata
        md = fact.metadata or {}
        technologies = md.get("technologies", [])
        if isinstance(technologies, str):
            technologies = [t.strip() for t in technologies.split(",")]
        tech_str = " ".join(str(t).lower() for t in technologies)

        # Also check technologies_csv
        tech_csv = (md.get("technologies_csv") or "").lower()

        # Combined searchable text
        searchable = f"{text_lower} {tech_str} {tech_csv}"

        # Check if any query tech is mentioned
        matches = any(tech in searchable for tech in query_techs)

        if matches:
            filtered.append(fact)
        else:
            logger.debug(
                "_filter_by_query_keywords: filtered out fact '%s' - no tech match",
                fact.text[:50] if fact.text else "no text",
            )

    # If filtering removed ALL facts, return original (safety fallback)
    if not filtered and facts:
        logger.warning(
            "_filter_by_query_keywords: all facts filtered out, returning original"
        )
        return facts

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
