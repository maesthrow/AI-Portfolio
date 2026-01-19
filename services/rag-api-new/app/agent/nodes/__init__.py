"""
LangGraph nodes for RAG agent.

Each node is a function that takes RAGState and returns partial state updates.

Simplified architecture (2 LLM):
1. scope_guard - Classifies question (portfolio/small_talk/off_topic/harmful)
2. simple_llm - Handles non-portfolio questions
3. planner - Creates QueryPlanV3 for portfolio questions (LLM #1)
4. rules_validator - Validates plan + injects session context
5. tool_executor - Executes chosen specialized tool
6. normalizer - Filters facts by intent/category
7. fact_bundler - Extracts entities for answer
8. answer_llm - Generates response (LLM #2)
9. session_updater - Updates last_company/project context
10. output - Formats final response

Legacy nodes (kept for rollback to 4-LLM architecture):
- retrieval (graph_retriever_node, search_retriever_node)
- merge (merge_results_node)
- critic (critic_node)
- grounding (grounding_verifier_node)
- rewrite (rewrite_llm_node)
- answer_deterministic_node
"""

# New simplified architecture nodes
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

# Legacy nodes (for backward compatibility with legacy graph)
from app.agent.nodes.retrieval import graph_retriever_node, search_retriever_node
from app.agent.nodes.merge import merge_results_node
from app.agent.nodes.critic import critic_node
from app.agent.nodes.answer import answer_deterministic_node
from app.agent.nodes.grounding import grounding_verifier_node
from app.agent.nodes.rewrite import rewrite_llm_node

__all__ = [
    # New architecture nodes
    "scope_guard_node",
    "simple_llm_node",
    "planner_node",
    "rules_validator_node",
    "tool_executor_node",
    "normalizer_node",
    "fact_bundler_node",
    "answer_llm_node",
    "session_updater_node",
    "output_formatter_node",
    # Legacy nodes
    "graph_retriever_node",
    "search_retriever_node",
    "merge_results_node",
    "critic_node",
    "answer_deterministic_node",
    "grounding_verifier_node",
    "rewrite_llm_node",
]
