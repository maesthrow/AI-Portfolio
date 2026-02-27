# Implementation Plan: Fix Agent Loop in RAG Pipeline

**Branch**: `006-fix-agent-loop` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-fix-agent-loop/spec.md`

## Summary

Устранить потенциальное зацикливание ReAct-агента, при котором Agent LLM повторно вызывает `portfolio_rag_tool` вместо возврата финального ответа. Три линии защиты: (1) явный запрет повторного вызова в системном промпте, (2) сокращение tool_result до `answer` + `found`, (3) снижение recursion_limit до 6 и добавление таймаута 90 секунд.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: LangGraph 1.x, LangChain 1.x, FastAPI
**Storage**: N/A (изменения не затрагивают БД)
**Testing**: pytest (без внешних зависимостей — unit tests)
**Target Platform**: Docker/Linux server
**Project Type**: web-service (RAG API)
**Performance Goals**: Один запрос = один вызов инструмента в 99%+ случаев; таймаут 90 сек
**Constraints**: `return_direct=False` НЕ подлежит изменению (обеспечивает стриминг)
**Scale/Scope**: 4 файла, ~50 строк изменений

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | Все строки — русский plain text, UTF-8 |
| II. Root-Cause Resolution | PASS | Устраняем корневую причину (промпт + tool_result), а не симптомы |
| III. Clean Architecture | PASS | Минимальные точечные изменения в существующих модулях |
| IV. Service Directory | PASS | Только `services/rag-api-new/` |
| V. API Versioning | PASS | Внешние API не меняются |
| VI. DB Migrations | N/A | БД не затрагивается |
| VII. Simplicity & YAGNI | PASS | Только запрошенные изменения, без лишних абстракций |

## Project Structure

### Documentation (this feature)

```text
specs/006-fix-agent-loop/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Research findings (all resolved in spec)
├── quickstart.md        # Testing guide
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (affected files)

```text
services/rag-api-new/
├── app/
│   ├── agent/
│   │   ├── graph.py           # FR-001: Anti-loop instruction in AGENT_SYSTEM_PROMPT
│   │   └── rag_tool.py        # FR-002: Reduce tool_result to answer+found; usage via side channel
│   ├── routers/
│   │   └── chat.py            # FR-003/004/005: recursion_limit=6, timeout=90s, error handling
│   └── settings.py            # FR-004: agent_timeout setting
└── tests/
    └── test_agent_loop_guard.py  # New: tests for anti-loop measures
```

**Structure Decision**: Точечные изменения в существующих файлах. Один новый файл — тест.

## Implementation Steps

### Step 1: Anti-loop instruction in system prompt (FR-001)

**File**: `services/rag-api-new/app/agent/graph.py`
**Lines**: 76-85 (section "2. ИСПОЛЬЗОВАНИЕ ИНСТРУМЕНТОВ")

**Change**: Добавить явный запрет повторного вызова инструмента в секцию правил использования инструментов.

**Конкретное изменение**: После строки 77 ("ОБЯЗАТЕЛЬНО вызывай portfolio_rag_tool для всех вопросов о портфолио") добавить:
```
   - НИКОГДА не вызывай portfolio_rag_tool повторно. ОДИН вызов — ОДИН ответ.
     После получения результата от инструмента — СРАЗУ отвечай пользователю.
```

**Риск**: Минимальный. Добавляем инструкцию, не удаляем существующие.

---

### Step 2: Reduce tool_result + usage side channel (FR-002)

**File**: `services/rag-api-new/app/agent/rag_tool.py`

**Проблема**: Если просто убрать `usage` из tool_result, `chat.py` (строки 414-424) не сможет агрегировать токены от RAG-пайплайна для rate limiting. Нужен обходной путь.

**Решение**: Передать `usage` через существующий `status_queue` side channel (уже используется для статусных событий) перед возвратом урезанного результата.

**Изменения**:

1. Добавить функцию `_emit_usage()` (аналогично `_emit_status()`):
```python
def _emit_usage(usage_data: dict, config: RunnableConfig) -> None:
    """Emit usage data via status queue side channel."""
    queue = (config.get("configurable") or {}).get("_status_queue")
    if queue is None:
        return
    try:
        queue.put_nowait({"stage": "_usage", "data": usage_data})
    except Exception:
        pass
```

2. Перед `return` (строки 373-395): эмитить usage, затем вернуть минимальный dict:
```python
# Emit usage via side channel (before reducing tool result)
collector.log_summary(f"rag_tool_{id(question)}")
_emit_usage(collector.to_dict(), config)

return {"answer": answer, "found": payload.found}
```

3. В `except` блоке (строки 397-409): аналогично:
```python
except Exception as e:
    logger.error("portfolio_rag_tool failed: %s", e, exc_info=True)
    _emit_usage(collector.to_dict(), config)
    return {
        "answer": "Произошла ошибка при обработке запроса. Попробуйте переформулировать вопрос.",
        "found": False,
    }
```

4. Обновить docstring инструмента (строки 68-75): убрать упоминания `rendered_facts`, `sources`, `confidence`, `intents`.

**File**: `services/rag-api-new/app/routers/chat.py`

5. В обработке unified queue (строки 324-330): добавить обработку `_usage` события:
```python
if tag == "status":
    stage = q_data.get("stage", "")
    if stage == "_usage":
        # Internal: aggregate rag_tool usage into collector
        tool_usage = q_data.get("data") or {}
        by_role = tool_usage.get("by_role") or {}
        for role, role_data in by_role.items():
            if isinstance(role_data, dict):
                collector.add(
                    role,
                    role_data.get("provider", "unknown"),
                    role_data.get("model", "unknown"),
                    role_data,
                )
        continue
    yield json.dumps({
        "type": "status",
        "stage": stage,
        "text": q_data.get("text", ""),
    }, ensure_ascii=False) + "\n"
    continue
```

6. Удалить старую логику извлечения usage из `on_tool_end` (строки 393-424 → только логирование + yield tool_end).

**Риск**: Средний. Меняем механизм передачи usage. Нужно тщательно проверить, что rate limiting продолжает работать корректно.

---

### Step 3: Recursion limit (FR-003)

**File**: `services/rag-api-new/app/routers/chat.py`
**Line**: 170

**Change**: `"recursion_limit": 8` → `"recursion_limit": 6`

**Обновить комментарий**:
```python
"recursion_limit": 6,  # Normal path=5 steps (router+model+tools+model+clear_pending) + 1 margin
```

**Риск**: Минимальный. Нормальный путь использует 5 шагов, 6 — с запасом.

---

### Step 4: Execution timeout (FR-004)

**File**: `services/rag-api-new/app/settings.py`

**Change**: Добавить настройку:
```python
# === Agent Execution ===
agent_timeout: int = 90
"""Таймаут выполнения агента в секундах. Защита от бесконечного зависания."""
```

**File**: `services/rag-api-new/app/routers/chat.py`

**Change**: В функции `_run_agent()` (строки 296-302) обернуть выполнение агента в `asyncio.wait_for()`:
```python
async def _run_agent():
    try:
        s = settings()
        async for ev in _iterate_agent_events(agent, state, config):
            await unified.put(("event", ev))
    except Exception as exc:
        await unified.put(("error", exc))
    await unified.put(("done", None))
```

Обернуть `agent_task` в таймаут при создании:
```python
agent_task = asyncio.create_task(_run_agent())
# Timeout safety net
s = settings()
timeout_task = asyncio.create_task(
    _apply_timeout(agent_task, s.agent_timeout, unified)
)
```

Где `_apply_timeout`:
```python
async def _apply_timeout(task: asyncio.Task, timeout: int, queue: asyncio.Queue):
    """Cancel agent task after timeout."""
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except asyncio.TimeoutError:
        task.cancel()
        await queue.put(("error", TimeoutError(
            f"Превышено время обработки запроса ({timeout} сек). Попробуйте упростить вопрос."
        )))
```

Хм, на самом деле проще — обернуть итерацию внутри `_run_agent` в `asyncio.wait_for`:

```python
async def _run_agent():
    try:
        s = settings()
        coro = _consume_agent_events(agent, state, config, unified)
        await asyncio.wait_for(coro, timeout=s.agent_timeout)
    except asyncio.TimeoutError:
        await unified.put(("error", TimeoutError(
            f"Превышено время обработки запроса ({s.agent_timeout} сек). Попробуйте упростить вопрос."
        )))
    except Exception as exc:
        await unified.put(("error", exc))
    await unified.put(("done", None))

async def _consume_agent_events(agent, state, config, queue):
    async for ev in _iterate_agent_events(agent, state, config):
        await queue.put(("event", ev))
```

**Риск**: Средний. Нужно убедиться, что отмена задачи не оставляет висящих ресурсов. `asyncio.wait_for` при TimeoutError отменяет корутину, что может прервать LLM-запрос в процессе. Это приемлемо — 90 секунд более чем достаточно для нормальной работы.

---

### Step 5: Graceful error messages (FR-005)

**File**: `services/rag-api-new/app/routers/chat.py`

**Change**: В блоке `except` (строки 428-431) — различать типы ошибок:

```python
except Exception as exc:
    # User-friendly messages for known safety-net errors
    if "recursion" in type(exc).__name__.lower() or "recursion" in str(exc).lower():
        msg = "Обработка запроса заняла слишком много шагов. Попробуйте переформулировать вопрос."
    elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        msg = str(exc) if str(exc) else "Превышено время обработки запроса. Попробуйте упростить вопрос."
    else:
        logger.exception("Agent streaming failed")
        msg = "Произошла ошибка при обработке запроса. Попробуйте позже."
    yield json.dumps({"type": "error", "message": msg}, ensure_ascii=False) + "\n"
    return
```

**Риск**: Минимальный. Только улучшаем текст ошибки.

---

### Step 6: Tests

**File**: `services/rag-api-new/tests/test_agent_loop_guard.py` (новый)

```python
"""Tests for anti-loop measures in the RAG agent pipeline."""

class TestAgentSystemPrompt:
    """Verify system prompt contains anti-loop instructions."""

    def test_prompt_forbids_repeated_tool_calls(self):
        """System prompt MUST explicitly forbid repeated tool invocations."""
        from app.agent.graph import AGENT_SYSTEM_PROMPT
        assert "НИКОГДА не вызывай portfolio_rag_tool повторно" in AGENT_SYSTEM_PROMPT

    def test_prompt_requires_immediate_response(self):
        """System prompt MUST instruct to respond immediately after tool result."""
        from app.agent.graph import AGENT_SYSTEM_PROMPT
        assert "СРАЗУ отвечай пользователю" in AGENT_SYSTEM_PROMPT


class TestToolResultReduction:
    """Verify tool_result contains only answer + found."""

    # Uses mock to call portfolio_rag_tool and inspect return value structure.
    # Tool returns dict with only 'answer' and 'found' keys.
    pass  # Implementation in actual test file


class TestSafetyNetSettings:
    """Verify recursion_limit and timeout settings."""

    def test_agent_timeout_default(self):
        """Default agent timeout MUST be 90 seconds."""
        from app.settings import Settings
        s = Settings()
        assert s.agent_timeout == 90
```

**Риск**: Минимальный. Тесты без внешних зависимостей.

## Execution Order

1. **Step 1** (prompt) — изолированное, безопасное изменение
2. **Step 2** (tool_result + usage channel) — самое сложное, core change
3. **Step 3** (recursion_limit) — одна строка
4. **Step 4** (timeout) — setting + async wrapper
5. **Step 5** (error messages) — улучшение UX
6. **Step 6** (tests) — валидация

Шаги 1 и 3 можно делать параллельно. Шаги 2 и 4 зависят друг от друга (оба меняют chat.py). Шаг 5 зависит от шага 4.

## Complexity Tracking

> No violations to justify — all changes are minimal and directly requested.

| Aspect | Complexity | Justification |
|--------|-----------|---------------|
| Usage side channel | Medium | Необходимо для сохранения rate limiting при урезании tool_result |
| Timeout wrapper | Low | Стандартный asyncio.wait_for |
| Prompt change | Trivial | Одна строка текста |
| Recursion limit | Trivial | Одно число |
