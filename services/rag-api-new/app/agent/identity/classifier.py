"""
Identity Classifier - определение вопросов об агенте.

Два уровня проверки:
1. Лингвистический: местоимения 2-го лица (ты, себя, твой) → Identity
2. Semantic: embedding similarity с референсными вопросами → Identity

Принцип: Наличие 2nd person marker имеет приоритет.
- "кто ты" → Identity (есть "ты")
- "расскажи о себе" → Identity (есть "себе")
- "кто такой Дмитрий" → НЕ Identity (нет маркеров) → Profile/RAG
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import numpy as np

from .prompts import IDENTITY_REFERENCE_QUESTIONS, get_identity_system_prompt

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

# Порог similarity для определения identity-вопроса
# 0.92 - консервативный порог, чтобы не ловить:
# - "расскажи об ML-проектах" (similarity ~0.87 с "расскажи о себе")
# - "кто такой Дмитрий" (similarity ~0.86 с "кто ты такой")
SIMILARITY_THRESHOLD = 0.92

# Маркеры 2-го лица (русский язык)
# Если вопрос содержит эти местоимения — это обращение к агенту
SECOND_PERSON_MARKERS = frozenset({
    # Личные местоимения 2-го лица
    "ты", "тебя", "тебе", "тобой", "тобою",
    # Возвратные местоимения (о себе = об агенте в контексте вопроса)
    "себя", "себе", "собой", "собою",
    # Притяжательные местоимения 2-го лица
    "твой", "твоя", "твои", "твоё", "твоему", "твоей",
})


def _has_second_person_marker(text: str) -> bool:
    """
    Проверяет наличие местоимений 2-го лица и возвратных.

    Если есть — вопрос об агенте (identity), не о разработчике (profile).

    Examples:
        "кто ты" → True (есть "ты")
        "расскажи о себе" → True (есть "себе")
        "кто такой Дмитрий" → False (нет маркеров)
    """
    words = set(re.findall(r"\b\w+\b", text.lower()))
    return bool(words & SECOND_PERSON_MARKERS)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Косинусное сходство между двумя векторами."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


@lru_cache(maxsize=1)
def _get_reference_embeddings() -> list[list[float]]:
    """
    Кэшированные embeddings референсных identity-вопросов.

    Вычисляются один раз при первом вызове.
    """
    from app.deps import embeddings

    emb = embeddings()
    logger.info("Computing reference embeddings for %d identity questions", len(IDENTITY_REFERENCE_QUESTIONS))

    # Batch embed для эффективности
    reference_embeddings = emb.embed_documents(IDENTITY_REFERENCE_QUESTIONS)

    logger.info("Reference embeddings computed: %d vectors of dim %d",
                len(reference_embeddings), len(reference_embeddings[0]) if reference_embeddings else 0)
    return reference_embeddings


def is_identity_question(question: str, threshold: float = SIMILARITY_THRESHOLD) -> tuple[bool, float]:
    """
    Проверяет, является ли вопрос identity-вопросом (про агента).

    Два уровня проверки:
    1. Лингвистический: местоимения 2-го лица → Identity (confidence=1.0)
    2. Semantic: embedding similarity → Identity (confidence=similarity)

    Args:
        question: Вопрос пользователя
        threshold: Порог similarity для semantic check (по умолчанию 0.92)

    Returns:
        tuple[is_identity, confidence]
        - confidence=1.0 для pronoun detection (детерминированно)
        - confidence=similarity для semantic detection
    """
    # Нормализация
    normalized = question.lower().strip()
    if not normalized:
        return False, 0.0

    # 1. Quick check: 2nd person pronouns → definitely identity
    if _has_second_person_marker(normalized):
        logger.info(
            "Identity detected by pronoun marker: %r",
            question,
        )
        return True, 1.0  # confidence = 1.0 (deterministic)

    # 2. Fallback: semantic similarity (для нестандартных формулировок)
    return _check_semantic_similarity(normalized, question, threshold)


def _check_semantic_similarity(
    normalized: str,
    original_question: str,
    threshold: float,
) -> tuple[bool, float]:
    """
    Проверка через semantic similarity с референсными вопросами.

    Используется как fallback когда pronoun check не сработал.
    """
    from app.deps import embeddings

    # Получаем embedding вопроса
    emb = embeddings()
    try:
        question_embedding = emb.embed_query(normalized)
    except Exception as e:
        logger.warning("Failed to embed question: %s", e)
        return False, 0.0

    # Получаем референсные embeddings (кэшированы)
    reference_embeddings = _get_reference_embeddings()

    # Находим максимальное сходство
    max_similarity = 0.0
    best_match = ""

    for i, ref_emb in enumerate(reference_embeddings):
        sim = _cosine_similarity(question_embedding, ref_emb)
        if sim > max_similarity:
            max_similarity = sim
            best_match = IDENTITY_REFERENCE_QUESTIONS[i]

    is_identity = max_similarity >= threshold

    if is_identity:
        logger.info(
            "Identity question detected by semantic: %r -> best_match=%r, similarity=%.3f",
            original_question, best_match, max_similarity
        )
    else:
        logger.debug(
            "Not identity question: %r, max_similarity=%.3f (threshold=%.2f)",
            original_question, max_similarity, threshold
        )

    return is_identity, max_similarity


async def generate_identity_response(question: str) -> tuple[str, dict | None]:
    """
    Генерирует ответ на identity-вопрос через LLM.

    Использует identity_llm с настройками из settings.

    Returns:
        tuple[str, dict | None]: Ответ и usage dict (или None при ошибке/fallback)
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.deps import identity_llm

    llm = identity_llm()

    system_prompt = get_identity_system_prompt()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    try:
        response = await llm.ainvoke(messages)
        usage = _extract_usage(response)
        return response.content, usage
    except Exception as e:
        logger.error("Failed to generate identity response: %s", e)
        # Fallback на статичный ответ
        return "Я AI-ассистент портфолио Дмитрия. Спрашивай о его проектах, опыте и навыках.", None


def _extract_usage(response: Any) -> dict | None:
    """Extract usage_metadata from LLM response and convert to dict."""
    usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
    elif hasattr(response, "response_metadata"):
        rm = response.response_metadata or {}
        usage = rm.get("token_usage") or rm.get("usage")

    if usage is None:
        return None

    # Convert to dict if it's a Pydantic model or similar
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if hasattr(usage, "dict"):
        return usage.dict()
    if isinstance(usage, dict):
        return usage
    return None
