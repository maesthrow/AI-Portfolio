from __future__ import annotations
from typing import List, Tuple
from .types import Doc, Retriever
from .utils import doc_id_of
from ..utils import bm25_index


def fetch_by_ids(vs, ids: list[str], question: str) -> list[Doc]:
    if not ids:
        return []
    try:
        docs = vs.similarity_search(question, k=len(ids), filter={"ref_id": {"$in": ids}})
    except Exception:
        return []
    by_id = {doc_id_of(d): d for d in docs}
    out = [by_id.get(i) for i in ids if by_id.get(i)]
    # normalize to our Doc type
    return [Doc(page_content=d.page_content, metadata=d.metadata or {}) for d in out]


class DenseRetriever(Retriever):
    def __init__(self, vs, where: dict | None = None):
        self.vs = vs
        self.where = where

    def retrieve(self, question: str, k: int) -> list[Doc]:
        docs = self.vs.similarity_search(question, k=k, filter=self.where) if self.where else \
               self.vs.similarity_search(question, k=k)
        return [Doc(d.page_content, d.metadata or {}) for d in docs]


def rrf_merge(dense: List[Tuple[str, float]], bm25: List[Tuple[str, float]], k: int = 60) -> List[str]:
    K = 60
    scores: dict[str, float] = {}
    for i, (did, _) in enumerate(dense):
        scores[did] = scores.get(did, 0.0) + 1.0 / (K + i + 1)
    for i, (did, _) in enumerate(bm25):
        scores[did] = scores.get(did, 0.0) + 1.0 / (K + i + 1)
    return [did for did, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)][:k]


def cosine(a: list[float], b: list[float]) -> float:
    # placeholder, но мы используем MMR по текстам — значит применим прокси-сим векторизации через vs по id.
    return 0.0


def mmr_order(docs: list[Doc], question: str, k: int, diversity: float = 0.3) -> list[Doc]:
    """
    Simplified MMR на уровне текста: приближённо используем эвристику «неповторности» по хэшу и ref_id.
    Для реальной косинусной меры можно хранить эмбеддинги (если доступно).
    """
    seen_parent = set()
    out: list[Doc] = []
    for d in docs:
        pid = (d.metadata or {}).get("parent_id") or doc_id_of(d)
        key = (pid, (d.metadata or {}).get("part"))
        if key in seen_parent:
            continue
        seen_parent.add(key)
        out.append(d)
        if len(out) >= k:
            break
    return out


def expand_by_project(vs, question: str, base_docs: list[Doc], k_related: int = 48) -> list[Doc]:
    proj_ids: list[int] = []
    seen = set()
    for d in base_docs:
        pid = (d.metadata or {}).get("project_id")
        if isinstance(pid, int) and pid not in seen:
            seen.add(pid)
            proj_ids.append(pid)
    if not proj_ids:
        return list(base_docs)
    try:
        related = vs.similarity_search(
            question, k=k_related,
            filter={"type": {"$in": ["project", "achievement", "document"]}, "project_id": {"$in": proj_ids}},
        )
    except Exception:
        return list(base_docs)
    out = list(base_docs)
    for d in related:
        md = (d.metadata or {})
        md["expanded"] = True
        out.append(Doc(d.page_content, md))
    return out


class HybridRetriever:
    """
    Объединяет dense и BM25 через RRF, подтягивает «пропущенные» документы по id, далее MMR и expand_by_project.
    """
    def __init__(self, vs, collection: str):
        self.vs = vs
        self.collection = collection

    def retrieve(self, question: str, k_dense: int, k_bm: int, k_final: int) -> list[Doc]:
        dense_docs = self.vs.similarity_search(question, k=k_dense)  # без фильтра
        dense_pairs = []
        for i, d in enumerate(dense_docs):
            did = doc_id_of(d) or f"doc:{i}"
            dense_pairs.append((did, 1.0))

        bm_hits = bm25_index.search(self.collection, question, k=k_bm) or []

        if not dense_pairs and not bm_hits:
            return []

        merged_ids = rrf_merge(dense_pairs, bm_hits, k=max(60, k_final * 6))
        by_id_dense = {doc_id_of(d): d for d in dense_docs if doc_id_of(d)}
        candidates = [by_id_dense[i] for i in merged_ids if i in by_id_dense]
        miss = [i for i in merged_ids if i not in by_id_dense]
        if miss:
            candidates += fetch_by_ids(self.vs, miss, question)

        # normalize -> Doc
        docs = [Doc(d.page_content, d.metadata or {}) for d in candidates]
        # MMR (approx) и расширение по проекту
        docs = mmr_order(docs, question, k=max(k_final * 2, k_final))
        docs = expand_by_project(self.vs, question, docs, k_related=max(48, k_final * 6))
        return docs
