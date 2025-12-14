from __future__ import annotations
from typing import Any, List, Tuple
from .types import Doc, Retriever
from .utils import doc_id_of
from ..indexing import bm25


def _to_chroma_where(where: dict | None) -> dict | None:
    """
    Chroma v2 strict where format: если условий > 1, требуется явный `$and`.
    Иначе сервер возвращает: "Expected where to have exactly one operator".
    """
    if not where:
        return None
    if len(where) <= 1:
        return where
    return {"$and": [{k: v} for k, v in where.items()]}


def fetch_by_ids(vs, ids: list[str], question: str) -> list[Doc]:
    if not ids:
        return []
    try:
        # Prefer direct Chroma get-by-ids (stable for hybrid merge) over metadata filters.
        data: dict[str, Any] | None = None
        coll = getattr(vs, "_collection", None)
        if coll is not None and hasattr(coll, "get"):
            data = coll.get(ids=ids, include=["documents", "metadatas"])
        elif hasattr(vs, "get"):
            data = vs.get(ids=ids, include=["documents", "metadatas"])
        if not isinstance(data, dict):
            return []
    except Exception:
        return []

    got_ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []
    by_id: dict[str, Doc] = {}
    for did, txt, md in zip(got_ids, docs, metas):
        if not did:
            continue
        by_id[str(did)] = Doc(page_content=txt or "", metadata=md or {})

    out = [by_id.get(str(i)) for i in ids if by_id.get(str(i))]
    return [d for d in out if d]


class DenseRetriever(Retriever):
    def __init__(self, vs, where: dict | None = None):
        self.vs = vs
        self.where = where

    def retrieve(self, question: str, k: int) -> list[Doc]:
        where = _to_chroma_where(self.where)
        docs = self.vs.similarity_search(question, k=k, filter=where) if where else \
               self.vs.similarity_search(question, k=k)
        return [Doc(d.page_content, d.metadata or {}) for d in docs]


def rrf_merge(dense: List[Tuple[str, float]], bm25_hits: List[Tuple[str, float]], k: int = 60) -> List[str]:
    K = 60
    scores: dict[str, float] = {}
    for i, (did, _) in enumerate(dense):
        scores[did] = scores.get(did, 0.0) + 1.0 / (K + i + 1)
    for i, (did, _) in enumerate(bm25_hits):
        scores[did] = scores.get(did, 0.0) + 1.0 / (K + i + 1)
    return [did for did, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)][:k]


def mmr_order(docs: list[Doc], question: str, k: int, diversity: float = 0.3) -> list[Doc]:
    """
    Simplified MMR: уникализируем по parent_id/ref_id + part, затем обрезаем.
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
        where = _to_chroma_where({"type": {"$in": ["project", "experience_project"]}, "project_id": {"$in": proj_ids}})
        related = vs.similarity_search(
            question,
            k=k_related,
            filter=where,
        )
    except Exception:
        return list(base_docs)
    out = list(base_docs)
    for d in related:
        md = d.metadata or {}
        md["expanded"] = True
        out.append(Doc(d.page_content, md))
    return out


class HybridRetriever:
    """
    Объединяет dense и BM25 через RRF, подтягивает пропущенные документы по id, далее MMR и expand_by_project.
    """

    def __init__(self, vs, collection: str):
        self.vs = vs
        self.collection = collection

    def _filter_types(self, docs: list[Doc], allowed: set[str] | None) -> list[Doc]:
        if not allowed:
            return docs
        out: list[Doc] = []
        for d in docs:
            t = (d.metadata or {}).get("type")
            if t is None or t in allowed:
                out.append(d)
        return out

    def retrieve(
        self,
        question: str,
        k_dense: int,
        k_bm: int,
        k_final: int,
        allowed_types: set[str] | None = None,
        where: dict | None = None,
        *,
        strict: bool = False,
    ) -> list[Doc]:
        where_final = dict(where or {})
        if allowed_types:
            prev = where_final.get("type")
            if isinstance(prev, dict) and isinstance(prev.get("$in"), list):
                allow = set(allowed_types)
                where_final["type"] = {"$in": [t for t in prev["$in"] if t in allow]}
            elif isinstance(prev, str):
                where_final["type"] = prev if prev in allowed_types else {"$in": list(allowed_types)}
            else:
                where_final["type"] = {"$in": list(allowed_types)}
        where_final = where_final or None
        where_filter = _to_chroma_where(where_final)

        dense_docs = self.vs.similarity_search(question, k=k_dense, filter=where_filter) if where_filter else \
                     self.vs.similarity_search(question, k=k_dense)
        dense_pairs = []
        for i, d in enumerate(dense_docs):
            did = doc_id_of(d) or f"doc:{i}"
            dense_pairs.append((did, 1.0))

        bm_hits = bm25.search(self.collection, question, k=k_bm) or []

        if not dense_pairs and not bm_hits:
            return []

        merged_ids = rrf_merge(dense_pairs, bm_hits, k=max(60, k_final * 6))
        by_id_dense = {doc_id_of(d): d for d in dense_docs if doc_id_of(d)}
        candidates = [by_id_dense[i] for i in merged_ids if i in by_id_dense]
        miss = [i for i in merged_ids if i not in by_id_dense]
        if miss:
            candidates += fetch_by_ids(self.vs, miss, question)

        docs = [Doc(d.page_content, d.metadata or {}) for d in candidates]
        docs = self._filter_types(docs, allowed_types)
        if where_final:
            docs = _filter_where(docs, where_final)
        docs = mmr_order(docs, question, k=max(k_final * 2, k_final))
        docs = expand_by_project(self.vs, question, docs, k_related=max(48, k_final * 6))
        if strict:
            docs = self._filter_types(docs, allowed_types)
            if where_final:
                docs = _filter_where(docs, where_final)
        return docs


def _match_where_value(value: Any, cond: Any) -> bool:
    if isinstance(cond, dict) and "$in" in cond and isinstance(cond["$in"], list):
        target = set(map(str, cond["$in"]))
        if isinstance(value, list):
            return any(str(v) in target for v in value)
        return str(value) in target
    if isinstance(value, list):
        return any(str(v) == str(cond) for v in value)
    return str(value) == str(cond)


def _filter_where(docs: list[Doc], where: dict) -> list[Doc]:
    out: list[Doc] = []
    for d in docs:
        md = d.metadata or {}
        ok = True
        for k, cond in where.items():
            if k == "type":
                continue  # already applied by allowed_types and _filter_types
            if k not in md:
                ok = False
                break
            if not _match_where_value(md.get(k), cond):
                ok = False
                break
        if ok:
            out.append(d)
    return out
