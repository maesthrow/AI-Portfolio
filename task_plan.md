# Task Plan: Thinking Status Indicators для AI-агента

## Goal
Добавить текстовые статусы этапов работы агента (thinking indicators) в чат — реальные события с бэкенда, отображаемые под бабблом агента с fade-анимацией и минимальной задержкой 800мс между сменами.

## Current Phase
Phase 6 (Hotfix) — complete. Ожидает runtime-тестирования.

## Решения по дизайну (согласовано с пользователем)
- **Подход A** — реальные статусы с бэкенда (не фейковые таймеры)
- **Размещение** — Вариант B: отдельная строка под бабблом агента, мелкий mono-текст `accent-soft`
- **Точки остаются** — TypingDots не трогаем, статус отдельно под бабблом
- **Минимальная задержка** — 800мс на статус, очередь если быстрые этапы
- **Fade-анимация** — crossfade между статусами, fade-out при первом delta
- **Язык** — русский

## Phases

### Phase 1: Детальное проектирование
- [x] Финализировать список этапов и тексты статусов
- [x] Спроектировать NDJSON event `status` (формат)
- [x] Спроектировать механизм `dispatch_custom_event` в rag_tool (sync, без async-конвертации)
- [x] Спроектировать фронтенд-компонент ThinkingStatus
- [x] Спроектировать очередь статусов с min-duration на фронте
- **Status:** complete

### Phase 2: Backend — эмиссия status-событий
- [x] Добавить `dispatch_custom_event` (sync) на каждом этапе пайплайна в rag_tool.py
- [x] Добавить обработку `on_custom_event` в `chat.py`
- [x] Emit NDJSON `{"type": "status", "stage": "...", "text": "..."}`
- [x] Emit `scope_check` статус на `on_tool_start` в chat.py
- [x] Проверить что identity fast-path тоже отправляет статус
- **Status:** complete
- **Решение:** оставлен sync tool + `dispatch_custom_event` вместо async-конвертации (меньше рисков)

### Phase 3: Frontend — обработка и отображение
- [x] Добавить тип `status` в `ChatStreamEvent` (`lib/api.ts`)
- [x] Добавить состояние `thinkingStatus` в `AgentDock.tsx`
- [x] Реализовать очередь статусов с min-duration 800мс (ThinkingStatus компонент)
- [x] Создать компонент `ThinkingStatus` с fade-анимацией
- [x] Интегрировать в `AgentMessageList.tsx` под последним бабблом агента
- [x] Прокидывать status через `AgentChatWindow`
- [x] Обработка `"status"` event в handleSend и handleMessageRetry
- [x] Сброс thinkingStatus при stop/error/finally
- **Status:** complete

### Phase 4: Тестирование и полировка
- Пропущено по запросу (runtime-тестирование вручную)
- **Status:** skipped

### Phase 5: Code Review (самопроверка)
- [x] Backend: rag_tool.py — корректность, нет сломанной логики, defensive _emit_status
- [x] Backend: chat.py — on_custom_event + scope_check + identity покрыты
- [x] Backend: контракты сохранены (return types, usage collection)
- [x] Frontend: api.ts — тип `status` в ChatStreamEvent union
- [x] Frontend: AgentDock.tsx — очередь статусов, сброс во всех ветках (send, retry, stop, finally)
- [x] Frontend: ThinkingStatus — min-duration queue, fade, cleanup, null-safe
- [x] Frontend: AgentMessageList.tsx — интеграция под бабблом, scroll-deps, wrapper div
- [x] Общее: нет circular imports, encoding UTF-8, naming conventions
- [x] Общее: SOLID/DRY/KISS — минимальные изменения, defensive подход
- **Status:** complete
- **Найденные риски:**
  1. `dispatch_custom_event` может не работать из sync tool в thread pool → нужно runtime-тестирование
  2. Малый layout shift при появлении/исчезновении ThinkingStatus → визуально незаметен

## Этапы пайплайна → статусы

| Этап в коде | stage ID | Текст статуса |
|-------------|----------|---------------|
| ScopeGuard | `scope_check` | Анализирую вопрос... |
| PlannerLLM | `planning` | Составляю план поиска... |
| PlanExecutor | `searching` | Ищу в базе знаний... |
| CriticLLM | `verifying` | Проверяю полноту данных... |
| AnswerLLM | `answering` | Формирую ответ... |
| Identity (fast-path) | `identity` | Формирую ответ... |

## NDJSON event формат
```json
{"type": "status", "stage": "planning", "text": "Составляю план поиска..."}
```

## Ключевые технические решения

| Решение | Обоснование |
|---------|-------------|
| `adispatch_custom_event` из LangChain | Нативный механизм LangGraph для custom events через `astream_events` |
| Конвертация rag_tool в async | Необходимо для `adispatch_custom_event` (работает только в async) |
| Min-duration очередь на фронте | Бэкенд не должен задерживать пайплайн ради UI, задержки — ответственность фронтенда |
| Fade-анимация 200мс | Достаточно быстро, не мешает восприятию |

### Phase 6: Hotfix — async конвертация rag_tool
- [x] `dispatch_custom_event` (sync) не работает из thread pool — подтверждено runtime-тестом
- [x] Конвертация `portfolio_rag_tool` в `async def`
- [x] Замена `dispatch_custom_event` → `adispatch_custom_event` (async)
- [x] Обёртка тяжёлых sync-операций в `asyncio.to_thread()`:
  - `get_plan_with_cache`, `executor.execute`, `critic_instance.evaluate`, `execute_portfolio_search`, `answer_gen.generate`
- [x] Быстрые операции (normalizer, renderer, grounding) — оставлены без обёртки
- [x] Code review: `graph.py` (`create_agent`) поддерживает async tools нативно
- **Status:** complete, ожидает runtime-тестирования

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `dispatch_custom_event` не работает из sync tool в thread pool | 1 (sync dispatch) | Конвертация tool в async + `adispatch_custom_event` + `asyncio.to_thread()` |
| `adispatch_custom_event` без явного config не находит callback context | 2 (async без config) | Добавлен `config: RunnableConfig` как keyword-only параметр tool, передаётся явно в `adispatch_custom_event(config=config)` |
| `adispatch_custom_event` с явным config — события всё равно не доходят до `astream_events` | 3 (async + config) | Отказ от LangChain event system. Заменено на `asyncio.Queue` через `config["configurable"]["_status_queue"]` + unified queue в `chat.py` |

## Notes
- `portfolio_rag_tool` конвертирован в **async** — `adispatch_custom_event` работает в async контексте
- LangChain v1.0.5, LangGraph v1.0.3 — `adispatch_custom_event` доступен
- `chat.py` обрабатывает `on_custom_event`, `on_tool_start`, identity fast-path
- Быстрые этапы (normalizer, render, grounding) — детерминистические, < 100мс, статусы для них не нужны
- `asyncio.to_thread()` с keyword args поддерживается Python 3.9+ (проект 3.12+)
