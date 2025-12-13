from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

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


def build_messages_for_answer(system_prompt: str, question: str, context: str, style_hint: str | None = None):
    """
    style_hint (опционально): 'ULTRASHORT', 'LIST', 'DEFAULT'.
    """
    style_line = ""
    if style_hint == "ULTRASHORT":
        style_line = "Отвечай максимально кратко: 1-2 предложения, без перечислений и примеров."
    elif style_hint == "LIST":
        style_line = "Если требуется перечисление - добавь в свой ответ короткий маркированный список (до 10 пунктов)."

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"Вопрос: {question}\n\nДанные о Дмитрии:\n{context}\n\n{style_line}\nОтвечай только по этим данным."
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
