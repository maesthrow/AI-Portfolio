from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.deps import chroma_client, settings, vectorstore, rate_limiter
from app.rate_limit import RateLimitStatus
from app.indexing import bm25
from app.schemas.admin import (
    ClearResult,
    StatsResult,
    GraphStats,
    EmbeddingCacheClearResult,
    PlanCacheClearResult,
    AllCacheClearResult,
    CacheStatsResult,
)
from app.cache.embedding_cache import invalidate_embedding_cache
from app.cache.cache_service import get_cache_service

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


@router.get("/admin/cache/stats", response_model=CacheStatsResult)
def cache_stats():
    """
    Статистика кэшей Redis.

    Показывает:
    - Доступность Redis
    - Количество ключей plan cache
    - Количество ключей embedding cache
    """
    cache = get_cache_service()
    if not cache.available:
        return CacheStatsResult(
            available=False,
            plan_cache_keys=0,
            embedding_cache_keys=0,
            redis_url=None,
        )

    plan_keys = 0
    emb_keys = 0
    try:
        for _ in cache.redis.scan_iter(f"{cache.PLAN_PREFIX}*"):
            plan_keys += 1
        for _ in cache.redis.scan_iter(f"{cache.EMB_PREFIX}*"):
            emb_keys += 1
    except Exception as e:
        logger.warning("Failed to count cache keys: %s", e)

    return CacheStatsResult(
        available=True,
        plan_cache_keys=plan_keys,
        embedding_cache_keys=emb_keys,
        redis_url=cache.settings.redis_url,
    )


@router.delete("/admin/cache/embeddings", response_model=EmbeddingCacheClearResult)
def clear_embedding_cache():
    """
    Инвалидировать все embedding кэши.

    Использовать при:
    - Смене embedding модели
    - Проблемах с кэшем
    """
    deleted = invalidate_embedding_cache()
    return EmbeddingCacheClearResult(deleted=deleted, message="Embedding cache cleared")


@router.delete("/admin/cache/plans", response_model=PlanCacheClearResult)
def clear_plan_cache():
    """
    Инвалидировать все plan кэши.

    Использовать при:
    - Изменении PLANNER_SYSTEM_PROMPT
    - Изменении логики планирования
    - Проблемах с кэшем
    """
    cache = get_cache_service()
    deleted = cache.invalidate_all()
    return PlanCacheClearResult(deleted=deleted, message="Plan cache cleared")


@router.delete("/admin/cache", response_model=AllCacheClearResult)
def clear_all_cache():
    """
    Инвалидировать ВСЕ кэши (plans + embeddings).

    Использовать при:
    - Полном сбросе системы
    - Серьёзных проблемах с кэшем
    """
    cache = get_cache_service()
    plans_deleted = cache.invalidate_all()
    embeddings_deleted = invalidate_embedding_cache()
    return AllCacheClearResult(
        plans_deleted=plans_deleted,
        embeddings_deleted=embeddings_deleted,
        message="All caches cleared",
    )


def _get_client_ip(request: Request) -> str:
    """Получить реальный IP клиента (учитывая прокси)."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip
    if request.client:
        return request.client.host
    return "unknown"


@router.get("/rate-limit/status", response_model=RateLimitStatus)
def get_rate_limit_status(request: Request):
    """
    Проверить текущий статус rate limit.

    Вызывается фронтом при монтировании AgentDock для определения
    доступности агента и текущего состояния лимитов.

    Лимитирование только по IP-адресу клиента.
    """
    limiter = rate_limiter()
    client_ip = _get_client_ip(request)

    return limiter.get_status(client_ip)
