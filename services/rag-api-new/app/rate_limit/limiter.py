"""
Rate Limiter - ограничение использования LLM по токенам.

Использует Redis для хранения счётчиков с TTL.
В отличие от CacheService, блокирует запросы при недоступности Redis (fail-closed).
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

    session_used: int
    ip_used: int
    session_ttl: int
    ip_ttl: int


class RateLimiter:
    """
    Rate limiter на основе Redis.

    Ограничивает использование LLM токенов по:
    - Сессии (session_id из клиента)
    - IP-адресу (защита от злоупотреблений)

    При недоступности Redis блокирует ВСЕ запросы (fail-closed).
    """

    SESSION_PREFIX = "rl:session:"
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

    def _get_usage(self, session_id: str, ip: str) -> _RateLimitUsage:
        """Получить текущее использование из Redis."""
        redis_client = self._get_redis()
        if not redis_client:
            # Если нет Redis - возвращаем максимальные значения (блокировка)
            return _RateLimitUsage(
                session_used=self.settings.rate_limit_session_tokens,
                ip_used=self.settings.rate_limit_ip_tokens,
                session_ttl=self.settings.rate_limit_window_seconds,
                ip_ttl=self.settings.rate_limit_window_seconds,
            )

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        ip_key = f"{self.IP_PREFIX}{ip}"

        pipe = redis_client.pipeline()
        pipe.get(session_key)
        pipe.get(ip_key)
        pipe.ttl(session_key)
        pipe.ttl(ip_key)
        results = pipe.execute()

        session_used = int(results[0] or 0)
        ip_used = int(results[1] or 0)
        session_ttl = results[2] if results[2] > 0 else self.settings.rate_limit_window_seconds
        ip_ttl = results[3] if results[3] > 0 else self.settings.rate_limit_window_seconds

        return _RateLimitUsage(
            session_used=session_used,
            ip_used=ip_used,
            session_ttl=session_ttl,
            ip_ttl=ip_ttl,
        )

    def _build_info(
        self, usage: _RateLimitUsage, exceeded_by: str | None = None
    ):
        """Построить RateLimitInfo из usage данных."""
        from .schemas import RateLimitBucket, RateLimitInfo

        session_limit = self.settings.rate_limit_session_tokens
        ip_limit = self.settings.rate_limit_ip_tokens
        threshold = self.settings.rate_limit_warning_threshold

        session_remaining = max(0, session_limit - usage.session_used)
        ip_remaining = max(0, ip_limit - usage.ip_used)

        session_ratio = usage.session_used / session_limit if session_limit > 0 else 0
        ip_ratio = usage.ip_used / ip_limit if ip_limit > 0 else 0

        show_warning = session_ratio >= threshold or ip_ratio >= threshold
        reset_in = max(usage.session_ttl, usage.ip_ttl)

        return RateLimitInfo(
            session=RateLimitBucket(
                used=usage.session_used,
                limit=session_limit,
                remaining=session_remaining,
            ),
            ip=RateLimitBucket(
                used=usage.ip_used,
                limit=ip_limit,
                remaining=ip_remaining,
            ),
            reset_in_seconds=reset_in,
            show_warning=show_warning,
            exceeded_by=exceeded_by,
        )

    def check_limit(self, session_id: str, ip: str):
        """
        Проверить, не превышен ли лимит.

        Args:
            session_id: ID сессии клиента
            ip: IP-адрес клиента

        Returns:
            tuple[bool, RateLimitInfo]: (allowed, info)
            - allowed=True если запрос можно обработать
            - allowed=False если лимит превышен
        """
        from .schemas import RateLimitInfo

        if not self.settings.rate_limit_enabled:
            # Rate limiting отключён - пропускаем с пустым info
            return True, self._build_info(_RateLimitUsage(0, 0, 0, 0))

        usage = self._get_usage(session_id, ip)

        session_exceeded = usage.session_used >= self.settings.rate_limit_session_tokens
        ip_exceeded = usage.ip_used >= self.settings.rate_limit_ip_tokens

        exceeded_by = None
        if session_exceeded:
            exceeded_by = "session"
        elif ip_exceeded:
            exceeded_by = "ip"

        allowed = not (session_exceeded or ip_exceeded)

        if not allowed:
            logger.warning(
                "Rate limit exceeded: ip=%s session_id=%s exceeded_by=%s used=%d limit=%d",
                self._mask_ip(ip),
                session_id,
                exceeded_by,
                usage.session_used if exceeded_by == "session" else usage.ip_used,
                (
                    self.settings.rate_limit_session_tokens
                    if exceeded_by == "session"
                    else self.settings.rate_limit_ip_tokens
                ),
            )

        return allowed, self._build_info(usage, exceeded_by)

    def record_usage(self, session_id: str, ip: str, tokens: int):
        """
        Записать использование токенов.

        Вызывается ПОСЛЕ успешного ответа LLM.
        Использует атомарный INCRBY + EXPIRE NX.

        Args:
            session_id: ID сессии клиента
            ip: IP-адрес клиента
            tokens: Количество использованных токенов

        Returns:
            RateLimitInfo с обновлёнными значениями
        """
        if not self.settings.rate_limit_enabled or tokens <= 0:
            return self._build_info(_RateLimitUsage(0, 0, 0, 0))

        redis_client = self._get_redis()
        if not redis_client:
            logger.warning("RateLimiter: Cannot record usage - Redis unavailable")
            return self._build_info(
                _RateLimitUsage(
                    tokens, tokens,
                    self.settings.rate_limit_window_seconds,
                    self.settings.rate_limit_window_seconds,
                )
            )

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        ip_key = f"{self.IP_PREFIX}{ip}"
        window = self.settings.rate_limit_window_seconds

        # Атомарный инкремент с установкой TTL (NX = только если нет TTL)
        pipe = redis_client.pipeline()
        pipe.incrby(session_key, tokens)
        pipe.expire(session_key, window, nx=True)
        pipe.incrby(ip_key, tokens)
        pipe.expire(ip_key, window, nx=True)
        pipe.ttl(session_key)
        pipe.ttl(ip_key)
        results = pipe.execute()

        new_session_used = results[0]
        new_ip_used = results[2]
        session_ttl = results[4] if results[4] > 0 else window
        ip_ttl = results[5] if results[5] > 0 else window

        logger.debug(
            "Rate limit recorded: session_id=%s tokens=%d new_session_total=%d new_ip_total=%d",
            session_id,
            tokens,
            new_session_used,
            new_ip_used,
        )

        return self._build_info(
            _RateLimitUsage(
                session_used=new_session_used,
                ip_used=new_ip_used,
                session_ttl=session_ttl,
                ip_ttl=ip_ttl,
            )
        )

    def get_status(self, session_id: str, ip: str):
        """
        Получить статус rate limit для GET endpoint.

        Args:
            session_id: ID сессии клиента
            ip: IP-адрес клиента

        Returns:
            RateLimitStatus с информацией о доступности и лимитах
        """
        from .schemas import RateLimitStatus

        if not self.settings.rate_limit_enabled:
            return RateLimitStatus(available=True, rate_limit=None)

        if not self.available:
            return RateLimitStatus(available=False, rate_limit=None)

        allowed, info = self.check_limit(session_id, ip)

        return RateLimitStatus(
            available=allowed,
            rate_limit=info,
        )
