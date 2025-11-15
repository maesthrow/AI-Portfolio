from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, Iterable


@dataclass(frozen=True)
class Doc:
    page_content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ScoredDoc:
    doc: Doc
    score: float


class Retriever(Protocol):
    def retrieve(self, question: str, k: int) -> list[Doc]: ...


class ReRanker(Protocol):
    def predict(self, pairs: list[list[str]]) -> list[float]: ...


@dataclass(frozen=True)
class SourceInfo:
    id: str | None
    type: str | None
    title: str | None
    url: str | None
    kind: str | None
    repo_url: str | None
    demo_url: str | None
    score: float
