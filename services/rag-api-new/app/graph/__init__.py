"""
Graph module - граф знаний портфолио.

Предоставляет in-memory граф для структурированных запросов
к данным портфолио.
"""
from .schema import NodeType, EdgeType, GraphNode, GraphEdge
from .store import GraphStore, get_graph_store, reset_graph_store
from .builder import build_graph_from_export
from .query import graph_query

__all__ = [
    "NodeType",
    "EdgeType",
    "GraphNode",
    "GraphEdge",
    "GraphStore",
    "get_graph_store",
    "reset_graph_store",
    "build_graph_from_export",
    "graph_query",
]
