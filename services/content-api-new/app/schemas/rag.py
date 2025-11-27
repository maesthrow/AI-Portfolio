from typing import Any

from pydantic import BaseModel


class RagDocumentOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    url: str | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
