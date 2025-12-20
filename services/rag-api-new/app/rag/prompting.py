from __future__ import annotations

from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

# === V1 Prompt (backward compatibility) ===

BASE_PROMPT = (
    "Ты — AI-ассистент, представляющий разработчика Дмитрия Каргина. Говоришь о Дмитрии в третьем лице, "
    "не выдаёшь себя за него. Представление краткое: кто ты (AI-ассистент Дмитрия) и чем помогаешь (факты об опыте, проектах, технологиях, контактах).\n\n"
    "Сфера: факты о проектах/компаниях/достижениях/технологиях, текущая роль, контакты. Не придумывай факты, ссылки, компании. "
    "Если данных нет — честно скажи и предложи уточнить.\n"
    "Стиль: 2-5 предложений или короткие маркеры. Без воды, без домыслов, только по вопросу. "
    "Не используй слово «контекст»; замени на «есть данные/нет данных». "
    "Не смешивай названия компаний, технологий и ролей — держи структуру ответа.\n"
    "Формат по умолчанию: короткая вводная + список ключевых пунктов (если уместно)."
)

LOW_CONFIDENCE_THRESHOLD = 0.35


def make_system_prompt(extra: str | None = None) -> str:
    return BASE_PROMPT if not extra else f"{BASE_PROMPT}\nДоп. инструкции: {extra.strip()}"


def classify_intent(llm, question: str) -> str:
    """
    Вернёт одно из: IDENTITY | TECH_LIST | GENERAL.
    Без кэширования объекта llm (никаких unhashable).
    """
    q = (question or "").strip()
    prompt = (
        "Определи намерение вопроса пользователя одним словом из списка:\n"
        "- IDENTITY - если спрашивают, кто ты/кто вы/что ты такое (самоидентификация).\n"
        "- TECH_LIST - если про перечисление/стек/набор технологий.\n"
        "- GENERAL - иначе.\n"
        "Ответь ровно одним словом."
    )
    try:
        out = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=q)])
        label = (out.content or "").strip().upper()
        return "IDENTITY" if "IDENTITY" in label else ("TECH_LIST" if "TECH_LIST" in label else "GENERAL")
    except Exception:
        return "GENERAL"


def build_messages_for_answer(
    system_prompt: str,
    question: str,
    context: str,
    style_hint: str | None = None,
    confidence: float | None = None,
):
    """
    style_hint (опционально): 'ULTRASHORT', 'LIST', 'DEFAULT'.
    """
    style_line = ""
    caution_line = ""
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        caution_line = (
            "Уверенность низкая: отвечай осторожно, коротко и без категоричности; "
            "если данных может быть недостаточно — попроси уточнить."
        )
        if style_hint != "LIST":
            style_hint = "ULTRASHORT"

    if style_hint == "ULTRASHORT":
        style_line = "Отвечай максимально кратко: 1-2 предложения, без перечислений и примеров."
    elif style_hint == "LIST":
        style_line = "Если требуется перечисление - добавь в свой ответ короткий маркированный список (до 10 пунктов)."

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Вопрос: {question}\n\nДанные о Дмитрии:\n{context}\n\n{caution_line}\n{style_line}\n"
                "Отвечай только по этим данным."
            )
        ),
    ]


def build_messages_when_empty(system_prompt: str, question: str, style_hint: str | None = None):
    style_line = ""
    if style_hint == "ULTRASHORT":
        style_line = "Отвечай максимально кратко: 1-2 предложения."
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Вопрос: {question}\n\nДанных нет.\n{style_line}\n"
                f"Если данных нет - честно скажи, что не можешь ответить и предложи, что уточнить."
            )
        ),
    ]


# === V2 Prompts (Epic 3: Natural Language Formatting) ===

BASE_PROMPT_V2 = """Ты — AI-ассистент разработчика Дмитрия. Говоришь о Дмитрии в третьем лице,
 не выдавая себя за него.  Отвечаешь дружелюбно.
 Представление краткое: кто ты (AI-ассистент Дмитрия) и чем помогаешь (факты об опыте, проектах, технологиях, контактах). 
 Сфера: факты о проектах/компаниях/достижениях/технологиях, текущая роль, контакты. Не придумывай факты, ссылки, компании.

Стиль ответа:
- Кратко и по делу, 2-5 предложений
- Без формальных вводных ("На данный момент...", "В соответствии...")
- Не перечисляй, чего нет — только факты
- Не добавляй ссылки вида [1], [2] в ответ
- Не упоминай confidence, уверенность или технические метаданные
- Если данных нет — скажи кратко и предложи уточнить вопрос
"""

STYLE_INSTRUCTIONS_V2 = {
    "LIST": (
        "Формат: маркированный список.\n"
        "- Каждый элемент с новой строки, начинается с дефиса\n"
        "- Короткое вступление (1 предложение) перед списком\n"
        "- Не более 10 пунктов"
    ),
    "ULTRASHORT": "Отвечай максимально кратко: 1-2 предложения, без списков.",
    "DEFAULT": "Короткий абзац, 2-4 предложения.",
}


def build_messages_for_answer_v2(
    question: str,
    context: str,
    style_hint: str | None = None,
    confidence: float | None = None,
    found: bool = True,
) -> List[BaseMessage]:
    """
    Build messages with v2 formatting (Epic 3).

    Key differences from v1:
    - First person voice (я, мой)
    - No confidence in prompt
    - Cleaner style instructions
    - No technical artifacts
    """
    from ..deps import settings
    cfg = settings()

    # Fallback to v1 if feature flag is disabled
    if not cfg.format_v2_enabled:
        return build_messages_for_answer(
            make_system_prompt(None), question, context, style_hint, confidence
        )

    style_line = STYLE_INSTRUCTIONS_V2.get(style_hint or "DEFAULT", "")

    # Don't pass confidence to prompt - handle it softly
    caution = ""
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        caution = "Если не уверен — лучше уточни у пользователя."

    user_content = f"Вопрос: {question}\n\nДанные:\n{context}\n\n{style_line}\n{caution}"

    return [
        SystemMessage(content=BASE_PROMPT_V2),
        HumanMessage(content=user_content.strip()),
    ]


def build_messages_when_empty_v2(question: str, style_hint: str | None = None) -> List[BaseMessage]:
    """
    Build messages for empty results with v2 formatting.

    Returns short, friendly "not found" response.
    """
    from ..deps import settings
    cfg = settings()

    if not cfg.format_v2_enabled:
        return build_messages_when_empty(make_system_prompt(None), question, style_hint)

    return [
        SystemMessage(content=BASE_PROMPT_V2),
        HumanMessage(
            content=(
                f"Вопрос: {question}\n\n"
                "Данных по этому запросу нет. Ответь коротко, что такой информации нет, "
                "и предложи уточнить вопрос. Не перечисляй, чего нет."
            )
        ),
    ]
