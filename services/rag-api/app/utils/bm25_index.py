from __future__ import annotations
from typing import List, Dict, Tuple
import re
from collections import defaultdict

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9+#\-]{2,}", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class _CollectionIndex:
    def __init__(self) -> None:
        self.docs: Dict[str, str] = {}
        self.doc_ids: List[str] = []
        self.corpus: List[List[str]] = []
        self.bm25 = None

    def _rebuild(self):
        if not BM25Okapi:
            self.bm25 = None
            return
        self.doc_ids = list(self.docs.keys())
        self.corpus = [_tokenize(self.docs[did]) for did in self.doc_ids]
        self.bm25 = BM25Okapi(self.corpus) if self.corpus else None

    def add_many(self, items: List[Tuple[str, str]]):
        for did, txt in items:
            self.docs[did] = txt or ""
        self._rebuild()

    def delete_many(self, ids: List[str]):
        for did in ids:
            self.docs.pop(did, None)
        self._rebuild()

    def search(self, query: str, k: int = 50) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        tokens = _tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        pairs = list(zip(self.doc_ids, [float(s) for s in scores]))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs[:k]

    def snapshot(self) -> Dict[str, str]:
        return dict(self.docs)


_REGISTRY: Dict[str, _CollectionIndex] = defaultdict(_CollectionIndex)


def add_texts(collection: str, ids: List[str], texts: List[str]):
    _REGISTRY[collection].add_many(list(zip(ids, texts)))


def delete_ids(collection: str, ids: List[str]):
    _REGISTRY[collection].delete_many(ids)


def search(collection: str, query: str, k: int = 50) -> List[Tuple[str, float]]:
    return _REGISTRY[collection].search(query, k=k)


def reset(collection: str):
    _REGISTRY.pop(collection, None)


def snapshot(collection: str) -> Dict[str, str]:
    return _REGISTRY[collection].snapshot()
