# Quickstart: Fix Planner Structured Output Method Per Provider

## What This Changes

Одна строка в `planner_llm.py`: `method="json_schema"` → provider-aware выбор метода.

- **GigaChat** → `json_schema` (без изменений, текущее поведение)
- **DeepSeek / Qwen** → `json_mode` (устраняет HTTP 400)

## File Modified (1 file)

| File | Change | Risk |
|------|--------|------|
| `app/agent/planner/planner_llm.py` | Replace hardcoded `"json_schema"` with `_method = "json_schema" if type(self.llm).__name__ == "GigaChat" else "json_mode"` | Very Low — additive, GigaChat path unchanged |

## Implementation (3 строки кода)

В методе `_plan_structured()` (строка ~106), внутри цикла retry, перед `self.llm.with_structured_output()`:

```python
# GigaChat uses json_schema; DeepSeek / Qwen (ChatOpenAI) use json_mode
_method = "json_schema" if type(self.llm).__name__ == "GigaChat" else "json_mode"
logger.debug("Planner structured output method: %s (llm=%s)", _method, type(self.llm).__name__)
structured_llm = self.llm.with_structured_output(
    QueryPlanV3,
    method=_method,      # was: method="json_schema"
    include_raw=True,
)
```

## How to Verify

### Шаг 1: Переключить планнер на DeepSeek

В `infra/.env.dev`:
```bash
PLANNER_LLM=deepseek:deepseek-chat
```

### Шаг 2: Пересобрать и проверить

```bash
docker compose -f infra/docker-compose.local.yaml up -d --build rag-api
docker compose -f infra/docker-compose.local.yaml up rag-ingest
```

### Шаг 3: Проверить логи prefetch

**Ожидаемое поведение (SUCCESS):**
```
INFO  app.agent.planner.planner_llm: Plan generated: intents=['project_list'], ...
INFO  app.agent.planner.planner_llm: Plan generated: intents=['technology_usage'], ...
INFO  app.prefetch: Prefetch complete: 39 questions, llm=33, cache=0, shortcut=6
```
Ни одной строки `Structured output failed` или `HTTP 400`.

**Провальное поведение (FAIL — значит фикс не применился):**
```
WARNING  Structured output failed (attempt 1/3): Error code: 400 ...
ERROR    Planner failed after 3 attempts, using fallback
```

### Шаг 4: Проверить регрессию на GigaChat

```bash
# Вернуть в .env.dev:
PLANNER_LLM=gigachat:GigaChat-2
# Пересобрать + prefetch
```

GigaChat может по-прежнему делать retry на первой попытке (это отдельный known issue) — это нормально и НЕ является регрессией данного фикса.

## What Is NOT Changed

- `_sanitize_plan()` — confidence=0.0 issue (ISSUE-002) не в scope
- `_validate_plan()` — логика валидации без изменений
- `deps.py` / `settings.py` — нет новых env vars
- `PLANNER_REPAIR_PROMPT` — не трогаем
- Docker compose, prefetch.py, все другие файлы
