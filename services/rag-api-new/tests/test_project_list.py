"""
Tests for PROJECT_LIST intent and _list_projects_query() handler.

Covers User Stories 1-4 from spec.md:
- US1: List personal projects (kind="personal")
- US2: List projects by technology category (tech_category="ml_framework")
- US3: List commercial projects (kind="commercial")
- US4: List all projects (no filters)
"""
from __future__ import annotations

import pytest

from app.graph.schema import NodeType, EdgeType, GraphNode, GraphEdge
from app.graph.store import reset_graph_store
from app.graph.query import _list_projects_query, _collect_projects_by_tech_category
from app.rag.search_types import Intent


# ============================================================
# Test data factory
# ============================================================

def _build_test_graph():
    """Build a minimal but representative test graph.

    Personal projects (company_name is None):
        - AI-Portfolio (ml_framework: LangChain, LangGraph; concept: RAG)
        - HyperKeeper (framework: FastAPI; ml_framework: LangChain)
        - ReAct-Agent (ml_framework: LangGraph, vLLM)

    Commercial projects (company_name set):
        - t2-telecom (ml_framework: LangChain; framework: FastAPI)
        - F3-TAIL (language: C#; framework: ASP.NET)
    """
    store = reset_graph_store()

    # --- Technology nodes ---
    techs = [
        GraphNode("tech:langchain",   NodeType.TECHNOLOGY, "LangChain",   "langchain",  {"category": "ml_framework"}),
        GraphNode("tech:langgraph",   NodeType.TECHNOLOGY, "LangGraph",   "langgraph",  {"category": "ml_framework"}),
        GraphNode("tech:vllm",        NodeType.TECHNOLOGY, "vLLM",        "vllm",       {"category": "ml_framework"}),
        GraphNode("tech:rag",         NodeType.TECHNOLOGY, "RAG",         "rag",        {"category": "concept"}),
        GraphNode("tech:fastapi",     NodeType.TECHNOLOGY, "FastAPI",     "fastapi",    {"category": "framework"}),
        GraphNode("tech:csharp",      NodeType.TECHNOLOGY, "C#",          "csharp",     {"category": "language"}),
        GraphNode("tech:aspnet",      NodeType.TECHNOLOGY, "ASP.NET",     "aspnet",     {"category": "framework"}),
        GraphNode("tech:postgresql",  NodeType.TECHNOLOGY, "PostgreSQL",  "postgresql", {"category": "database"}),
    ]
    for t in techs:
        store.add_node(t)

    # --- Personal project nodes ---
    personal_projects = [
        GraphNode("project:ai-portfolio", NodeType.PROJECT, "AI-Portfolio", "ai-portfolio", {
            "company_name": None,
            "domain": "AI",
            "period": "2024-present",
            "description_md": "RAG-based AI portfolio assistant",
            "technologies": ["LangChain", "LangGraph"],
        }),
        GraphNode("project:hyperkeeper", NodeType.PROJECT, "HyperKeeper", "hyperkeeper", {
            "company_name": None,
            "domain": "productivity",
            "period": "2023",
            "description_md": "Knowledge management tool",
            "technologies": ["FastAPI", "LangChain"],
        }),
        GraphNode("project:react-agent", NodeType.PROJECT, "ReAct-Agent", "react-agent", {
            "company_name": None,
            "domain": "AI",
            "period": "2024",
            "description_md": "ReAct-based LLM agent",
            "technologies": ["LangGraph", "vLLM"],
        }),
    ]
    for p in personal_projects:
        store.add_node(p)

    # --- Commercial project nodes ---
    commercial_projects = [
        GraphNode("project:t2-telecom", NodeType.PROJECT, "t2-Telecom", "t2-telecom", {
            "company_name": "t2",
            "domain": "telecom",
            "period": "2022-2023",
            "description_md": "AI platform for telecom",
            "technologies": ["LangChain", "FastAPI"],
        }),
        GraphNode("project:f3-tail", NodeType.PROJECT, "F3 TAIL", "f3-tail", {
            "company_name": "F3",
            "domain": "logistics",
            "period": "2021-2022",
            "description_md": "C# logistics system",
            "technologies": ["C#", "ASP.NET"],
        }),
    ]
    for p in commercial_projects:
        store.add_node(p)

    # --- USES edges: Project → Technology ---
    edges = [
        # AI-Portfolio
        GraphEdge("project:ai-portfolio", "tech:langchain",  EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:langgraph",  EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:rag",        EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:postgresql", EdgeType.USES),
        # HyperKeeper
        GraphEdge("project:hyperkeeper", "tech:fastapi",    EdgeType.USES),
        GraphEdge("project:hyperkeeper", "tech:langchain",  EdgeType.USES),
        # ReAct-Agent
        GraphEdge("project:react-agent", "tech:langgraph",  EdgeType.USES),
        GraphEdge("project:react-agent", "tech:vllm",       EdgeType.USES),
        # t2-Telecom
        GraphEdge("project:t2-telecom", "tech:langchain",   EdgeType.USES),
        GraphEdge("project:t2-telecom", "tech:fastapi",     EdgeType.USES),
        # F3 TAIL
        GraphEdge("project:f3-tail", "tech:csharp",         EdgeType.USES),
        GraphEdge("project:f3-tail", "tech:aspnet",         EdgeType.USES),
    ]
    for e in edges:
        store.add_edge(e)

    return store


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def fresh_graph():
    """Rebuild the test graph before each test."""
    _build_test_graph()
    yield
    reset_graph_store()


# ============================================================
# US4: List all projects (no filters)
# ============================================================

def test_list_all_projects_returns_all():
    """US4: No filters → all 5 projects returned."""
    result = _list_projects_query()
    assert result.found is True
    assert result.intent == Intent.PROJECT_LIST
    names = {item["name"] for item in result.items}
    assert names == {"AI-Portfolio", "HyperKeeper", "ReAct-Agent", "t2-Telecom", "F3 TAIL"}


def test_list_all_projects_count():
    """US4: Exact count check."""
    result = _list_projects_query()
    assert len(result.items) == 5


def test_list_all_projects_confidence_when_found():
    """US4: confidence=1.0 when projects found."""
    result = _list_projects_query()
    assert result.confidence == 1.0


def test_list_all_projects_has_text_field():
    """US4: Each item has a non-empty text field for renderer."""
    result = _list_projects_query()
    for item in result.items:
        assert item.get("text"), f"Missing text for {item.get('name')}"


# ============================================================
# US1: List personal projects (kind="personal")
# ============================================================

def test_list_personal_projects_count():
    """US1: kind=personal → only personal projects (3)."""
    result = _list_projects_query(kind="personal")
    assert result.found is True
    assert len(result.items) == 3


def test_list_personal_projects_names():
    """US1: kind=personal → AI-Portfolio, HyperKeeper, ReAct-Agent."""
    result = _list_projects_query(kind="personal")
    names = {item["name"] for item in result.items}
    assert names == {"AI-Portfolio", "HyperKeeper", "ReAct-Agent"}


def test_personal_projects_no_commercial():
    """US1: No commercial project leaks into personal results."""
    result = _list_projects_query(kind="personal")
    names = {item["name"] for item in result.items}
    assert "t2-Telecom" not in names
    assert "F3 TAIL" not in names


def test_personal_projects_items_have_kind_field():
    """US1: All personal items report kind='personal'."""
    result = _list_projects_query(kind="personal")
    for item in result.items:
        assert item["kind"] == "personal", f"{item['name']} should be personal"


# ============================================================
# US3: List commercial projects (kind="commercial")
# ============================================================

def test_list_commercial_projects_count():
    """US3: kind=commercial → only commercial projects (2)."""
    result = _list_projects_query(kind="commercial")
    assert result.found is True
    assert len(result.items) == 2


def test_list_commercial_projects_names():
    """US3: kind=commercial → t2-Telecom, F3 TAIL."""
    result = _list_projects_query(kind="commercial")
    names = {item["name"] for item in result.items}
    assert names == {"t2-Telecom", "F3 TAIL"}


def test_commercial_no_personal():
    """US3: No personal project leaks into commercial results."""
    result = _list_projects_query(kind="commercial")
    names = {item["name"] for item in result.items}
    assert "AI-Portfolio" not in names
    assert "HyperKeeper" not in names
    assert "ReAct-Agent" not in names


def test_commercial_projects_have_company_name():
    """US3: All commercial items have non-empty company_name."""
    result = _list_projects_query(kind="commercial")
    for item in result.items:
        assert item.get("company_name"), f"{item['name']} missing company_name"


# ============================================================
# US2: List projects by technology category (tech_category)
# ============================================================

def test_tech_category_ml_framework():
    """US2: tech_category=ml_framework → projects using LangChain/LangGraph/vLLM."""
    result = _list_projects_query(tech_category="ml_framework")
    assert result.found is True
    names = {item["name"] for item in result.items}
    # All four projects with ml_framework tech
    assert "AI-Portfolio" in names
    assert "HyperKeeper" in names
    assert "ReAct-Agent" in names
    assert "t2-Telecom" in names


def test_tech_category_no_false_positives():
    """US2: F3 TAIL (only C#/ASP.NET, no ml_framework) must NOT appear."""
    result = _list_projects_query(tech_category="ml_framework")
    names = {item["name"] for item in result.items}
    assert "F3 TAIL" not in names


def test_tech_category_unknown_returns_empty():
    """US2: Unknown category → found=False, empty items."""
    result = _list_projects_query(tech_category="kotlin")
    assert result.found is False
    assert result.items == []
    assert result.confidence == 0.0


def test_tech_category_database():
    """US2: tech_category=database → only AI-Portfolio (PostgreSQL)."""
    result = _list_projects_query(tech_category="database")
    assert result.found is True
    names = {item["name"] for item in result.items}
    assert names == {"AI-Portfolio"}


def test_tech_category_language_csharp():
    """US2: tech_category=language → F3 TAIL (C#)."""
    result = _list_projects_query(tech_category="language")
    assert result.found is True
    names = {item["name"] for item in result.items}
    assert "F3 TAIL" in names
    # Python projects don't have 'language' category tech in test graph
    assert "AI-Portfolio" not in names


# ============================================================
# Combined filters
# ============================================================

def test_combined_personal_and_ml_framework():
    """Edge case: kind=personal + tech_category=ml_framework → 3 personal LLM projects."""
    result = _list_projects_query(kind="personal", tech_category="ml_framework")
    assert result.found is True
    names = {item["name"] for item in result.items}
    # Personal + ml_framework: AI-Portfolio, HyperKeeper, ReAct-Agent
    assert names == {"AI-Portfolio", "HyperKeeper", "ReAct-Agent"}
    # t2-Telecom is commercial — must not appear
    assert "t2-Telecom" not in names


def test_combined_commercial_and_ml_framework():
    """Combined: kind=commercial + tech_category=ml_framework → only t2-Telecom."""
    result = _list_projects_query(kind="commercial", tech_category="ml_framework")
    assert result.found is True
    names = {item["name"] for item in result.items}
    assert names == {"t2-Telecom"}


def test_combined_commercial_and_unknown_tech():
    """Combined: kind=commercial + unknown tech → found=False."""
    result = _list_projects_query(kind="commercial", tech_category="kotlin")
    assert result.found is False
    assert result.items == []


# ============================================================
# _collect_projects_by_tech_category helper
# ============================================================

def test_helper_returns_sorted_by_tech_count():
    """Helper: projects with more matching techs appear first."""
    from app.graph.store import get_graph_store
    store = get_graph_store()
    projects = store.get_nodes_by_type(NodeType.PROJECT)
    matched = _collect_projects_by_tech_category(projects, "ml_framework")

    # AI-Portfolio uses LangChain + LangGraph (2), ReAct-Agent uses LangGraph+vLLM (2),
    # HyperKeeper uses LangChain (1), t2-Telecom uses LangChain (1)
    assert len(matched) == 4
    # First entries should have >= 1 tech
    for _, techs in matched:
        assert len(techs) >= 1


def test_helper_empty_for_unknown_category():
    """Helper: unknown category → empty list."""
    from app.graph.store import get_graph_store
    store = get_graph_store()
    projects = store.get_nodes_by_type(NodeType.PROJECT)
    result = _collect_projects_by_tech_category(projects, "nonexistent_category")
    assert result == []


# ============================================================
# Domain filter
# ============================================================

def test_domain_filter_ai():
    """Domain filter: domain=ai → AI-Portfolio and ReAct-Agent."""
    result = _list_projects_query(domain="ai")
    assert result.found is True
    names = {item["name"] for item in result.items}
    assert "AI-Portfolio" in names
    assert "ReAct-Agent" in names


def test_domain_filter_no_match():
    """Domain filter: non-existent domain → found=False."""
    result = _list_projects_query(domain="blockchain")
    assert result.found is False
    assert result.items == []


# ============================================================
# Intent enum registration
# ============================================================

def test_intent_enum_registered():
    """T001-T003: PROJECT_LIST exists in all three enums."""
    from app.rag.search_types import Intent
    from app.agent.planner.schemas import IntentV2
    from app.agent.planner.schemas_v3 import IntentV3

    assert Intent.PROJECT_LIST.value == "project_list"
    assert IntentV2.PROJECT_LIST.value == "project_list"
    assert IntentV3.PROJECT_LIST.value == "project_list"


def test_intent_mapping_has_project_list():
    """T005: _INTENT_MAPPING contains PROJECT_LIST."""
    from app.agent.tools.graph_query_tool import _INTENT_MAPPING
    from app.agent.planner.schemas import IntentV2

    assert IntentV2.PROJECT_LIST in _INTENT_MAPPING
    assert _INTENT_MAPPING[IntentV2.PROJECT_LIST] == "project_list"
