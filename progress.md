# Progress Log

## Session: 2026-02-03

### Phase 1: Исследование текущего кода
- **Status:** complete
- **Started:** 2026-02-03
- Actions taken:
  - Прочитана спецификация `discource/specs/agent-identity-vs-profile-detection.md`
  - Изучен classifier.py — только semantic matching, нет pronoun check
  - Изучен schemas_v3.py — IntentV3 без PROFILE
  - Изучен shortcuts.py — "кто такой" → EXPERIENCE_SUMMARY
  - Изучен query.py — нет _profile_query, только _experience_query
  - Изучен rag_export.py — ProfileExport без location
  - Изучен builder.py — PERSON node без location
- Files created/modified:
  - task_plan.md (created)
  - findings.md (created)
  - progress.md (created)

### Phase 2: Реализация Identity Classifier
- **Status:** complete
- Actions taken:
  - Добавлен import re
  - Добавлена константа SECOND_PERSON_MARKERS (frozenset)
  - Добавлена функция _has_second_person_marker()
  - Обновлена is_identity_question() с приоритетом pronoun check
  - Выделена _check_semantic_similarity() для чистоты кода
- Files created/modified:
  - classifier.py (modified)

### Phase 3: Реализация Intent PROFILE
- **Status:** complete
- Actions taken:
  - Добавлен Intent.PROFILE в search_types.py
  - Добавлен IntentV3.PROFILE в schemas_v3.py
  - Обновлён shortcut "кто такой" → IntentV3.PROFILE
- Files created/modified:
  - search_types.py (modified)
  - schemas_v3.py (modified)
  - shortcuts.py (modified)

### Phase 4: Реализация Profile Query Handler
- **Status:** complete
- Actions taken:
  - Добавлена функция _profile_query() в query.py
  - Добавлена функция _build_profile_text() для форматирования
  - Зарегистрирован Intent.PROFILE в handlers dict
  - Реализован топ-5 технологий через KNOWS edges с сортировкой по использованию
- Files created/modified:
  - query.py (modified)
  - graph_query_tool.py (modified - добавлен profile fact_type)

### Phase 5: Добавление location в Profile Export
- **Status:** complete
- Actions taken:
  - Добавлено поле location в ProfileExport
  - Добавлено location в PERSON node data в builder.py
- Files created/modified:
  - rag_export.py (modified)
  - builder.py (modified)

### Phase 6: Тестирование
- **Status:** complete
- Actions taken:
  - Протестирована функция _has_second_person_marker()
  - Проверены все импорты модулей
  - Все тесты из спецификации прошли
- Files created/modified:
  - task_plan.md (updated)
  - progress.md (updated)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Identity: "кто ты" | _has_second_person_marker | True | True | PASS |
| Identity: "ты кто такой" | _has_second_person_marker | True | True | PASS |
| Identity: "расскажи о себе" | _has_second_person_marker | True | True | PASS |
| Identity: "что ты умеешь" | _has_second_person_marker | True | True | PASS |
| Identity: "как тебя зовут" | _has_second_person_marker | True | True | PASS |
| Identity: "Дмитрий, кто ты?" | _has_second_person_marker | True | True | PASS |
| Profile: "кто такой Дмитрий" | _has_second_person_marker | False | False | PASS |
| Profile: "кто он такой" | _has_second_person_marker | False | False | PASS |
| Profile: "расскажи о разработчике" | _has_second_person_marker | False | False | PASS |
| Profile: "кто автор сайта" | _has_second_person_marker | False | False | PASS |
| Import: classifier | python import | OK | OK | PASS |
| Import: Intent.PROFILE | python import | OK | OK | PASS |
| Import: IntentV3.PROFILE | python import | OK | OK | PASS |
| Import: _profile_query | python import | OK | OK | PASS |
| Import: ProfileExport.location | python import | OK | OK | PASS |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-02-03 | AttributeError: 'ProfileExport' object has no attribute 'location' | 1 | Добавлено location в rag-api-new/app/schemas/export.py (дублирующий ProfileExport) |
| 2026-02-03 | "где живет" → "нет информации" | 1 | Добавлен shortcut для location вопросов в shortcuts.py |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | COMPLETED - все фазы завершены |
| Where am I going? | Задача выполнена |
| What's the goal? | Разграничить identity/profile вопросы |
| What have I learned? | См. findings.md |
| What have I done? | Реализованы все изменения из спецификации |

---
*Session completed successfully*

## Session: 2026-02-04

### Phase 1: Диагностика зацикливания агента
- **Status:** complete
- Actions taken:
  - Изучен `graph.py` - agent system prompt и create_agent
  - Изучен `rag_tool.py` - пайплайн и return structure
  - Изучен `query.py` - `_profile_query()` всегда возвращает `found=True`
  - Изучен `answer_llm.py` - генерация "нет информации" при отсутствии данных
  - Изучен `prompts.py` - NOT_FOUND_BY_INTENT без "profile"
- Root cause identified:
  - `_profile_query()` returns `found=True` когда PERSON exists
  - Answer LLM returns "нет информации" когда location=None
  - Противоречие вызывает retry loop в LangGraph ReAct agent

### Phase 2: Исправление зацикливания
- **Status:** complete
- Actions taken:
  - Добавлена функция `_looks_like_not_found()` в rag_tool.py
  - Добавлена синхронизация `found` с содержимым ответа
  - Добавлен NOT_FOUND_BY_INTENT["profile"] в prompts.py
- Files modified:
  - `services/rag-api-new/app/agent/rag_tool.py`
  - `services/rag-api-new/app/agent/answer/prompts.py`

### Pending: Данные location
- Необходимо пересеять БД и переингестировать данные
- См. findings.md для инструкций

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-02-04 | Agent looping 5+ times | 1 | Добавлена синхронизация found с answer content |
