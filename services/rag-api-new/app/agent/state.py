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

from app.agent.planner.schemas import FactItem, SourceInfo
from app.agent.planner.schemas_v3 import (
    FactBundle,
    FactBundleItem,
    QueryPlanV3,
)


class RAGState(TypedDict, total=False):
    """
    Central state for the RAG LangGraph agent.

    All nodes read from and write to this state.
    Uses total=False to allow partial updates.

    IMPORTANT: Field Lifecycle
    ==========================
    Fields are classified into two categories:

    1. PER-REQUEST fields: Reset at the start of each request pipeline.
       These fields contain data specific to the current question and
       MUST NOT leak between requests. Cleared by state_cleanup_node.

    2. PERSISTENT fields: Maintained across requests within a session.
       These fields provide context continuity (e.g., "там" referring
       to previous company). Persisted by LangGraph MemorySaver.

    Flow:
    1. Input → state_cleanup (clears per-request fields)
    2. state_cleanup → scope_guard
    3. scope_guard → route (portfolio/small_talk/off_topic/harmful)
    4. portfolio path: planner → rules_validator → tool_executor → normalizer → answer → output
    5. other paths: simple_llm → output
    """

    # =====================================================================
    # INPUT FIELDS (set at graph invocation)
    # =====================================================================
    messages: Annotated[list[BaseMessage], add_messages]  # PERSISTENT: conversation history
    question: str              # PER-REQUEST: current question
    session_id: str            # PERSISTENT: session identifier

    # =====================================================================
    # PER-REQUEST FIELDS (cleared at start of each request)
    # These fields are specific to the current question and must not
    # leak data between requests.
    # =====================================================================

    # --- Scope Guard Output ---
    in_scope: bool
    scope_category: Literal["portfolio", "small_talk", "off_topic", "harmful"]
    scope_reason: str
    suggested_prompts: list[str]

    # --- Planner Output ---
    plan: QueryPlanV3 | None
    plan_confidence: float

    # --- Retrieval/Tool Executor Output ---
    sources: list[SourceInfo]
    evidence_text: str              # CRITICAL: must be cleared to prevent state pollution
    retrieval_found: bool
    merged_facts: list[FactItem]

    # --- Normalizer Output ---
    normalized_facts: list[FactBundleItem]
    removed_facts_count: int
    normalization_rules_applied: list[str]

    # --- Fact Bundler Output ---
    fact_bundle: FactBundle | None

    # --- Answer Output ---
    answer: str
    answer_is_deterministic: bool

    # --- Final Output ---
    final_response: dict[str, Any]

    # --- Rules Validator Output ---
    validated_entities: dict[str, str | None]

    # =====================================================================
    # PERSISTENT FIELDS (maintained across requests in session)
    # These fields provide context continuity for follow-up questions
    # like "а там?", "какой стек?", etc.
    # =====================================================================

    # --- Session Context ---
    last_company: str | None          # Last mentioned company (slug)
    last_project: str | None          # Last mentioned project (slug)
    last_technology: str | None       # Last mentioned technology
    context_entities: list[dict]      # All entities mentioned in session


# =========================================================================
# PER-REQUEST FIELD CLEANUP
# =========================================================================
# These fields must be explicitly cleared at the start of each request
# to prevent state pollution from previous requests in the same session.

PER_REQUEST_FIELDS_CLEANUP: dict[str, Any] = {
    # Scope Guard
    "in_scope": None,
    "scope_category": None,
    "scope_reason": "",
    "suggested_prompts": [],

    # Planner
    "plan": None,
    "plan_confidence": 0.0,

    # Retrieval/Tool Executor - CRITICAL: evidence_text was causing state pollution
    "sources": [],
    "evidence_text": "",  # MUST be cleared to prevent contamination
    "retrieval_found": False,
    "merged_facts": [],

    # Normalizer
    "normalized_facts": [],
    "removed_facts_count": 0,
    "normalization_rules_applied": [],

    # Fact Bundler
    "fact_bundle": None,

    # Answer
    "answer": "",
    "answer_is_deterministic": False,

    # Final
    "final_response": {},

    # Rules Validator
    "validated_entities": {},
}


def get_cleanup_state() -> dict[str, Any]:
    """
    Get a state update dict that clears all per-request fields.

    Use this at the start of each request pipeline to prevent
    state pollution from previous requests.

    Returns:
        Dict with all per-request fields set to their default values
    """
    return PER_REQUEST_FIELDS_CLEANUP.copy()


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
