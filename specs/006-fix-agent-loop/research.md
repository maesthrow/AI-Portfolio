# Research: Fix Agent Loop in RAG Pipeline

**Date**: 2026-02-28

## All Unknowns Resolved in Spec Phase

Все исследования были проведены на этапе `/speckit.specify`. Ключевые findings зафиксированы в секции `Research Findings` файла [spec.md](spec.md).

## Key Decisions

### Decision 1: `return_direct=False` — не менять

- **Decision**: Оставить `return_direct=False` на `portfolio_rag_tool`
- **Rationale**: Agent LLM обеспечивает стриминг ответа пользователю через `on_chat_model_stream` события. При `return_direct=True` стриминг сломается — ответ придёт одним блоком
- **Alternatives considered**: `return_direct=True` (отвергнуто — ломает UX стриминга)

### Decision 2: Минимальный tool_result — `answer` + `found`

- **Decision**: Возвращать только `{"answer": "...", "found": true/false}` из инструмента
- **Rationale**: Agent LLM не использует остальные поля (промпт запрещает). Сырые данные (`items`, `rendered_facts`, `sources`, `confidence`) создают шум и могут спровоцировать повторный вызов
- **Alternatives considered**: `answer` + `found` + `confidence` (отвергнуто — confidence может спровоцировать ретрай)

### Decision 3: Usage через status_queue side channel

- **Decision**: Передавать usage-данные через существующий `status_queue` вместо tool_result
- **Rationale**: `chat.py` использует `usage` из tool_result для rate limiting. Убирая `usage` из tool_result, нужен альтернативный канал. `status_queue` уже существует и используется для status events
- **Alternatives considered**: Оставить `usage` в tool_result (отвергнуто — нарушает FR-002); логировать и не агрегировать (отвергнуто — ломает rate limiting)

### Decision 4: `recursion_limit=6`

- **Decision**: Снизить с 8 до 6
- **Rationale**: Нормальный путь = 5 шагов (router + model + tools + model + clear_pending). 6 = минимальный запас. При повторе — быстрая ошибка вместо бесполезного 15-секундного ожидания
- **Alternatives considered**: 5 (слишком жёстко, 0 запас), 8 (позволяет 1 полный повтор — бесполезный)

### Decision 5: Таймаут 90 секунд

- **Decision**: `agent_timeout=90`
- **Rationale**: Нормальный запрос = 5-15 сек. 90 сек покрывает медленные провайдеры без обрезки, но не даёт висеть бесконечно
- **Alternatives considered**: 30 сек (может обрезать медленный GigaChat), 60 сек (приемлемо, но пользователь выбрал 90)
