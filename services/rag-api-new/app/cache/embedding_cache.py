"""
Embedding Cache - кэширование embeddings запросов в Redis.

Ключи: rag:emb:{model}:{hash16}
Значение: JSON-сериализованный list[float]
TTL: 24 часа (embedding_cache_ttl)

NOTE: Embedding cache НЕ инвалидируется при изменении контента (ingest),
т.к. зависит только от текста запроса, не от данных.
Для очистки используйте invalidate_embedding_cache() или admin endpoint.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Callable

from .cache_service import get_cache_service, CacheService

logger = logging.getLogger(__name__)


def get_embedding_with_cache(
    text: str,
    embed_fn: Callable[[str], list[float]],
    model_name: str = "default",
) -> tuple[list[float], str]:
    """
    Получить embedding с использованием кэша.

    Args:
        text: Текст для embedding
        embed_fn: Функция получения embedding (TEI или GigaChat)
        model_name: Название модели (для разделения кэшей)

    Returns:
        tuple[embedding, source] где source = "cache" | "api"
    """
    cache = get_cache_service()

    # Нормализуем текст для cache key (убираем "Дмитрия" и т.д.)
    normalized = CacheService._normalize_question(text)
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    cache_key = f"{CacheService.EMB_PREFIX}{model_name}:{hash_val}"

    # 1. Try cache
    if cache.available:
        cached = cache._safe_get(cache_key)
        if cached:
            try:
                embedding = json.loads(cached)
                logger.info(
                    "Embedding CACHE HIT: key=%s, text=%r",
                    cache_key,
                    text[:50],
                )
                return embedding, "cache"
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in embedding cache: key=%s", cache_key)

    # 2. API fallback (TEI or GigaChat depending on EMBEDDING_PROVIDER)
    embedding = embed_fn(text)

    # 3. Cache result
    if cache.available:
        try:
            cache._safe_set(
                cache_key,
                json.dumps(embedding),
                ttl=cache.settings.embedding_cache_ttl,
            )
            logger.info(
                "Embedding CACHE SET: key=%s, text=%r",
                cache_key,
                text[:50],
            )
        except Exception as e:
            logger.warning("Failed to cache embedding: %s", e)

    return embedding, "api"


def invalidate_embedding_cache() -> int:
    """
    Инвалидировать все embedding кэши.

    Вызывается при:
    - Смене embedding модели
    - Ручном сбросе через admin endpoint

    Returns:
        Количество удалённых ключей
    """
    cache = get_cache_service()
    if not cache.available:
        return 0

    try:
        deleted = 0
        for key in cache.redis.scan_iter(f"{CacheService.EMB_PREFIX}*"):
            cache.redis.delete(key)
            deleted += 1
        logger.info("Embedding cache invalidated: %d keys", deleted)
        return deleted
    except Exception as e:
        logger.warning("Embedding cache invalidation failed: %s", e)
        return 0
