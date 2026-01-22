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


class EmbeddingCacheClearResult(BaseModel):
    """Результат очистки embedding cache."""
    deleted: int
    message: str


class PlanCacheClearResult(BaseModel):
    """Результат очистки plan cache."""
    deleted: int
    message: str


class AllCacheClearResult(BaseModel):
    """Результат очистки всех кэшей."""
    plans_deleted: int
    embeddings_deleted: int
    message: str
