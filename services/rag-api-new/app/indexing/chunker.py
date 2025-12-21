from __future__ import annotations

import re

# Эмбед-модель даёт ~512 токенов; грубая оценка ~4 символа на токен для RU.
# Держим чанки в районе ~230–300 токенов, чтобы не размывать релевантность.
MAX_CHARS = 1800
_SENT_SPLITTER = re.compile(r"(?<=[\.\!\?])\s+")


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """
    Heuristically split long markdown/text blocks into sub-chunks that
    stay within `max_chars` to avoid over-long embeddings.
    """
    cleaned = re.sub(r"[ \t]+", " ", text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    paragraphs = [p.strip() for p in cleaned.split("\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush_buf():
        nonlocal buf
        b = buf.strip()
        if b:
            chunks.append(b)
        buf = ""

    for para in paragraphs:
        if len(para) <= max_chars:
            if len(buf) + (1 if buf else 0) + len(para) <= max_chars:
                buf = f"{buf}\n{para}" if buf else para
            else:
                flush_buf()
                buf = para
        else:
            sents = [_ for _ in _SENT_SPLITTER.split(para) if _]
            cur = ""
            for sent in sents:
                s = sent.strip()
                if not s:
                    continue
                if len(s) > max_chars:
                    if cur:
                        chunks.append(cur.strip())
                        cur = ""
                    for i in range(0, len(s), max_chars):
                        piece = s[i : i + max_chars].strip()
                        if piece:
                            chunks.append(piece)
                    continue
                if len(cur) + (1 if cur else 0) + len(s) <= max_chars:
                    cur = f"{cur} {s}".strip() if cur else s
                else:
                    if cur:
                        chunks.append(cur.strip())
                    cur = s
            if cur:
                chunks.append(cur.strip())

    flush_buf()

    out: list[str] = []
    for ch in chunks:
        if len(ch) <= max_chars:
            out.append(ch)
        else:
            for i in range(0, len(ch), max_chars):
                piece = ch[i : i + max_chars].strip()
                if piece:
                    out.append(piece)
    return [c for c in out if c]
