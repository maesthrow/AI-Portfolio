# ТЗ (v3): Универсальные интенты + таксономия технологий + строгий контроль роли (AI‑Portfolio / rag-api-new)

Дата: 2025‑12‑21  
Статус: обновление ТЗ v2 с учётом требования **не плодить узкие интенты**, а использовать **универсальные интенты + параметры (slots/filters)**.

---

## 0) Цель

Улучшить качество ответов агента без усложнения intent‑схемы за счёт:

1) **Таксономии технологий** (`Technology.category`) и использования её через **параметры** в существующих intents и tool‑вызовах.  
2) **ScopeGuard** (защита роли): отказ от оффтопа (“сказки” и т.п.).  
3) **Запрет на догадки** + **Grounding Verifier**: ответ не должен содержать сущности, которых нет в фактах.  
4) Исправление критической проблемы: self‑check должен улучшать именно **facts для Answer LLM**, а не только “evidence”.

---

## 1) Серьёзные дефекты, которые обязаны быть устранены (P0)

### P0‑1. Выход за рамки роли (оффтоп)
- Любые запросы не про портфолио Дмитрия → **вежливый отказ + возврат к теме** (без tool‑calls).

### P0‑2. Галлюцинации/догадки (“вероятно MySQL”)
- Запрещены предположения. Если данных нет — так и сказать.

### P0‑3. Ошибочное “присваивание” описаний проектов пользователю (кейсы типа ALOR)
- Для вопросов “чем занимался в компании X” агент обязан отвечать из **Experience** (роль/обязанности/период), а не из “описания проекта”.

---

## 2) Текущие intents остаются, но становятся параметризованными (универсальными)

### 2.1. Список intents (как есть)
- `current_job`
- `project_details`
- `project_achievements`
- `project_tech_stack`
- `technology_overview`
- `technology_usage`
- `experience_summary`
- `contacts`
- `general_unstructured`

### 2.2. Главное изменение: Planner возвращает **slots/filters** (параметры)
Вместо добавления узких интентов (`databases_overview/languages_overview/rag_usage`) вводится единый механизм:

- вопрос “какие языки?” → `intent=technology_overview` + `tech_filter.category=language`
- вопрос “какие БД?” → `intent=technology_overview` + `tech_filter.category=database`
- вопрос “где применял RAG?” → `intent=technology_usage` + `entities.technology_key="rag"` (или alias)
- вопрос “чем занимался в ALOR?” → `intent=experience_summary` + `scope.company_id="company:alor"` + `info_need="responsibilities"`

> Идея: intent отвечает за **тип операции**, а параметры — за **конкретизацию**.

---

## 3) Таксономия технологий (P0) — сохраняем, но используем через фильтры

### 3.1. Technology.category
Ввести типизацию `Technology.category`:

- `language`
- `database`
- `framework`
- `ml_framework` (опционально)
- `tool`
- `cloud`
- `library`
- `concept` (рекомендуется добавить для RAG/ReAct/LLM как понятий)
- `other`

### 3.2. Где хранить
- Источник истины: Postgres (content-api) → отдавать в ingest.
- Дублировать в graph (node metadata) и vector metadata.

### 3.3. Обязательные правила поведения
- “какие языки знает” → **только** `category=language`
- “какие БД использовал” → **только** `category=database`
- “какой стек/технологии” → можно группировать по категориям, но **не смешивать** в секции “Языки” то, что не language.

---

## 4) НОВАЯ универсальная схема плана (QueryPlanV3)

### 4.1. План должен возвращать структурный JSON (Pydantic)
Рекомендуемая модель:

```json
{
  "intent": "technology_overview",
  "entities": {
    "company_id": "company:alor|null",
    "project_id": "project:ai-portfolio|null",
    "technology_key": "rag|python|postgresql|null"
  },
  "tech_filter": {
    "category": "language|database|framework|tool|cloud|library|concept|other|null",
    "tags_any": ["ml","rag","llm"],
    "strict": true
  },
  "scope": {
    "level": "global|company|project",
    "company_id": "company:alor|null",
    "project_id": "project:...|null"
  },
  "info_need": "summary|details|achievements|tech_stack|usage|responsibilities|dates",
  "tool_plan": [
    { "tool": "graph_query_tool", "args": { "...": "..." } },
    { "tool": "portfolio_search_tool", "args": { "...": "..." } }
  ],
  "answer_style": { "format": "bullets|paragraph", "lang": "ru" }
}
```

### 4.2. Канонизация значений (P1)
В коде обязателен `normalize_plan()`:
- маппинг синонимов (`bulleted_list` → `bullets` и т.п.)
- заполнение дефолтов при отсутствии полей.

---

## 5) Обновление tool‑контрактов (P0)

### 5.1. graph_query_tool должен поддерживать фильтры
Добавить аргументы:
- `scope`: global/company/project
- `company_id`, `project_id`
- `technology_key` (или `technology_id`)
- `tech_category` (из taxonomy)
- `relation_types` (опционально)
- `limit`

**Ожидаемый результат:** структурные элементы, пригодные для factual ответа:
- опыт (роль, период, обязанности) — из Experience nodes/docs
- связи “проект → технологии”
- связи “технология → проекты (usage)”

### 5.2. portfolio_search_tool должен поддерживать filters + threshold
Добавить аргументы:
- `types`: ["experience","project","technology","achievement", ...]
- `filters`: { company_id?, project_id?, tech_category?, tags_any? }
- `min_score` (для vector)
- `top_k`

**Запрещено:** добирать количество документов без релевантности.

---

## 6) Исправление “опыт по компании” без нового узкого интента (P0)

**Требование:** вопросы вида:
- “чем занимался в компании X”
- “какая роль в X”
- “что делал в X”
должны маршрутизироваться как:

- `intent=experience_summary`
- `scope.level=company`, `scope.company_id=...`
- `info_need in {responsibilities, achievements, dates, role}`

и tool‑план обязан:
1) запросить опыт (Experience) по company_id (graph или retrieval с type=experience),
2) только потом (опционально) подтянуть связанные проекты.

**Запрет:** отвечать только `project_details` для company‑вопросов.

---

## 7) Self‑check (Critic) должен улучшать facts для Answer LLM (P0)

Если Critic запускает дополнительный поиск:
- результаты обязаны попадать в **единый EvidencePool**,
- затем пройти extraction в `FactBundle`,
- и быть использованы в финальном `rendered_facts` / `NormalizerOutput`.

Иначе self‑check может “найти правильное”, но ответ не улучшится (как в кейсе ALOR).

---

## 8) НОВЫЙ шаг: ScopeGuard (P0)

### 8.1. Интерфейс
`scope_guard(question, thread_context) -> { in_scope: bool, reason, suggested_prompts[] }`

### 8.2. Политика
- `OUT_OF_SCOPE` (сказки/развлечения/общие знания) → ответ без tools:
  - 1 строка отказа,
  - 2–3 примера вопросов по портфолио.

---

## 9) Grounding Verifier (P0)

### 9.1. Правило
Каждая “именованная сущность” в ответе (технология/БД/компания/проект/роль/дата):
- должна присутствовать в `FactBundle/NormalizerOutput`.

### 9.2. Действия при нарушении
- Автоматический rewrite ответа “строго по фактам”, **без добавления новых сущностей**.
- Если после rewrite невозможно ответить → честный ответ “в портфолио не найдено”.

**Цель:** исключить “MySQL”, “вероятно”, “можно предположить”.

---

## 10) Нормализация фактов (Normalizer) — обязательна (P0)

Перед Answer LLM применить детерминированные правила:

- Если `intent=technology_overview` и `tech_filter.category=database` → оставить только технологии категории database, лимитировать **после фильтрации**.
- Если `intent=technology_overview` и `category=language` → оставить только языки.
- Если `intent=technology_usage` и `technology_key=rag` → оставить только проекты/контексты, где явно отмечен RAG (по graph/metadata/tags).

---

## 11) Приёмочные тесты (минимум)

### A) Роль/оффтоп
- “расскажи сказку” → отказ + возврат к теме портфолио (без tools).

### B) Базы данных
- “какие БД использовал” → только БД, реально присутствующие в базе (без MySQL/догадок).

### C) Языки
- “какие языки программирования знает” → только `category=language`, без Next.js/.NET/Alembic.

### D) Опыт по компании
- “чем занимался в компании АЛОР” → роль/обязанности из Experience, а не описание “биржевой брокер”.

### E) RAG usage
- “где применял RAG” → перечисление проектов + 1–2 детали по применению, без новых выдуманных проектов.

---

## 12) План внедрения (приоритет)

**Этап 1 (P0):** ScopeGuard + запрет оффтопа  
**Этап 2 (P0):** Technology.category (в data + metadata) + фильтры в tools  
**Этап 3 (P0):** Маршрутизация company‑вопросов через `experience_summary + scope.company_id`  
**Этап 4 (P0):** Self‑check → FactBundle (объединение evidence и извлечение фактов)  
**Этап 5 (P0):** Grounding Verifier + rewrite/отказ  
**Этап 6 (P1):** normalize_plan() для устойчивых enum + регресс‑набор тестов

---

## 13) Deliverables

1) Pydantic схемы: `QueryPlanV3`, `TechFilter`, `Scope`, `FactBundle`, `NormalizerOutput`, `ScopeDecision`.
2) Обновлённые `graph_query_tool` и `portfolio_search_tool` с filters/category/min_score.
3) Реализация `ScopeGuard`, `Normalizer`, `GroundingVerifier`.
4) Исправление пайплайна self‑check: результаты влияют на финальные факты.
5) Регресс‑набор тест‑кейсов (10–20) и запуск в CI (опционально).

---

## 14) Примечание по “узким интентам”
Интенты `databases_overview/languages_overview/rag_usage` **не вводим**.  
Их функциональность реализуется через:
- `technology_overview + tech_filter.category=...`
- `technology_usage + entities.technology_key=...`
- `experience_summary + scope.company_id=...`

Таким образом intent‑схема остаётся универсальной и стабильной, а точность достигается типизацией и фильтрами.
