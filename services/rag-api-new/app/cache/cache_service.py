"""
CacheService - сервис кэширования с graceful degradation.

Если Redis недоступен - система работает без кэша (fallback на LLM).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from functools import lru_cache

from ..settings import get_settings

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    """Ленивая инициализация Redis клиента."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if not settings.cache_enabled:
            return None
        try:
            import redis
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _redis_client.ping()
            logger.info("Redis connected: %s", settings.redis_url)
        except Exception as e:
            logger.warning("Redis unavailable, caching disabled: %s", e)
            _redis_client = False  # Marker: tried but failed
    return _redis_client if _redis_client else None


class CacheService:
    """Сервис кэширования с graceful degradation."""

    CONTENT_HASH_KEY = "rag:content:hash"
    PLAN_PREFIX = "rag:plan:"
    EMB_PREFIX = "rag:emb:"

    def __init__(self):
        self.settings = get_settings()

    @property
    def redis(self):
        return _get_redis()

    @property
    def available(self) -> bool:
        return self.redis is not None and self.settings.cache_enabled

    def _safe_get(self, key: str) -> str | None:
        if not self.available:
            return None
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.warning("Redis get failed for %s: %s", key, e)
            return None

    def _safe_set(self, key: str, value: str, ttl: int | None = None) -> bool:
        if not self.available:
            return False
        try:
            if ttl:
                self.redis.setex(key, ttl, value)
            else:
                self.redis.set(key, value)
            return True
        except Exception as e:
            logger.warning("Redis set failed for %s: %s", key, e)
            return False

    # === Content Hash ===

    def get_content_hash(self) -> str | None:
        return self._safe_get(self.CONTENT_HASH_KEY)

    def set_content_hash(self, hash_value: str) -> bool:
        return self._safe_set(self.CONTENT_HASH_KEY, hash_value)

    # === Cache Invalidation ===

    def invalidate_all(self) -> int:
        if not self.available:
            return 0
        try:
            deleted = 0
            for prefix in [self.PLAN_PREFIX, self.EMB_PREFIX]:
                for key in self.redis.scan_iter(f"{prefix}*"):
                    self.redis.delete(key)
                    deleted += 1
            logger.info("Cache invalidated: %d keys deleted", deleted)
            return deleted
        except Exception as e:
            logger.warning("Cache invalidation failed: %s", e)
            return 0

    # === Question Normalization ===

    @staticmethod
    def _normalize_question(question: str) -> str:
        """
        Нормализация вопроса для cache key и shortcuts matching.

        Приводит разные формулировки к единому виду:
        - "ML-проекты?" → "ml проекты"
        - "расскажи о проектах Дмитрия" → "расскажи о проектах"

        NOTE: LangGraph Agent добавляет имя владельца к вопросам,
        убираем для унификации cache keys и shortcuts.
        """
        s = question.lower().strip()
        s = re.sub(r"[?!.,;:«»\"']+", "", s)  # Убрать пунктуацию
        s = re.sub(r"[-–—]+", " ", s)          # Дефисы → пробелы
        # Убираем имя владельца (агент добавляет контекст)
        s = re.sub(r"\s+(дмитрия?|dmitriy?)\s*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()     # Схлопнуть пробелы
        return s

    # === Plan Cache ===

    def _plan_key(self, question: str) -> str:
        normalized = self._normalize_question(question)
        hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.PLAN_PREFIX}{hash_val}"

    def get_cached_plan(self, question: str) -> dict | None:
        data = self._safe_get(self._plan_key(question))
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_cached_plan(self, question: str, plan_dict: dict) -> bool:
        return self._safe_set(
            self._plan_key(question),
            json.dumps(plan_dict, ensure_ascii=False),
            ttl=self.settings.plan_cache_ttl,
        )


@lru_cache
def get_cache_service() -> CacheService:
    return CacheService()
