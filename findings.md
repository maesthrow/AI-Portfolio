# Findings: Thinking Status Indicators

## Requirements (согласовано)
- Реальные статусы с бэкенда (не фейковые таймеры)
- Отображение под бабблом агента, отдельной строкой (Вариант B)
- TypingDots остаются без изменений
- Минимальная задержка 800мс между сменой статусов
- Fade-анимация (crossfade между статусами, fade-out при delta)
- Язык статусов — русский

## Research Findings

### Backend: Текущая архитектура стриминга
- `chat.py` использует `agent_app.astream_events()` для получения событий из LangGraph
- Обрабатываются: `on_chat_model_stream`, `on_chat_model_end`, `on_chain_end`, `on_tool_start`, `on_tool_end`
- **Не обрабатывается:** `on_custom_event` — нужно добавить
- NDJSON-типы на клиент: `start`, `delta`, `tool_start`, `tool_end`, `end`, `error`
- `tool_start`/`tool_end` приходят на фронт, но только логируются (не отображаются)

### Backend: portfolio_rag_tool — текущее состояние
- **Синхронная** функция с декоратором `@tool`
- Этапы выполнения (в порядке):
  1. `get_plan_with_cache()` — планирование (shortcut → cache → LLM)
  2. `PlanExecutor.execute()` — поиск (граф + hybrid retrieval)
  3. `CriticLLM.evaluate()` — проверка полноты (опционально, lazy)
  4. `FactNormalizer.normalize()` — фильтрация фактов (детерминистический)
  5. `RenderEngine.render()` — форматирование (детерминистический)
  6. `AnswerLLM.generate()` — генерация ответа
  7. `GroundingVerifier.verify()` — проверка (детерминистический)
- Возвращает dict с answer, rendered_facts, usage и т.д.

### Backend: Механизм custom events
- LangChain v1.0.5 поддерживает `adispatch_custom_event` из `langchain_core.callbacks`
- Для работы требуется **async** контекст (async tool)
- Events появляются в `astream_events` как `{"event": "on_custom_event", "name": "...", "data": {...}}`
- Это нативный механизм LangGraph, не хак

### Backend: Identity fast-path
- Вопросы типа "кто ты?" обрабатываются ДО агента в `chat.py` (строки 208-260)
- Пропускают весь RAG-пайплайн
- Нужно отдельно эмитить статус для этого пути

### Frontend: Текущая архитектура
- `AgentDock.tsx` — главный стейт: messages, loading, streamingStarted
- `AgentChatWindow.tsx` — layout, прокидывает `typing = loading && !streamingStarted`
- `AgentMessageList.tsx` — рендер сообщений, TypingDots показываются когда typing=true
- `TypingDots` — 3 пульсирующих кружка `bg-accent-soft`, animation pulse
- Character pump (charQueueRef + RAF) — посимвольная анимация стриминга
- `ChatStreamEvent` тип определён в `lib/api.ts`

### Frontend: Существующие event-типы
```typescript
type ChatStreamEvent =
  | { type: "start"; message_id: string; created_at: string }
  | { type: "delta"; content: string }
  | { type: "tool_start"; tool: string }
  | { type: "tool_end" }
  | { type: "end"; message_id: string; usage?: ...; rate_limit?: ... }
  | { type: "error"; message: string };
```

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Использовать `adispatch_custom_event` | Нативный механизм LangGraph, чистая архитектура |
| Конвертировать rag_tool в async | Необходимо для adispatch_custom_event |
| Min-duration очередь на фронте, не на бэке | Бэк не должен искусственно задерживать пайплайн |
| Не показывать статусы для быстрых этапов | normalizer/render/grounding < 100мс, нет смысла |
| Отдельный компонент ThinkingStatus | Изоляция логики анимации и очереди |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
- `services/rag-api-new/app/agent/rag_tool.py` — основной файл для бэкенд-изменений
- `services/rag-api-new/app/routers/chat.py` — обработка событий стриминга
- `frontend-new/components/agent/AgentMessageList.tsx` — рендер сообщений
- `frontend-new/components/agent/AgentDock.tsx` — стейт и обработка stream events
- `frontend-new/lib/api.ts` — типы ChatStreamEvent
