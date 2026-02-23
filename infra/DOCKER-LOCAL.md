# Docker Commands - Local Development

**Project:** `ai-portfolio-local`
**Compose:** `docker-compose.local.yaml`
**Env:** `.env.local`

---

## Quick Reference

```bash
# Базовый префикс для всех команд
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local
```

---

## Запуск

```bash
# Запустить все сервисы
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d

# Запустить с пересборкой образов
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d --build

# Пересборка без кэша (полная)
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local build --no-cache
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d

# Запустить конкретный сервис
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d frontend
```

---

## Остановка

```bash
# Остановить все сервисы
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local down

# Остановить с удалением volumes (ОСТОРОЖНО - удалит данные!)
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local down -v

# Остановить конкретный сервис
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local stop rag-api
```

---

## Статус и логи

```bash
# Статус всех контейнеров
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local ps

# Логи всех сервисов
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local logs

# Логи конкретного сервиса (последние 100 строк)
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local logs rag-api --tail 100

# Логи в реальном времени
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local logs -f rag-api

# Логи нескольких сервисов
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local logs -f rag-api content-api
```

---

## Перезапуск

```bash
# Перезапустить сервис
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local restart rag-api

# Пересоздать сервис (force recreate)
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d --force-recreate rag-api

# Пересобрать и перезапустить сервис
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d --build rag-api
```

---

## Content API - Управление данными

На локалке seeder запускается автоматически при старте content-api.
Для ручного управления данными:

```bash
# Запустить seeder вручную (обновит/добавит данные)
docker exec -it ai-portfolio-local-content-api-1 python -m app.seed.seed_ai_portfolio_new

# Зайти в PostgreSQL
docker exec -it ai-portfolio-local-postgres-1 psql -U ai_portfolio_user -d ai_portfolio_new

# Очистить ВСЕ данные из таблиц (ОСТОРОЖНО!)
docker exec -it ai-portfolio-local-postgres-1 psql -U ai_portfolio_user -d ai_portfolio_new -c "
TRUNCATE TABLE
  experience_project,
  experience,
  project_technology,
  project,
  technology,
  publication,
  contact,
  stats,
  tech_focus,
  tech_focus_tag,
  hero_tag,
  focus_area_bullet,
  focus_area,
  work_approach_bullet,
  work_approach,
  section_meta,
  profile
CASCADE;"

# После очистки - запустить seeder заново
docker exec -it ai-portfolio-local-content-api-1 python -m app.seed.seed_ai_portfolio_new

# После обновления данных в content-api - перезапустить ingest в RAG
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local restart rag-ingest
```

**Полный сброс данных (удаление volume):**
```bash
# Остановить сервисы
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local down

# Удалить volume PostgreSQL (УДАЛИТ ВСЕ ДАННЫЕ!)
docker volume rm ai-portfolio-local_pg_data

# Запустить заново (миграции + seeder выполнятся автоматически)
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local up -d
```

---

## RAG Ingest

На локалке `rag-ingest` запускается автоматически при `up`.
Для ручного перезапуска:

```bash
# Перезапустить ingest
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local restart rag-ingest

# Посмотреть логи ingest
docker compose -p ai-portfolio-local -f docker-compose.local.yaml --env-file .env.local logs rag-ingest
```

---

## RAG API Stats

```bash
# Статистика коллекции pgvector (количество документов по типам)
curl.exe "http://localhost:8004/api/v1/admin/stats"

# Красивый вывод JSON
curl.exe -s "http://localhost:8004/api/v1/admin/stats" | python -m json.tool

# Очистить коллекцию (ОСТОРОЖНО!)
curl.exe -X DELETE "http://localhost:8004/api/v1/admin/collection"
```

---

## RAG API Cache

RAG использует Redis для кэширования планов и embeddings.

```bash
# Статистика кэшей (количество ключей plan/embedding cache)
curl.exe "http://localhost:8004/api/v1/admin/cache/stats"

# Красивый вывод
curl.exe -s "http://localhost:8004/api/v1/admin/cache/stats" | python -m json.tool

# Очистить plan cache (после изменения промптов или логики планирования)
curl.exe -X DELETE "http://localhost:8004/api/v1/admin/cache/plans"

# Очистить embedding cache (после смены embedding модели)
curl.exe -X DELETE "http://localhost:8004/api/v1/admin/cache/embeddings"

# Очистить ВСЕ кэши (plans + embeddings)
curl.exe -X DELETE "http://localhost:8004/api/v1/admin/cache"
```

**Когда очищать кэши:**
- `plans` - изменили PLANNER_SYSTEM_PROMPT или логику планирования
- `embeddings` - сменили embedding модель
- `all` - полный сброс или серьёзные проблемы

**Автоматическая инвалидация:**
- Plan cache автоматически очищается при изменении данных (ingest с новым content hash)
- Embedding cache НЕ инвалидируется при ingest (зависит только от текста запроса)

---

## Полезные команды

```bash
# Зайти в контейнер
docker exec -it ai-portfolio-local-rag-api-1 bash
docker exec -it ai-portfolio-local-postgres-1 psql -U ai_portfolio_user -d ai_portfolio_new

# Посмотреть все контейнеры проекта
docker ps --filter "name=ai-portfolio-local"

# Очистить неиспользуемые образы
docker image prune -f
```

---

## Сервисы и порты

| Сервис | Внутренний порт | Внешний порт | URL |
|--------|-----------------|--------------|-----|
| frontend | 3000 | 3000 | http://localhost:3000 |
| content-api | 8000 | 8003 | http://localhost:8003 |
| rag-api | 8000 | 8004 | http://localhost:8004 |
| postgres | 5432 | 5433 | localhost:5433 |
| litellm | 4000 | 8005 | http://localhost:8005 |
| tei | 80 | 8006 | http://localhost:8006 |

---

## Troubleshooting

```bash
# Порт занят - найти процесс
netstat -ano | findstr :8001

# Остановить все контейнеры Docker
docker stop $(docker ps -aq)

# Проверить health статус
docker inspect ai-portfolio-local-content-api-1 --format='{{.State.Health.Status}}'
```
