"""
LangGraph nodes for RAG agent.

Each node is a function that takes RAGState and returns partial state updates.
Nodes are organized by their role in the pipeline:

1. scope_guard - Classifies question (portfolio/small_talk/off_topic/harmful)
2. simple_llm - Handles non-portfolio questions
3. planner - Creates QueryPlanV3 for portfolio questions
4. retrieval - Parallel graph_query + portfolio_search
5. merge - Combines and deduplicates facts
6. critic - Checks result sufficiency
7. normalizer - Filters facts by intent/category
8. fact_bundler - Extracts entities for grounding
9. answer - Generates response (deterministic or LLM)
10. grounding - Verifies answer against facts
11. rewrite - Rewrites answer if hallucinations detected
12. output - Formats final response
"""

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

__all__ = [
    "scope_guard_node",
    "simple_llm_node",
    "planner_node",
    "graph_retriever_node",
    "search_retriever_node",
    "merge_results_node",
    "critic_node",
    "normalizer_node",
    "fact_bundler_node",
    "answer_deterministic_node",
    "answer_llm_node",
    "grounding_verifier_node",
    "rewrite_llm_node",
    "output_formatter_node",
]
