from __future__ import annotations

import logging
from typing import Any, Iterable

from fastapi import APIRouter, HTTPException

from app.deps import settings, vectorstore
from app.indexing import bm25
from app.indexing.persistence import bm25_try_load, bm25_try_save
from app.schemas.ingest import IngestItem, IngestRequest, IngestResult
from app.utils.metadata import doc_id_to_langchain_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ingest"])


def _batched(seq: Iterable[Any], n: int):
    items = list(seq)
    for i in range(0, len(items), n):
        yield items[i : i + n]


def upsert_documents(collection: str, items: list[IngestItem]) -> IngestResult:
    if not items:
        raise HTTPException(400, "items is empty")

    max_batch = getattr(settings(), "embedding_batch_size", 16) or 16
    vs = vectorstore(collection)
    ids_all = [it.id for it in items]

    bm25_try_load(collection)

    # PGVectorStore langchain_id is UUID — convert string doc_ids to deterministic UUIDs
    try:
        if ids_all:
            uuid_ids = [doc_id_to_langchain_id(i) for i in ids_all]
            vs.delete(ids=uuid_ids)
    except Exception:
        logger.warning("vectorstore delete_ids failed", exc_info=True)
    try:
        bm25.delete_ids(collection, ids_all)
    except Exception:
        logger.warning("bm25 delete_ids failed", exc_info=True)

    upserted = 0
    for batch in _batched(items, max_batch):
        ids = [it.id for it in batch]
        uuid_batch_ids = [doc_id_to_langchain_id(i) for i in ids]
        texts = [it.text for it in batch]
        metadatas = [it.metadata or {} for it in batch]
        try:
            vs.add_texts(texts=texts, metadatas=metadatas, ids=uuid_batch_ids)
            upserted += len(batch)
        except Exception as e:
            preview = ", ".join(ids[:3])
            raise HTTPException(
                500,
                f"pgvector upsert failed on batch size {len(batch)} (e.g. ids: {preview}...): {e}",
            )

        try:
            bm25.add_texts(collection, ids, texts)
        except Exception:
            logger.warning("bm25 add_texts failed", exc_info=True)

    try:
        snapshot = bm25.snapshot(collection)
        bm25_try_save(collection, snapshot)
    except Exception:
        logger.warning("bm25 snapshot save failed", exc_info=True)

    return IngestResult(ok=True, upserted=upserted, collection=collection)


@router.post("/ingest", response_model=IngestResult)
def ingest(req: IngestRequest):
    coll = req.collection or settings().collection_name
    return upsert_documents(coll, req.items)
