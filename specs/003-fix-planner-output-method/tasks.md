# Tasks: Fix Planner Structured Output Method Per Provider

**Input**: Design documents from `/specs/003-fix-planner-output-method/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Not included — spec does not request TDD. Verification is via deployment + prefetch log inspection (see quickstart.md).

**Organization**: Все три user story (US1, US2, US3) реализуются одним и тем же изменением — выбор метода по провайдеру. Одна задача покрывает все истории; отдельные фазы валидации.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно выполнять параллельно
- **[Story]**: Какой user story принадлежит задача
- Все пути относительно `services/rag-api-new/`

---

## Phase 1: Implementation — All User Stories (P1 + P2)

**Goal**: Реализовать provider-aware выбор метода structured output. Единственное изменение кода в проекте.

**Independent Test**: Описано в Phase 2 (Validation) — нужен деплой с DeepSeek и GigaChat-планнером.

- [x] T001 [US1] [US2] [US3] In `_plan_structured()` method (line ~106) inside the retry loop in `app/agent/planner/planner_llm.py`: replace hardcoded `method="json_schema"` with provider-aware selection by adding `_method = "json_schema" if type(self.llm).__name__ == "GigaChat" else "json_mode"` on the line before the `with_structured_output()` call; add `logger.debug("Planner structured output method: %s (llm=%s)", _method, type(self.llm).__name__)` immediately after; change `method="json_schema"` argument to `method=_method` in the `with_structured_output()` call

**Checkpoint**: Code change applied. File saves and imports without error. Confirm `method=_method` is inside the retry `for` loop (not before it, to re-evaluate per attempt if needed).

---

## Phase 2: Validation — DeepSeek (US1)

**Goal**: Подтвердить, что DeepSeek работает как планнер без HTTP 400 и без fallback на `general_unstructured`.

**Independent Test**: Zero `"Structured output failed"` warnings in prefetch log when `PLANNER_LLM=deepseek:deepseek-chat`.

- [x] T002 [US1] Set `PLANNER_LLM=deepseek:deepseek-chat` in `infra/.env.dev`, rebuild rag-api container, run rag-ingest, and inspect prefetch logs — verify zero `Structured output failed` / `HTTP 400` warnings and all 33 LLM-planned questions receive non-`general_unstructured` intents (per quickstart.md step-by-step)

**Checkpoint**: Prefetch log shows `Prefetch complete: 39 questions` with no planner failure warnings. SC-001 and SC-002 met.

---

## Phase 3: Validation — GigaChat Regression (US2)

**Goal**: Подтвердить, что поведение с GigaChat не изменилось.

**Independent Test**: GigaChat-планнер ведёт себя идентично поведению до изменения.

- [ ] T003 [US2] Restore `PLANNER_LLM=gigachat:GigaChat-2` in `infra/.env.dev`, rebuild rag-api container, run rag-ingest, and confirm planner behaviour is identical to pre-change — GigaChat may still occasionally retry (that is expected and NOT a regression), and all intents are correctly planned

**Checkpoint**: SC-003 met — GigaChat retry rate unchanged. No new failure modes introduced.

---

## Phase 4: Polish

**Purpose**: Финальная уборка — вернуть prod конфигурацию, задокументировать изменение.

- [ ] T004 Confirm `infra/.env.dev` has `PLANNER_LLM` restored to desired production value (check with team which provider to use in prod) and rebuild if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Implementation)**: Нет зависимостей — выполняется сразу
- **Phase 2 (DeepSeek validation)**: Зависит от Phase 1
- **Phase 3 (GigaChat regression)**: Зависит от Phase 1; независима от Phase 2
- **Phase 4 (Polish)**: Зависит от Phase 2 + Phase 3

### User Story Dependencies

- **US1 (P1)**: Реализуется в T001 + валидируется в T002
- **US2 (P1)**: Реализуется в T001 (GigaChat path unchanged) + валидируется в T003
- **US3 (P2)**: Реализуется в T001 (automatic detection — no config needed) — не требует отдельной валидации

### Parallel Opportunities

T002 и T003 теоретически параллельны (разные `.env.dev` конфигурации), но практически выполняются последовательно т.к. требуют rebuild + restart одного контейнера.

---

## Implementation Strategy

### MVP First (All Stories — Single Task)

1. Complete T001 (code change)
2. Complete T002 (DeepSeek validation) — SC-001, SC-002 verified
3. **STOP AND VALIDATE**: If T002 passes — US1 и US2 готовы, US3 выполнена автоматически
4. Complete T003 (GigaChat regression) — SC-003 verified
5. Complete T004 (Polish)

Вся реализация занимает 3-4 строки кода. Основное время — деплой и проверка логов.

---

## Summary

| Метрика | Значение |
|---------|----------|
| Всего задач | 4 |
| Phase 1 (Implementation) | 1 задача — весь код |
| Phase 2 (DeepSeek validation) | 1 задача |
| Phase 3 (GigaChat regression) | 1 задача |
| Phase 4 (Polish) | 1 задача |
| Параллелизуемых | 0 (все последовательные из-за shared контейнера) |
| Модифицируемых файлов | 1 (`planner_llm.py`) |
| Строк кода | ~3 |
| MVP scope | Все задачи (фича атомарна) |
