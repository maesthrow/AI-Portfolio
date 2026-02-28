# Feature Specification: Graph Concept Resolution for Concept Queries

**Feature Branch**: `008-improve-concept-queries`
**Created**: 2026-02-28
**Status**: Draft
**Input**: Запросы о широких концепциях (AI-агенты, Machine Learning, RAG) через граф знаний возвращают пустой результат, потому что Technology-ноды существуют только для конкретных инструментов (Python, LangChain), но не для абстрактных понятий.

## Clarifications

### Session 2026-02-28

- Q: Scope reduction — реализуем только FR-003 или все FR? → A: Только FR-003 (graph concept resolution). FR-001/002/004/005 (планнер, retrieval) исключены из scope — высокий риск регрессий.
- Q: Concept → TechCategory mapping: 1:1 или 1:N? → A: 1:1 (one concept → one TechCategory). Проще, безопаснее, zero false positives.

## Context & Root Cause Analysis

При тестировании spec-007 обнаружены 3 связанные проблемы:

1. **Планнер** генерирует разные планы для синонимичных запросов: "какой опыт с машинным обучением" использует `entity_id=technology:machine-learning` (не найден в графе), а "какой опыт с ml" использует `tech_category=ml_framework` (находит 4 проекта). Результаты кардинально различаются.

2. **Граф знаний** не содержит ноды для концепций (AI Agents, Machine Learning, RAG). Technology-ноды создаются только из таблицы `Technology` (конкретные инструменты: Python, LangChain, Docker), но не из абстрактных понятий. Запрос `graph_query(entity_key="ai-agents")` всегда возвращает пустой результат.

3. **Retrieval** не матчит кросс-языковые синонимы: поиск по "ии-агентами" не находит документ AI-Portfolio, хотя его `description_md` содержит "AI-агентом". BM25 не сопоставляет "ИИ" с "AI", а embedding similarity недостаточна для попадания в top-k.

**Scope этой спецификации**: решаем только проблему 2 (граф знаний). Проблемы 1 и 3 документированы как контекст, но НЕ входят в scope реализации.

## User Scenarios & Testing

### User Story 1 - Корректная обработка концептуальных запросов через граф (Priority: P1)

Когда планнер генерирует graph_query с entity_key для концепции (например, `entity_key="machine-learning"`), граф знаний вместо пустого результата маппит концепцию на соответствующую TechCategory и возвращает проекты, использующие технологии из этой категории.

**Why this priority**: Единственный FR в scope. Graph query для концепций сейчас всегда возвращает пустой результат — это теряет структурированные данные и вынуждает fallback на vector search.

**Independent Test**: Выполнить graph_query с entity_key для концепции ML или AI-agents и проверить что возвращается непустой результат с релевантными проектами.

**Acceptance Scenarios**:

1. **Given** граф содержит проекты с технологиями из категории `ml_framework`, **When** выполняется `_technologies_query(entity_key="machine-learning")`, **Then** граф возвращает проекты, использующие ML-технологии (вместо пустого результата).
2. **Given** граф содержит проекты с технологиями из категории `concept` (ReAct, LLM, RAG), **When** выполняется `_technologies_query(entity_key="ai-agents")`, **Then** граф возвращает проекты, использующие эти технологии.
3. **Given** entity_key="python" (существующая technology-нода), **When** выполняется `_technologies_query(entity_key="python")`, **Then** граф работает как раньше — находит ноду напрямую, concept mapping НЕ активируется.
4. **Given** entity_key="blockchain" (не существует ни как нода, ни как концепция), **When** выполняется `_technologies_query(entity_key="blockchain")`, **Then** граф возвращает пустой результат (как сейчас).

---

### Edge Cases

- Что если entity_key совпадает со slug существующей technology-ноды И с concept mapping? → Technology-нода приоритетнее, concept mapping не активируется.
- Что если concept не маппится ни на одну TechCategory (например, "DevOps")? → Пустой результат (текущее поведение сохраняется).
- Что если entity_key — неизвестный slug, не существующий ни в нодах, ни в concept mapping? → Пустой результат (текущее поведение сохраняется).

## Requirements

### Functional Requirements

- **FR-003**: Граф знаний ДОЛЖЕН маппить запросы о концепциях на соответствующую TechCategory (1:1 mapping), возвращая проекты с технологиями из этой категории, вместо пустого результата.
- **FR-006**: Система ДОЛЖНА сохранять обратную совместимость: запросы о конкретных технологиях (Python, PostgreSQL, LangChain) ДОЛЖНЫ продолжать работать через entity_id как раньше. Concept mapping активируется ТОЛЬКО когда entity_key не найден как technology-нода или project-нода в графе.

### Out of Scope

Следующие требования документированы в контексте, но НЕ реализуются в этой спецификации:

- ~~FR-001~~: Изменение промпта планнера для генерации `tech_category` вместо `entity_id` — высокий риск регрессий, влияет на ВСЕ запросы.
- ~~FR-002~~: Комбинирование graph_query + portfolio_search для концепций — зависит от FR-001.
- ~~FR-004~~: Кросс-языковые синонимы в retrieval (BM25) — средний риск, меняет ранжирование.
- ~~FR-005~~: Консистентность планов для синонимичных запросов — зависит от FR-001.

### Key Entities

- **Concept**: Абстрактное понятие (AI Agents, Machine Learning, RAG), маппится на одну TechCategory (1:1). Не является отдельной technology-нодой в графе, но разрешается через маппинг concept_slug → TechCategory.
- **TechCategory**: Категория технологий в графе (ml_framework, concept, language, etc.). Содержит конкретные technology-ноды и связанные с ними проекты.

## Success Criteria

### Measurable Outcomes

- **SC-003**: Graph query для концепций (ML, AI-agents, RAG) возвращает непустой результат с релевантными проектами, без необходимости fallback на vector search.
- **SC-004**: Все существующие тесты продолжают проходить без модификации (обратная совместимость).
- **SC-006**: Запросы о конкретных технологиях (Python, PostgreSQL, LangChain) продолжают работать через entity_id без регрессий.

### Out of Scope Criteria

Следующие критерии НЕ входят в scope этой спецификации (требуют FR-001/FR-004):

- ~~SC-001~~: Консистентность ответов на синонимичные запросы ("машинным обучением" vs "ml").
- ~~SC-002~~: Полнота ответа про AI-агентов (включение AI-Portfolio).
- ~~SC-005~~: Кросс-языковая эквивалентность ("ИИ-агенты" vs "AI agents").

## Assumptions

- Маппинг concept → TechCategory основан на существующей структуре TechCategory enum (не требует новых категорий).
- Список концепций для маппинга ограничен теми, что реально встречаются в портфолио: Machine Learning, AI Agents, RAG, Computer Vision, NLP.
- Маппинг 1:1 (один concept → одна TechCategory) достаточен для текущей задачи.
- Concept mapping активируется ТОЛЬКО как fallback в `_technologies_query()`, когда entity_key не найден ни как technology-нода, ни как project-нода.
- Изменения затрагивают только один файл: `app/graph/query.py`.
