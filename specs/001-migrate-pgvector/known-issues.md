# Known Issues — Post-Migration pgvector

Обнаружены при тестировании агента после миграции ChromaDB → pgvector.
**НЕ связаны с миграцией** — это pre-existing проблемы, ставшие видимыми при E2E тестировании.

Дата: 2026-02-24, ветка: `001-migrate-pgvector`

---

## ISSUE-001: Planner NoneType на первой попытке (CRITICAL)

**Симптом**: `with_structured_output(QueryPlanV3, method="json_schema")` возвращает `parsed=None` при первом вызове GigaChat-2. Retry через `PLANNER_REPAIR_PROMPT` срабатывает, но тратит двойные токены и +5-10с латентности.

**Файл**: `services/rag-api-new/app/agent/planner/planner_llm.py:106`

**Причина**: GigaChat-2 нестабильно поддерживает `json_schema` mode для structured output. Первый ответ часто невалидный JSON.

**Варианты решения**:
1. Переключить `PLANNER_LLM` на `deepseek:deepseek-chat` (лучше поддерживает structured output)
2. Попробовать `method="function_calling"` вместо `"json_schema"` для GigaChat
3. Добавить prompt-level JSON instructions в `PLANNER_SYSTEM_PROMPT` для надёжности GigaChat

**Влияние**: +5-10с латентности, +~1500 токенов на retry, каскадно вызывает ISSUE-002.

---

## ISSUE-002: Planner confidence=0.00 при успешном плане (HIGH)

**Симптом**: После retry планнер генерирует валидный `QueryPlanV3` с intent=`experience_summary`, но `confidence=0.00`. Это принудительно запускает hybrid search (rag_tool.py:140: `if plan_confidence < 0.5`).

**Файл**: `services/rag-api-new/app/agent/rag_tool.py:140-148`

**Причина**: GigaChat-2 при retry (с repair prompt) не заполняет поле `confidence` корректно — вероятно, оно остаётся дефолтным (0.0).

**Варианты решения**:
1. В `_sanitize_plan()` — если confidence=0.0, но план валиден и есть intents+tool_calls, выставить минимум 0.5
2. Переключить PLANNER_LLM на deepseek (решит и ISSUE-001, и ISSUE-002)
3. Изменить порог в rag_tool.py: использовать confidence < 0.3 вместо < 0.5

**Влияние**: Лишний цикл hybrid search (+10-15с), лишние токены на retrieval.

---

## ISSUE-003: Reranker неэффективен на русском языке (MEDIUM)

**Симптом**: `bge-reranker-base` даёт scores ~0.001-0.003 для русскоязычных запросов. Для сравнения, нормальные релевантные документы должны иметь scores >0.1.

**Наблюдение**: Запрос "был ли опыт в качестве архитектора агентов" → 8 документов из hybrid search, все с reranker score ~0.001. Reranker фактически не различает релевантные и нерелевантные документы.

**Файл**: `services/rag-api-new/app/rag/rank.py`

**Причина**: `BAAI/bge-reranker-base` обучен преимущественно на английских данных. Русскоязычные запросы и документы он оценивает с крайне низкими скорами.

**Варианты решения**:
1. Заменить на `BAAI/bge-reranker-v2-m3` (мультиязычный, поддерживает русский)
2. Отключить reranker для русского языка, полагаясь на RRF merge
3. Нормализовать scores reranker'а по диапазону (min-max scaling)

**Влияние**: Reranker не улучшает (но и не ухудшает) качество ранжирования для русских запросов. Тратит ~1.3с CPU впустую.

---

## ISSUE-004: Agent LLM потребляет 88% токенов (HIGH)

**Симптом**: Из 15,495 токенов на один запрос, agent LLM (ReAct orchestration) потребляет ~13,625 токенов. Остальные роли (planner, answer) — только ~1,870.

**Файл**: `services/rag-api-new/app/agent/graph.py` (AGENT_SYSTEM_PROMPT)

**Причина**: ReAct агент получает большой system prompt + tool descriptions + историю сообщений. GigaChat-2 также может быть не оптимален для ReAct-формата.

**Варианты решения**:
1. Сократить `AGENT_SYSTEM_PROMPT` — убрать дублирующие инструкции
2. Переключить `AGENT_LLM` на `deepseek:deepseek-chat` (дешевле per-token)
3. Ограничить `max_tokens` для agent LLM
4. Рассмотреть прямой вызов RAG tool без ReAct loop для простых вопросов

**Влияние**: При лимите 50,000 tokens/час пользователь может сделать ~3-5 запросов. При 15,000 tokens/минуту (текущие тестовые настройки) — 1 запрос блокирует лимит.

---

## ISSUE-005: Rate Limit настройки для тестирования (LOW)

**Симптом**: `settings.py:138-142` установлен rate limit 15,000 tokens / 60 секунд (тестовый режим). Один запрос на ~15,500 токенов превышает лимит, второй запрос блокируется.

**Файл**: `services/rag-api-new/app/settings.py:138-142`

```python
rate_limit_ip_tokens: int = 15_000  # 50_000
rate_limit_window_seconds: int = 60  # 3600
```

**Решение**: Для prod вернуть закомментированные значения: 50,000 tokens / 3600 сек. Для тестов — поднять до 100,000 / 60 сек или отключить.

---

## ISSUE-006: Общая латентность ~52 секунды (HIGH)

**Симптом**: Полный цикл обработки запроса занимает ~52 секунд. Breakdown:
- Router LLM classification: ~1-2с
- Planner (attempt 1 + retry): ~10-15с
- Graph query execution: ~2-3с
- Hybrid search (forced by low confidence): ~15-20с
- Normalizer + FactBundle: ~1с
- Answer LLM: ~5-10с
- Grounding verification: ~1с

**Целевое значение**: <15с (SC-002 в spec.md: "не более 10% деградации от baseline").

**Основные bottleneck'и**:
1. Planner retry из-за ISSUE-001 (+10с)
2. Forced hybrid search из-за ISSUE-002 (+15с)
3. GigaChat API latency (>DeepSeek для structured output)

**Варианты решения**: Решение ISSUE-001 и ISSUE-002 должно сократить время до ~25-30с. Дальнейшая оптимизация — переход на DeepSeek для planner/agent.

---

## Приоритеты

| Issue | Severity | Effort | Impact on UX | Quick Fix |
|-------|----------|--------|-------------|-----------|
| ISSUE-001 | CRITICAL | Low | Высокий (latency + tokens) | Сменить PLANNER_LLM на deepseek |
| ISSUE-002 | HIGH | Low | Высокий (лишний search) | Минимум confidence=0.5 в sanitize |
| ISSUE-004 | HIGH | Medium | Высокий (token budget) | Сократить AGENT_SYSTEM_PROMPT |
| ISSUE-006 | HIGH | — | Высокий (UX) | Следствие 001+002 |
| ISSUE-003 | MEDIUM | Medium | Средний (качество) | bge-reranker-v2-m3 |
| ISSUE-005 | LOW | Trivial | Низкий (только тесты) | env variable change |

---

## Связь с миграцией pgvector

Все issue **НЕ вызваны миграцией**. Миграция ChromaDB → pgvector прошла успешно:
- Ingest: 87 документов загружены корректно
- Graph: 81 нод, 163 ребра — корректно
- Retrieval (dense + BM25 + RRF): работает
- Admin endpoints (stats, truncate): работают
- Prefetch: 33 cache hits, 6 shortcuts — работает

Проблемы обнаружены в слоях **выше** vector store: planner LLM, reranker model, agent token consumption.
