from __future__ import annotations
from typing import Iterable
from .types import Doc, ScoredDoc, ReRanker


def adjust_score(doc: Doc, score: float) -> float:
    md = doc.metadata or {}
    s = float(score)
    if md.get("expanded"):
        s *= 0.8
    return s


def rerank(rr: ReRanker, question: str, docs: list[Doc]) -> list[ScoredDoc]:
    if not docs:
        return []
    pairs = [[question, d.page_content] for d in docs]
    scores = rr.predict(pairs)
    take = min(len(docs), len(scores))
    scored = [ScoredDoc(docs[i], adjust_score(docs[i], float(scores[i]))) for i in range(take)]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
