"""
Agent module - LangGraph agent and tools.

Contains:
- graph.py: LangGraph ReAct agent builder
- tools.py: v1 RAG tools
- tools_v2.py: v2 tools with query planning
- tools_v3.py: v3 full LLM pipeline (Planner + Executor + Answer)

Submodules:
- planner/: LLM-based query planning
- executor/: Plan execution and fact collection
- render/: Deterministic fact rendering
- answer/: LLM-based answer generation
- tools/: Tool wrappers for executor
"""
