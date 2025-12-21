"""
Smoke-тесты для Graph-RAG и Query Planning (Эпики 1 и 2).

Минимальные тесты для проверки критичных функций без внешних зависимостей.
"""
from __future__ import annotations

import pytest

from app.rag.search_types import (
    Intent,
    EntityType,
    EntityPolicy,
    Entity,
    QueryPlan,
    GraphQueryResult,
    SearchResult,
)
from app.rag.entities import EntityRegistry, get_entity_registry, reset_entity_registry
# NOTE: plan_query removed in v3 (LLM-based planning used instead)
# from app.rag.query_plan import plan_query
from app.graph.schema import NodeType, EdgeType, GraphNode, GraphEdge
from app.graph.store import GraphStore, get_graph_store, reset_graph_store
from app.graph.query import graph_query


class TestEntityRegistry:
    """Тесты для EntityRegistry."""

    def setup_method(self):
        """Сброс реестра перед каждым тестом."""
        reset_entity_registry()

    def test_register_and_find_by_slug(self):
        """Регистрация сущности и поиск по slug."""
        registry = get_entity_registry()
        registry.register(
            entity_type=EntityType.PROJECT,
            slug="ai-portfolio",
            name="AI-Portfolio",
            aliases=["portfolio", "ai portfolio"],
        )

        entity = registry.find_entity("ai-portfolio")
        assert entity is not None
        assert entity.slug == "ai-portfolio"
        assert entity.name == "AI-Portfolio"
        assert entity.type == EntityType.PROJECT

    def test_find_by_alias(self):
        """Поиск сущности по alias."""
        registry = get_entity_registry()
        registry.register(
            entity_type=EntityType.COMPANY,
            slug="alor-broker",
            name="ALOR Broker",
            aliases=["alor", "алор", "алор брокер"],
        )

        entity = registry.find_entity("алор")
        assert entity is not None
        assert entity.slug == "alor-broker"

    def test_extract_entities_from_question(self):
        """Извлечение сущностей из вопроса."""
        registry = get_entity_registry()
        registry.register(EntityType.PROJECT, "ai-portfolio", "AI-Portfolio", ["ai portfolio"])
        registry.register(EntityType.TECHNOLOGY, "python", "Python", ["питон"])

        entities = registry.extract_entities("Расскажи о проекте ai portfolio на Python")
        assert len(entities) >= 1  # Должен найти хотя бы AI-Portfolio

    def test_list_by_type(self):
        """Получение списка сущностей по типу."""
        registry = get_entity_registry()
        registry.register(EntityType.PROJECT, "proj1", "Project 1", [])
        registry.register(EntityType.PROJECT, "proj2", "Project 2", [])
        registry.register(EntityType.COMPANY, "comp1", "Company 1", [])

        projects = registry.list_by_type(EntityType.PROJECT)
        assert len(projects) == 2
        assert "proj1" in projects
        assert "proj2" in projects

    def test_clear(self):
        """Очистка реестра."""
        registry = get_entity_registry()
        registry.register(EntityType.PROJECT, "test", "Test", [])
        registry.clear()

        entity = registry.find_entity("test")
        assert entity is None


# NOTE: TestIntentClassification removed in v3 - uses deleted plan_query (keyword-based intent)
# In v3 intent classification is done by LLM Planner instead
# class TestIntentClassification:
#     """Тесты для классификации интента (v1/v2 only)."""
#
#     def setup_method(self):
#         """Сброс реестра перед каждым тестом."""
#         reset_entity_registry()
#
#     def test_achievements_intent(self):
#         """Определение intent ACHIEVEMENTS."""
#         plan = plan_query("Какие достижения на проекте?", use_graph_feature=False)
#         assert plan.intent == Intent.ACHIEVEMENTS
#
#     def test_current_job_intent(self):
#         """Определение intent CURRENT_JOB."""
#         plan = plan_query("Где сейчас работает?", use_graph_feature=False)
#         assert plan.intent == Intent.CURRENT_JOB
#
#     def test_technologies_intent(self):
#         """Определение intent TECHNOLOGIES."""
#         plan = plan_query("Какой стек технологий использует?", use_graph_feature=False)
#         assert plan.intent == Intent.TECHNOLOGIES
#
#     def test_contacts_intent(self):
#         """Определение intent CONTACTS."""
#         plan = plan_query("Как связаться?", use_graph_feature=False)
#         assert plan.intent == Intent.CONTACTS
#
#     def test_experience_intent(self):
#         """Определение intent EXPERIENCE."""
#         plan = plan_query("Какой опыт работы?", use_graph_feature=False)
#         assert plan.intent == Intent.EXPERIENCE
#
#     def test_general_intent_fallback(self):
#         """Fallback на GENERAL для неопределённых вопросов."""
#         plan = plan_query("Привет, расскажи о себе", use_graph_feature=False)
#         assert plan.intent == Intent.GENERAL
#
#     def test_query_plan_structure(self):
#         """Проверка структуры QueryPlan."""
#         plan = plan_query("Какие достижения?", use_graph_feature=True)
#
#         assert isinstance(plan.intent, Intent)
#         assert isinstance(plan.entities, list)
#         assert isinstance(plan.entity_policy, EntityPolicy)
#         assert isinstance(plan.use_graph, bool)
#         assert isinstance(plan.k_dense, int)
#         assert isinstance(plan.k_bm, int)
#         assert isinstance(plan.k_final, int)


class TestGraphStore:
    """Тесты для GraphStore."""

    def setup_method(self):
        """Сброс графа перед каждым тестом."""
        reset_graph_store()

    def test_add_and_get_node(self):
        """Добавление и получение узла."""
        store = get_graph_store()

        node = GraphNode(
            id="person:dmitry",
            type=NodeType.PERSON,
            name="Dmitry",
            slug="dmitry",
            data={"title": "Developer"},
        )
        store.add_node(node)

        retrieved = store.get_node("person:dmitry")
        assert retrieved is not None
        assert retrieved.name == "Dmitry"
        assert retrieved.type == NodeType.PERSON

    def test_get_node_by_slug(self):
        """Получение узла по slug."""
        store = get_graph_store()

        node = GraphNode(
            id="project:ai-portfolio",
            type=NodeType.PROJECT,
            name="AI-Portfolio",
            slug="ai-portfolio",
            data={},
        )
        store.add_node(node)

        retrieved = store.get_node_by_slug("ai-portfolio")
        assert retrieved is not None
        assert retrieved.id == "project:ai-portfolio"

    def test_add_and_get_edge(self):
        """Добавление и получение ребра."""
        store = get_graph_store()

        # Добавляем узлы
        person = GraphNode("person:dmitry", NodeType.PERSON, "Dmitry", "dmitry", {})
        company = GraphNode("company:alor", NodeType.COMPANY, "ALOR", "alor", {})
        store.add_node(person)
        store.add_node(company)

        # Добавляем ребро
        edge = GraphEdge(
            source_id="person:dmitry",
            target_id="company:alor",
            type=EdgeType.WORKS_AT,
            data={"is_current": True},
        )
        store.add_edge(edge)

        # Проверяем
        edges = store.get_outgoing_edges("person:dmitry", EdgeType.WORKS_AT)
        assert len(edges) == 1
        assert edges[0].target_id == "company:alor"

    def test_get_nodes_by_type(self):
        """Получение узлов по типу."""
        store = get_graph_store()

        store.add_node(GraphNode("tech:python", NodeType.TECHNOLOGY, "Python", "python", {}))
        store.add_node(GraphNode("tech:fastapi", NodeType.TECHNOLOGY, "FastAPI", "fastapi", {}))
        store.add_node(GraphNode("project:test", NodeType.PROJECT, "Test", "test", {}))

        tech_nodes = store.get_nodes_by_type(NodeType.TECHNOLOGY)
        assert len(tech_nodes) == 2

    def test_stats(self):
        """Получение статистики графа."""
        store = get_graph_store()

        store.add_node(GraphNode("p1", NodeType.PROJECT, "P1", "p1", {}))
        store.add_node(GraphNode("p2", NodeType.PROJECT, "P2", "p2", {}))
        store.add_node(GraphNode("t1", NodeType.TECHNOLOGY, "T1", "t1", {}))
        store.add_edge(GraphEdge("p1", "t1", EdgeType.USES, {}))

        stats = store.stats()
        assert stats["nodes"] == 3
        assert stats["edges"] == 1
        assert stats["nodes_by_type"]["PROJECT"] == 2
        assert stats["nodes_by_type"]["TECHNOLOGY"] == 1

    def test_clear(self):
        """Очистка графа."""
        store = get_graph_store()
        store.add_node(GraphNode("test", NodeType.PROJECT, "Test", "test", {}))
        store.clear()

        assert store.get_node("test") is None
        stats = store.stats()
        assert stats["nodes"] == 0


class TestGraphQuery:
    """Тесты для графовых запросов."""

    def setup_method(self):
        """Сброс графа перед каждым тестом."""
        reset_graph_store()
        reset_entity_registry()

    def test_achievements_query_returns_structure(self):
        """Запрос достижений возвращает правильную структуру."""
        store = get_graph_store()

        # Добавляем проект и достижение
        store.add_node(GraphNode(
            "project:test",
            NodeType.PROJECT,
            "Test Project",
            "test",
            {}
        ))
        store.add_node(GraphNode(
            "achievement:test-1",
            NodeType.ACHIEVEMENT,
            "First Achievement",
            "test-1",
            {"text": "Сократил время обработки на 50%", "project_slug": "test"}
        ))
        store.add_edge(GraphEdge(
            "project:test",
            "achievement:test-1",
            EdgeType.ACHIEVED,
            {}
        ))

        result = graph_query(Intent.ACHIEVEMENTS, entity_key=None)

        assert isinstance(result, GraphQueryResult)
        assert result.found is True
        assert len(result.items) >= 1
        assert result.confidence > 0

    def test_current_job_query(self):
        """Запрос текущего места работы."""
        store = get_graph_store()

        # Добавляем компанию с is_current=True
        store.add_node(GraphNode(
            "company:current",
            NodeType.COMPANY,
            "Current Company",
            "current",
            {"is_current": True, "role": "Senior Developer"}
        ))

        result = graph_query(Intent.CURRENT_JOB, entity_key=None)

        assert isinstance(result, GraphQueryResult)
        assert result.found is True
        assert len(result.items) >= 1

    def test_contacts_query(self):
        """Запрос контактов."""
        store = get_graph_store()

        store.add_node(GraphNode(
            "contact:email",
            NodeType.CONTACT,
            "Email",
            "email",
            {"kind": "email", "value": "test@example.com"}
        ))

        result = graph_query(Intent.CONTACTS, entity_key=None)

        assert isinstance(result, GraphQueryResult)
        assert result.found is True

    def test_empty_graph_returns_not_found(self):
        """Пустой граф возвращает found=False."""
        result = graph_query(Intent.ACHIEVEMENTS, entity_key=None)

        assert result.found is False
        assert len(result.items) == 0
        assert result.confidence == 0.0


class TestSearchTypes:
    """Тесты для типов данных."""

    def test_entity_creation(self):
        """Создание Entity."""
        entity = Entity(
            type=EntityType.PROJECT,
            slug="test",
            name="Test",
            confidence=0.9,
        )
        assert entity.slug == "test"
        assert entity.confidence == 0.9

    def test_search_result_creation(self):
        """Создание SearchResult."""
        result = SearchResult(
            query="test query",
            intent=Intent.GENERAL,
            entities=[],
            items=[],
            evidence="Some evidence",
            sources=[],
            confidence=0.8,
            found=True,
            used_graph=False,
        )
        assert result.query == "test query"
        assert result.found is True
        assert result.used_graph is False

    def test_graph_query_result_creation(self):
        """Создание GraphQueryResult."""
        result = GraphQueryResult(
            items=[{"name": "test"}],
            found=True,
            sources=["source1"],
            confidence=0.95,
            intent=Intent.ACHIEVEMENTS,
            entity_key="test",
        )
        assert result.found is True
        assert result.confidence == 0.95


# === Epic 3: Response Formatting Tests ===

from app.rag.formatter import FormatRenderer, format_not_found_response


class TestFormatRenderer:
    """Тесты для FormatRenderer (Epic 3)."""

    def test_removes_references(self):
        """Post-processing удаляет ссылки [1], [2]."""
        renderer = FormatRenderer()
        text = "Дмитрий работает с Python [1] и FastAPI [2]."
        result = renderer.post_process(text)
        assert "[1]" not in result
        assert "[2]" not in result
        assert "Python" in result
        assert "FastAPI" in result

    def test_removes_confidence(self):
        """Post-processing удаляет упоминания confidence."""
        renderer = FormatRenderer()
        text = "Результат с confidence: 0.85. Дмитрий - разработчик."
        result = renderer.post_process(text)
        assert "confidence" not in result.lower()
        assert "0.85" not in result
        assert "разработчик" in result

    def test_removes_tail_phrases(self):
        """Post-processing удаляет 'хвосты' про отсутствие данных."""
        renderer = FormatRenderer()
        text = "Дмитрий знает Python. Конкретных упоминаний больше не найдено."
        result = renderer.post_process(text)
        assert "не найдено" not in result
        assert "Python" in result

    def test_list_format_technologies(self):
        """Рендеринг технологий в маркированный список."""
        renderer = FormatRenderer(style_hint="LIST")
        items = [{"name": "Python"}, {"name": "FastAPI"}, {"name": "PostgreSQL"}]
        result = renderer.render_technologies(items)
        assert "- Python" in result
        assert "- FastAPI" in result
        assert "- PostgreSQL" in result

    def test_list_format_achievements(self):
        """Рендеринг достижений в маркированный список."""
        renderer = FormatRenderer()
        items = [
            {"text": "Сократил время обработки на 50%"},
            {"achievement": "Внедрил RAG систему"},
        ]
        result = renderer.render_achievements(items)
        assert "- Сократил время обработки на 50%" in result
        assert "- Внедрил RAG систему" in result

    def test_list_format_contacts(self):
        """Рендеринг контактов."""
        renderer = FormatRenderer()
        items = [
            {"kind": "email", "value": "test@example.com"},
            {"kind": "github", "url": "https://github.com/test"},
        ]
        result = renderer.render_contacts(items)
        assert "email:" in result.lower() or "email" in result
        assert "github:" in result.lower() or "github" in result

    def test_empty_items(self):
        """Пустой список возвращает пустую строку."""
        renderer = FormatRenderer()
        result = renderer.render_technologies([])
        assert result == ""

    def test_whitespace_cleanup(self):
        """Post-processing очищает лишние пробелы."""
        renderer = FormatRenderer()
        text = "Дмитрий   работает    в компании."
        result = renderer.post_process(text)
        assert "   " not in result
        assert "Дмитрий работает в компании" in result


class TestNotFoundResponses:
    """Тесты для ответов 'не найдено' (Epic 3)."""

    def test_not_found_technologies(self):
        """Ответ 'не найдено' для технологий короткий."""
        response = format_not_found_response(Intent.TECHNOLOGIES)
        assert len(response) < 100
        assert "нет" in response.lower()

    def test_not_found_achievements(self):
        """Ответ 'не найдено' для достижений."""
        response = format_not_found_response(Intent.ACHIEVEMENTS)
        assert len(response) < 100
        assert "нет" in response.lower()

    def test_not_found_project(self):
        """Ответ 'не найдено' для проекта."""
        response = format_not_found_response(Intent.PROJECT_DETAILS)
        assert "проект" in response.lower()

    def test_not_found_contacts(self):
        """Ответ 'не найдено' для контактов."""
        response = format_not_found_response(Intent.CONTACTS)
        assert "нет" in response.lower()

    def test_not_found_general(self):
        """Ответ 'не найдено' для общего запроса."""
        response = format_not_found_response(Intent.GENERAL)
        assert len(response) < 100


# === Промпты V2 тестируются только при наличии langchain_core ===
# Эти тесты пропускаются если langchain_core не установлен (локальная среда)

try:
    from app.rag.prompting import BASE_PROMPT_V2, STYLE_INSTRUCTIONS_V2
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False


@pytest.mark.skipif(not _HAS_LANGCHAIN, reason="langchain_core not installed")
class TestPromptingV2:
    """Тесты для промптов V2 (Epic 3)."""

    def test_base_prompt_v2_first_person(self):
        """V2 промпт содержит упоминание первого лица."""
        # Проверяем что промпт содержит инструкции о первом лице
        assert "я" in BASE_PROMPT_V2.lower() or "мой" in BASE_PROMPT_V2.lower()

    def test_base_prompt_v2_no_references(self):
        """V2 промпт запрещает ссылки [1], [2]."""
        assert "[1]" in BASE_PROMPT_V2 or "ссылки" in BASE_PROMPT_V2.lower()

    def test_base_prompt_v2_no_confidence(self):
        """V2 промпт запрещает упоминание confidence."""
        assert "confidence" in BASE_PROMPT_V2.lower()

    def test_style_instructions_v2_list(self):
        """V2 стиль LIST содержит инструкции о списках."""
        assert "LIST" in STYLE_INSTRUCTIONS_V2
        list_style = STYLE_INSTRUCTIONS_V2["LIST"]
        assert "список" in list_style.lower() or "дефис" in list_style.lower()

    def test_style_instructions_v2_ultrashort(self):
        """V2 стиль ULTRASHORT содержит инструкции о краткости."""
        assert "ULTRASHORT" in STYLE_INSTRUCTIONS_V2
        short_style = STYLE_INSTRUCTIONS_V2["ULTRASHORT"]
        assert "кратко" in short_style.lower()


try:
    from app.agent.graph import AGENT_SYSTEM_PROMPT_V2
    _HAS_AGENT = True
except ImportError:
    _HAS_AGENT = False
    AGENT_SYSTEM_PROMPT_V2 = ""


@pytest.mark.skipif(not _HAS_AGENT, reason="langchain_core not installed")
class TestAgentPromptV2:
    """Тесты для агентского промпта V2 (Epic 3)."""

    def test_agent_prompt_v2_exists(self):
        """Агентский промпт V2 существует."""
        assert AGENT_SYSTEM_PROMPT_V2 is not None
        assert len(AGENT_SYSTEM_PROMPT_V2) > 100

    def test_agent_prompt_v2_first_person(self):
        """Агентский промпт V2 содержит инструкции о первом лице."""
        assert "первого лица" in AGENT_SYSTEM_PROMPT_V2.lower() or "я" in AGENT_SYSTEM_PROMPT_V2

    def test_agent_prompt_v2_no_references(self):
        """Агентский промпт V2 запрещает ссылки."""
        assert "[1]" in AGENT_SYSTEM_PROMPT_V2

    def test_agent_prompt_v2_no_confidence(self):
        """Агентский промпт V2 запрещает confidence."""
        assert "confidence" in AGENT_SYSTEM_PROMPT_V2.lower()
