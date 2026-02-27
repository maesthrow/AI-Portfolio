# Quickstart: Fix Agent Loop in RAG Pipeline

## Что изменилось

1. **Системный промпт**: явный запрет повторного вызова `portfolio_rag_tool`
2. **Tool result**: урезан до `{"answer": "...", "found": true/false}` — без сырых данных
3. **Usage channel**: токены от RAG-пайплайна передаются через status_queue (не через tool_result)
4. **Recursion limit**: снижен с 8 до 6
5. **Timeout**: добавлен `agent_timeout=90` секунд
6. **Error messages**: понятные сообщения при recursion limit / timeout

## Как проверить

### 1. Запуск сервисов

```bash
cd infra
docker compose -f docker-compose.local.yaml up -d postgres tei litellm redis content-api rag-api
docker compose -f docker-compose.local.yaml up rag-ingest
```

### 2. Базовый тест — один вызов инструмента

Отправить вопрос и проверить в логах:

```bash
curl -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Какие проекты есть в портфолио?", "session_id": "test-loop-1"}'
```

**Ожидание**: В логах `rag-api` — один `tool_start` и один `tool_end` для `portfolio_rag_tool`. После `tool_end` — стриминг `delta` событий с ответом. НЕТ повторного `tool_start`.

### 3. Проверка rate limiting (usage side channel)

```bash
# Проверить, что usage агрегируется корректно
curl http://localhost:8014/api/v1/rate-limit/status
```

В NDJSON-ответе на вопрос поле `end.usage` должно содержать `by_role` с `planner`, `answer` и опционально `critic` — это означает, что usage от RAG-пайплайна корректно передаётся через status_queue.

### 4. Проверка edge case: found=false

```bash
curl -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Есть ли опыт работы с Haskell?", "session_id": "test-loop-2"}'
```

**Ожидание**: Один вызов инструмента, ответ "такой информации нет" или аналогичный. НЕТ повторного вызова.

### 5. Юнит-тесты

```bash
cd services/rag-api-new
pytest tests/test_agent_loop_guard.py -v
```

## Новые настройки

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `AGENT_TIMEOUT` | `90` | Таймаут выполнения агента в секундах |

## Что НЕ изменилось

- `return_direct=False` — не трогали (обеспечивает стриминг)
- Внешний API (`/api/v1/agent/chat/stream`) — формат NDJSON без изменений
- Логика Critic/Grounding/AnswerLLM — без изменений
- Детерминистические ответы — работают как раньше
