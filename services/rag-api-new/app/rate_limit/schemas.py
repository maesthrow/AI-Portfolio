"""Rate limiting schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RateLimitBucket(BaseModel):
    """Информация о лимите по IP."""

    used: int = Field(..., description="Использовано токенов")
    limit: int = Field(..., description="Лимит токенов")
    remaining: int = Field(..., description="Осталось токенов")


class RateLimitInfo(BaseModel):
    """Rate limit информация для ответа клиенту."""

    ip: RateLimitBucket
    reset_in_seconds: int = Field(..., description="Секунд до сброса лимита")
    window_seconds: int = Field(..., description="Размер окна лимита в секундах (для warning)")
    show_warning: bool = Field(False, description="Показать warning (использовано >=80%)")
    exceeded: bool = Field(False, description="Лимит превышен")


class RateLimitStatus(BaseModel):
    """Ответ GET /rate-limit/status."""

    available: bool = Field(..., description="Доступен ли агент (Redis работает)")
    rate_limit: RateLimitInfo | None = Field(None, description="Информация о лимитах")
