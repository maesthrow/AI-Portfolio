from __future__ import annotations

import logging

from fastapi import APIRouter

from app.deps import chroma_client, settings, vectorstore, response_cache
from app.indexing import bm25
from app.schemas.admin import ClearResult, StatsResult, GraphStats, CacheStatsResult, CacheClearResult

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


# === Response Cache Endpoints ===

@router.get("/admin/cache/stats", response_model=CacheStatsResult)
def cache_stats():
    """
    Статистика кэша ответов агента.

    Returns:
        CacheStatsResult с информацией о кэше
    """
    cache = response_cache()

    if not cache:
        return CacheStatsResult(
            enabled=False,
            collection="",
            total_entries=0,
            total_hits=0,
        )

    stats = cache.stats()
    return CacheStatsResult(
        enabled=stats.enabled,
        collection=stats.collection,
        total_entries=stats.total_entries,
        total_hits=stats.total_hits,
    )


@router.delete("/admin/cache", response_model=CacheClearResult)
def clear_cache():
    """
    Очистить кэш ответов агента.

    Returns:
        CacheClearResult с количеством удалённых записей
    """
    cache = response_cache()

    if not cache:
        return CacheClearResult(
            ok=True,
            cleared=0,
            message="Cache is disabled",
        )

    cleared = cache.clear()
    logger.info("Response cache cleared: %d entries removed", cleared)

    return CacheClearResult(
        ok=True,
        cleared=cleared,
        message=f"Cleared {cleared} cached responses",
    )
