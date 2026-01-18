"""
LangGraph RAG agent with explicit nodes and edges.

Quality-First architecture:
- scope_guard → [portfolio/other] → ...
- Portfolio path: planner → retrieval (parallel) → merge → critic → normalizer → fact_bundler → answer → grounding → output
- Other path: simple_llm → END

Key features:
- Parallel retrieval (graph + search)
- Critic ALWAYS runs (quality focus)
- Deterministic answer path for simple intents
- Grounding verification with LLM rewrite
- Session memory via MemorySaver
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import RAGState

# Import all nodes
from app.agent.nodes.scope_guard import scope_guard_node
from app.agent.nodes.simple_llm import simple_llm_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.retrieval import graph_retriever_node, search_retriever_node
from app.agent.nodes.merge import merge_results_node
from app.agent.nodes.critic import critic_node
from app.agent.nodes.normalizer import normalizer_node
from app.agent.nodes.fact_bundler import fact_bundler_node
from app.agent.nodes.answer import answer_deterministic_node, answer_llm_node
from app.agent.nodes.grounding import grounding_verifier_node
from app.agent.nodes.rewrite import rewrite_llm_node
from app.agent.nodes.output import output_formatter_node

# Import routing functions
from app.agent.edges.routing import (
    route_scope,
    route_needs_search,
    route_answer,
    route_grounding,
)

logger = logging.getLogger(__name__)


def additional_search_node(state: RAGState) -> dict:
    """
    Additional search when critic determines more context is needed.

    Re-runs portfolio search with the critic's suggested query.
    """
    from app.agent.tools.portfolio_search_tool import execute_portfolio_search

    query = state.get("additional_search_query", "")
    question = state.get("question", "")
    existing_facts = state.get("merged_facts", [])

    if not query:
        query = question

    logger.info(f"AdditionalSearch: query={query[:50]}...")

    try:
        facts, sources, found, confidence, evidence = execute_portfolio_search(
            query=query,
            k=8,
        )

        # Merge with existing facts (avoid duplicates)
        from app.agent.planner.schemas import SourceInfo

        existing_source_ids = {f.source_id for f in existing_facts if f.source_id}
        new_facts = [f for f in facts if f.source_id not in existing_source_ids]

        merged_facts = existing_facts + new_facts

        logger.info(
            f"AdditionalSearch: found {len(new_facts)} new facts, "
            f"total {len(merged_facts)}"
        )

        return {
            "merged_facts": merged_facts,
            "retrieval_found": True if merged_facts else False,
        }

    except Exception as e:
        logger.error(f"AdditionalSearch error: {e}")
        return {}


def build_rag_graph():
    """
    Build the RAG LangGraph with nodes and edges.

    Graph structure:
    START
      │
      ▼
    scope_guard (deterministic)
      │
      ▼
    [route_scope]
      │
      ├─ portfolio ─────────────────────────────────────────┐
      │                                                      │
      └─ small_talk/off_topic/harmful ── simple_llm ── END  │
                                                             │
      ┌──────────────────────────────────────────────────────┘
      ▼
    planner (LLM #1)
      │
      ▼ (fan-out: parallel)
    ┌─────┴─────┐
    │           │
    graph_ret  search_ret  (deterministic)
    │           │
    └─────┬─────┘
          ▼ (fan-in)
    merge_results
      │
      ▼
    critic (LLM #2: ALWAYS for quality)
      │
      ▼
    [route_needs_search]
      │
      ├─ yes ─► additional_search ─┐
      │                            │
      └─ no ───────────────────────┤
                                   ▼
                            normalizer
                                   │
                                   ▼
                            fact_bundler
                                   │
                                   ▼
                            [route_answer]
                                   │
      ┌────────────────────────────┴────────────────────────┐
      │                                                      │
    answer_deterministic                              answer_llm (LLM #3)
      │                                                      │
      └────────────────────────┬─────────────────────────────┘
                               ▼
                        grounding_verifier
                               │
                               ▼
                        [route_grounding]
                               │
      ┌────────────────────────┴────────────────────────┐
      │                                                  │
    accept ─► output ─► END                          rewrite ─► rewrite_llm (LLM #4)
                                                              │
                                                              ▼
                                                          output ─► END

    Returns:
        Compiled StateGraph with checkpointer for session memory
    """
    # Create graph builder
    graph = StateGraph(RAGState)

    # === Add all nodes ===
    graph.add_node("scope_guard", scope_guard_node)
    graph.add_node("simple_llm", simple_llm_node)
    graph.add_node("planner", planner_node)
    graph.add_node("graph_retriever", graph_retriever_node)
    graph.add_node("search_retriever", search_retriever_node)
    graph.add_node("merge_results", merge_results_node)
    graph.add_node("critic", critic_node)
    graph.add_node("additional_search", additional_search_node)
    graph.add_node("normalizer", normalizer_node)
    graph.add_node("fact_bundler", fact_bundler_node)
    graph.add_node("answer_deterministic", answer_deterministic_node)
    graph.add_node("answer_llm", answer_llm_node)
    graph.add_node("grounding_verifier", grounding_verifier_node)
    graph.add_node("rewrite", rewrite_llm_node)
    graph.add_node("output", output_formatter_node)

    # === Set entry point ===
    graph.set_entry_point("scope_guard")

    # === Add edges ===

    # 1. Scope guard → route to planner or simple_llm
    graph.add_conditional_edges(
        "scope_guard",
        route_scope,
        {
            "planner": "planner",
            "simple_llm": "simple_llm",
        },
    )

    # 2. Simple LLM → END (for non-portfolio questions)
    graph.add_edge("simple_llm", END)

    # 3. Planner → parallel retrieval (fan-out)
    # Note: LangGraph handles parallel execution automatically
    # when the same source has multiple edges
    graph.add_edge("planner", "graph_retriever")
    graph.add_edge("planner", "search_retriever")

    # 4. Both retrievers → merge (fan-in)
    graph.add_edge("graph_retriever", "merge_results")
    graph.add_edge("search_retriever", "merge_results")

    # 5. Merge → critic (ALWAYS for quality)
    graph.add_edge("merge_results", "critic")

    # 6. Critic → route based on needs_additional_search
    graph.add_conditional_edges(
        "critic",
        route_needs_search,
        {
            "additional_search": "additional_search",
            "normalizer": "normalizer",
        },
    )

    # 7. Additional search → normalizer
    graph.add_edge("additional_search", "normalizer")

    # 8. Normalizer → fact_bundler
    graph.add_edge("normalizer", "fact_bundler")

    # 9. Fact bundler → route to answer type
    graph.add_conditional_edges(
        "fact_bundler",
        route_answer,
        {
            "answer_deterministic": "answer_deterministic",
            "answer_llm": "answer_llm",
        },
    )

    # 10. Both answer types → grounding verifier
    graph.add_edge("answer_deterministic", "grounding_verifier")
    graph.add_edge("answer_llm", "grounding_verifier")

    # 11. Grounding → route based on action
    graph.add_conditional_edges(
        "grounding_verifier",
        route_grounding,
        {
            "output": "output",
            "rewrite": "rewrite",
        },
    )

    # 12. Rewrite → output
    graph.add_edge("rewrite", "output")

    # 13. Output → END
    graph.add_edge("output", END)

    # === Compile with checkpointer for session memory ===
    checkpointer = MemorySaver()

    logger.info("Building RAG graph with Quality-First architecture")

    return graph.compile(checkpointer=checkpointer)


def build_agent_graph():
    """
    Legacy function name for compatibility.

    Returns the new node-based RAG graph.
    """
    return build_rag_graph()
