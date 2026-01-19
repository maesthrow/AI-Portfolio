"""
Retrieval nodes for RAG agent.

Two parallel nodes:
- graph_retriever_node: Executes graph_query_tool based on plan
- search_retriever_node: Executes portfolio_search_tool based on plan

These nodes run in parallel (fan-out) and their results are merged
by merge_results_node (fan-in).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.planner.schemas import FactItem
from app.agent.tools.graph_query_tool import execute_graph_query
from app.agent.tools.portfolio_search_tool import execute_portfolio_search

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def graph_retriever_node(state: RAGState) -> dict:
    """
    Execute graph queries based on plan.

    Iterates through tool_calls in the plan and executes
    those targeting graph_query_tool.

    Args:
        state: Current RAGState with plan

    Returns:
        Partial state update with:
        - graph_facts: List of FactItem from graph queries
        - sources: List of source references (partial, merged later)
    """
    plan = state.get("plan")
    if not plan:
        logger.warning("GraphRetriever: no plan available")
        return {
            "graph_facts": [],
        }

    all_facts: list[FactItem] = []
    all_sources: list[dict] = []

    for tool_call in plan.tool_calls:
        if tool_call.tool != "graph_query_tool":
            continue

        args = tool_call.args
        intent = args.get("intent", "general_unstructured")
        entity_id = args.get("entity_id")
        tech_category = args.get("tech_category")
        scope = args.get("scope")
        company_id = args.get("company_id")
        project_id = args.get("project_id")
        limit = args.get("limit", 20)

        logger.info(
            f"GraphRetriever executing: intent={intent}, entity_id={entity_id}, "
            f"tech_category={tech_category}"
        )

        try:
            facts, sources, found, confidence = execute_graph_query(
                intent=intent,
                entity_id=entity_id,
                tech_category=tech_category,
                scope=scope,
                company_id=company_id,
                project_id=project_id,
                limit=limit,
            )

            all_facts.extend(facts)
            all_sources.extend(sources)

            logger.info(
                f"GraphRetriever result: facts={len(facts)}, found={found}, "
                f"confidence={confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"GraphRetriever error: {e}")

    # Note: sources are merged in merge_results_node to avoid concurrent updates
    return {
        "graph_facts": all_facts,
        "graph_sources": all_sources,  # Raw sources, will be processed in merge
    }


def search_retriever_node(state: RAGState) -> dict:
    """
    Execute portfolio search based on plan.

    Iterates through tool_calls in the plan and executes
    those targeting portfolio_search_tool.

    Also falls back to question-based search if no explicit
    search tool calls are present.

    Args:
        state: Current RAGState with plan and question

    Returns:
        Partial state update with:
        - search_facts: List of FactItem from searches
        - evidence_text: Raw evidence text for context
        - sources: List of source references (partial, merged later)
    """
    plan = state.get("plan")
    question = state.get("question", "")

    if not plan:
        logger.warning("SearchRetriever: no plan available")
        return {
            "search_facts": [],
            "evidence_text": "",
        }

    all_facts: list[FactItem] = []
    all_sources: list[dict] = []
    evidence_texts: list[str] = []
    executed_search = False

    for tool_call in plan.tool_calls:
        if tool_call.tool != "portfolio_search_tool":
            continue

        executed_search = True
        args = tool_call.args
        query = args.get("query", question)
        k = args.get("k", 8)
        allowed_types = args.get("allowed_types")
        filters = args.get("filters")
        min_score = args.get("min_score")
        tech_category = args.get("tech_category")

        logger.info(
            f"SearchRetriever executing: query={query[:50]}..., k={k}, "
            f"types={allowed_types}, tech_category={tech_category}"
        )

        try:
            facts, sources, found, confidence, evidence = execute_portfolio_search(
                query=query,
                k=k,
                allowed_types=allowed_types,
                filters=filters,
                min_score=min_score,
                tech_category=tech_category,
            )

            all_facts.extend(facts)
            all_sources.extend(sources)
            if evidence:
                evidence_texts.append(evidence)

            logger.info(
                f"SearchRetriever result: facts={len(facts)}, found={found}, "
                f"confidence={confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"SearchRetriever error: {e}")

    # If no search tool calls, but we have a question, do a fallback search
    # P0 FIX: Use entity-aware fallback query when plan has entities
    if not executed_search and question:
        fallback_query = question

        # Try to build entity-aware fallback query from plan entities
        if plan and hasattr(plan, "entities") and plan.entities:
            for entity in plan.entities:
                entity_type = ""
                entity_name = ""

                # Handle both dict and object access patterns
                if isinstance(entity, dict):
                    entity_type = entity.get("type", "")
                    entity_name = entity.get("name", "") or entity.get("id", "").split(":")[-1]
                elif hasattr(entity, "type"):
                    entity_type = getattr(entity, "type", "")
                    entity_name = getattr(entity, "name", "") or getattr(entity, "id", "").split(":")[-1]

                if entity_type == "company" and entity_name:
                    fallback_query = f"проекты {entity_name}"
                    logger.info(
                        "SearchRetriever: entity-aware fallback, query='%s' (company=%s)",
                        fallback_query,
                        entity_name,
                    )
                    break
                elif entity_type == "project" and entity_name:
                    fallback_query = f"проект {entity_name}"
                    logger.info(
                        "SearchRetriever: entity-aware fallback, query='%s' (project=%s)",
                        fallback_query,
                        entity_name,
                    )
                    break

        logger.info("SearchRetriever: fallback search with query='%s'", fallback_query[:50])
        try:
            facts, sources, found, confidence, evidence = execute_portfolio_search(
                query=fallback_query,
                k=8,
            )
            all_facts.extend(facts)
            all_sources.extend(sources)
            if evidence:
                evidence_texts.append(evidence)

        except Exception as e:
            logger.error(f"SearchRetriever fallback error: {e}")

    # Note: sources are merged in merge_results_node to avoid concurrent updates
    return {
        "search_facts": all_facts,
        "evidence_text": "\n\n".join(evidence_texts),
        "search_sources": all_sources,  # Raw sources, will be processed in merge
    }
