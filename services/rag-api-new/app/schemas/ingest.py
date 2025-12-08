from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IngestItem(BaseModel):
    id: str = Field(..., description="doc id, например 'project:1'")
    text: str
    metadata: dict[str, Any] | None = None


class IngestRequest(BaseModel):
    collection: str | None = None
    items: list[IngestItem] = Field(default_factory=list)


class IngestResult(BaseModel):
    ok: bool
    upserted: int
    collection: str


class IngestBatchResult(BaseModel):
    added: int
    collection: str
