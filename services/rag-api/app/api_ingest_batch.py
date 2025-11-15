from fastapi import APIRouter
from pydantic import BaseModel

from .deps import settings
from .schemas.ingest_schema import ExportPayload, IngestItem
from .utils.normalize_export_rich import normalize_export_rich
from .api_ingest import upsert_documents

router = APIRouter(tags=["ingest"])


class IngestBatchResult(BaseModel):
    added: int
    collection: str


@router.post("/ingest/batch", response_model=IngestBatchResult)
def ingest_batch(payload: ExportPayload):
    coll = settings().chroma_collection
    items: list[IngestItem] = [
        IngestItem(id=doc_id, text=text, metadata=meta)
        for doc_id, text, meta in normalize_export_rich(payload)
    ]
    if not items:
        return IngestBatchResult(added=0, collection=coll)
    res = upsert_documents(coll, items)
    return IngestBatchResult(added=res.upserted, collection=res.collection)
