from __future__ import annotations
from typing import Any
import os, pickle, logging
from ..utils import bm25_index

log = logging.getLogger("uvicorn.error")


def _bm25_state_path(collection: str) -> str | None:
    # Храним рядом с данными (по умолчанию — просто файл в рабочей директории)
    fname = f".bm25.{collection}.pkl"
    return os.path.abspath(fname)


def bm25_try_load(collection: str):
    path = _bm25_state_path(collection)
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, "rb") as f:
            docs = pickle.load(f)  # dict[id] = text
        ids = list(docs.keys())
        texts = [docs[i] for i in ids]
        bm25_index.add_texts(collection, ids, texts)
        log.info(f"BM25 restored for {collection}: {len(ids)} docs")
    except Exception:
        log.warning("BM25 restore failed", exc_info=True)


def bm25_try_save(collection: str, full_docs: dict[str, str]):
    path = _bm25_state_path(collection)
    if not path:
        return
    try:
        with open(path, "wb") as f:
            pickle.dump(full_docs, f)
    except Exception:
        log.warning("BM25 save failed", exc_info=True)
