"""
Rate Limiter - ограничение использования LLM по токенам.

Использует Redis для хранения счётчиков с TTL.
В отличие от CacheService, блокирует запросы при недоступности Redis (fail-closed).
Ограничение только по IP-адресу.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..settings import Settings

logger = logging.getLogger(__name__)

# Redis клиент (ленивая инициализация)
_redis_client = None


@dataclass
class _RateLimitUsage:
    """Внутренняя структура для usage данных."""

    ip_used: int
    ip_ttl: int


class RateLimiter:
    """
    Rate limiter на основе Redis.

    Ограничивает использование LLM токенов по IP-адресу.
    При недоступности Redis блокирует ВСЕ запросы (fail-closed).
    """

    IP_PREFIX = "rl:ip:"

    def __init__(self, settings: Settings):
        self.settings = settings

    def _get_redis(self):
        """
        Ленивая инициализация Redis клиента.

        Возвращает None если Redis недоступен.
        """
        global _redis_client

        if _redis_client is None:
            try:
                import redis

                _redis_client = redis.from_url(
                    self.settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                _redis_client.ping()
                logger.info("RateLimiter: Redis connected")
            except Exception as e:
                logger.error("RateLimiter: Redis unavailable: %s", e)
                _redis_client = False  # Маркер: попытались, но не удалось

        return _redis_client if _redis_client else None

    @property
    def available(self) -> bool:
        """
        Проверить доступность rate limiter.

        Если rate_limit_enabled=False, возвращает True (пропускаем).
        Если Redis недоступен, возвращает False (блокируем).
        """
        if not self.settings.rate_limit_enabled:
            return True  # Rate limiting отключён - пропускаем
        return self._get_redis() is not None

    def _mask_ip(self, ip: str) -> str:
        """Маскировать IP для логирования (по настройке)."""
        if self.settings.rate_limit_log_ip_mode == "full":
            return ip
        # masked mode - скрываем последний октет
        if "." in ip:  # IPv4
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.*"
        elif ":" in ip:  # IPv6 - упрощённо скрываем последние части
            parts = ip.split(":")
            if len(parts) > 4:
                return ":".join(parts[:4]) + ":*:*:*:*"
        return ip

    def _get_usage(self, ip: str) -> _RateLimitUsage:
        """Получить текущее использование из Redis."""
        redis_client = self._get_redis()
        if not redis_client:
            # Если нет Redis - возвращаем максимальные значения (блокировка)
            return _RateLimitUsage(
                ip_used=self.settings.rate_limit_ip_tokens,
                ip_ttl=self.settings.rate_limit_window_seconds,
            )

        ip_key = f"{self.IP_PREFIX}{ip}"

        pipe = redis_client.pipeline()
        pipe.get(ip_key)
        pipe.ttl(ip_key)
        results = pipe.execute()

        ip_used = int(results[0] or 0)
        ip_ttl = results[1] if results[1] > 0 else self.settings.rate_limit_window_seconds

        return _RateLimitUsage(
            ip_used=ip_used,
            ip_ttl=ip_ttl,
        )

    def _build_info(self, usage: _RateLimitUsage, exceeded: bool = False):
        """Построить RateLimitInfo из usage данных."""
        from .schemas import RateLimitBucket, RateLimitInfo

        ip_limit = self.settings.rate_limit_ip_tokens
        threshold = self.settings.rate_limit_warning_threshold
        window = self.settings.rate_limit_window_seconds

        ip_remaining = max(0, ip_limit - usage.ip_used)
        ip_ratio = usage.ip_used / ip_limit if ip_limit > 0 else 0

        # Don't show warning if already exceeded
        show_warning = not exceeded and ip_ratio >= threshold

        return RateLimitInfo(
            ip=RateLimitBucket(
                used=usage.ip_used,
                limit=ip_limit,
                remaining=ip_remaining,
            ),
            reset_in_seconds=usage.ip_ttl,
            window_seconds=window,
            show_warning=show_warning,
            exceeded=exceeded,
        )

    def check_limit(self, ip: str):
        """
        Проверить, не превышен ли лимит.

        Args:
            ip: IP-адрес клиента

        Returns:
            tuple[bool, RateLimitInfo]: (allowed, info)
            - allowed=True если запрос можно обработать
            - allowed=False если лимит превышен
        """
        if not self.settings.rate_limit_enabled:
            # Rate limiting отключён - пропускаем с дефолтным info
            return True, self._build_info(_RateLimitUsage(0, self.settings.rate_limit_window_seconds))

        usage = self._get_usage(ip)
        exceeded = usage.ip_used >= self.settings.rate_limit_ip_tokens

        if exceeded:
            logger.warning(
                "Rate limit exceeded: ip=%s used=%d limit=%d",
                self._mask_ip(ip),
                usage.ip_used,
                self.settings.rate_limit_ip_tokens,
            )

        return not exceeded, self._build_info(usage, exceeded)

    def record_usage(self, ip: str, tokens: int):
        """
        Записать использование токенов.

        Вызывается ПОСЛЕ успешного ответа LLM.
        Использует атомарный INCRBY + EXPIRE NX.

        Args:
            ip: IP-адрес клиента
            tokens: Количество использованных токенов

        Returns:
            RateLimitInfo с обновлёнными значениями
        """
        if not self.settings.rate_limit_enabled or tokens <= 0:
            return self._build_info(_RateLimitUsage(0, self.settings.rate_limit_window_seconds))

        redis_client = self._get_redis()
        if not redis_client:
            logger.warning("RateLimiter: Cannot record usage - Redis unavailable")
            return self._build_info(
                _RateLimitUsage(
                    ip_used=tokens,
                    ip_ttl=self.settings.rate_limit_window_seconds,
                )
            )

        ip_key = f"{self.IP_PREFIX}{ip}"
        window = self.settings.rate_limit_window_seconds

        # Атомарный инкремент с установкой TTL (NX = только если нет TTL)
        pipe = redis_client.pipeline()
        pipe.incrby(ip_key, tokens)
        pipe.expire(ip_key, window, nx=True)
        pipe.ttl(ip_key)
        results = pipe.execute()

        new_ip_used = results[0]
        ip_ttl = results[2] if results[2] > 0 else window

        logger.debug(
            "Rate limit recorded: ip=%s tokens=%d new_total=%d",
            self._mask_ip(ip),
            tokens,
            new_ip_used,
        )

        # Calculate exceeded after recording usage
        exceeded = new_ip_used >= self.settings.rate_limit_ip_tokens

        return self._build_info(
            _RateLimitUsage(
                ip_used=new_ip_used,
                ip_ttl=ip_ttl,
            ),
            exceeded=exceeded,
        )

    def get_status(self, ip: str):
        """
        Получить статус rate limit для GET endpoint.

        Args:
            ip: IP-адрес клиента

        Returns:
            RateLimitStatus с информацией о доступности и лимитах
        """
        from .schemas import RateLimitStatus

        if not self.settings.rate_limit_enabled:
            return RateLimitStatus(available=True, rate_limit=None)

        if not self.available:
            return RateLimitStatus(available=False, rate_limit=None)

        _, info = self.check_limit(ip)

        # available=True means Redis is working (service is available)
        # Rate limit exceeded state is indicated by info.exceeded
        return RateLimitStatus(
            available=True,
            rate_limit=info,
        )
