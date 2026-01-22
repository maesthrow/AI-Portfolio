from __future__ import annotations

import hashlib
import logging
import threading

from fastapi import APIRouter

from app.deps import settings
from app.prefetch import prefetch_popular_plans

logger = logging.getLogger(__name__)
from app.indexing.normalizer import normalize_export
from app.schemas.export import ExportPayload
from app.schemas.ingest import IngestBatchResult, IngestItem
from .ingest import upsert_documents

router = APIRouter(prefix="/api/v1", tags=["ingest"])


def _compute_payload_hash(payload: ExportPayload) -> str:
    """Вычислить детерминированный хеш payload."""
    payload_json = payload.model_dump_json(exclude_none=True)
    return hashlib.sha256(payload_json.encode()).hexdigest()[:16]


@router.post("/ingest/batch", response_model=IngestBatchResult)
def ingest_batch(payload: ExportPayload):
    coll = settings().chroma_collection

    # 1. Вычисляем hash payload
    new_hash = _compute_payload_hash(payload)

    # 2. Сравниваем с предыдущим hash
    from app.cache import get_cache_service
    cache = get_cache_service()
    old_hash = cache.get_content_hash()
    data_changed = (old_hash is None) or (old_hash != new_hash)

    if data_changed:
        logger.info("Content changed: hash %s -> %s, invalidating caches", old_hash or "None", new_hash)
        cache.invalidate_all()
    else:
        logger.info("Content unchanged (hash=%s), keeping caches", new_hash)

    # 3. Нормализация и индексация
    items = [
        IngestItem(id=doc_id, text=text, metadata=meta)
        for doc_id, text, meta in normalize_export(payload)
    ]
    if not items:
        return IngestBatchResult(
            added=0,
            collection=coll,
            cache_invalidated=data_changed,
            content_hash=new_hash,
        )

    res = upsert_documents(coll, items)

    # 4. Graph-RAG: построение графа знаний
    from app.graph.builder import build_graph_from_export
    store = build_graph_from_export(payload)
    logger.info("Graph built: %s", store.stats())

    # 5. Сохраняем новый hash
    cache.set_content_hash(new_hash)

    # 6. Prefetch в фоне (не блокирует response)
    def _background_prefetch():
        try:
            prefetch_popular_plans()
        except Exception as e:
            logger.warning("Background prefetch failed: %s", e)

    threading.Thread(target=_background_prefetch, daemon=True).start()
    logger.info("Background prefetch started")

    return IngestBatchResult(
        added=res.upserted,
        collection=res.collection,
        cache_invalidated=data_changed,
        content_hash=new_hash,
    )
