from __future__ import annotations

import json
import logging
from typing import Any, Iterable

from fastapi import APIRouter, HTTPException

from app.deps import settings, vectorstore
from app.indexing import bm25
from app.indexing.persistence import bm25_try_load, bm25_try_save
from app.schemas.ingest import IngestItem, IngestRequest, IngestResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ingest"])


def _filter_complex_metadata(md: dict[str, Any] | None) -> dict[str, Any]:
    if not md:
        return {}
    out: dict[str, Any] = {}
    for k, v in md.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            try:
                out[f"{k}_csv"] = ",".join(map(str, v))
            except Exception:
                pass
            out[k] = json.dumps(v, ensure_ascii=False, sort_keys=True)
        elif isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False, sort_keys=True)
        else:
            out[k] = str(v)
    return out


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

    try:
        if ids_all:
            vs.delete(ids=ids_all)
    except Exception:
        logger.warning("vectorstore delete_ids failed", exc_info=True)
    try:
        bm25.delete_ids(collection, ids_all)
    except Exception:
        logger.warning("bm25 delete_ids failed", exc_info=True)

    upserted = 0
    for batch in _batched(items, max_batch):
        ids = [it.id for it in batch]
        texts = [it.text for it in batch]
        metadatas = [_filter_complex_metadata(it.metadata) for it in batch]
        try:
            vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            upserted += len(batch)
        except Exception as e:
            preview = ", ".join(ids[:3])
            raise HTTPException(
                500,
                f"Chroma upsert failed on batch size {len(batch)} (e.g. ids: {preview}...): {e}",
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
    coll = req.collection or settings().chroma_collection
    return upsert_documents(coll, req.items)
