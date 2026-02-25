# Docker Commands - Production Server

**Project:** `ai-folio`
**Compose:** `docker-compose-prod.yaml`
**Env:** `.env.prod`
**Server:** `ai-folio-prod` (`/opt/ai-folio/AI-Portfolio/infra`)

---

## Quick Reference

```bash
# Базовый префикс для всех команд
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod
```

---

## Деплой / Обновление

```bash
# 1. Получить изменения из репозитория
cd /opt/ai-folio/AI-Portfolio
git pull

# 2. Пересобрать и перезапустить
cd infra
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d --build

# 3. (Опционально) Перезапустить ingest если изменились данные
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up rag-ingest
```

---

## Запуск

```bash
# Запустить все сервисы
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d

# Запустить с пересборкой
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d --build

# Пересборка без кэша
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod build --no-cache
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d

# Запустить конкретный сервис
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d rag-api
```

---

## Остановка

```bash
# Остановить все сервисы
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod down

# Остановить с удалением volumes (ОСТОРОЖНО - удалит данные БД!)
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod down -v

# Остановить конкретный сервис
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod stop rag-api
```

---

## Статус и логи

```bash
# Статус всех контейнеров
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod ps

# Быстрый просмотр (без compose)
docker ps --filter "name=ai-folio"

# Логи конкретного сервиса
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod logs rag-api --tail 100

# Логи в реальном времени
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod logs -f rag-api

# Логи напрямую (без compose)
docker logs ai-folio-rag-api-1 --tail 100
docker logs -f ai-folio-rag-api-1
```

---

## Перезапуск

```bash
# Перезапустить сервис
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod restart rag-api

# Пересоздать сервис
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d --force-recreate rag-api

# Пересобрать и перезапустить
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d --build rag-api

# Перезапустить все
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod restart
```

---

## Content API - Управление данными

На проде seeder НЕ запускается автоматически (только миграции).
Данные сохраняются в `pg_data` volume между рестартами.

```bash
# Запустить seeder вручную (обновит/добавит данные)
docker exec -it ai-folio-content-api-1 python -m app.seed.seed_ai_portfolio_new

# Зайти в PostgreSQL
docker exec -it ai-folio-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB

# Очистить ВСЕ данные из таблиц (ОСТОРОЖНО!)
docker exec -it ai-folio-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
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

# После очистки - запустить seeder
docker exec -it ai-folio-content-api-1 python -m app.seed.seed_ai_portfolio_new

# После обновления данных - ОБЯЗАТЕЛЬНО перезапустить ingest
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up rag-ingest
```

**Полный сброс данных (удаление volume):**
```bash
# Остановить сервисы
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod down

# Удалить volume PostgreSQL (УДАЛИТ ВСЕ ДАННЫЕ!)
docker volume rm ai-folio_pg_data

# Запустить заново (миграции выполнятся автоматически)
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d

# Подождать пока content-api поднимется, затем seeder + ingest
sleep 15
docker exec -it ai-folio-content-api-1 python -m app.seed.seed_ai_portfolio_new
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up rag-ingest
или
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod run --rm rag-ingest
```

```

---

## RAG Ingest

На проде `rag-ingest` НЕ запускается автоматически (использует `profiles: ["init"]`).
Запускать вручную после обновления данных:

```bash
# Запустить ingest (выполнит export -> ingest и остановится)
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up rag-ingest

# Запустить в фоне
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up -d rag-ingest

# Посмотреть логи ingest
docker logs ai-folio-rag-ingest-1
docker logs -f ai-folio-rag-ingest-1
```

---

## RAG API Stats

**Примечание:** В контейнере rag-api нет curl, используем Python urllib.

```bash
# Статистика коллекции pgvector
docker exec ai-folio-rag-api-1 python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/admin/stats').read().decode())"

# Красивый вывод JSON
docker exec ai-folio-rag-api-1 python -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/admin/stats').read()), indent=2, ensure_ascii=False))"

# Очистить коллекцию (ОСТОРОЖНО!)
docker exec ai-folio-rag-api-1 python -c "import urllib.request; r=urllib.request.Request('http://localhost:8000/api/v1/admin/collection', method='DELETE'); print(urllib.request.urlopen(r).read().decode())"
```

---

## RAG API Cache

RAG использует Redis для кэширования планов и embeddings.
На проде порты не проброшены, поэтому используем `docker exec` с Python.

```bash
# Статистика кэшей (количество ключей plan/embedding cache)
docker exec ai-folio-rag-api-1 python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/admin/cache/stats').read().decode())"

# Красивый вывод
docker exec ai-folio-rag-api-1 python -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/admin/cache/stats').read()), indent=2))"

# Очистить plan cache (после изменения промптов или логики планирования)
docker exec ai-folio-rag-api-1 python -c "import urllib.request; r=urllib.request.Request('http://localhost:8000/api/v1/admin/cache/plans', method='DELETE'); print(urllib.request.urlopen(r).read().decode())"

# Очистить embedding cache (после смены embedding модели)
docker exec ai-folio-rag-api-1 python -c "import urllib.request; r=urllib.request.Request('http://localhost:8000/api/v1/admin/cache/embeddings', method='DELETE'); print(urllib.request.urlopen(r).read().decode())"

# Очистить ВСЕ кэши (plans + embeddings)
docker exec ai-folio-rag-api-1 python -c "import urllib.request; r=urllib.request.Request('http://localhost:8000/api/v1/admin/cache', method='DELETE'); print(urllib.request.urlopen(r).read().decode())"
```

**Когда очищать кэши:**
- `plans` - изменили PLANNER_SYSTEM_PROMPT или логику планирования
- `embeddings` - сменили embedding модель
- `all` - полный сброс или серьёзные проблемы

**Автоматическая инвалидация:**
- Plan cache автоматически очищается при изменении данных (ingest с новым content hash)
- Embedding cache НЕ инвалидируется при ingest (зависит только от текста запроса)

---

## Caddy (Reverse Proxy + HTTPS)

```bash
# Перезагрузить конфиг Caddy
docker exec ai-folio-caddy-1 caddy reload --config /etc/caddy/Caddyfile

# Логи Caddy
docker logs ai-folio-caddy-1 --tail 100

# Проверить сертификаты
docker exec ai-folio-caddy-1 caddy list-modules
```

---

## Полезные команды

```bash
# Зайти в контейнер
docker exec -it ai-folio-rag-api-1 bash
docker exec -it ai-folio-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB

# Health check статус
docker inspect ai-folio-content-api-1 --format='{{.State.Health.Status}}'

# Использование ресурсов
docker stats --no-stream

# Очистить неиспользуемые образы
docker image prune -f

# Очистить все неиспользуемое (images, containers, networks)
docker system prune -f
```

---

## Сервисы и порты

| Сервис | Внутренний порт | Внешний порт | Описание |
|--------|-----------------|--------------|----------|
| caddy | 80, 443 | 80, 443 | Reverse proxy + HTTPS |
| frontend | 3000 | - (через caddy) | Next.js |
| content-api | 8000 | - (через caddy) | FastAPI |
| rag-api | 8000 | - (через caddy) | RAG Agent API |
| postgres | 5432 | - (internal) | PostgreSQL |
| litellm | 4000 | - (internal) | LLM Proxy |
| tei | 80 | - (internal) | Embeddings |

---

## Troubleshooting

```bash
# Проверить unhealthy контейнеры
docker ps --filter "health=unhealthy"

# Детальная информация о контейнере
docker inspect ai-folio-content-api-1

# Проверить сеть
docker network ls
docker network inspect infra_default

# Проверить volumes
docker volume ls | grep ai-folio

# Перезапустить Docker daemon (если совсем плохо)
systemctl restart docker
```

---

## Полный деплой с нуля

```bash
# 1. Клонировать репозиторий
cd /opt/ai-folio
git clone <repo-url> AI-Portfolio
cd AI-Portfolio/infra

# 2. Создать .env.prod из шаблона
cp .env.dev .env.prod
# Отредактировать .env.prod

# 3. Запустить все сервисы
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod up -d --build

# 4. Подождать пока сервисы поднимутся, затем ingest
sleep 30
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod --profile init up rag-ingest

# 5. Проверить статус
docker compose -p ai-folio -f docker-compose-prod.yaml --env-file .env.prod ps
```
