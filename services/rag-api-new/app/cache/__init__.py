"""
Cache module - сервис кэширования с graceful degradation.
"""
from .cache_service import CacheService, get_cache_service
from .plan_cache import get_plan_with_cache

__all__ = ["CacheService", "get_cache_service", "get_plan_with_cache"]
