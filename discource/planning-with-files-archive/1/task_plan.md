# Task Plan: Agent Identity vs Profile Detection

## Goal
Разграничить вопросы об агенте (identity) и о разработчике (profile) с помощью лингвистического анализа местоимений 2-го лица, добавить intent PROFILE с полноценным handler для данных о разработчике.

## Current Phase
COMPLETED

## Phases

### Phase 1: Исследование текущего кода
- [x] Изучить `identity/classifier.py` — текущая реализация
- [x] Изучить `planner/schemas_v3.py` — существующие intents
- [x] Изучить `planner/shortcuts.py` — текущие shortcuts
- [x] Изучить `graph/query.py` — существующие handlers
- [x] Изучить `rag_export.py` и `builder.py` — структура Profile
- **Status:** complete

### Phase 2: Реализация Identity Classifier
- [x] Добавить `_has_second_person_marker()` в `classifier.py`
- [x] Обновить `is_identity_question()` с приоритетом pronoun check
- [x] Добавить SECOND_PERSON_MARKERS константу
- **Status:** complete

### Phase 3: Реализация Intent PROFILE
- [x] Добавить `IntentV3.PROFILE` в `schemas_v3.py`
- [x] Добавить `Intent.PROFILE` в `search_types.py`
- [x] Обновить shortcut "кто такой" → intent: profile в `shortcuts.py`
- **Status:** complete

### Phase 4: Реализация Profile Query Handler
- [x] Добавить `_profile_query()` в `graph/query.py`
- [x] Зарегистрировать handler для Intent.PROFILE
- [x] Включить топ-5 технологий через KNOWS edges
- [x] Добавить `_build_profile_text()` helper
- **Status:** complete

### Phase 5: Добавление location в Profile Export
- [x] Добавить `location` в `ProfileExport` (`rag_export.py`)
- [x] Добавить `location` в PERSON node data (`builder.py`)
- **Status:** complete

### Phase 6: Тестирование
- [x] Проверить identity вопросы (ты, себя) — все PASS
- [x] Проверить profile вопросы (кто такой Дмитрий) — все PASS
- [x] Проверить синтаксис всех модулей — OK
- **Status:** complete

## Key Questions
1. Есть ли уже Intent.PROFILE в search_types.py? — НЕТ, добавлен
2. Как устроен mapping между IntentV3 и Intent? — через Intent(intent_lower) в graph_query_tool
3. Какие данные уже есть в PERSON node? — title, subtitle, current_position, hero_*, summary_md (+ location)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Pronoun check имеет приоритет над semantic | Детерминированное поведение, быстрее |
| Только русские маркеры | Целевая аудитория русскоязычная |
| Топ-5 технологий в profile | Добавит контекста без перегрузки |
| _check_semantic_similarity как отдельная функция | Чистый код, легко тестировать |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Нет ошибок | - | - |

## Files Modified
| File | Changes |
|------|---------|
| `services/rag-api-new/app/agent/identity/classifier.py` | +SECOND_PERSON_MARKERS, +_has_second_person_marker(), обновлён is_identity_question() |
| `services/rag-api-new/app/rag/search_types.py` | +Intent.PROFILE |
| `services/rag-api-new/app/agent/planner/schemas_v3.py` | +IntentV3.PROFILE |
| `services/rag-api-new/app/agent/planner/shortcuts.py` | "кто такой" → PROFILE, + location shortcut |
| `services/rag-api-new/app/graph/query.py` | +_profile_query(), +_build_profile_text(), зарегистрирован handler |
| `services/rag-api-new/app/agent/tools/graph_query_tool.py` | +profile fact_type detection |
| `services/content-api-new/app/schemas/rag_export.py` | +location в ProfileExport |
| `services/rag-api-new/app/schemas/export.py` | +location в ProfileExport (дублирующая схема) |
| `services/rag-api-new/app/graph/builder.py` | +location в PERSON node data |

## Notes
- Спецификация: `discource/specs/agent-identity-vs-profile-detection.md`
- Ключевой принцип: 2nd person marker → Identity, иначе → Profile/RAG
- Все тесты из спеки прошли успешно
