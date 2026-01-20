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

        # P1 FIX: Apply domain filtering for AI/ML queries
        # This prioritizes projects with AI/ML domains (ml_platform, rag, AI-agents)
        facts = _filter_by_domain(facts, query)

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
    "ai", "ml",  # P0 FIX: Added "ai" - was missing, causing inconsistent behavior
    "rag", "llm", "langchain", "langgraph", "chromadb", "vector", "embedding",
    "machine learning", "deep learning", "neural", "нейросет",
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


# P0 FIX: Semantic aliases for keyword expansion
# When user asks about "ml", we should also match "llm", "rag", "langchain", etc.
TECHNOLOGY_ALIASES: dict[str, set[str]] = {
    # ML/AI aliases - "ml" expands to all related terms
    "ml": {
        "ml", "llm", "rag", "langchain", "langgraph", "machine learning",
        "deep learning", "neural", "нейросет", "embedding", "vector",
        "transformer", "bert", "gpt", "vllm",
    },
    "ai": {
        "ai", "ml", "llm", "rag", "langchain", "langgraph", "machine learning",
        "deep learning", "neural", "нейросет", "embedding", "vector",
        "искусственный интеллект",
    },
    "нейросет": {"нейросет", "ml", "llm", "neural", "deep learning", "machine learning"},

    # Database aliases
    "database": {
        "database", "postgresql", "postgres", "mysql", "mongodb", "redis",
        "chromadb", "sqlite", "clickhouse", "бд", "база данных",
    },
    "бд": {"бд", "база данных", "database", "postgresql", "postgres", "mysql"},

    # Backend aliases
    "backend": {"backend", "fastapi", "django", "flask", "python", "api", "rest"},
    "api": {"api", "rest", "fastapi", "graphql", "grpc"},
}


# P1: Domain-based filtering for AI/ML queries
AI_ML_DOMAINS = {"ml_platform", "rag", "AI-agents"}
BOT_WITH_LLM_KEYWORDS = {"llm", "langchain", "langgraph", "gpt", "rag"}


def _expand_keywords_with_aliases(keywords: list[str]) -> set[str]:
    """
    Expand keywords using TECHNOLOGY_ALIASES.

    P0 FIX: "ml" expands to ["ml", "llm", "rag", "langchain", ...]
    This ensures "ML-проекты" finds all ML/AI related projects.
    """
    expanded = set()
    for kw in keywords:
        expanded.add(kw)
        if kw in TECHNOLOGY_ALIASES:
            expanded.update(TECHNOLOGY_ALIASES[kw])
    return expanded


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

    P0 FIX: Now uses TECHNOLOGY_ALIASES for semantic expansion.
    "ml" query now matches documents with "llm", "rag", "langchain", etc.

    Args:
        facts: List of facts from search
        query: Original search query

    Returns:
        Filtered list - facts mentioning at least one query technology (or alias)
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

    # P0 FIX: Expand keywords using aliases
    expanded_techs = _expand_keywords_with_aliases(query_techs)

    logger.info(
        "_filter_by_query_keywords: found techs %s -> expanded to %s",
        query_techs,
        sorted(expanded_techs)[:10],  # Log first 10 for brevity
    )

    # Filter: keep facts that mention at least one of the expanded technologies
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

        # Check if any expanded tech is mentioned
        matches = any(tech in searchable for tech in expanded_techs)

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


def _filter_by_domain(facts: list[FactItem], query: str) -> list[FactItem]:
    """
    P1: Filter facts by domain for AI/ML queries.

    Projects have a 'domain' field in metadata: ml_platform, rag, AI-agents, Bot, backend, cv.
    When user asks about AI/ML projects, prioritize facts from AI_ML_DOMAINS.

    Args:
        facts: List of facts from search
        query: Original search query

    Returns:
        Filtered list prioritizing AI/ML domain facts
    """
    if not facts:
        return facts

    query_lower = query.lower()

    # Check if query is about AI/ML
    ai_ml_keywords = {"ml", "ai", "нейросет", "machine learning", "искусственный интеллект"}
    is_ai_ml_query = any(kw in query_lower for kw in ai_ml_keywords)

    if not is_ai_ml_query:
        return facts

    logger.info("_filter_by_domain: AI/ML query detected, applying domain filter")

    filtered = []
    for fact in facts:
        md = fact.metadata or {}
        domain = (md.get("domain") or "").lower()

        # Direct match with AI/ML domains (case-insensitive)
        domain_matches = domain in {d.lower() for d in AI_ML_DOMAINS}
        if domain_matches:
            filtered.append(fact)
            continue

        # Bot with LLM technologies
        if domain == "bot":
            technologies = md.get("technologies", [])
            if isinstance(technologies, str):
                technologies = [t.strip() for t in technologies.split(",")]
            tech_lower = {str(t).lower() for t in technologies}
            if tech_lower & BOT_WITH_LLM_KEYWORDS:
                filtered.append(fact)
                continue

        # Fallback: check tech stack for AI/ML keywords
        technologies = md.get("technologies", [])
        if isinstance(technologies, str):
            technologies = [t.strip() for t in technologies.split(",")]
        tech_lower = {str(t).lower() for t in technologies}
        ml_aliases = TECHNOLOGY_ALIASES.get("ml", set())
        if tech_lower & ml_aliases:
            filtered.append(fact)

    # Don't return empty result - fallback to original
    if not filtered and facts:
        logger.warning("_filter_by_domain: all facts filtered out, returning original")
        return facts

    logger.info("_filter_by_domain: %d -> %d facts after domain filter", len(facts), len(filtered))
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
