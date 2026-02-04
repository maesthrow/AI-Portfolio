# Findings & Decisions

## Requirements
- Разграничить вопросы об агенте ("кто ты") и о разработчике ("кто такой Дмитрий")
- Вопросы с местоимениями 2-го лица → Identity (про агента)
- Вопросы без 2nd person markers → Profile/RAG (про разработчика)
- Добавить intent PROFILE для запроса данных о PERSON node
- Добавить поле `location` в ProfileExport

## Research Findings

### Лингвистические маркеры 2-го лица (из спеки)
```python
SECOND_PERSON_MARKERS = {
    # Личные местоимения
    "ты", "тебя", "тебе", "тобой", "тобою",
    # Возвратные
    "себя", "себе", "собой", "собою",
    # Притяжательные
    "твой", "твоя", "твои", "твоё", "твоему", "твоей",
}
```

### Правило классификации
- Есть 2nd person marker → Identity (confidence=1.0)
- Нет marker → semantic similarity check → если < threshold → Profile/RAG

### Edge Cases (из спеки)
| Вопрос | Маркер | Результат |
|--------|--------|-----------|
| "кто ты такой" | ты | Identity |
| "Дмитрий, расскажи о себе" | себе | Identity |
| "кто такой Дмитрий" | нет | Profile |
| "кто он такой" | нет | Profile |

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Pronoun check в classifier.py | Single Responsibility, вся identity логика в одном месте |
| Intent.PROFILE отдельно от EXPERIENCE_SUMMARY | Profile = данные о человеке, Experience = компании/роли |
| location не status в export | status — UI fallback, current_position достаточно для RAG |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| ProfileExport.location AttributeError | Дублирующая схема в rag-api-new не была обновлена |

## Lessons Learned

### Дублирующие схемы между сервисами
**Ошибка:** При добавлении `location` в ProfileExport обновил только `content-api-new`, забыв про `rag-api-new`.

**Причина:** Не выполнил поиск всех определений класса в Phase 1.

**Правило на будущее:** При изменении Pydantic-схем **всегда** искать все вхождения:
```bash
grep -rn "class ИмяКласса" --include="*.py"
```

**Архитектура проекта:**
- `content-api-new/app/schemas/rag_export.py` — источник (отдаёт JSON)
- `rag-api-new/app/schemas/export.py` — получатель (валидирует JSON)
- Обе схемы должны быть синхронизированы вручную (нет shared library)

## Resources
- Спецификация: `discource/specs/agent-identity-vs-profile-detection.md`
- Identity classifier: `services/rag-api-new/app/agent/identity/classifier.py`
- Planner schemas: `services/rag-api-new/app/agent/planner/schemas_v3.py`
- Graph query: `services/rag-api-new/app/graph/query.py`
- RAG export: `services/content-api-new/app/schemas/rag_export.py`
- Graph builder: `services/rag-api-new/app/graph/builder.py`

## Visual/Browser Findings
- Пока нет

---

## Session: 2026-02-04 - Agent Looping Fix

### Проблема: Зацикливание агента
**Симптом:** Агент отвечал "Такой информации нет в портфолио" 5+ раз подряд на вопрос "в каком городе живет Дмитрий".

**Корневая причина:**
1. `_profile_query()` возвращает `found=True` всегда, когда PERSON node существует
2. Но если `location=None` в данных, Answer LLM генерирует "нет информации"
3. Агент видит `found=True` + ответ "нет" → **противоречие**
4. LangGraph ReAct агент интерпретирует это как "нужно больше данных" → вызывает tool снова
5. Бесконечный цикл

**Схема ошибки:**
```
Agent → portfolio_rag_tool("в каком городе")
    → _profile_query() returns found=True (PERSON exists)
    → But location=None in data
    → Answer LLM: "Такой информации нет"
    → Agent sees found=True but answer="нет" → retry
    → LOOP!
```

### Исправление
**Файл:** `services/rag-api-new/app/agent/rag_tool.py`

Добавлена синхронизация `found` с содержимым ответа:
```python
def _looks_like_not_found(answer: str) -> bool:
    """Check if answer text indicates 'not found' response."""
    a = (answer or "").strip().lower()
    needles = ("такой информации нет", "нет в портфолио", ...)
    return (len(a) <= 250) and any(n in a for n in needles)

# В return блоке:
actual_found = payload.found
if actual_found and _looks_like_not_found(answer):
    actual_found = False  # Override to prevent agent loops
```

### Почему location=None
**Возможные причины:**
1. Seeder не был перезапущен после добавления location в БД
2. Данные не были переингестированы после изменений кода

**Для исправления данных необходимо:**
```bash
# 1. Пересеять БД (content-api-new)
cd services/content-api-new
python -m app.seed.seed_ai_portfolio_new

# 2. Переингестировать данные (rag-api-new)
# GET http://localhost:8003/api/v1/rag/export → payload
# POST http://localhost:8014/api/v1/ingest/batch с payload

# 3. Очистить кэш
# DELETE http://localhost:8014/api/v1/admin/cache
```

### Файлы изменены
| Файл | Изменения |
|------|-----------|
| `services/rag-api-new/app/agent/rag_tool.py` | +`_looks_like_not_found()`, синхронизация found с answer |
| `services/rag-api-new/app/agent/answer/prompts.py` | +NOT_FOUND_BY_INTENT["profile"] |

---
*Update this file after every 2 view/browser/search operations*
