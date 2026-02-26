# Tasks: Fix Agent Answer Relevance

**Input**: Design documents from `specs/005-fix-agent-answer-relevance/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All files in `services/rag-api-new/app/agent/` unless noted otherwise.

---

## Phase 1: Setup

**Purpose**: Cache cleanup and branch preparation

- [ ] T001 Clear plan cache to avoid stale cached plans: `curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core changes that MUST be complete before user stories — `AnswerLLM.generate()` return signature change

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Modify `AnswerLLM.generate()` in `services/rag-api-new/app/agent/answer/answer_llm.py` to return a 3-tuple `(answer: str, usage: Any, deterministic_used: bool)` instead of 2-tuple `(answer: str, usage: Any)`. When `_try_deterministic_answer()` returns non-None, set `deterministic_used=True`. When LLM path is used, set `deterministic_used=False`. Update the recovery path (line 165-176) to also return `deterministic_used=True` when recovery succeeds.
- [X] T003 Update all callers of `AnswerLLM.generate()` to unpack the 3-tuple. In `services/rag-api-new/app/agent/rag_tool.py` line 297: change `answer, answer_usage = ...` to `answer, answer_usage, deterministic_used = ...`. Also update test callers in `services/rag-api-new/tests/test_answer_llm_usage.py` lines 58 and 78: change `answer, _ = AnswerLLM(llm).generate(payload)` to `answer, _, _ = AnswerLLM(llm).generate(payload)`.
- [X] T004 Run existing tests to verify no regression: `cd services/rag-api-new && pytest tests/ -v`

**Checkpoint**: Foundation ready — `generate()` returns `deterministic_used` flag, all callers updated

---

## Phase 3: User Story 1 — Technology-specific answers contain only relevant achievements (Priority: P1) MVP

**Goal**: When user asks about a specific technology, the answer includes ONLY achievements related to that technology, filtering out unrelated achievements from the same project.

**Independent Test**: Ask "какой опыт с компьютерным зрением" — response includes CV achievements, does NOT include "LLM-ассистент с RAG для расчёта штрафов" or "Backend на FastAPI".

### Implementation for User Story 1

- [X] T005 [US1] Add keyword building helper `_build_content_keywords()` to `services/rag-api-new/app/agent/normalizer/normalizer.py`. Method takes `entity_names: list[str]`, `question: str`, `fact_metadata: dict` and returns `set[str]` of lowercased matching keywords. Build from 3 sources: (a) entity name tokens + full phrase + common abbreviations via `TECH_ABBREVIATIONS` dict (e.g., "Computer Vision" → {"computer", "vision", "computer vision", "cv"}, "Machine Learning" → {"machine", "learning", "machine learning", "ml"}, "Natural Language Processing" → {"nlp"}, etc. — include at least: CV, ML, NLP, AI, DL, NER, OCR, LLM), (b) significant tokens from question (≥ 3 chars, excluding Russian stop words like "какой", "опыт", "есть") → {"компьютерн", "зрени"} (use stem-like prefix matching by taking first 8+ chars for words ≥ 8 chars, keep full word otherwise), (c) technology names from `fact_metadata.get("technologies", [])` that are related to the entity (simple inclusion check).

- [X] T006 [US1] Add content-level bullet filtering helper `_filter_fact_bullets()` to `services/rag-api-new/app/agent/normalizer/normalizer.py`. Method takes `fact: FactItem` and `keywords: set[str]`, splits `fact.text` into header lines and bullet lines (bullets start with `- ` or `• `), keeps all header lines and only bullets where ANY keyword matches (case-insensitive substring in bullet text). Returns modified `FactItem` with filtered text, or `None` if no bullets matched.

- [X] T007 [US1] Add new content filter rule (Rule 2b) in `FactNormalizer.normalize()` in `services/rag-api-new/app/agent/normalizer/normalizer.py`. After existing Rule 2 (type filter, lines 88-99), when `intent_str == "technology_usage"` AND `entity_names` is non-empty: (1) build keywords via `_build_content_keywords()`, (2) apply `_filter_fact_bullets()` to each fact, (3) remove facts where filter returns None, (4) append `"technology_usage_content_filter"` to `rules_applied`. Add `entity_names: list[str] | None = None` and `question: str | None = None` parameters to `normalize()` method signature.

- [X] T008 [US1] Update convenience function `normalize_facts()` at bottom of `services/rag-api-new/app/agent/normalizer/normalizer.py` to accept and pass through `entity_names` and `question` params.

- [X] T009 [US1] In `services/rag-api-new/app/agent/rag_tool.py`, pass entity names and question to normalizer call (around line 245). Extract entity names from `plan.entities`: `entity_names = [e.get("name") for e in (plan.entities or []) if e.get("name")]`. Pass `entity_names=entity_names, question=question` to `normalizer.normalize()`.

- [ ] T010 [US1] Run existing tests and manually verify: `cd services/rag-api-new && pytest tests/ -v`. Then manually test via chat: ask "какой опыт с компьютерным зрением" and check logs for `Normalizer: X -> Y facts, rules=['technology_usage_filter', 'technology_usage_content_filter']`.

**Checkpoint**: Content filtering works — normalizer removes irrelevant bullets for technology_usage queries

---

## Phase 4: User Story 2 — Agent uses pre-generated answer without re-synthesis (Priority: P1)

**Goal**: When the RAG tool generates a deterministic answer, the agent relays it without re-synthesizing from raw data. Achieved via (a) conditional surface reduction in tool return and (b) prompt strengthening.

**Independent Test**: Send technology query, verify final streamed response matches the deterministic `answer` field content — no additional facts from `rendered_facts` appear.

### Implementation for User Story 2

- [X] T011 [P] [US2] Strengthen AGENT_SYSTEM_PROMPT in `services/rag-api-new/app/agent/graph.py`. Replace the existing instruction at line 81 (`- КРИТИЧЕСКИ ВАЖНО: Извлекай поле "answer"...`) with a more forceful version: `- КРИТИЧЕСКИ ВАЖНО: Поле "answer" из результата portfolio_rag_tool — это ГОТОВЫЙ ФИНАЛЬНЫЙ ОТВЕТ. Верни его пользователю КАК ЕСТЬ. НЕ добавляй информацию из других полей (rendered_facts, items). НЕ перефразируй и НЕ дополняй ответ.` Also remove or consolidate the redundant line 82-83 about escaping.

- [X] T012 [US2] Implement conditional surface reduction in `services/rag-api-new/app/agent/rag_tool.py`. In the return dict (line 332-343): when `deterministic_used is True`, set `"rendered_facts": ""` and `"items": []`. When `deterministic_used is False`, keep current behavior (full rendered_facts and items). Add logging: `logger.info("Surface reduction: deterministic_used=%s, rendered_facts_stripped=%s", deterministic_used, deterministic_used)`.

- [ ] T013 [US2] Manually test surface reduction: ask "какой опыт с компьютерным зрением" and check logs for `tool_end` output — verify `rendered_facts` is empty string and `items` is empty list. Then ask a non-technology question (e.g., "расскажи о проекте AI-Portfolio") and verify `rendered_facts` is NOT empty (LLM path, no surface reduction).

**Checkpoint**: Agent no longer has raw data to re-synthesize from for deterministic answers

---

## Phase 5: User Story 3 — Rich deterministic answers for technology_usage (Priority: P2)

**Goal**: The deterministic answer for technology_usage includes specific achievements per project (not just project names), making re-synthesis unnecessary and improving UX.

**Independent Test**: Ask "какой опыт с компьютерным зрением" and verify the deterministic answer (logged as `Answer deterministic_used=True preview=...`) includes specific CV achievements like "Внедрил сервис компьютерного зрения" and "Разработал MVP бэкенда авто-обучения и инференса CV-моделей".

### Implementation for User Story 3

- [X] T014 [US3] Rewrite `_answer_technology_usage()` in `services/rag-api-new/app/agent/answer/answer_llm.py`. The new implementation should: (1) keep existing graph-path extraction (metadata technology→project mapping) as fallback, (2) add primary path: iterate facts with type `project` or `experience_project`, extract project context from metadata (name, company_name, period), extract bullet lines from `fact.text` (lines starting with `- `), format as `"project_name (company, period):\n- bullet1\n- bullet2"`, (3) for `technology_usage` type facts (from graph tool): include as introductory context line, (4) combine: preamble `"Дмитрий применял {tech} в проекте {name} ({company}, {period}):"` + filtered bullets, (5) fallback: if no bullets extracted from facts, fall back to current project-name-only listing.

- [X] T015 [US3] Handle multi-project case in `_answer_technology_usage()` in `services/rag-api-new/app/agent/answer/answer_llm.py`. When multiple projects have achievements for the queried technology, group achievements under each project heading. Use `"Дмитрий применял {tech} в проектах:"` as preamble, then for each project: `"\n\n**{project_name}** ({company}, {period}):\n- bullet1\n- bullet2"`. Deduplicate projects by name.

- [ ] T016 [US3] Manually test rich deterministic answer: ask "какой опыт с компьютерным зрением" and verify log line `Answer deterministic_used=True preview=...` shows specific CV achievements, not just `"Дмитрий применял Computer Vision в проектах:\n- t2 — Нейросети"`.

**Checkpoint**: Deterministic answers include specific achievements — rich and self-sufficient

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression checks, cache cleanup

- [X] T017 Run full test suite: `cd services/rag-api-new && pytest tests/ -v`
- [ ] T018 Bidirectional relevance test: ask "опыт с LLM и RAG" and verify response includes LLM+RAG assistant achievement and excludes CV brand recognition service
- [ ] T019 Non-regression test: ask "расскажи о проекте AI-Portfolio" (project_details intent) and verify full project details appear (no content filtering applied)
- [ ] T020 Non-regression test: ask "контакты" and verify contacts appear correctly (deterministic contacts path unchanged)
- [ ] T021 Non-regression test: ask "какие технологии знает Дмитрий" (technology_overview intent) and verify full technology list appears
- [ ] T022 Edge case test: ask about technology NOT in portfolio (e.g., "опыт с Kubernetes") and verify "нет в портфолио" response
- [ ] T023 Clear plan cache after all changes: `curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans`
- [ ] T024 Run quickstart.md validation scenarios from `specs/005-fix-agent-answer-relevance/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (generate() signature change)
- **User Story 1 (Phase 3)**: Depends on Phase 2 — content filtering in normalizer
- **User Story 2 (Phase 4)**: Depends on Phase 2 — surface reduction + prompt strengthening
- **User Story 3 (Phase 5)**: Depends on Phase 3 (needs filtered facts to generate rich answer)
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **User Story 2 (P1)**: Can start after Phase 2 — independent from US1, can run in PARALLEL with US1
- **User Story 3 (P2)**: Depends on US1 (needs content-filtered facts to extract relevant bullets for rich answer)

### Within Each User Story

- Helpers before main logic (T005, T006 before T007)
- Normalizer changes before rag_tool changes (T007 before T009)
- Implementation before manual testing

### Parallel Opportunities

- **Phase 2**: T002 and T003 are sequential (T003 depends on T002)
- **Phase 3 + Phase 4**: US1 (T005-T010) and US2 (T011-T013) can run in PARALLEL after Phase 2
  - T011 (graph.py prompt) has no dependencies on normalizer work
  - T012 (surface reduction) only depends on T003 (foundational)
- **Within US1**: T005 and T006 are [P] — helper methods in same file but independent logic

---

## Parallel Example: US1 + US2

```text
After Phase 2 completes:

Thread A (User Story 1 — normalizer):        Thread B (User Story 2 — surface reduction + prompt):
  T005: _build_content_keywords()              T011: Strengthen AGENT_SYSTEM_PROMPT (graph.py)
  T006: _filter_fact_bullets()                 T012: Conditional surface reduction (rag_tool.py)
  T007: Add Rule 2b to normalize()             T013: Manual test surface reduction
  T008: Update normalize_facts()
  T009: Pass entities in rag_tool.py
  T010: Test content filtering

Then sequentially:
  T014-T016: User Story 3 (depends on US1 filtered facts)
  T017-T024: Polish & validation
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (clear cache)
2. Complete Phase 2: Foundational (generate() return signature)
3. Complete Phase 3: US1 — content filtering (core fix)
4. Complete Phase 4: US2 — surface reduction + prompt (prevents re-synthesis)
5. **STOP and VALIDATE**: Test "какой опыт с компьютерным зрением" — should now return only CV achievements
6. If MVP validates, proceed to US3

### Incremental Delivery

1. Setup + Foundational → generate() returns deterministic_used flag
2. Add US1 (content filtering) → normalizer filters irrelevant bullets
3. Add US2 (surface reduction + prompt) → agent can't re-synthesize → **MVP complete**
4. Add US3 (rich answer) → deterministic answer includes achievements → **full feature complete**
5. Polish → regression testing, cache cleanup

---

## Notes

- No new test files required — spec says "All existing tests pass without modification" (SC-005)
- Manual testing is primary validation method (acceptance scenarios from spec)
- All changes scoped to 4 files in `services/rag-api-new/app/agent/`
- Content filtering only activates for `technology_usage` intent with non-empty entity_names — zero risk to other intents
- Clear plan cache (T001, T023) is critical — stale cached plans won't trigger new normalizer logic
