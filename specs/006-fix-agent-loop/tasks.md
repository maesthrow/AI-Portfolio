# Tasks: Fix Agent Loop in RAG Pipeline

**Input**: Design documents from `/specs/006-fix-agent-loop/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Included — spec mentions testability and plan.md defines specific tests.

**Organization**: Tasks are grouped by user story. US1 and US3 share implementation (same files) and are combined in one phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All paths relative to `services/rag-api-new/`.

---

## Phase 1: User Story 1 + 3 — Prevent Agent Loop (Priority: P1 + P3) 🎯 MVP

**Goal**: Агент вызывает инструмент ровно 1 раз и сразу отвечает. Tool result содержит только `answer` + `found`. Usage-данные передаются через side channel для rate limiting.

**Independent Test**: Отправить портфолио-вопрос → в логах один `tool_start`/`tool_end`, ответ стримится, `end.usage.by_role` содержит `planner`/`answer`.

### Implementation

- [x] T001 [P] [US1] Add anti-loop instruction to `AGENT_SYSTEM_PROMPT` in `app/agent/graph.py`: after line 77 add "НИКОГДА не вызывай portfolio_rag_tool повторно. ОДИН вызов — ОДИН ответ. После получения результата от инструмента — СРАЗУ отвечай пользователю."
- [x] T002 [P] [US3] Add `_emit_usage()` helper function in `app/agent/rag_tool.py` (analogous to existing `_emit_status()`): puts `{"stage": "_usage", "data": usage_dict}` onto `status_queue` from config
- [x] T003 [US3] Reduce tool_result return in `app/agent/rag_tool.py`: replace return dict (lines 384-395) with `{"answer": answer, "found": payload.found}`, call `_emit_usage(collector.to_dict(), config)` before return. Remove `deterministic_used` surface-reduction block (lines 376-382) as it's now unnecessary — ALL returns are reduced. Update the `except` block return (lines 399-409) identically.
- [x] T004 [US3] Update tool docstring in `app/agent/rag_tool.py` (lines 46-75): remove mentions of `rendered_facts`, `sources`, `confidence`, `intents` from Returns section, document only `answer` and `found`
- [x] T005 [US1] Add `_usage` event handler in `app/routers/chat.py`: in the `if tag == "status"` block (line 324), check for `stage == "_usage"` and aggregate usage into `collector` via `collector.add()` before continuing (do NOT yield this event to user)
- [x] T006 [US1] Remove old usage extraction from `on_tool_end` handler in `app/routers/chat.py` (lines 393-424): remove the `parsed_output` / `"usage" in parsed_output` logic. Keep tool_end logging and `yield tool_end` event

**Checkpoint**: Tool returns only `answer` + `found`. Prompt explicitly forbids re-invocation. Usage flows via side channel. Rate limiting works correctly.

---

## Phase 2: User Story 2 — Safety Nets (Priority: P2)

**Goal**: При аномальном поведении LLM — быстрая ошибка с понятным сообщением, а не бесконечное зависание.

**Independent Test**: Временно установить `recursion_limit=3` → убедиться, что при срабатывании лимита приходит понятное сообщение (не стектрейс).

### Implementation

- [x] T007 [P] [US2] Add `agent_timeout` setting in `app/settings.py`: `agent_timeout: int = 90` with docstring "Таймаут выполнения агента в секундах. Защита от бесконечного зависания."
- [x] T008 [P] [US2] Change `recursion_limit` from 8 to 6 in `app/routers/chat.py` (line 170) and update comment to: `# Normal path=5 steps (router+model+tools+model+clear_pending) + 1 margin`
- [x] T009 [US2] Add timeout wrapper in `app/routers/chat.py`: extract agent event consumption into `_consume_agent_events()` coroutine, wrap it with `asyncio.wait_for(coro, timeout=settings().agent_timeout)` inside `_run_agent()`, catch `asyncio.TimeoutError` and put user-friendly error into unified queue
- [x] T010 [US2] Improve error handling in `app/routers/chat.py` except block (line 428): detect `GraphRecursionError` (by class name check) → "Обработка запроса заняла слишком много шагов. Попробуйте переформулировать вопрос."; detect `TimeoutError`/`asyncio.TimeoutError` → use error message from timeout; default → "Произошла ошибка при обработке запроса. Попробуйте позже."

**Checkpoint**: Recursion limit = 6, timeout = 90s, all errors produce user-friendly messages.

---

## Phase 3: Tests & Validation

**Purpose**: Автоматизированная проверка всех anti-loop мер

- [x] T011 [P] Create test file `tests/test_agent_loop_guard.py` with `TestAgentSystemPrompt` class: test that `AGENT_SYSTEM_PROMPT` from `app.agent.graph` contains "НИКОГДА не вызывай portfolio_rag_tool повторно" and "СРАЗУ отвечай пользователю"
- [x] T012 [P] Add `TestSafetyNetSettings` class in `tests/test_agent_loop_guard.py`: test that `Settings().agent_timeout == 90` and that `recursion_limit == 6` (import config dict from `app/routers/chat.py` or verify the value at the call site)
- [x] T013 [P] Add `TestToolResultReduction` class in `tests/test_agent_loop_guard.py`: mock RAG pipeline internals, call `portfolio_rag_tool`, assert returned dict keys are exactly `{"answer", "found"}` — no extra fields (`rendered_facts`, `sources`, `confidence`, `usage`, etc.)
- [x] T014 Run existing tests to verify no regressions: `pytest tests/ -v` from `services/rag-api-new/`

**Checkpoint**: All tests pass. No regressions in existing test suite.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1+US3)**: No dependencies — can start immediately
- **Phase 2 (US2)**: Independent of Phase 1 (modifies different sections of `chat.py`)
- **Phase 3 (Tests)**: Depends on Phase 1 and Phase 2 completion

### Within Phase 1

```
T001 (graph.py prompt)     ─── parallel ───  T002 (rag_tool.py _emit_usage)
                                                       │
                                                       ▼
                                              T003 (rag_tool.py reduce return)
                                                       │
                                                       ▼
                                              T004 (rag_tool.py docstring)
                                                       │
T005 (chat.py _usage handler) ◄────────────────────────┘
         │
         ▼
T006 (chat.py remove old usage extraction)
```

### Within Phase 2

```
T007 (settings.py timeout)  ─── parallel ───  T008 (chat.py recursion_limit)
         │
         ▼
T009 (chat.py timeout wrapper)
         │
         ▼
T010 (chat.py error messages)
```

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T007 and T008 can run in parallel (different files)
- T011, T012, and T013 can run in parallel (same file but independent test classes)
- Phase 1 and Phase 2 can run in parallel (different sections of shared files)

---

## Implementation Strategy

### MVP First (Phase 1 Only)

1. Complete T001-T006 (prompt + tool_result + usage channel)
2. **STOP and VALIDATE**: Test manually per quickstart.md — verify single tool call, streaming works, rate limiting works
3. This alone should eliminate 99%+ of looping cases

### Full Implementation

1. Phase 1: Anti-loop prevention (T001-T006) → validate
2. Phase 2: Safety nets (T007-T010) → validate
3. Phase 3: Tests (T011-T014) → all green
4. Manual validation per quickstart.md

---

## Notes

- All changes are in `services/rag-api-new/` (active RAG API directory)
- `return_direct=False` is NOT changed — it ensures streaming works
- `chat.py` is modified by both Phase 1 (status handler, tool_end handler) and Phase 2 (recursion_limit, timeout, error messages) — these touch different sections and don't conflict
- Total: 14 tasks across 4 files + 1 new test file
