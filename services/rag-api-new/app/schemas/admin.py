from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ClearResult(BaseModel):
    ok: bool
    collection: str
    recreated: bool


class GraphStats(BaseModel):
    """Статистика графа знаний."""
    nodes: int
    edges: int
    nodes_by_type: dict[str, int]


class StatsResult(BaseModel):
    collection: str
    total: int
    by_type: dict[str, Any] | None = None
    graph_stats: GraphStats | None = None
