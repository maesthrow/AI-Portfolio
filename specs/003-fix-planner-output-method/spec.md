# Feature Specification: Fix Planner Structured Output Method Per Provider

**Feature Branch**: `003-fix-planner-output-method`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Fix planner structured output method to be provider-dependent: GigaChat uses json_schema, DeepSeek uses json_mode. Fixes ISSUE-001 (planner NoneType retry on first attempt) and ISSUE-002 (confidence=0.0 after retry triggering unnecessary hybrid search). Currently planner_llm.py hardcodes method=json_schema which GigaChat supports unreliably and DeepSeek rejects entirely with HTTP 400."

## Clarifications

### Session 2026-02-24

- Q: Should fixing `_sanitize_plan()` to replace `confidence=0.0` with `0.5` on valid retry plans (ISSUE-002) be included in this scope? → A: No — out of scope. Only provider-aware method selection is in scope. ISSUE-002 for GigaChat retry is tracked separately.

This means: **FR-007 is confirmed** — no changes to `_sanitize_plan()`, no changes to confidence handling logic. The only code change is in `_plan_structured()` where `method=` is selected.

---

## Problem Statement

The AI agent's query planner fails when configured to use DeepSeek as the planning model:

**Current behaviour** (ISSUE-001 + ISSUE-002 from `specs/001-migrate-pgvector/known-issues.md`):

1. **DeepSeek (HTTP 400)**: Planner sends a `json_schema` structured-output request; DeepSeek API rejects it entirely with `"This response_format type is unavailable now"`. All 3 retry attempts fail → planner falls back to `general_unstructured` intent, ignoring the user's actual question.
2. **GigaChat (NoneType)**: GigaChat accepts the request but often returns an empty/null parsed result on attempt 1 → retry is triggered → +5–10 s latency, +1 500 tokens. After retry, `confidence` field is often `0.0` → a redundant hybrid search is triggered → additional +15–20 s and more tokens (ISSUE-002).

The root cause is a single hardcoded line: `method="json_schema"` in `planner_llm.py`. DeepSeek requires `method="json_mode"` (JSON-object format), while GigaChat works with `json_schema` (albeit unreliably).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Switch PLANNER_LLM to DeepSeek Without Failures (Priority: P1)

An administrator configures `PLANNER_LLM=deepseek:deepseek-chat` in the environment and restarts the service. The query planner works correctly for all questions — no HTTP 400 errors, no fallback to `general_unstructured`.

**Why this priority**: This is the primary blocker. Without this fix, DeepSeek cannot be used as the planner at all, despite being the intended ISSUE-001 solution.

**Independent Test**: Set `PLANNER_LLM=deepseek:deepseek-chat`, restart rag-api, run the prefetch log — zero `Structured output failed` warnings, all questions receive a meaningful intent (not `general_unstructured`).

**Acceptance Scenarios**:

1. **Given** `PLANNER_LLM=deepseek:deepseek-chat` is set, **When** the planner processes "расскажи о проектах", **Then** it returns a valid plan with `intents=["project_list"]` and no `Structured output failed` warning
2. **Given** `PLANNER_LLM=deepseek:deepseek-chat` is set, **When** the planner processes "где применялся RAG", **Then** it returns `intents=["technology_usage"]` with `confidence >= 0.7`
3. **Given** `PLANNER_LLM=deepseek:deepseek-chat` is set, **When** the planner processes any of the 39 prefetch questions, **Then** zero HTTP 400 errors occur and all intents are non-`general_unstructured`

---

### User Story 2 — GigaChat Planner Continues to Work (Priority: P1)

When `PLANNER_LLM=gigachat:GigaChat-2` (current default), the planner behaviour is identical to before this change — same intents, same latency profile, no regression.

**Why this priority**: Cannot break what already works. GigaChat is the production default.

**Independent Test**: Set `PLANNER_LLM=gigachat:GigaChat-2`, run a question through the agent — plan is generated successfully, no change in behaviour.

**Acceptance Scenarios**:

1. **Given** `PLANNER_LLM=gigachat:GigaChat-2`, **When** the planner processes any question, **Then** it uses `json_schema` method (existing behaviour) and produces a valid plan
2. **Given** `PLANNER_LLM=gigachat:GigaChat-2`, **When** GigaChat returns a null result on attempt 1, **Then** retry fires as before — no new behaviour is introduced

---

### User Story 3 — No Manual Configuration Required (Priority: P2)

The correct output method is selected automatically based on the configured LLM provider. An operator switches provider in `.env` and the system self-adapts without any other changes.

**Why this priority**: Reduces operational burden; future provider additions should also work without extra configuration.

**Independent Test**: Switch between GigaChat and DeepSeek providers using only `PLANNER_LLM` env var — no other changes needed, correct method selected each time.

**Acceptance Scenarios**:

1. **Given** `PLANNER_LLM=deepseek:deepseek-chat`, **When** no other planner config is changed, **Then** `json_mode` is automatically used
2. **Given** `PLANNER_LLM=gigachat:GigaChat-2`, **When** no other planner config is changed, **Then** `json_schema` is automatically used
3. **Given** an unknown/new provider is configured as PLANNER_LLM, **When** the planner initialises, **Then** the system defaults to a safe fallback method without crashing

---

### Edge Cases

- What happens when DeepSeek API is temporarily unavailable? → Same fallback behaviour as current: `general_unstructured` plan returned, no crash
- What happens when a new provider is added that supports neither `json_schema` nor `json_mode`? → System falls back to `json_mode` as the more universally supported option
- What if GigaChat improves and `json_schema` works consistently in the future? → No change needed, system still selects `json_schema` for GigaChat correctly
- What happens if `confidence=0.0` occurs after a successful DeepSeek first attempt? → DeepSeek should populate confidence correctly; if not, that is a separate issue (ISSUE-002 tracking)

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The planner MUST select the structured-output method based on the LLM provider (`json_schema` for GigaChat, `json_mode` for DeepSeek)
- **FR-002**: The planner MUST NOT require any additional environment variable or configuration to determine the correct method — provider detection is automatic
- **FR-003**: The planner MUST continue to use `json_schema` when the configured provider is GigaChat — identical to current behaviour, no regression
- **FR-004**: The planner MUST use `json_mode` when the configured provider is DeepSeek, eliminating HTTP 400 errors entirely
- **FR-005**: When an unrecognised provider is configured, the planner MUST fall back to `json_mode` as the safer default and log a warning
- **FR-006**: Provider detection MUST work without network calls — determined from the LLM instance or its attributes at initialisation time
- **FR-007**: The fix MUST NOT change any public interfaces, environment variable names, API contracts, or planner output schemas

### Key Entities

- **PlannerLLM**: The component that generates query plans; contains `_plan_structured()` where the output method is selected
- **LLM Provider**: The configured backend (GigaChat, DeepSeek, Qwen) — derived from the `PLANNER_LLM` env var or LLM instance type
- **Structured Output Method**: The serialisation format used to extract JSON from LLM response (`json_schema` = strict schema enforcement; `json_mode` = JSON-object mode)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When `PLANNER_LLM=deepseek:deepseek-chat`, zero `"Structured output failed"` warnings appear in the prefetch log across all 39 questions
- **SC-002**: When `PLANNER_LLM=deepseek:deepseek-chat`, zero questions are assigned `general_unstructured` intent due to planner failure (shortcuts excluded)
- **SC-003**: When `PLANNER_LLM=gigachat:GigaChat-2`, the planner retry rate does not increase compared to the current baseline — no regression
- **SC-004**: No new environment variables are required — the fix is fully transparent to operators switching providers
- **SC-005**: The change is localised to a single file with minimal lines changed — surgical fix, not a refactor

---

## Assumptions

- DeepSeek API supports `json_mode` (`response_format: {"type": "json_object"}`) — confirmed by DeepSeek documentation; LangChain's `ChatOpenAI` translates `method="json_mode"` to this format correctly
- Provider identity can be reliably detected from the LLM class name or its base URL at the time `PlannerLLM` is instantiated — no runtime API calls needed
- Qwen (via LiteLLM) and any other unknown provider default to `json_mode` — this is the safer, more widely supported format
- This fix makes DeepSeek usable as planner, but does NOT eliminate GigaChat's occasional first-attempt NoneType (ISSUE-001 partial) — GigaChat retry may still fire; this is a known LLM behaviour
- The `confidence=0.0` issue on GigaChat retry (ISSUE-002) is out of scope for this ticket — tracked separately
