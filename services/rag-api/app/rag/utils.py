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
    return md.get("ref_id") or md.get("id") or md.get("source")
