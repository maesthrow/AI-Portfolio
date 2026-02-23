from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from sqlalchemy import text

from app.deps import pg_engine, settings, vectorstore, rate_limiter
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
    collection_name = cfg.collection_name
    engine = pg_engine()

    try:
        async def _truncate():
            async with engine._pool.connect() as conn:
                await conn.execute(text(f'TRUNCATE TABLE "{collection_name}"'))
                await conn.commit()
        engine._run_as_sync(_truncate())
    except Exception:
        logger.warning("pgvector TRUNCATE failed", exc_info=True)

    try:
        bm25.reset(collection_name)
    except Exception:
        logger.warning("BM25 reset failed", exc_info=True)

    return ClearResult(ok=True, collection=collection_name, recreated=True)


@router.get("/admin/stats", response_model=StatsResult)
def collection_stats():
    cfg = settings()
    engine = pg_engine()
    collection_name = cfg.collection_name

    total = 0
    by_type: dict[str, int] | None = None
    try:
        async def _stats():
            async with engine._pool.connect() as conn:
                r1 = await conn.execute(text(f'SELECT COUNT(*) FROM "{collection_name}"'))
                cnt = r1.scalar() or 0
                r2 = await conn.execute(
                    text(f'SELECT type, COUNT(*) FROM "{collection_name}" GROUP BY type')
                )
                types = {row[0] or "unknown": row[1] for row in r2}
                return cnt, types
        total, by_type = engine._run_as_sync(_stats())
    except Exception:
        logger.warning("pgvector stats query failed", exc_info=True)

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
        collection=collection_name,
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
