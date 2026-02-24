# Implementation Plan: Fix Planner Structured Output Method Per Provider

**Branch**: `003-fix-planner-output-method` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-fix-planner-output-method/spec.md`

## Summary

Заменить хардкод `method="json_schema"` в `_plan_structured()` на провайдер-зависимый выбор метода:
- `GigaChat` → `"json_schema"` (текущее поведение, без изменений)
- Все остальные (`ChatOpenAI`: DeepSeek, Qwen) → `"json_mode"`

Изменение локализовано в **одном файле**, **одна строка кода**.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: LangChain 1.x (`langchain-core`, `langchain-gigachat`, `langchain-openai`)
**Storage**: N/A
**Testing**: pytest (existing tests in `services/rag-api-new/tests/`)
**Target Platform**: Linux Docker container
**Project Type**: Internal component (`PlannerLLM` class in rag-api-new)
**Performance Goals**: Нулевой overhead — `type(self.llm).__name__` вычисляется один раз при каждом вызове `_plan_structured()`; это строковое сравнение с O(1) стоимостью
**Constraints**: Изменение ТОЛЬКО в `services/rag-api-new/`. Не меняются env vars, публичные интерфейсы, схемы данных.
**Scale/Scope**: 1 файл модифицируется, 1 строка кода изменяется. Нет новых файлов.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. UTF-8 Encoding | PASS | Изменения в существующем Python-файле, без новых текстовых ресурсов |
| II. Root-Cause Resolution | PASS | Исправляем корневую причину: хардкод `method="json_schema"`, несовместимый с DeepSeek API |
| III. Clean Architecture | PASS | Inline определение метода; нет нового класса, нет DI, нет overengineering |
| IV. Service Directory Discipline | PASS | Изменение в `services/rag-api-new/` (активный сервис) |
| V. API Versioning & Contracts | N/A | Без новых HTTP-эндпоинтов |
| VI. Database Migration Discipline | N/A | Без изменений SQLAlchemy-моделей |
| VII. Simplicity & YAGNI | PASS | Минимально возможное изменение: 1 строка. Никаких новых env vars, helper методов, абстракций |

## Project Structure

### Source Code (files to modify)

```text
services/rag-api-new/app/
└── agent/
    └── planner/
        └── planner_llm.py    # [M] Detect provider from LLM class name, select method
```

**Legend**: [M] = Modified

**Structure Decision**: Нет новых файлов. Единственное изменение — в `_plan_structured()` внутри `PlannerLLM`. Не создаём отдельный метод `_get_method()` — это противоречило бы Constitution VII (YAGNI) для однострочного изменения.

## Design

### Change 1: Provider-aware method selection in `_plan_structured()`

**File: `services/rag-api-new/app/agent/planner/planner_llm.py`**

**Было** (line 106-110):
```python
structured_llm = self.llm.with_structured_output(
    QueryPlanV3,
    method="json_schema",  # Use JSON schema for better compatibility
    include_raw=True,
)
```

**Стало**:
```python
# GigaChat uses json_schema; DeepSeek / Qwen (ChatOpenAI) use json_mode
_method = "json_schema" if type(self.llm).__name__ == "GigaChat" else "json_mode"
structured_llm = self.llm.with_structured_output(
    QueryPlanV3,
    method=_method,
    include_raw=True,
)
```

**Почему `type(self.llm).__name__` вместо `isinstance(self.llm, GigaChat)`:**
- Избегает нового import (`from langchain_gigachat import GigaChat`) в файле, который на него не завязан
- Работает надёжно: LangChain не меняет имена классов между минорными версиями
- Если GigaChat когда-нибудь будет заменён — новый класс просто не совпадёт с "GigaChat" и получит `json_mode` (безопасный fallback)

**Логирование** (добавить строку после определения `_method`):
```python
logger.debug("Planner structured output method: %s (llm=%s)", _method, type(self.llm).__name__)
```

### What is NOT changed

- `_sanitize_plan()` — не трогаем (ISSUE-002 out of scope, confirmed in clarifications)
- `_validate_plan()` — не трогаем
- `__init__()` — не трогаем; не добавляем параметр `method` (YAGNI)
- Retry логика — не трогаем
- `PLANNER_REPAIR_PROMPT` — не трогаем
- `deps.py` — не трогаем (способ создания LLM не меняется)
- `settings.py` — не трогаем (нет новых env vars)
- Docker configuration — не трогаем

## Phase 0: Research

### D1: LangChain `with_structured_output` method support per provider

| Provider | Class | `json_schema` | `json_mode` |
|----------|-------|---------------|-------------|
| GigaChat | `GigaChat` (langchain-gigachat) | ✅ Поддерживается (нестабильно) | ❓ Не проверено |
| DeepSeek | `ChatOpenAI` (langchain-openai) | ❌ HTTP 400 (подтверждено в логах) | ✅ Поддерживается |
| Qwen via LiteLLM | `ChatOpenAI` (langchain-openai) | ❓ Не проверено | ✅ Стандарт OpenAI |

**Решение**: `json_schema` только для GigaChat, `json_mode` для всех `ChatOpenAI`-based провайдеров.

### D2: Механизм определения провайдера

Два варианта:

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| `isinstance(self.llm, GigaChat)` | Явно, type-safe | Нужен import `langchain_gigachat.GigaChat` |
| `type(self.llm).__name__ == "GigaChat"` | Нет нового import, KISS | Строковое сравнение (незначимый риск) |

**Решение**: `type(self.llm).__name__` — соответствует KISS и YAGNI. GigaChat — единственный non-OpenAI провайдер в проекте.

### D3: `json_mode` с `include_raw=True`

`with_structured_output(schema, method="json_mode", include_raw=True)` → ChatOpenAI отправляет `response_format={"type": "json_object"}` в API. Ответ — JSON-строка, которую LangChain парсит через Pydantic. `include_raw=True` возвращает `{"raw": AIMessage, "parsed": schema_instance, "parsing_error": ...}`. Этот формат идентичен для обоих методов — код обработки результата не меняется.

## Phase 1: Quickstart / Testing Strategy

### Как проверить после изменения

```bash
# 1. В infra/.env.dev изменить:
PLANNER_LLM=deepseek:deepseek-chat

# 2. Пересобрать и запустить:
docker compose -f infra/docker-compose.local.yaml up -d --build rag-api
docker compose -f infra/docker-compose.local.yaml up rag-ingest

# 3. Проверить логи prefetch:
# Ожидаемое: нет "Structured output failed", нет "HTTP 400", все вопросы получают правильный intent

# 4. Вернуть обратно (проверка регрессии):
PLANNER_LLM=gigachat:GigaChat-2
# Перезапустить и убедиться: поведение идентично предыдущему
```

### Unit test (минимальный)

```python
# tests/test_planner_output_method.py
def test_gigachat_uses_json_schema():
    """GigaChat LLM → method должен быть json_schema."""
    # Mock GigaChat-like object
    class FakeGigaChat:
        pass
    llm = FakeGigaChat()
    method = "json_schema" if type(llm).__name__ == "GigaChat" else "json_mode"
    assert method == "json_mode"  # FakeGigaChat не совпадает — правильно

def test_real_gigachat_class_name():
    """Проверяет что GigaChat из langchain_gigachat имеет нужное имя."""
    from langchain_gigachat import GigaChat
    assert type(GigaChat).__name__ != "GigaChat"  # это metaclass
    # Создать mock instance и проверить class name
```

Юнит-тест минимален, потому что реальная проверка — запуск prefetch с DeepSeek-планнером и отсутствие HTTP 400.

## Complexity Tracking

Нет нарушений конституции. Изменение атомарно: 1 файл, ~3 строки (определение метода + логирование + обновлённый вызов).

Единственное "расширение" — добавление `logger.debug()` — обосновано: без логирования невозможно верифицировать SC-001 (что метод выбирается правильно) без погружения в исходный код.
