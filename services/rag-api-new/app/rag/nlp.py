from __future__ import annotations
import re

_STOP = {
    "и","а","но","или","что","где","когда","как","какой","какая","какие","про",
    "в","на","по","из","для","с","со","у","о","об","от","до","за","над","под",
    "это","этот","эта","эти","мой","моя","мои","твой","тебя","меня","мне",
    # Частые короткие служебные слова/частицы (важно после расширения min_len до 2)
    "не","да","ну","ок","ты","вы","мы","он","она","они","его","ее","их",
}
_WORD = re.compile(r"[a-zA-Zа-яА-Я0-9+#\-\.]{2,}")


def keywords(q: str) -> list[str]:
    """Extract keywords from query string, removing stopwords."""
    words = [w.lower() for w in _WORD.findall(q or "")]
    return [w for w in words if w not in _STOP]
