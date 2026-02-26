# Quickstart: Fix Technology Query Bugs

**Branch**: `004-fix-normalizer-technology-filter`

## What This Fixes

- **Bug 1**: Agent answers "no experience found" for "какой опыт с компьютерным зрением" but correctly answers "где использовал компьютерное зрение" — inconsistent because the normalizer silently dropped `experience` documents.
- **Bug 2**: Agent returns only .NET/C# technologies for "какими технологиями владеет Дмитрий" — truncated at 12 alphabetically-first items, missing the primary Python/AI stack.

---

## Deploy

```bash
# 1. Build and restart rag-api
docker compose -f infra/docker-compose.local.yaml up -d --build rag-api

# 2. REQUIRED: Clear plan cache (old cached plans have wrong max_items)
curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans
```

---

## Verify Bug 1 Fix

Both questions must return t2/Aston CV experience with Detectron2/Ultralytics/YOLO.

```bash
# Question that previously failed (returned "no CV experience")
curl -s -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "какой опыт с компьютерным зрением"}]}' \
  | grep '"answer"'

# Question that previously worked (should still work)
curl -s -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "где использовал компьютерное зрение"}]}' \
  | grep '"answer"'
```

**Expected**: Both return t2 project with "Detectron2", "Ultralytics", "YOLO".

---

## Verify Bug 2 Fix

```bash
curl -s -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "какими технологиями владеет Дмитрий"}]}' \
  | grep '"answer"'
```

**Expected**: Response includes Python, LangChain, FastAPI, LangGraph (2024-2025 stack). Legacy .NET/C# technologies present but not dominant. Total technologies ≥15.

---

## Verify No Regression

```bash
# Run existing test suite
cd services/rag-api-new
pytest tests/ -v
```

All tests must pass.

---

## Check Plan Cache Was Cleared

```bash
curl http://localhost:8014/api/v1/admin/cache/stats
```

Plan cache hit count should reset to 0 after clearing.

---

## Rollback

If issues arise, revert the 3 changed files and redeploy:
```bash
git revert HEAD
docker compose -f infra/docker-compose.local.yaml up -d --build rag-api
curl -X DELETE http://localhost:8014/api/v1/admin/cache/plans
```
