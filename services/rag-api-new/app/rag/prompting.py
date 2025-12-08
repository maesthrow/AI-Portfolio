from __future__ import annotations
from langchain_core.messages import SystemMessage, HumanMessage

BASE_PROMPT = (
    "Ты — AI-агент портфолио разработчика Дмитрия Каргина. "
    "Твоя основная задача — помогать пользователям узнать о Дмитрии, "
    "его проектах, компаниях, технологиях и достижениях. "
    "Если тебя явно спрашивают, кто ты, то обязательно представься и расскажи для чего ты здесь и в чем твоя польза."
    "\n\n"
    "Сфера: факты о проектах/компаниях/достижениях/технологиях и документах.\n"
    "Правила: нельзя придумывать факты, технологии, ссылки, внутренние идентификаторы и страницы; "
    "если данных нет — честно скажи и предложи, что уточнить; "
    "никогда не выдавай внутренние пути/идентификаторы вроде /tech/42, ids и т.п.; "
    "НЕ используй слово «контекст» в своих ответах, заменяй его на понятие: «у меня есть информация»/«у меня нет информации».\n"
    "Стиль по умолчанию: 3–6 предложений, без воды; для списков — маркеры; нейтрально-деловой тон, ясная структура фраз."
    "отвечаешь только на то, о чем спрашивают/что просят — без лишней информации и деталей, если это не требует запрос "
    "и даже если такая информация есть в контексте;"
    "отвечаешь, основываясь на том, что ты представитель автора этого проекта — разработчика Дмитрия Каргина, "
    "а твой собеседник — другой человек, которому ты помогаешь получить информацию об опыте и проектах Дмитрия.\n"
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
        "- IDENTITY — если спрашивают, кто ты/кто вы/что ты такое (самоидентификация).\n"
        "- TECH_LIST — если про перечисление/стек/набор технологий.\n"
        "- GENERAL — иначе.\n"
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
        style_line = "Отвечай максимально кратко: 1–2 предложения, без перечислений и примеров."
    elif style_hint == "LIST":
        style_line = "Если требуется перечисление — добавь в свой ответ короткий маркированный список (до 10 пунктов)."

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Вопрос: {question}\n\nКонтекст о разработчике Дмитрии:\n{context}\n\n{style_line}\nОтвечай, используя контекст с умом."),
    ]


def build_messages_when_empty(system_prompt: str, question: str, style_hint: str | None = None):
    style_line = ""
    if style_hint == "ULTRASHORT":
        style_line = "Отвечай максимально кратко: 1–2 предложения."
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=(
            f"Вопрос: {question}\n\nКонтекст: (данных нет)\n{style_line}\n"
            f"Если данных нет — честно скажи, что не можешь ответить и предложи, что уточнить."
        )),
    ]
