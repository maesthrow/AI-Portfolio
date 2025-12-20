"""
Query Planning - планирование запросов.

Определяет Intent (намерение) из вопроса, извлекает сущности,
и формирует QueryPlan для оптимального поиска.
"""
from __future__ import annotations
from typing import List, Set, Tuple

from .search_types import Intent, QueryPlan, Entity, EntityPolicy, EntityType
from .entities import get_entity_registry


_USAGE_PHRASES: tuple[str, ...] = (
    # RU
    "где примен",
    "где использ",
    "в каких проектах",
    "на каких проектах",
    "проекты с использованием",
    "проекты с применением",
    "с использованием",
    "с применением",
    "используется в",
    "использовал",
    "применял",
    # EN
    "where used",
    "used in",
)


def _looks_like_usage_query(question: str) -> bool:
    q = (question or "").lower()
    return any(p in q for p in _USAGE_PHRASES)


# === Intent classification rules ===
# (Intent, keywords, allowed_doc_types, style_hint)

_INTENT_RULES: List[Tuple[Intent, List[str], Set[str] | None, str | None]] = [
    # Текущая работа
    (
        Intent.CURRENT_JOB,
        [
            "где работаешь",
            "где работает",
            "текущ",
            "сейчас работаешь",
            "сейчас работает",
            "current position",
            "current job",
            "текущее место",
            "место работы",
        ],
        {"profile", "experience", "experience_project"},
        "LIST",
    ),
    # Достижения
    (
        Intent.ACHIEVEMENTS,
        [
            "достижен",
            "что сделал",
            "чем занимался",
            "результат",
            "accomplishment",
            "achieve",
            "успех",
            "реализовал",
        ],
        {"experience", "experience_project", "project"},
        "LIST",
    ),
    # Языки программирования
    (
        Intent.LANGUAGES,
        [
            "языки программирования",
            "languages",
            "на каких языках",
            "какие языки",
            "programming languages",
            "язык программирования",
        ],
        {"technology", "project", "catalog"},
        "LIST",
    ),
    # Технологии и стек
    (
        Intent.TECHNOLOGIES,
        [
            "стек",
            "технолог",
            "какие бд",
            "какие базы",
            "tech stack",
            "framework",
            "инструмент",
            "библиотек",
            "database",
        ],
        {"technology", "project", "tech_focus", "catalog"},
        "LIST",
    ),
    # RAG и связанные технологии
    (
        Intent.TECHNOLOGIES,
        [
            "rag",
            "агент",
            "agent",
            "retrieval",
            "langgraph",
            "langchain",
            "vector",
            "llm",
            "gpt",
            "нейросет",
        ],
        {"technology", "project", "tech_focus", "experience_project", "catalog"},
        "LIST",
    ),
    # Контакты
    (
        Intent.CONTACTS,
        [
            "контакт",
            "связаться",
            "email",
            "telegram",
            "github",
            "linkedin",
            "contact",
            "почта",
            "телефон",
        ],
        {"contact", "profile"},
        "LIST",
    ),
    # Детали проекта
    (
        Intent.PROJECT_DETAILS,
        [
            "проект",
            "project",
            "репозиторий",
            "demo",
            "описание проекта",
            "расскажи про проект",
            "что за проект",
        ],
        {"project", "experience_project"},
        None,
    ),
    # Опыт работы
    (
        Intent.EXPERIENCE,
        [
            "опыт",
            "experience",
            "работал",
            "компания",
            "company",
            "место работы",
            "карьер",
        ],
        {"experience", "experience_project"},
        "LIST",
    ),
]


def _match_intent(question: str) -> Tuple[Intent, Set[str] | None, str | None]:
    """
    Определить Intent по ключевым словам.

    Проходит по правилам в порядке приоритета.

    Returns:
        (Intent, allowed_types, style_hint)
    """
    q = question.lower()

    for intent, keywords, allowed_types, style in _INTENT_RULES:
        if any(kw in q for kw in keywords):
            return intent, allowed_types, style

    return Intent.GENERAL, None, None


def _should_use_graph(intent: Intent, entities: List[Entity]) -> bool:
    """
    Определить, подходит ли запрос для графового поиска.

    Граф используется для структурированных intent'ов с чёткой сущностью.
    """
    graph_intents = {
        Intent.ACHIEVEMENTS,
        Intent.CURRENT_JOB,
        Intent.CONTACTS,
        Intent.PROJECT_DETAILS,
        Intent.LANGUAGES,
    }

    # Используем граф для структурных запросов с 0-1 сущностями
    return intent in graph_intents and len(entities) <= 1


def _determine_entity_policy(intent: Intent, entities: List[Entity]) -> EntityPolicy:
    """
    Определить политику применения сущностей при поиске.

    - STRICT: жёсткая фильтрация (только документы с этой сущностью)
    - BOOST: повышение релевантности (но не исключение других)
    - NONE: без фильтрации
    """
    if not entities:
        return EntityPolicy.NONE

    # Для конкретного проекта - строгая фильтрация
    if intent == Intent.PROJECT_DETAILS:
        return EntityPolicy.STRICT

    # Для достижений и технологий - повышение, но не исключение
    if intent in {Intent.ACHIEVEMENTS, Intent.TECHNOLOGIES}:
        return EntityPolicy.BOOST

    return EntityPolicy.NONE


def plan_query(question: str, use_graph_feature: bool = True) -> QueryPlan:
    """
    Сформировать план выполнения запроса.

    1. Определяет Intent по ключевым словам
    2. Извлекает сущности через EntityRegistry
    3. Определяет политику фильтрации
    4. Решает, использовать ли граф

    Args:
        question: Вопрос пользователя
        use_graph_feature: Разрешено ли использование графа (feature flag)

    Returns:
        QueryPlan со всеми параметрами поиска

    Note:
        Open/Closed principle: для добавления новых Intent'ов
        достаточно расширить _INTENT_RULES.
    """
    intent, allowed_types, style_hint = _match_intent(question)

    registry = get_entity_registry()
    entities = registry.extract_entities(question)

    # Общий кейс "где применял/использовал <технология>": это всё ещё TECHNOLOGIES (без частных intent'ов),
    # но с более узкими типами документов и более строгой фильтрацией.
    is_usage_query = _looks_like_usage_query(question)
    has_tech_entity = any(e.type == EntityType.TECHNOLOGY for e in entities)
    if is_usage_query and has_tech_entity:
        intent = Intent.TECHNOLOGIES
        allowed_types = {"technology", "project", "experience_project"}
        style_hint = "LIST"

    entity_policy = _determine_entity_policy(intent, entities)
    if is_usage_query and has_tech_entity:
        entity_policy = EntityPolicy.STRICT
    use_graph = use_graph_feature and _should_use_graph(intent, entities)

    # Настройка параметров выборки в зависимости от Intent
    k_dense = 40
    k_bm = 40
    k_final = 24

    if intent == Intent.CONTACTS:
        # Контакты - мало документов, уменьшаем выборку
        k_dense = 10
        k_bm = 10
        k_final = 5
    elif intent == Intent.PROJECT_DETAILS and entities:
        # Конкретный проект - средняя выборка
        k_dense = 20
        k_bm = 20
        k_final = 8
    elif intent == Intent.ACHIEVEMENTS:
        # Достижения - увеличиваем для полноты
        k_dense = 50
        k_bm = 50
        k_final = 30

    return QueryPlan(
        intent=intent,
        entities=entities,
        allowed_types=allowed_types,
        entity_policy=entity_policy,
        use_graph=use_graph,
        k_dense=k_dense,
        k_bm=k_bm,
        k_final=k_final,
        style_hint=style_hint,
    )
