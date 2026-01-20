"""
LangGraph nodes for RAG agent.

Each node is a function that takes RAGState and returns partial state updates.

Simplified architecture (2 LLM):
0. state_cleanup - Clears per-request fields (MUST be first to prevent state pollution)
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
"""

from app.agent.nodes.state_cleanup import state_cleanup_node
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

__all__ = [
    "state_cleanup_node",
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
]
