from __future__ import annotations

from fastapi import APIRouter

from app.deps import settings
from app.indexing.normalizer import normalize_export
from app.schemas.export import ExportPayload
from app.schemas.ingest import IngestBatchResult, IngestItem
from .ingest import upsert_documents

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest/batch", response_model=IngestBatchResult)
def ingest_batch(payload: ExportPayload):
    coll = settings().chroma_collection
    enable_atomic = bool(getattr(settings(), "rag_atomic_docs", False))
    items = [
        IngestItem(id=doc_id, text=text, metadata=meta)
        for doc_id, text, meta in normalize_export(payload, enable_atomic=enable_atomic)
    ]
    if not items:
        return IngestBatchResult(added=0, collection=coll)

    res = upsert_documents(coll, items)
    return IngestBatchResult(added=res.upserted, collection=res.collection)
