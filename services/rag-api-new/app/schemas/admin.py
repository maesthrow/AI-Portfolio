from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ClearResult(BaseModel):
    ok: bool
    collection: str
    recreated: bool


class StatsResult(BaseModel):
    collection: str
    total: int
    by_type: dict[str, Any] | None = None
