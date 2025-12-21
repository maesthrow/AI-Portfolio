from __future__ import annotations

import logging

from fastapi import APIRouter

from app.deps import chroma_client, settings, vectorstore
from app.indexing import bm25
from app.schemas.admin import ClearResult, StatsResult, GraphStats

router = APIRouter(prefix="/api/v1", tags=["admin"])
logger = logging.getLogger(__name__)


@router.delete("/admin/collection", response_model=ClearResult)
def clear_collection():
    cfg = settings()
    client = chroma_client()
    collection_name = cfg.chroma_collection

    try:
        client.delete_collection(collection_name)
    except Exception:
        logger.warning("Chroma delete_collection failed", exc_info=True)
    finally:
        try:
            bm25.reset(collection_name)
        except Exception:
            logger.warning("BM25 reset failed", exc_info=True)

    vectorstore(collection_name)
    return ClearResult(ok=True, collection=collection_name, recreated=True)


@router.get("/admin/stats", response_model=StatsResult)
def collection_stats():
    cfg = settings()
    client = chroma_client()
    coll = client.get_or_create_collection(cfg.chroma_collection)

    total = coll.count()
    by_type = None
    safe_limit = 5000
    if total and total <= safe_limit:
        data = coll.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for md in data.get("metadatas") or []:
            t = (md or {}).get("type") or "unknown"
            counts[t] = counts.get(t, 0) + 1
        by_type = counts

    # === Graph-RAG: статистика графа (always enabled) ===
    from app.graph.store import get_graph_store
    store = get_graph_store()
    stats = store.stats()
    graph_stats = GraphStats(
        nodes=stats["nodes"],
            edges=stats["edges"],
            nodes_by_type=stats["nodes_by_type"],
        )

    return StatsResult(
        collection=cfg.chroma_collection,
        total=total,
        by_type=by_type,
        graph_stats=graph_stats,
    )
