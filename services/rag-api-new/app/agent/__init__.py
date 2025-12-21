"""
Agent module - LangGraph agent and tools.

Contains:
- graph.py: LangGraph ReAct agent builder
- rag_tool.py: Full LLM pipeline (Planner + Executor + Answer)

Submodules:
- planner/: LLM-based query planning
- executor/: Plan execution and fact collection
- render/: Deterministic fact rendering
- answer/: LLM-based answer generation
- tools/: Tool wrappers for executor
"""
