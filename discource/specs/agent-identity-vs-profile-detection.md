# Agent Identity vs Profile Detection

> **Дата:** 2026-02-03
> **Статус:** Анализ завершён, готово к реализации
> **Связанные файлы:**
> - `services/rag-api-new/app/agent/identity/classifier.py`
> - `services/rag-api-new/app/agent/identity/prompts.py`
> - `services/rag-api-new/app/agent/planner/shortcuts.py`
> - `services/rag-api-new/app/graph/query.py`
> - `services/content-api-new/app/schemas/rag_export.py`

---

## 1. Проблема

### 1.1 Вопрос "кто такой Дмитрий" даёт неполный ответ

**Текущий flow:**
```
"кто такой Дмитрий"
    ↓ (shortcut срабатывает)
intent: EXPERIENCE_SUMMARY
    ↓ (graph_query_tool)
_experience_query()
    ↓
Возвращает ТОЛЬКО компании (NodeType.COMPANY)
❌ НЕ возвращает данные PERSON node!
```

**Что пользователь ожидает:**
- Кто он (full_name, title, subtitle)
- Чем занимается (summary_md, current_position)
- Краткое описание (hero_description)
- Где находится (location)

**Что получает:**
- Только список компаний с ролями (без профильной информации о человеке)

**Корневая причина:** В `graph/query.py` нет handler для запроса данных о PERSON node. Функция `_experience_query()` возвращает только COMPANY nodes.

### 1.2 Нет разграничения между вопросами об агенте и о разработчике

**Проблемные примеры:**

| Вопрос | Текущий результат | Ожидаемый результат |
|--------|-------------------|---------------------|
| "кто ты такой" | Может попасть в shortcut "кто такой" → Profile | Identity (про агента) |
| "расскажи о себе" | RAG search | Identity (про агента) |
| "кто такой Дмитрий" | Profile/RAG | Profile (правильно) |

### 1.3 Потеря поля `location` при экспорте в RAG

**ProfileExport** (rag_export.py) не включает поле `location`:

```python
class ProfileExport(BaseModel):
    id: int
    full_name: str
    title: str
    subtitle: str | None = None
    summary_md: str | None = None
    hero_headline: str | None = None
    hero_description: str | None = None
    current_position: str | None = None
    # ❌ НЕТ: location
    # ⚠️ status — не нужен (только для UI, есть current_position)
```

**В seeder есть:**
```python
PROFILE_DATA = {
    "location": "Самара, Россия",  # ✅ задано, но теряется
    ...
}
```

**Примечание:** Поле `status` не нужно передавать в RAG — это fallback для UI, если нет `current_position` (см. HeroIntro.tsx строка 42).

---

## 2. Анализ: Лингвистический паттерн

### 2.1 Ключевое наблюдение

**Вопросы об агенте** (identity) используют местоимения **2-го лица** и **возвратные**:
- "кто **ты**", "**ты** кто такой"
- "что **ты** умеешь"
- "расскажи о **себе**"
- "как **тебя** зовут"

**Вопросы о разработчике** (profile) используют **3-е лицо** или **имя**:
- "кто такой **Дмитрий**"
- "кто **он** такой"
- "расскажи о **разработчике**"
- "кто **автор** сайта"

### 2.2 Маркеры 2-го лица (русский язык)

```python
SECOND_PERSON_MARKERS = {
    # Личные местоимения 2-го лица
    "ты", "тебя", "тебе", "тобой", "тобою",

    # Возвратные местоимения (о себе = об агенте в контексте вопроса)
    "себя", "себе", "собой", "собою",

    # Притяжательные местоимения 2-го лица
    "твой", "твоя", "твои", "твоё", "твоему", "твоей",
}
```

### 2.3 Правило классификации

```
Вопрос содержит 2nd person marker?
    ↓ Да                    ↓ Нет
Identity Question      → Semantic check / Profile shortcut
(про агента)           (про разработчика или RAG)
```

**Принцип:** Наличие 2nd person marker имеет **приоритет**. Если есть "ты/себя" — это обращение к агенту, даже если упомянуто имя.

---

## 3. Edge Cases

| Вопрос | Маркер | Результат | Обоснование |
|--------|--------|-----------|-------------|
| "кто ты такой" | **ты** | Identity | Прямое обращение к агенту |
| "ты кто такой, Дмитрий?" | **ты** | Identity | "Дмитрий" в vocative (звательный падеж) — обращение к агенту по имени |
| "Дмитрий, расскажи о себе" | **себе** | Identity | Команда агенту рассказать о себе |
| "расскажи о себе" | **себе** | Identity | Рефлексивное → об агенте |
| "кто такой Дмитрий" | нет | Profile | Нет 2nd person → profile/RAG |
| "кто он такой" | нет | Profile | "он" = 3rd person |
| "расскажи о Дмитрии" | нет | Profile | Нет 2nd person → profile |
| "кто автор сайта" | нет | Profile | Нет 2nd person → profile |

---

## 4. Решение

### 4.1 Добавить Intent `PROFILE` с отдельным handler

**Новый intent в `schemas_v3.py`:**
```python
class IntentV3(str, Enum):
    PROFILE = "profile"  # Информация о разработчике (PERSON node)
    # ... остальные
```

**Новый handler в `query.py`:**
```python
def _profile_query() -> GraphQueryResult:
    """Запрос информации о разработчике (PERSON node)."""
    store = get_graph_store()
    persons = store.get_nodes_by_type(NodeType.PERSON)

    if not persons:
        return GraphQueryResult(items=[], found=False, ...)

    person = persons[0]  # Единственный PERSON

    # Текущая компания
    current_company = None
    for c in store.get_nodes_by_type(NodeType.COMPANY):
        if c.data.get("is_current"):
            current_company = c
            break

    item = {
        "name": person.name,
        "title": person.data.get("title"),
        "subtitle": person.data.get("subtitle"),
        "current_position": person.data.get("current_position"),
        "summary_md": person.data.get("summary_md"),
        "hero_headline": person.data.get("hero_headline"),
        "hero_description": person.data.get("hero_description"),
        "location": person.data.get("location"),
        "current_company": current_company.name if current_company else None,
        "current_role": current_company.data.get("role") if current_company else None,
    }

    return GraphQueryResult(
        items=[item],
        found=True,
        sources=[_node_to_source(person)],
        confidence=0.95,
        intent=Intent.PROFILE,
    )
```

### 4.2 Расширить Identity Classifier

**Размещение:** В `identity/classifier.py` (Вариант A)

**Обоснование:**
- Pronoun check — это **часть** identity classification
- Single Responsibility: модуль отвечает за "определение identity вопросов"
- Не создаём лишних абстракций для простой функции
- Вся логика "это identity вопрос?" в одном месте

**Изменения в `is_identity_question()`:**
```python
def is_identity_question(question: str, threshold: float = SIMILARITY_THRESHOLD) -> tuple[bool, float]:
    # 1. Quick check: 2nd person pronouns → definitely identity
    if _has_second_person_marker(question):
        logger.info("Identity detected by pronoun marker: %r", question)
        return True, 1.0  # confidence = 1.0 (deterministic)

    # 2. Fallback: semantic similarity (для нестандартных формулировок)
    return _check_semantic_similarity(question, threshold)


def _has_second_person_marker(text: str) -> bool:
    """Проверяет наличие местоимений 2-го лица и возвратных."""
    SECOND_PERSON_MARKERS = {
        "ты", "тебя", "тебе", "тобой", "тобою",
        "себя", "себе", "собой", "собою",
        "твой", "твоя", "твои", "твоё", "твоему", "твоей",
    }
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return bool(words & SECOND_PERSON_MARKERS)
```

### 4.3 Обновить Shortcut для Profile

**В `shortcuts.py`:**
```python
# Кто такой Дмитрий / о разработчике → Profile (не Experience!)
r"кто такой|кто это|кто он|о разработчике|про разработчика|об авторе|про автора": QueryPlanV3(
    intents=[IntentV3.PROFILE],  # ← Изменено с EXPERIENCE_SUMMARY
    entities=[],
    tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "profile"})],
    render_style=RenderStyleV3.PARAGRAPH,
    answer_style=AnswerStyleV3.NATURAL_RU,
    confidence=0.95,
),
```

### 4.4 Добавить `location` в ProfileExport

**В `rag_export.py`:**
```python
class ProfileExport(BaseModel):
    id: int
    full_name: str
    title: str
    subtitle: str | None = None
    summary_md: str | None = None
    hero_headline: str | None = None
    hero_description: str | None = None
    current_position: str | None = None
    location: str | None = None  # ← ДОБАВИТЬ
```

**В `builder.py` (PERSON node data):**
```python
store.add_node(GraphNode(
    id=person_id,
    type=NodeType.PERSON,
    name=p.full_name,
    slug="dmitry",
    data={
        "title": p.title,
        "subtitle": p.subtitle,
        "current_position": p.current_position,
        "hero_headline": p.hero_headline,
        "hero_description": p.hero_description,
        "summary_md": p.summary_md,
        "location": p.location,  # ← ДОБАВИТЬ
    }
))
```

---

## 5. Итоговый Flow

```
User Question
    ↓
[Identity Classifier]
├─ _has_second_person_marker()? → YES → Identity Response (про агента)
└─ NO → semantic similarity check
         ├─ similarity >= 0.92 → Identity Response
         └─ similarity < 0.92 → Continue to Planner
    ↓
[Scope Guard] → in_scope check
    ↓
[Shortcuts / Planner]
├─ "кто такой" pattern → Intent: PROFILE
├─ "контакты" pattern → Intent: CONTACTS
├─ ... other patterns
└─ No match → LLM Planner
    ↓
[Graph Query Tool]
├─ intent: profile → _profile_query() → PERSON node data
├─ intent: experience → _experience_query() → COMPANY nodes
└─ ... other intents
    ↓
[Answer LLM] → Response
```

---

## 6. Открытые вопросы

### 6.1 Английские маркеры

Нужно ли добавлять английские маркеры? ("you", "yourself", "your")

**Рекомендация:** Пока только русский. Если появятся англоязычные пользователи — добавить.

### 6.2 Технологии в Profile ответе

Включать ли ключевые технологии (через KNOWS edges) в ответ на "кто такой"?

**Рекомендация:** Да, топ-5 технологий добавят контекста. Реализовать в `_profile_query()`.

---

## 7. Файлы для изменения

| Файл | Изменение |
|------|-----------|
| `services/rag-api-new/app/agent/identity/classifier.py` | Добавить `_has_second_person_marker()`, обновить `is_identity_question()` |
| `services/rag-api-new/app/agent/planner/schemas_v3.py` | Добавить `IntentV3.PROFILE` |
| `services/rag-api-new/app/agent/planner/shortcuts.py` | Обновить shortcut для "кто такой" → intent: profile |
| `services/rag-api-new/app/graph/query.py` | Добавить `_profile_query()`, зарегистрировать в handlers |
| `services/rag-api-new/app/rag/search_types.py` | Добавить `Intent.PROFILE` (если нужно для legacy mapping) |
| `services/content-api-new/app/schemas/rag_export.py` | Добавить `location` в `ProfileExport` |
| `services/rag-api-new/app/graph/builder.py` | Добавить `location` в PERSON node data |
| `services/rag-api-new/app/indexing/normalizer.py` | Добавить `location` в profile docs metadata |

---

## 8. Тест-кейсы

После реализации проверить:

```python
# Identity (про агента)
assert is_identity("кто ты") == True
assert is_identity("ты кто такой") == True
assert is_identity("расскажи о себе") == True
assert is_identity("что ты умеешь") == True
assert is_identity("Дмитрий, кто ты?") == True  # vocative

# Profile (про разработчика)
assert is_identity("кто такой Дмитрий") == False
assert is_identity("кто он такой") == False
assert is_identity("расскажи о разработчике") == False
assert is_identity("кто автор сайта") == False

# Profile query возвращает данные
profile_result = graph_query(Intent.PROFILE)
assert profile_result.found == True
assert "Дмитрий" in profile_result.items[0]["name"]
assert profile_result.items[0]["location"] == "Самара, Россия"
```
