"""
RAGState definition for LangGraph agent.

Central state TypedDict that flows through all nodes in the graph.
Based on the Quality-First architecture design.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.agent.critic.schemas import CriticDecision
from app.agent.planner.schemas import FactItem, SourceInfo
from app.agent.planner.schemas_v3 import (
    FactBundle,
    FactBundleItem,
    GroundingResult,
    QueryPlanV3,
)


class RAGState(TypedDict, total=False):
    """
    Central state for the RAG LangGraph agent.

    All nodes read from and write to this state.
    Uses total=False to allow partial updates.

    Flow:
    1. Input → scope_guard
    2. scope_guard → route (portfolio/small_talk/off_topic/harmful)
    3. portfolio path: planner → retrieval → merge → critic → normalizer → fact_bundler → answer → grounding → output
    4. other paths: simple_llm → output
    """

    # === Input (set at graph invocation) ===
    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    session_id: str

    # === Scope Guard Output ===
    in_scope: bool
    scope_category: Literal["portfolio", "small_talk", "off_topic", "harmful"]
    scope_reason: str
    suggested_prompts: list[str]

    # === Planner Output ===
    plan: QueryPlanV3 | None
    plan_confidence: float

    # === Retrieval Output (parallel: graph + search) ===
    graph_facts: list[FactItem]
    search_facts: list[FactItem]
    graph_sources: list[dict]  # Raw sources from graph retriever (merged later)
    search_sources: list[dict]  # Raw sources from search retriever (merged later)
    sources: list[SourceInfo]  # Final merged sources (set by merge_results_node)
    evidence_text: str
    retrieval_found: bool

    # === Merge Output ===
    merged_facts: list[FactItem]

    # === Critic Output ===
    critic_decision: CriticDecision | None
    needs_additional_search: bool
    additional_search_query: str

    # === Normalizer Output ===
    normalized_facts: list[FactBundleItem]
    removed_facts_count: int
    normalization_rules_applied: list[str]

    # === Fact Bundler Output ===
    fact_bundle: FactBundle | None

    # === Answer Output ===
    answer: str
    answer_is_deterministic: bool

    # === Grounding Output ===
    grounding_result: GroundingResult | None
    grounding_action: Literal["accept", "rewrite", "refuse"]

    # === Final Output ===
    final_response: dict[str, Any]

    # === Session Context (P0: persistent context between questions) ===
    last_company: str | None          # Last mentioned company (slug)
    last_project: str | None          # Last mentioned project (slug)
    last_technology: str | None       # Last mentioned technology
    context_entities: list[dict]      # All entities mentioned in session

    # === Rules Validator Output ===
    validated_entities: dict[str, str | None]  # Validated company/project from rules


def create_initial_state(
    question: str,
    session_id: str,
    messages: list[BaseMessage] | None = None,
) -> RAGState:
    """
    Create initial state for graph invocation.

    Args:
        question: User's question text
        session_id: Session ID for memory
        messages: Optional existing messages (for multi-turn)

    Returns:
        RAGState with input fields populated
    """
    from langchain_core.messages import HumanMessage

    initial_messages = messages or []
    if not any(
        isinstance(m, HumanMessage) and m.content == question
        for m in initial_messages
    ):
        initial_messages.append(HumanMessage(content=question))

    return RAGState(
        messages=initial_messages,
        question=question,
        session_id=session_id,
        # All other fields will be set by nodes
    )
