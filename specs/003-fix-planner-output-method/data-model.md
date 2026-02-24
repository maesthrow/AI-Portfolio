# Data Model: Fix Planner Structured Output Method Per Provider

**Feature**: `003-fix-planner-output-method`

## Entities Affected

No new entities. No schema changes. No database migrations.

## Runtime State Change

The only "data" involved is the string value of the `method` parameter passed to `with_structured_output()`:

| Condition | `method` value | API behaviour |
|-----------|---------------|---------------|
| `type(self.llm).__name__ == "GigaChat"` | `"json_schema"` | Sends `response_format: {"type": "json_schema", "json_schema": {...}}` |
| Any other class name | `"json_mode"` | Sends `response_format: {"type": "json_object"}` |

## Provider → LLM Class Mapping (existing, unchanged)

| `PLANNER_LLM` env value | LLM class created by `LLMFactory` | Selected method |
|-------------------------|----------------------------------|-----------------|
| `gigachat:GigaChat-2` | `GigaChat` (langchain_gigachat) | `json_schema` |
| `deepseek:deepseek-chat` | `ChatOpenAI` (langchain_openai) | `json_mode` |
| `qwen:<model>` | `ChatOpenAI` (langchain_openai via LiteLLM) | `json_mode` |
| any other provider | `ChatOpenAI` or unknown | `json_mode` (safe default) |

## Output Schema (unchanged)

`QueryPlanV3` Pydantic schema is unchanged. Both `json_schema` and `json_mode` produce the same Pydantic instance — the difference is only in how the LLM API is instructed to format its response.
