from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    k: int = 8
    collection: str | None = None
    system_prompt: str | None = None
    session_id: str | None = None  # клиентская сессия для трейсинга/чекпоинтов


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    found: int
    collection: str
    model: str
