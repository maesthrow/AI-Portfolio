"""Rate limiting schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RateLimitBucket(BaseModel):
    """Информация об одном лимите (session или IP)."""

    used: int = Field(..., description="Использовано токенов")
    limit: int = Field(..., description="Лимит токенов")
    remaining: int = Field(..., description="Осталось токенов")


class RateLimitInfo(BaseModel):
    """Rate limit информация для ответа клиенту."""

    session: RateLimitBucket
    ip: RateLimitBucket
    reset_in_seconds: int = Field(..., description="Секунд до сброса лимита")
    show_warning: bool = Field(False, description="Показать warning (использовано >=80%)")
    exceeded_by: str | None = Field(None, description="Какой лимит превышен: session/ip")


class RateLimitStatus(BaseModel):
    """Ответ GET /rate-limit/status."""

    available: bool = Field(..., description="Доступен ли агент")
    rate_limit: RateLimitInfo | None = Field(None, description="Информация о лимитах")
