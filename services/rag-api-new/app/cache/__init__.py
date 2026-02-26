"""
Cache module - сервис кэширования с graceful degradation.

Содержит:
- CacheService: базовый сервис Redis с graceful degradation
- get_plan_with_cache: hybrid план-кэш (shortcut → cache → LLM)
- get_embedding_with_cache: кэширование query embeddings (P3)
"""
from .cache_service import CacheService, get_cache_service
from .plan_cache import get_plan_with_cache, try_plan_fast
from .embedding_cache import get_embedding_with_cache, invalidate_embedding_cache

__all__ = [
    "CacheService",
    "get_cache_service",
    "get_plan_with_cache",
    "try_plan_fast",
    "get_embedding_with_cache",
    "invalidate_embedding_cache",
]
