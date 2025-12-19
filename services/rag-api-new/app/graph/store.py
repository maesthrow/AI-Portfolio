"""
GraphStore - in-memory хранилище графа знаний.

Реализует граф на основе adjacency lists (списков смежности).
Без внешних зависимостей, достаточно для ~1000 узлов.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from .schema import NodeType, EdgeType, GraphNode, GraphEdge


class GraphStore:
    """
    In-memory граф знаний на основе adjacency lists.

    Thread-safe для чтения. Записи должны быть атомарными
    (полное перестроение при инжесте).
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._outgoing: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._incoming: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._by_type: Dict[NodeType, List[str]] = defaultdict(list)
        self._by_slug: Dict[str, str] = {}  # slug -> node_id

    def add_node(self, node: GraphNode) -> None:
        """Добавить узел в граф."""
        self._nodes[node.id] = node
        self._by_type[node.type].append(node.id)
        self._by_slug[node.slug] = node.id

    def add_edge(self, edge: GraphEdge) -> None:
        """Добавить ребро в граф."""
        self._edges.append(edge)
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Получить узел по ID."""
        return self._nodes.get(node_id)

    def get_node_by_slug(self, slug: str) -> Optional[GraphNode]:
        """Получить узел по slug."""
        node_id = self._by_slug.get(slug)
        return self._nodes.get(node_id) if node_id else None

    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Получить все узлы указанного типа."""
        return [self._nodes[nid] for nid in self._by_type.get(node_type, [])
                if nid in self._nodes]

    def get_outgoing_edges(
        self,
        node_id: str,
        edge_type: Optional[EdgeType] = None
    ) -> List[GraphEdge]:
        """Получить исходящие рёбра узла."""
        edges = self._outgoing.get(node_id, [])
        if edge_type:
            return [e for e in edges if e.type == edge_type]
        return list(edges)

    def get_incoming_edges(
        self,
        node_id: str,
        edge_type: Optional[EdgeType] = None
    ) -> List[GraphEdge]:
        """Получить входящие рёбра узла."""
        edges = self._incoming.get(node_id, [])
        if edge_type:
            return [e for e in edges if e.type == edge_type]
        return list(edges)

    def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[Set[EdgeType]] = None
    ) -> List[GraphNode]:
        """Получить соседние узлы (по исходящим рёбрам)."""
        edges = self._outgoing.get(node_id, [])
        if edge_types:
            edges = [e for e in edges if e.type in edge_types]
        return [self._nodes[e.target_id] for e in edges
                if e.target_id in self._nodes]

    def traverse(
        self,
        start_id: str,
        edge_types: Set[EdgeType],
        max_depth: int = 2
    ) -> List[GraphNode]:
        """
        BFS-обход графа от стартового узла.

        Args:
            start_id: ID стартового узла
            edge_types: Типы рёбер для обхода
            max_depth: Максимальная глубина

        Returns:
            Список узлов (без стартового)
        """
        visited: Set[str] = {start_id}
        result: List[GraphNode] = []
        frontier: List[tuple[str, int]] = [(start_id, 0)]

        while frontier:
            node_id, depth = frontier.pop(0)

            if depth > 0:
                node = self._nodes.get(node_id)
                if node:
                    result.append(node)

            if depth < max_depth:
                for edge in self._outgoing.get(node_id, []):
                    if edge.type in edge_types and edge.target_id not in visited:
                        visited.add(edge.target_id)
                        frontier.append((edge.target_id, depth + 1))

        return result

    def find_nodes_by_data(
        self,
        node_type: NodeType,
        key: str,
        value: Any
    ) -> List[GraphNode]:
        """Найти узлы по значению в data."""
        result = []
        for node in self.get_nodes_by_type(node_type):
            if node.data.get(key) == value:
                result.append(node)
        return result

    def clear(self) -> None:
        """Очистить граф."""
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()
        self._by_slug.clear()

    def stats(self) -> Dict[str, Any]:
        """Статистика графа."""
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "by_type": {t.value: len(ids) for t, ids in self._by_type.items() if ids},
        }


# === Global singleton ===

_GRAPH_STORE: GraphStore | None = None


def get_graph_store() -> GraphStore:
    """Получить глобальное хранилище графа."""
    global _GRAPH_STORE
    if _GRAPH_STORE is None:
        _GRAPH_STORE = GraphStore()
    return _GRAPH_STORE


def reset_graph_store() -> GraphStore:
    """Сбросить и вернуть новое хранилище."""
    global _GRAPH_STORE
    _GRAPH_STORE = GraphStore()
    return _GRAPH_STORE
