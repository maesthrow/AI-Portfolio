from __future__ import annotations

import logging

from fastapi import APIRouter

from app.deps import settings

logger = logging.getLogger(__name__)
from app.indexing.normalizer import normalize_export
from app.schemas.export import ExportPayload
from app.schemas.ingest import IngestBatchResult, IngestItem
from .ingest import upsert_documents

router = APIRouter(prefix="/api/v1", tags=["ingest"])


@router.post("/ingest/batch", response_model=IngestBatchResult)
def ingest_batch(payload: ExportPayload):
    coll = settings().chroma_collection
    items = [
        IngestItem(id=doc_id, text=text, metadata=meta)
        for doc_id, text, meta in normalize_export(payload)
    ]
    if not items:
        return IngestBatchResult(added=0, collection=coll)

    res = upsert_documents(coll, items)

    # === Graph-RAG: построение графа знаний ===
    cfg = settings()
    logger.info("graph_rag_enabled=%s", cfg.graph_rag_enabled)
    if cfg.graph_rag_enabled:
        from app.graph.builder import build_graph_from_export
        store = build_graph_from_export(payload)
        logger.info("Graph built: %s", store.stats())

    return IngestBatchResult(added=res.upserted, collection=res.collection)
