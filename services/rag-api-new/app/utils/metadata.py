from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Iterable


def _sha1(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def make_doc(
    doc_type: str, ref_id: str | int, text: str, metadata: dict[str, Any] | None = None
) -> tuple[str, str, dict[str, Any]]:
    md = dict(metadata or {})
    md["type"] = doc_type
    md["ref_id"] = ref_id
    md["content_hash"] = _sha1(
        {
            "type": doc_type,
            "ref_id": ref_id,
            "text": text,
            "metadata": md,
        }
    )
    return f"{doc_type}:{ref_id}", text, md


def chunk_doc(
    doc_type: str,
    ref_id: str | int,
    text: str,
    metadata: dict[str, Any] | None,
    splitter: Callable[..., list[str]],
) -> list[tuple[str, str, dict[str, Any]]]:
    parts = splitter(text or "")
    if not parts:
        return []
    if len(parts) == 1:
        return [make_doc(doc_type, ref_id, parts[0], metadata)]

    parent_id = f"{doc_type}:{ref_id}"
    docs: list[tuple[str, str, dict[str, Any]]] = []
    for idx, part in enumerate(parts, 1):
        md = dict(metadata or {})
        md["parent_id"] = parent_id
        md["part"] = idx
        docs.append(make_doc(doc_type, f"{ref_id}:c{idx}", part, md))
    return docs
