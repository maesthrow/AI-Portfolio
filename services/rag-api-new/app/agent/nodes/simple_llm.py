"""
Simple LLM node for non-portfolio questions.

Handles:
- small_talk: Greetings, thanks, etc.
- off_topic: Questions not about portfolio
- harmful: Harmful requests (polite refusal)

Uses a single LLM call without RAG pipeline.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.scope_guard.scope_guard import get_scope_guard

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


SIMPLE_SYSTEM_PROMPT_RU = """Ты AI-ассистент портфолио разработчика Дмитрия.

Правила:
1. Отвечай кратко и дружелюбно (1-3 предложения)
2. Говори на русском языке
3. Если вопрос не о портфолио - вежливо направь к теме
4. Ты помогаешь узнать о проектах, опыте и навыках Дмитрия

Контекст вопроса: {context}"""


SIMPLE_SYSTEM_PROMPT_EN = """You are an AI assistant for Dmitry's developer portfolio.

Rules:
1. Answer briefly and friendly (1-3 sentences)
2. Speak in the same language as the user
3. If the question is not about the portfolio - politely redirect to the topic
4. You help learn about Dmitry's projects, experience, and skills

Question context: {context}"""


def simple_llm_node(state: RAGState) -> dict:
    """
    Handle non-portfolio questions with simple LLM response.

    For small_talk (greetings, thanks) - respond friendly.
    For off_topic - respond politely and redirect.
    For harmful - refuse and redirect.

    Args:
        state: Current RAGState with question and scope_category

    Returns:
        Partial state update with:
        - answer: Generated response
        - final_response: Complete response dict
    """
    question = state.get("question", "")
    scope_category = state.get("scope_category", "off_topic")
    suggested_prompts = state.get("suggested_prompts", [])

    logger.info(f"SimpleLLM handling: category={scope_category}")

    # Determine context for the LLM
    if scope_category == "small_talk":
        context = (
            "Пользователь приветствует или благодарит. "
            "Ответь дружелюбно, представься как AI-ассистент портфолио Дмитрия "
            "и предложи спросить о проектах, технологиях или опыте."
        )
    elif scope_category == "harmful":
        context = (
            "Пользователь задает потенциально вредный вопрос. "
            "Вежливо откажи и предложи спросить о портфолио."
        )
    else:  # off_topic
        context = (
            "Вопрос не относится к портфолио. "
            "Вежливо объясни, что ты помогаешь узнать о портфолио Дмитрия, "
            "и предложи примеры вопросов."
        )

    # Detect language
    is_english = any(
        word in question.lower()
        for word in ["hello", "hi", "hey", "thanks", "thank", "bye", "what", "how"]
    )
    system_prompt = (
        SIMPLE_SYSTEM_PROMPT_EN if is_english else SIMPLE_SYSTEM_PROMPT_RU
    ).format(context=context)

    # Call LLM (lazy import to avoid circular imports)
    from app.deps import chat_llm
    llm = chat_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    try:
        response = llm.invoke(messages)
        answer = response.content
    except Exception as e:
        logger.error(f"SimpleLLM error: {e}")
        # Fallback to deterministic response
        scope_guard = get_scope_guard()
        from app.agent.scope_guard.schemas import ScopeDecision

        decision = ScopeDecision(
            in_scope=False,
            category=scope_category,
            suggested_prompts=suggested_prompts,
        )
        answer = scope_guard.get_refusal_response(decision, lang="en" if is_english else "ru")

    # Build final response
    final_response = {
        "answer": answer,
        "sources": [],
        "found": True,
        "intents": [],
        "confidence": 1.0,
        "grounded": True,
        "scope_category": scope_category,
    }

    return {
        "answer": answer,
        "answer_is_deterministic": False,
        "final_response": final_response,
    }
