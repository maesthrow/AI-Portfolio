# Quickstart: Fix Agent Answer Relevance

**Date**: 2026-02-26
**Branch**: `005-fix-agent-answer-relevance`

## Prerequisites

- Docker services running: `postgres`, `tei`, `litellm`, `redis`, `content-api`, `rag-api`
- RAG data ingested (run `rag-ingest` if fresh setup)

## Local Development

```bash
cd infra
docker compose -f docker-compose.local.yaml up -d
docker compose -f docker-compose.local.yaml up rag-ingest  # if needed
```

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `services/rag-api-new/app/agent/normalizer/normalizer.py` | Add content-level bullet filtering for `technology_usage` | P1 |
| `services/rag-api-new/app/agent/rag_tool.py` | Pass entity names to normalizer; conditional surface reduction | P1 |
| `services/rag-api-new/app/agent/answer/answer_llm.py` | Rich deterministic answer with filtered achievements | P2 |
| `services/rag-api-new/app/agent/graph.py` | Strengthen AGENT_SYSTEM_PROMPT relay instruction | P1 |

## Testing

### Manual Test (primary acceptance)

1. Clear plan cache:
```bash
curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans
```

2. Ask via chat UI or curl:
```bash
curl -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"какой опыт с компьютерным зрением"}],"thread_id":"test-005"}'
```

3. Verify response:
   - INCLUDES: CV-related achievements (brand recognition, CV model training)
   - EXCLUDES: "LLM-ассистент с RAG для расчёта штрафов"
   - EXCLUDES: "Backend на FastAPI, интеграции"

4. Bidirectional test:
```bash
curl -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"опыт с LLM и RAG"}],"thread_id":"test-005-b"}'
```
   - INCLUDES: LLM+RAG assistant achievement
   - EXCLUDES: CV brand recognition service

### Automated Tests

```bash
cd services/rag-api-new
pytest tests/ -v
```

## Debugging

Check normalizer output in logs:
```
Normalizer: X -> Y facts, rules=['technology_usage_filter', 'technology_usage_content_filter']
```

Check deterministic answer:
```
Answer deterministic_used=True preview='Дмитрий применял Computer Vision в проекте t2 — Нейросети (Aston, 2024–2025):...'
```

Check surface reduction:
```
tool_end ... output_preview='content=\'{"answer": "...", "rendered_facts": "", "items": []...'
```
