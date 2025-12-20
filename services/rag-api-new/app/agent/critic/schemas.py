from __future__ import annotations

from pydantic import BaseModel, Field


class CriticDecision(BaseModel):
    sufficient: bool = Field(default=False)
    need_search: bool = Field(default=True)
    query: str = Field(default="")
    reason: str = Field(default="")

