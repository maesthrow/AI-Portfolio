from __future__ import annotations

import json
from typing import Any


def truncate_text(value: Any, limit: int = 1200) -> str:
    if value is None:
        return ""
    try:
        text = value if isinstance(value, str) else str(value)
    except Exception:
        return ""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 12)] + "...<truncated>"


def compact_json(value: Any, limit: int = 8000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception:
        text = truncate_text(value, limit=limit)
    return truncate_text(text, limit=limit)

