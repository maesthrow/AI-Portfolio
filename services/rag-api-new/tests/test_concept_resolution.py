"""
Tests for concept → TechCategory resolution in graph queries.

When entity_key is not found as a technology/project node, the graph
checks CONCEPT_TO_CATEGORY mapping and delegates to
_projects_by_tech_category_query() instead of returning empty.

Covers spec 008-improve-concept-queries (FR-003, FR-006).
"""
from __future__ import annotations

import pytest

from app.graph.schema import NodeType, EdgeType, GraphNode, GraphEdge
from app.graph.store import reset_graph_store
from app.graph.query import _technologies_query, CONCEPT_TO_CATEGORY
from app.rag.search_types import Intent


# ============================================================
# Test data factory
# ============================================================

def _build_test_graph():
    """Build a minimal graph with technologies from different categories.

    Technologies:
        - Python (language)
        - LangChain (ml_framework)
        - LangGraph (ml_framework)
        - PyTorch (ml_framework)
        - RAG (concept)
        - ReAct (concept)
        - FastAPI (framework)

    Projects:
        - AI-Portfolio: LangChain, LangGraph, RAG, FastAPI
        - Нейросети: PyTorch
        - ReAct-Agent: LangGraph, ReAct
    """
    store = reset_graph_store()

    techs = [
        GraphNode("tech:python",    NodeType.TECHNOLOGY, "Python",    "python",    {"category": "language"}),
        GraphNode("tech:langchain", NodeType.TECHNOLOGY, "LangChain", "langchain", {"category": "ml_framework"}),
        GraphNode("tech:langgraph", NodeType.TECHNOLOGY, "LangGraph", "langgraph", {"category": "ml_framework"}),
        GraphNode("tech:pytorch",   NodeType.TECHNOLOGY, "PyTorch",   "pytorch",   {"category": "ml_framework"}),
        GraphNode("tech:rag",       NodeType.TECHNOLOGY, "RAG",       "rag",       {"category": "concept"}),
        GraphNode("tech:react",     NodeType.TECHNOLOGY, "ReAct",     "react",     {"category": "concept"}),
        GraphNode("tech:fastapi",   NodeType.TECHNOLOGY, "FastAPI",   "fastapi",   {"category": "framework"}),
    ]
    for t in techs:
        store.add_node(t)

    projects = [
        GraphNode("project:ai-portfolio", NodeType.PROJECT, "AI-Portfolio", "ai-portfolio", {
            "company_name": None,
            "domain": "AI",
            "period": "2024-present",
            "description_md": "RAG-based AI portfolio",
        }),
        GraphNode("project:neuronets", NodeType.PROJECT, "Нейросети", "neuronets", {
            "company_name": None,
            "domain": "ML",
            "period": "2023",
            "description_md": "Computer vision with PyTorch",
        }),
        GraphNode("project:react-agent", NodeType.PROJECT, "ReAct-Agent", "react-agent", {
            "company_name": None,
            "domain": "AI",
            "period": "2024",
            "description_md": "ReAct-based LLM agent",
        }),
    ]
    for p in projects:
        store.add_node(p)

    edges = [
        # AI-Portfolio
        GraphEdge("project:ai-portfolio", "tech:python",    EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:langchain", EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:langgraph", EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:rag",       EdgeType.USES),
        GraphEdge("project:ai-portfolio", "tech:fastapi",   EdgeType.USES),
        # Нейросети
        GraphEdge("project:neuronets", "tech:pytorch", EdgeType.USES),
        # ReAct-Agent
        GraphEdge("project:react-agent", "tech:langgraph", EdgeType.USES),
        GraphEdge("project:react-agent", "tech:react",     EdgeType.USES),
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
# Concept resolution: ML
# ============================================================

def test_concept_mapping_ml():
    """entity_key='machine-learning' → projects with ml_framework technologies."""
    result = _technologies_query("machine-learning")
    assert result.found is True
    assert result.intent == Intent.TECHNOLOGIES
    names = {item["project"] for item in result.items}
    # AI-Portfolio (LangChain, LangGraph), Нейросети (PyTorch), ReAct-Agent (LangGraph)
    assert "AI-Portfolio" in names
    assert "Нейросети" in names
    assert "ReAct-Agent" in names


def test_concept_mapping_ml_short():
    """entity_key='ml' → same as 'machine-learning'."""
    result = _technologies_query("ml")
    assert result.found is True
    names = {item["project"] for item in result.items}
    assert "AI-Portfolio" in names
    assert "Нейросети" in names


# ============================================================
# Concept resolution: AI Agents
# ============================================================

def test_concept_mapping_ai_agents():
    """entity_key='ai-agents' → projects with concept technologies (RAG, ReAct)."""
    result = _technologies_query("ai-agents")
    assert result.found is True
    names = {item["project"] for item in result.items}
    # AI-Portfolio uses RAG (concept), ReAct-Agent uses ReAct (concept)
    assert "AI-Portfolio" in names
    assert "ReAct-Agent" in names


def test_concept_mapping_ai_agent_singular():
    """entity_key='ai-agent' (singular) → same as 'ai-agents'."""
    result = _technologies_query("ai-agent")
    assert result.found is True
    names = {item["project"] for item in result.items}
    assert "AI-Portfolio" in names


# ============================================================
# Concept resolution: RAG
# ============================================================

def test_concept_mapping_rag():
    """entity_key='rag' resolves via concept mapping (not tech node slug).

    Note: 'rag' exists as both a technology node slug AND a concept mapping key.
    Since the technology node is found first by get_node_by_slug(), the concept
    mapping is NOT activated — the node lookup takes priority.
    """
    result = _technologies_query("rag")
    assert result.found is True
    # RAG is found as a technology node (slug='rag'), so returns projects USING RAG
    # This is the backward-compatible path via node lookup, NOT concept mapping
    names = {item.get("project") for item in result.items}
    assert "AI-Portfolio" in names


# ============================================================
# Backward compatibility (FR-006)
# ============================================================

def test_existing_technology_not_intercepted():
    """entity_key='python' → found as technology node, concept mapping NOT used."""
    result = _technologies_query("python")
    assert result.found is True
    # Python is a real technology node — returns items about Python usage
    # The result format differs from concept resolution (which uses _projects_by_tech_category_query)
    assert result.confidence == 0.9  # Technology node lookup confidence


def test_existing_project_not_intercepted():
    """entity_key='ai-portfolio' → found as project node, concept mapping NOT used."""
    result = _technologies_query("ai-portfolio")
    assert result.found is True
    # Returns technologies OF the project (not projects BY category)
    tech_names = {item.get("name") for item in result.items}
    assert "LangChain" in tech_names
    assert "FastAPI" in tech_names


# ============================================================
# Unknown concepts
# ============================================================

def test_concept_mapping_unknown():
    """entity_key='blockchain' → not in mapping, returns empty."""
    result = _technologies_query("blockchain")
    assert result.found is False
    assert result.items == []
    assert result.confidence == 0.0


def test_concept_mapping_devops():
    """entity_key='devops' → not in mapping (edge case from spec), returns empty."""
    result = _technologies_query("devops")
    assert result.found is False
    assert result.items == []


# ============================================================
# Case insensitivity
# ============================================================

def test_concept_mapping_case_insensitive():
    """entity_key='Machine-Learning' (mixed case) → still maps correctly."""
    result = _technologies_query("Machine-Learning")
    assert result.found is True
    names = {item["project"] for item in result.items}
    assert "AI-Portfolio" in names


def test_concept_mapping_uppercase():
    """entity_key='ML' (uppercase) → maps to ml_framework."""
    result = _technologies_query("ML")
    assert result.found is True
    names = {item["project"] for item in result.items}
    assert "AI-Portfolio" in names


# ============================================================
# CONCEPT_TO_CATEGORY dict integrity
# ============================================================

def test_mapping_dict_has_expected_entries():
    """CONCEPT_TO_CATEGORY contains all expected concept slugs."""
    assert "machine-learning" in CONCEPT_TO_CATEGORY
    assert "ml" in CONCEPT_TO_CATEGORY
    assert "ai-agents" in CONCEPT_TO_CATEGORY
    assert "ai-agent" in CONCEPT_TO_CATEGORY
    assert "rag" in CONCEPT_TO_CATEGORY
    assert "computer-vision" in CONCEPT_TO_CATEGORY
    assert "nlp" in CONCEPT_TO_CATEGORY


def test_mapping_values_are_valid_categories():
    """All CONCEPT_TO_CATEGORY values are valid TechCategory strings."""
    from app.agent.planner.schemas_v3 import TechCategory
    valid_categories = {tc.value for tc in TechCategory}
    for slug, category in CONCEPT_TO_CATEGORY.items():
        assert category in valid_categories, f"'{slug}' maps to invalid category '{category}'"
