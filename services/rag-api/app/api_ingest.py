import json
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .deps import vectorstore, settings
from .schemas.ingest_schema import IngestRequest, IngestItem
from .utils import bm25_index
from .rag.index import bm25_try_save, bm25_try_load

import logging
logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["ingest"])


class IngestResult(BaseModel):
    ok: bool
    upserted: int
    collection: str


def _filter_complex_metadata(md: Dict[str, Any] | None) -> Dict[str, Any]:
    if not md:
        return {}
    out: Dict[str, Any] = {}
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


def _batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def upsert_documents(collection: str, items: List[IngestItem]) -> IngestResult:
    if not items:
        raise HTTPException(400, "items is empty")

    max_batch = getattr(settings(), "embedding_batch_size", 16) or 16
    vs = vectorstore(collection)
    ids_all = [it.id for it in items]

    # попытка восстановить BM25 на холодном старте
    bm25_try_load(collection)

    # 1) удалить старые id
    try:
        if ids_all:
            vs.delete(ids=ids_all)
    except Exception:
        logger.warning("vectorstore delete_ids failed", exc_info=True)
    try:
        bm25_index.delete_ids(collection, ids_all)
    except Exception:
        logger.warning("bm25 delete_ids failed", exc_info=True)

    upserted = 0
    # 2) батчами заливаем
    for batch in _batched(items, max_batch):
        ids = [it.id for it in batch]
        texts = [it.text for it in batch]
        metadatas = [_filter_complex_metadata(it.metadata) for it in batch]
        try:
            vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            upserted += len(batch)
        except Exception as e:
            preview = ", ".join(ids[:3])
            raise HTTPException(500, f"Chroma upsert failed on batch size {len(batch)} (e.g. ids: {preview}...): {e}")

        # 3) сразу обновляем BM25
        try:
            bm25_index.add_texts(collection, ids, texts)
        except Exception:
            logger.warning("bm25 add_texts failed", exc_info=True)

    # 4) персистим снапшот BM25 (опционально)
    try:
        snapshot = bm25_index.snapshot(collection)
        bm25_try_save(collection, snapshot)
    except Exception:
        logger.warning("bm25 snapshot save failed", exc_info=True)

    return IngestResult(ok=True, upserted=upserted, collection=collection)


@router.post("/ingest", response_model=IngestResult)
def ingest(req: IngestRequest):
    coll = req.collection or settings().chroma_collection
    return upsert_documents(coll, req.items)
