from __future__ import annotations
import json
from typing import Any


def md_get_list(md: dict, key: str) -> list[str]:
    v = md.get(key)
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in s.split(",") if x.strip()]
    return []


def md_get_dict(md: dict, key: str) -> dict:
    v = md.get(key)
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
    return {}


def doc_id_of(d) -> str | None:
    md = getattr(d, "metadata", None) or {}
    doc_id = md.get("doc_id")
    if isinstance(doc_id, str) and doc_id.strip():
        return doc_id.strip()

    t = md.get("type")
    ref = md.get("ref_id") or md.get("id") or md.get("source")
    if t and ref is not None:
        ref_s = str(ref)
        if ref_s.startswith(f"{t}:"):
            return ref_s
        return f"{t}:{ref_s}"

    if ref is None:
        return None
    return str(ref)
