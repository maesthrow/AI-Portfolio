# Quickstart: Verify pgvector Migration

**Branch**: `001-migrate-pgvector`

## Prerequisites

- Docker + Docker Compose installed
- Project repo cloned, branch `001-migrate-pgvector` checked out

## 1. Start Infrastructure

```bash
cd infra
docker compose -f docker-compose.local.yaml up -d postgres redis tei litellm
```

Verify PostgreSQL has pgvector:
```bash
docker compose -f docker-compose.local.yaml exec postgres psql -U ai_user -d ai_portfolio_new \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

Expected: one row with `vector` and version like `0.8.0`.

## 2. Start Services

```bash
docker compose -f docker-compose.local.yaml up -d content-api rag-api
```

Check rag-api health:
```bash
curl -s http://localhost:8014/healthz | python -m json.tool
```

Expected: `{"status": "ok"}`.

## 3. Run Ingestion

```bash
docker compose -f docker-compose.local.yaml up rag-ingest
```

Verify document count:
```bash
curl -s http://localhost:8014/api/v1/admin/stats | python -m json.tool
```

Expected: `total` count ~120-200, breakdown by `type`.

## 4. Test Agent

```bash
curl -s -X POST http://localhost:8014/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Какие проекты используют FastAPI?"}]}' \
  | head -20
```

Expected: NDJSON stream with `start`, `status`, `delta`, `end` events.

## 5. Verify No ChromaDB

```bash
# ChromaDB service should NOT exist
docker compose -f docker-compose.local.yaml ps | grep chroma
# Expected: no output

# Verify pgvector table exists
docker compose -f docker-compose.local.yaml exec postgres psql -U ai_user -d ai_portfolio_new \
  -c "SELECT COUNT(*) FROM portfolio_new;"
# Expected: row count matching admin/stats total
```

## 6. Verify Backup

```bash
docker compose -f docker-compose.local.yaml exec postgres \
  pg_dump -U ai_user ai_portfolio_new --schema-only | grep -A5 "portfolio_new"
```

Expected: `CREATE TABLE portfolio_new` with `vector(768)` column.

## 7. Run Tests

```bash
cd services/rag-api-new
pytest tests/ -v
```

Expected: all tests pass.

## 8. Grep for ChromaDB Remnants

```bash
cd /path/to/AI-Portfolio
grep -ri "chroma" --include="*.py" --include="*.yaml" --include="*.md" \
  --include="*.toml" --include="*.env*" --include="*.sql" \
  --exclude-dir=".git" --exclude-dir="node_modules" \
  --exclude-dir="specs" --exclude-dir=".specify"
```

Expected: no active references to ChromaDB in code, config, or documentation.
