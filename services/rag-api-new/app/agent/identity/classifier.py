"""
Identity Classifier - semantic matching для identity-вопросов.

Использует embedding similarity вместо regex для устойчивости к:
- Опечаткам ("ктоты", "тыкто")
- Переформулировкам ("скажи кто ты", "а ты вообще кто")
- Вариациям ("расскажи о себе", "чем можешь помочь")
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

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
    Проверяет, является ли вопрос identity-вопросом через semantic matching.

    Args:
        question: Вопрос пользователя
        threshold: Порог similarity (по умолчанию 0.85)

    Returns:
        tuple[is_identity, max_similarity]
    """
    from app.deps import embeddings

    # Нормализация
    normalized = question.lower().strip()
    if not normalized:
        return False, 0.0

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
            "Identity question detected: %r -> best_match=%r, similarity=%.3f",
            question, best_match, max_similarity
        )
    else:
        logger.debug(
            "Not identity question: %r, max_similarity=%.3f (threshold=%.2f)",
            question, max_similarity, threshold
        )

    return is_identity, max_similarity


async def generate_identity_response(question: str) -> str:
    """
    Генерирует ответ на identity-вопрос через LLM.

    Использует отдельный промпт с описанием возможностей агента.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.deps import _create_llm_with_temperature

    # Используем низкую температуру для стабильного ответа
    llm = _create_llm_with_temperature(0.3)

    system_prompt = get_identity_system_prompt()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    try:
        response = await llm.ainvoke(messages)
        return response.content
    except Exception as e:
        logger.error("Failed to generate identity response: %s", e)
        # Fallback на статичный ответ
        return "Я AI-ассистент портфолио Дмитрия. Спрашивай о его проектах, опыте и навыках."
