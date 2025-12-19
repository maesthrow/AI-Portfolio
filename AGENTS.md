# AGENTS.md (RU)

Этот файл — короткие правила для AI-ассистентов (Codex/Claude и др.) при работе с репозиторием **AI-Portfolio**.

## 1) Актуальные директории и файлы

- `frontend-new/` — актуальный Next.js фронтенд.
- `services/content-api-new/` — актуальный Content API (FastAPI + Postgres).
- `services/rag-api-new/` — RAG/Agent API (новая версия).
- `services/rag-api/` — RAG/Agent API (предыдущая версия; используйте только если явно нужно).
- `infra/compose.apps.yaml` — основной Docker Compose стек для разработки.
- `infra/.env.dev` — dev-конфиг окружения (используется `docker compose` и подхватывается сервисами).

Если не уверены, какой сервис/версия используется фронтом — сначала смотрите `infra/compose.apps.yaml` и конфиг в `frontend-new/`.

## 2) Что считать устаревшим

- `services/content-api/` — legacy Content API.
- `infra/docker-compose.yaml` и похожие старые compose-файлы — используйте только если прямо попросили.

## 3) Как запускать (рекомендуемый путь)

### Docker Compose

Ориентируйтесь на один базовый префикс команды:

- Список сервисов: `docker compose -f infra/compose.apps.yaml --env-file infra/.env.dev config --services`
- Сборка сервиса: `docker compose -f infra/compose.apps.yaml --env-file infra/.env.dev build <service>`
- Запуск сервиса: `docker compose -f infra/compose.apps.yaml --env-file infra/.env.dev up -d <service>`
- Полный стек: `docker compose -f infra/compose.apps.yaml --env-file infra/.env.dev up -d --build`

### Локально без Docker (когда нужно)

- `frontend-new/`: `npm install` → `npm run dev`
- `services/*`: запуск через `uvicorn` (см. `Dockerfile` конкретного сервиса). Учтите, что сервисы ожидают переменные окружения из `infra/.env.dev`.

## 4) Принципы изменений (важно)

- Всегда читать CLAUDE.md, где подробно описаны правила 
- Делайте минимальные и локальные правки; не рефакторьте “заодно”.
- Не ломайте API-контракты: префикс `/api/v1` сохраняйте, схемы меняйте осознанно.
- Для `rag-api-new`: при изменениях в поиске/индексации/инструментах агента обновляйте документацию `rag-api-new-doc.md`.
- Избегайте добавления новых зависимостей без необходимости (и без проверки сборки).
- Если правите Compose/infra — убедитесь, что имена сервисов совпадают с `services:` в YAML (Compose чувствителен к точным именам).

## 5) Проверка перед завершением

Минимум:

- Python: `python -m compileall services/<service>/app`
- Frontend: `npm run build` (если меняли `frontend-new/`)

Если в репозитории есть дополнительные инструкции — используйте `CLAUDE_RU.md` как расширенную справку.

