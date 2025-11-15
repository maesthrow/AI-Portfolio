from fastapi import APIRouter
from pydantic import BaseModel

from .deps import chroma_client, settings, vectorstore
from .utils import bm25_index

router = APIRouter(tags=["admin"])


class ClearResult(BaseModel):
    ok: bool
    collection: str
    recreated: bool


@router.delete("/admin/collection", response_model=ClearResult)
def clear_collection():
    s = settings()
    client = chroma_client()
    collection_name = s.chroma_collection

    # Удаляем коллекцию, если она была
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    finally:
        try:
            bm25_index.reset(collection_name)
        except Exception:
            pass

    # Создаём заново (через vectorstore, чтобы сразу инициализировать)
    vectorstore(collection_name)
    return ClearResult(ok=True, collection=collection_name, recreated=True)


class StatsResult(BaseModel):
    collection: str
    total: int
    by_type: dict | None = None  # опционально, покажем разбивку если документов немного


@router.get("/admin/stats", response_model=StatsResult)
def collection_stats():
    s = settings()
    client = chroma_client()
    coll = client.get_or_create_collection(s.chroma_collection)

    total = coll.count()

    # Опциональная разбивка по типам (метаданные `type`), чтобы не грузить огромные выборки
    by_type = None
    SAFE_LIMIT = 5000
    if total and total <= SAFE_LIMIT:
        # Получим все метаданные и посчитаем распределение по metadata["type"]
        data = coll.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for md in (data.get("metadatas") or []):
            t = (md or {}).get("type") or "unknown"
            counts[t] = counts.get(t, 0) + 1
        by_type = counts

    return StatsResult(collection=s.chroma_collection, total=total, by_type=by_type)
