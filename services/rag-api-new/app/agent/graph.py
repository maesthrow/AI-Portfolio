"""
LangGraph RAG agent with simplified 2-LLM architecture.

Simplified Quality-Focused architecture:
- scope_guard -> [portfolio/other] -> ...
- Portfolio path: planner -> rules_validator -> tool_executor -> normalizer -> answer_llm -> session_updater -> output
- Other path: simple_llm -> END

Key features:
- 2 LLM calls only (Planner + Answer) instead of 4
- Rules-based validation and entity extraction
- Specialized tools (get_company_projects, get_project_details, get_technologies, search_portfolio)
- Session context persistence (last_company, last_project)
- Sequential execution (no parallel retrieval)
- Session memory via MemorySaver
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import RAGState

# Import nodes
from app.agent.nodes.scope_guard import scope_guard_node
from app.agent.nodes.simple_llm import simple_llm_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.rules_validator import rules_validator_node
from app.agent.nodes.tool_executor import tool_executor_node
from app.agent.nodes.normalizer import normalizer_node
from app.agent.nodes.fact_bundler import fact_bundler_node
from app.agent.nodes.answer import answer_llm_node
from app.agent.nodes.session_updater import session_updater_node
from app.agent.nodes.output import output_formatter_node

# Import routing functions
from app.agent.edges.routing import route_scope

logger = logging.getLogger(__name__)


def build_rag_graph():
    """
    Build the simplified RAG LangGraph with nodes and edges.

    Graph structure:
    START
      |
      v
    scope_guard (deterministic)
      |
      v
    [route_scope]
      |
      +-- portfolio -----------------------------------------------+
      |                                                            |
      +-- small_talk/off_topic/harmful --> simple_llm --> END      |
                                                                   |
      +------------------------------------------------------------+
      v
    planner (LLM #1) <-- Chooses tool + extracts entities
      |
      v
    rules_validator (deterministic) <-- Validates + augments with session context
      |
      v
    tool_executor (deterministic) <-- Executes chosen tool
      |
      +-- get_company_projects(company_name) --> projects[]
      +-- get_project_details(project_name) --> project + techs + achievements
      +-- get_technologies(project_name | category) --> technologies[]
      +-- search_portfolio(query) --> documents[]
      |
      v
    normalizer (deterministic) <-- Entity scope filtering
      |
      v
    fact_bundler (deterministic) <-- Prepares facts for answer
      |
      v
    answer_llm (LLM #2) <-- Generates response
      |
      v
    session_updater (deterministic) <-- Updates last_company/project
      |
      v
    output --> END

    REMOVED from old architecture:
    - critic (LLM) - replaced by rules_validator
    - grounding_verifier (deterministic) - removed
    - rewrite_llm (LLM) - removed
    - additional_search - integrated into tool_executor fallback
    - parallel retrieval - replaced by sequential tool_executor

    Returns:
        Compiled StateGraph with checkpointer for session memory
    """
    # Create graph builder
    graph = StateGraph(RAGState)

    # === Add nodes ===
    graph.add_node("scope_guard", scope_guard_node)
    graph.add_node("simple_llm", simple_llm_node)
    graph.add_node("planner", planner_node)           # LLM #1
    graph.add_node("rules_validator", rules_validator_node)  # NEW: deterministic
    graph.add_node("tool_executor", tool_executor_node)      # NEW: replaces retrieval
    graph.add_node("normalizer", normalizer_node)
    graph.add_node("fact_bundler", fact_bundler_node)
    graph.add_node("answer_llm", answer_llm_node)     # LLM #2
    graph.add_node("session_updater", session_updater_node)  # NEW: session context
    graph.add_node("output", output_formatter_node)

    # === Set entry point ===
    graph.set_entry_point("scope_guard")

    # === Add edges ===

    # 1. Scope guard -> route to planner or simple_llm
    graph.add_conditional_edges(
        "scope_guard",
        route_scope,
        {
            "planner": "planner",
            "simple_llm": "simple_llm",
        },
    )

    # 2. Simple LLM -> END (for non-portfolio questions)
    graph.add_edge("simple_llm", END)

    # 3. Main pipeline (sequential)
    graph.add_edge("planner", "rules_validator")
    graph.add_edge("rules_validator", "tool_executor")
    graph.add_edge("tool_executor", "normalizer")
    graph.add_edge("normalizer", "fact_bundler")
    graph.add_edge("fact_bundler", "answer_llm")
    graph.add_edge("answer_llm", "session_updater")
    graph.add_edge("session_updater", "output")
    graph.add_edge("output", END)

    # === Compile with checkpointer for session memory ===
    checkpointer = MemorySaver()

    logger.info("Building simplified RAG graph (2 LLM architecture)")

    return graph.compile(checkpointer=checkpointer)


def build_agent_graph():
    """
    Legacy function name for compatibility.

    Returns the new simplified RAG graph.
    """
    return build_rag_graph()


# === Legacy graph builder (kept for rollback if needed) ===

def build_rag_graph_legacy():
    """
    Build the legacy RAG graph with 4 LLM calls.

    DEPRECATED: Use build_rag_graph() for new simplified architecture.

    This function is kept for rollback purposes only.
    """
    from app.agent.nodes.retrieval import graph_retriever_node, search_retriever_node
    from app.agent.nodes.merge import merge_results_node
    from app.agent.nodes.critic import critic_node
    from app.agent.nodes.answer import answer_deterministic_node
    from app.agent.nodes.grounding import grounding_verifier_node
    from app.agent.nodes.rewrite import rewrite_llm_node
    from app.agent.edges.routing import route_needs_search, route_answer, route_grounding

    graph = StateGraph(RAGState)

    # Add all nodes (legacy)
    graph.add_node("scope_guard", scope_guard_node)
    graph.add_node("simple_llm", simple_llm_node)
    graph.add_node("planner", planner_node)
    graph.add_node("graph_retriever", graph_retriever_node)
    graph.add_node("search_retriever", search_retriever_node)
    graph.add_node("merge_results", merge_results_node)
    graph.add_node("critic", critic_node)
    graph.add_node("normalizer", normalizer_node)
    graph.add_node("fact_bundler", fact_bundler_node)
    graph.add_node("answer_deterministic", answer_deterministic_node)
    graph.add_node("answer_llm", answer_llm_node)
    graph.add_node("grounding_verifier", grounding_verifier_node)
    graph.add_node("rewrite", rewrite_llm_node)
    graph.add_node("output", output_formatter_node)

    graph.set_entry_point("scope_guard")

    # Legacy edges
    graph.add_conditional_edges("scope_guard", route_scope, {
        "planner": "planner",
        "simple_llm": "simple_llm",
    })
    graph.add_edge("simple_llm", END)
    graph.add_edge("planner", "graph_retriever")
    graph.add_edge("planner", "search_retriever")
    graph.add_edge("graph_retriever", "merge_results")
    graph.add_edge("search_retriever", "merge_results")
    graph.add_edge("merge_results", "critic")
    graph.add_conditional_edges("critic", route_needs_search, {
        "additional_search": "additional_search",
        "normalizer": "normalizer",
    })
    graph.add_edge("normalizer", "fact_bundler")
    graph.add_conditional_edges("fact_bundler", route_answer, {
        "answer_deterministic": "answer_deterministic",
        "answer_llm": "answer_llm",
    })
    graph.add_edge("answer_deterministic", "grounding_verifier")
    graph.add_edge("answer_llm", "grounding_verifier")
    graph.add_conditional_edges("grounding_verifier", route_grounding, {
        "output": "output",
        "rewrite": "rewrite",
    })
    graph.add_edge("rewrite", "output")
    graph.add_edge("output", END)

    checkpointer = MemorySaver()
    logger.info("Building LEGACY RAG graph (4 LLM architecture)")

    return graph.compile(checkpointer=checkpointer)
