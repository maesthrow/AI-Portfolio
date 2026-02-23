from __future__ import annotations
import logging
from typing import List, Tuple
from .types import Doc, Retriever
from .utils import doc_id_of
from ..indexing import bm25
from ..cache.embedding_cache import get_embedding_with_cache
from ..deps import embeddings, settings
from ..utils.metadata import doc_id_to_langchain_id

logger = logging.getLogger(__name__)


def fetch_by_ids(vs, ids: list[str], question: str) -> list[Doc]:
    """Fetch documents by ID via PGVectorStore.get_by_ids().

    Args:
        ids: String doc_ids (e.g. "profile:1") — converted to UUID for langchain_id lookup.
    """
    if not ids:
        return []
    try:
        uuid_ids = [doc_id_to_langchain_id(i) for i in ids]
        documents = vs.get_by_ids(uuid_ids)
        return [Doc(page_content=d.page_content, metadata=d.metadata or {}) for d in documents]
    except Exception:
        logger.warning("fetch_by_ids failed for %d ids", len(ids), exc_info=True)
        return []


class DenseRetriever(Retriever):
    def __init__(self, vs, where: dict | None = None):
        self.vs = vs
        self.where = where

    def retrieve(self, question: str, k: int) -> list[Doc]:
        # Получаем embedding с кэшированием
        query_embedding, emb_source = get_embedding_with_cache(
            question,
            embed_fn=embeddings().embed_query,
            model_name=settings().embedding_model or "default",
        )
        logger.info("DenseRetriever embedding source: %s", emb_source)

        docs = self.vs.similarity_search_by_vector(query_embedding, k=k, filter=self.where) if self.where else \
               self.vs.similarity_search_by_vector(query_embedding, k=k)
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


def expand_by_project(vs, question: str, base_docs: list[Doc], k_related: int = 48, query_embedding: list[float] | None = None) -> list[Doc]:
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
        # Используем переданный embedding или получаем из кэша
        if query_embedding is None:
            query_embedding, _ = get_embedding_with_cache(
                question,
                embed_fn=embeddings().embed_query,
                model_name=settings().embedding_model or "default",
            )
        related = vs.similarity_search_by_vector(
            query_embedding,
            k=k_related,
            filter={"type": {"$in": ["project", "experience_project"]}, "project_id": {"$in": proj_ids}},
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
    ) -> list[Doc]:
        # Получаем embedding с кэшированием
        query_embedding, emb_source = get_embedding_with_cache(
            question,
            embed_fn=embeddings().embed_query,
            model_name=settings().embedding_model or "default",
        )
        logger.info("HybridRetriever embedding source: %s", emb_source)

        where = {"type": {"$in": list(allowed_types)}} if allowed_types else None
        dense_docs = self.vs.similarity_search_by_vector(query_embedding, k=k_dense, filter=where) if where else \
                     self.vs.similarity_search_by_vector(query_embedding, k=k_dense)
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
        docs = mmr_order(docs, question, k=max(k_final * 2, k_final))
        # Передаём embedding чтобы не вычислять повторно
        docs = expand_by_project(self.vs, question, docs, k_related=max(48, k_final * 6), query_embedding=query_embedding)
        return docs
