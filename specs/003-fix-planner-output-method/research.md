# Research: Fix Planner Structured Output Method Per Provider

**Feature**: `003-fix-planner-output-method`
**Date**: 2026-02-24

## Decisions

### D1: LangChain `with_structured_output` method per provider

**Decision**: Use `method="json_schema"` for GigaChat, `method="json_mode"` for all other providers (DeepSeek, Qwen).

**Rationale**:
- Confirmed from production logs: DeepSeek rejects `json_schema` with HTTP 400 `"This response_format type is unavailable now"` — every attempt fails
- GigaChat accepts `json_schema` (albeit unreliably, causing NoneType on attempt 1)
- `json_mode` = `response_format: {"type": "json_object"}` — supported by all OpenAI-compatible APIs including DeepSeek
- LangChain's `ChatOpenAI` translates `method="json_mode"` to this format correctly

**Alternatives considered**:
- `method="function_calling"` — would require tool schema changes; more complex migration; rejected (YAGNI)
- Patching DeepSeek API to support `json_schema` — not in our control; rejected
- Separate env var `PLANNER_OUTPUT_METHOD` — unnecessary complexity; rejected (YAGNI)

---

### D2: Provider detection mechanism

**Decision**: `type(self.llm).__name__ == "GigaChat"` (string comparison on class name).

**Rationale**:
- `PlannerLLM` receives a `BaseChatModel` instance; the concrete class encodes provider identity
- `GigaChat` (from `langchain_gigachat`) is the only provider that needs `json_schema`; all others (`ChatOpenAI` for DeepSeek and Qwen) use `json_mode`
- No new import needed — avoids adding `langchain_gigachat` as a direct dependency of `planner_llm.py`
- GigaChat's class name has been stable across versions and is unlikely to change

**Alternatives considered**:
- `isinstance(self.llm, GigaChat)` — requires `from langchain_gigachat import GigaChat`; adds import coupling; rejected (KISS)
- Passing `method` parameter to `PlannerLLM.__init__()` — exposes internal detail to callers; rejected (YAGNI)
- Checking `self.llm.__class__.__module__.startswith("langchain_gigachat")` — more fragile; rejected

---

### D3: Effect on `include_raw=True` behaviour

**Decision**: No change to result processing code.

**Rationale**:
- `with_structured_output(schema, method="json_mode", include_raw=True)` returns the same dict structure `{"raw": AIMessage, "parsed": schema_instance, "parsing_error": ...}` as `json_schema`
- The existing code that processes this dict (lines 116-124 in `_plan_structured()`) works unchanged for both methods
- Verified: LangChain's ChatOpenAI implementation uses identical parsing path for both `json_schema` and `json_mode` when `include_raw=True`

---

### D4: Fallback behaviour for unknown providers

**Decision**: Unknown providers (future additions) get `json_mode` by default.

**Rationale**:
- `json_mode` is the more universal, widely-supported format (standard OpenAI API)
- If a new provider is added (e.g., a custom model), it's more likely OpenAI-compatible than GigaChat-compatible
- This matches the spec FR-005: "unknown provider MUST fall back to `json_mode`"

---

### D5: No unit test file needed

**Decision**: No new test file. Single unit test (if any) is trivial and can be added inline.

**Rationale**:
- The core logic is a string comparison — not meaningfully testable with unit tests
- The real verification is the E2E test: run with `PLANNER_LLM=deepseek:deepseek-chat` and check prefetch logs
- Adding a test file for a 1-line change would violate Constitution VII (YAGNI)
- SC-001 and SC-002 are verified through the deployment validation step, not unit tests
