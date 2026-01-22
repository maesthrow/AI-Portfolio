# ТЗ: Rate Limiting для AI-агента

**Версия**: 1.0
**Дата**: 2025-01-23

---

## Цель

Защитить LLM-ресурсы (GigaChat) от злоупотреблений путём ограничения потребления токенов на уровне сессии и IP-адреса.

---

## Требования

### Функциональные

1. **Лимит по токенам** (не по количеству сообщений)
   - Считаются только LLM-токены (GigaChat): `prompt_tokens + completion_tokens`
   - Embeddings НЕ ограничиваются

2. **Два независимых лимита**:
   - **Session**: 20 000 токенов/час (ограничение одного пользователя)
   - **IP**: 50 000 токенов/час (защита от атак с одного источника)
   - Блокировка если превышен ЛЮБОЙ из лимитов

3. **Warning при приближении к лимиту**
   - Показывать когда использовано ≥80% лимита (осталось ≤20%)

4. **Graceful degradation**
   - Если Redis недоступен → блокировать ВСЕ запросы к агенту
   - Возвращать понятную ошибку пользователю

### Нефункциональные

- Все параметры конфигурируемые через settings
- Минимальное влияние на латентность (<5ms на проверку)
- Логирование превышений для мониторинга

---

## Архитектура

### Схема работы

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Запрос от пользователя                        │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. Проверка доступности Redis                                          │
│     └─ Если недоступен → 503 "Сервис временно недоступен"               │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. Проверка лимитов (ДО обработки запроса)                             │
│     ├─ Получить текущее использование: session + IP                     │
│     └─ Если любой лимит превышен → 429 + rate_limit info                │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. Обработка запроса (LLM pipeline)                                    │
│     └─ Получить usage.total_tokens из ответа GigaChat                   │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. Инкремент счётчиков (ПОСЛЕ успешного ответа)                        │
│     ├─ INCRBY rl:session:{session_id} {tokens}                          │
│     ├─ INCRBY rl:ip:{ip} {tokens}                                       │
│     └─ EXPIRE на оба ключа (если первый инкремент)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. Ответ клиенту                                                       │
│     └─ Включить rate_limit info (remaining, show_warning, reset_in)     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Логика двух лимитов

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ИНТЕРНЕТ                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Офис (1 IP: 85.140.10.5)              Дом (IP: 178.57.20.30)          │
│  ┌─────────┐ ┌─────────┐               ┌─────────┐                     │
│  │ Вася    │ │ Петя    │               │ Вася    │                     │
│  │session-1│ │session-2│               │session-3│  ← другой IP,       │
│  │ 15K/20K │ │ 8K/20K  │               │ 5K/20K  │    тот же человек   │
│  └─────────┘ └─────────┘               └─────────┘                     │
│       │           │                          │                         │
│       └─────┬─────┘                          │                         │
│             ▼                                ▼                         │
│      IP лимит: 23K/50K                 IP лимит: 5K/50K                │
│      (сумма всех сессий)               (личный)                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Сценарии:
1. Вася (session-1) использовал 15K → может ещё 5K по сессии
2. Офисный IP использовал 23K → может ещё 27K суммарно
3. Если Вася очистит localStorage → новая сессия, но IP помнит 23K
4. Вася дома с другим IP → начинает с нуля по IP, но session-3 отдельный
```

---

## API изменения

### Ответ при успешном запросе

В финальный chunk стриминга добавляется `rate_limit`:

```json
{
  "type": "done",
  "usage": {
    "tokens_used": 847
  },
  "rate_limit": {
    "session": {
      "used": 16847,
      "limit": 20000,
      "remaining": 3153
    },
    "ip": {
      "used": 28500,
      "limit": 50000,
      "remaining": 21500
    },
    "reset_in_seconds": 1847,
    "show_warning": true
  }
}
```

**Поля:**
- `session.used` / `session.remaining` — использовано/осталось по сессии
- `ip.used` / `ip.remaining` — использовано/осталось по IP
- `reset_in_seconds` — через сколько секунд сбросится лимит (минимум из двух)
- `show_warning` — `true` если любой лимит использован на ≥80%

### Ответ при превышении лимита (429)

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Достигнут лимит использования AI-агента. Попробуйте снова через 31 минуту",
    "details": {
      "exceeded_by": "session",
      "reset_in_seconds": 1892,
      "reset_in_human": "31 минуту"
    }
  }
}
```

### Ответ при недоступности Redis (503)

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "AI-агент временно недоступен. Попробуйте позже"
  }
}
```

---

## Настройки (settings.py)

```python
# Rate Limiting
rate_limit_enabled: bool = True
rate_limit_session_tokens: int = 20_000       # токенов/окно на сессию
rate_limit_ip_tokens: int = 50_000            # токенов/окно на IP
rate_limit_window_seconds: int = 3600         # окно = 1 час
rate_limit_warning_threshold: float = 0.8     # warning при 80%+ использования
```

---

## Redis ключи

| Ключ | TTL | Значение |
|------|-----|----------|
| `rl:session:{session_id}` | `rate_limit_window_seconds` |累计 токенов |
| `rl:ip:{ip}` | `rate_limit_window_seconds` |累计 токенов |

**Пример:**
```
rl:session:abc123def456  →  15420  (TTL: 2847s)
rl:ip:85.140.10.5        →  28500  (TTL: 2847s)
```

---

## Структура файлов

```
services/rag-api-new/app/
├── rate_limit/
│   ├── __init__.py
│   ├── limiter.py          # RateLimiter class
│   ├── schemas.py          # RateLimitInfo, RateLimitError
│   └── middleware.py       # FastAPI middleware (опционально)
```

### limiter.py (псевдокод)

```python
class RateLimiter:
    """Rate limiter на основе Redis."""

    def __init__(self, cache: CacheService, settings: Settings):
        self.cache = cache
        self.settings = settings

    def check_available(self) -> bool:
        """Проверить доступность Redis."""
        return self.cache.available

    def get_usage(self, session_id: str, ip: str) -> RateLimitUsage:
        """Получить текущее использование."""
        session_used = self.cache.redis.get(f"rl:session:{session_id}") or 0
        ip_used = self.cache.redis.get(f"rl:ip:{ip}") or 0

        session_ttl = self.cache.redis.ttl(f"rl:session:{session_id}")
        ip_ttl = self.cache.redis.ttl(f"rl:ip:{ip}")

        return RateLimitUsage(
            session_used=int(session_used),
            ip_used=int(ip_used),
            reset_in_seconds=max(session_ttl, ip_ttl, 0)
        )

    def check_limit(self, session_id: str, ip: str) -> tuple[bool, RateLimitInfo]:
        """
        Проверить, не превышен ли лимит.

        Returns:
            (allowed, info)
        """
        usage = self.get_usage(session_id, ip)

        session_exceeded = usage.session_used >= self.settings.rate_limit_session_tokens
        ip_exceeded = usage.ip_used >= self.settings.rate_limit_ip_tokens

        allowed = not (session_exceeded or ip_exceeded)
        exceeded_by = "session" if session_exceeded else ("ip" if ip_exceeded else None)

        info = self._build_info(usage, exceeded_by)
        return allowed, info

    def record_usage(self, session_id: str, ip: str, tokens: int) -> RateLimitInfo:
        """
        Записать использование токенов.
        Вызывается ПОСЛЕ успешного ответа LLM.
        """
        window = self.settings.rate_limit_window_seconds

        # Атомарный инкремент с установкой TTL
        pipe = self.cache.redis.pipeline()

        session_key = f"rl:session:{session_id}"
        ip_key = f"rl:ip:{ip}"

        pipe.incrby(session_key, tokens)
        pipe.expire(session_key, window, nx=True)  # NX = только если нет TTL

        pipe.incrby(ip_key, tokens)
        pipe.expire(ip_key, window, nx=True)

        results = pipe.execute()

        new_session_used = results[0]
        new_ip_used = results[2]

        return self._build_info(
            RateLimitUsage(
                session_used=new_session_used,
                ip_used=new_ip_used,
                reset_in_seconds=window
            ),
            exceeded_by=None
        )

    def _build_info(self, usage: RateLimitUsage, exceeded_by: str | None) -> RateLimitInfo:
        """Построить RateLimitInfo для ответа."""
        session_limit = self.settings.rate_limit_session_tokens
        ip_limit = self.settings.rate_limit_ip_tokens
        threshold = self.settings.rate_limit_warning_threshold

        session_ratio = usage.session_used / session_limit
        ip_ratio = usage.ip_used / ip_limit

        show_warning = session_ratio >= threshold or ip_ratio >= threshold

        return RateLimitInfo(
            session=RateLimitBucket(
                used=usage.session_used,
                limit=session_limit,
                remaining=max(0, session_limit - usage.session_used)
            ),
            ip=RateLimitBucket(
                used=usage.ip_used,
                limit=ip_limit,
                remaining=max(0, ip_limit - usage.ip_used)
            ),
            reset_in_seconds=usage.reset_in_seconds,
            show_warning=show_warning,
            exceeded_by=exceeded_by
        )
```

---

## Интеграция в chat.py

```python
@router.post("/api/v1/agent/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    # 1. Проверка Redis
    if not rate_limiter.check_available():
        raise HTTPException(503, detail={
            "code": "SERVICE_UNAVAILABLE",
            "message": "AI-агент временно недоступен. Попробуйте позже"
        })

    # 2. Получить идентификаторы
    client_ip = get_client_ip(req)  # Учитывать X-Forwarded-For
    session_id = request.session_id

    # 3. Проверка лимита ДО обработки
    allowed, info = rate_limiter.check_limit(session_id, client_ip)
    if not allowed:
        raise HTTPException(429, detail={
            "code": "RATE_LIMIT_EXCEEDED",
            "message": f"Достигнут лимит использования AI-агента. "
                       f"Попробуйте снова через {format_duration(info.reset_in_seconds)}",
            "details": {
                "exceeded_by": info.exceeded_by,
                "reset_in_seconds": info.reset_in_seconds,
                "reset_in_human": format_duration(info.reset_in_seconds)
            }
        })

    # 4. Обработка запроса (существующая логика)
    # ... streaming response ...

    # 5. После получения ответа LLM — записать usage
    tokens_used = response.usage.total_tokens  # из GigaChat response
    final_info = rate_limiter.record_usage(session_id, client_ip, tokens_used)

    # 6. Добавить rate_limit в финальный chunk
    yield {
        "type": "done",
        "usage": {"tokens_used": tokens_used},
        "rate_limit": final_info.model_dump()
    }
```

---

## UI/UX Спецификация

> **Референс:** Текущий дизайн чата — тёмная cyberpunk тема с циан акцентами.
> Цвета: фон `#0d1117`, акцент `#22d3ee` (cyan-400), границы с glow-эффектом.

### Текущая структура интерфейса

```
┌─────────────────────────────────────────────────┐
│  AI-АГЕНТ                           ● online   │  ← Header
│  GigaChat + RAG по данным портфолио             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ВЫ                                             │
│  ┌─────────────────────────────────────────┐   │
│  │ Как можно связаться?                    │   │  ← User message
│  └─────────────────────────────────────────┘   │
│                                                 │
│  АГЕНТ                                          │
│  ┌─────────────────────────────────────────┐   │
│  │ • Через Telegram: @kargindmitriy        │   │  ← Agent response
│  │ • По электронной почте: ...             │   │
│  │ • ...                                   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
├─────────────────────────────────────────────────┤
│  [Расскажи об ML-проектах] [Где применял RAG?] │  ← Quick suggestions
│  [Опыт с LLM и агентами]  [Как можно связаться]│
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌───────────┐ │
│  │ Напишите вопрос...          │ │ Отправить │ │  ← Input area
│  └─────────────────────────────┘ └───────────┘ │
└─────────────────────────────────────────────────┘
```

---

### Warning State (show_warning: true)

**Когда:** использовано ≥80% любого лимита

**Где показывать:** между quick suggestions и полем ввода

**Визуал:**
```
├─────────────────────────────────────────────────┤
│  [Расскажи об ML-проектах] [Где применял RAG?] │
│  [Опыт с LLM и агентами]  [Как можно связаться]│
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐   │
│  │ ⚠ Осталось ~18% лимита. Сбросится       │   │  ← WARNING BANNER
│  │   через 34 мин                          │   │
│  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌───────────┐ │
│  │ Напишите вопрос...          │ │ Отправить │ │
│  └─────────────────────────────┘ └───────────┘ │
└─────────────────────────────────────────────────┘
```

**Стилизация (в контексте cyberpunk темы):**
```css
/* Warning banner */
.rate-limit-warning {
  background: rgba(251, 191, 36, 0.1);    /* amber-400/10 */
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 8px 12px;
}

.rate-limit-warning-icon {
  color: #fbbf24;  /* amber-400 */
}

.rate-limit-warning-text {
  color: #fcd34d;  /* amber-300 */
  font-size: 13px;
}
```

**Tailwind классы:**
```
bg-amber-400/10 border border-amber-400/30 rounded-lg px-3 py-2 mx-3 my-2
text-amber-300 text-sm
```

**Анимация появления:**
- `opacity: 0 → 1` за 200ms
- `translateY: -8px → 0` (slide down)

**Расчёт процента:**
```typescript
const sessionPercent = 100 - (info.session.remaining / info.session.limit * 100);
const ipPercent = 100 - (info.ip.remaining / info.ip.limit * 100);
const usedPercent = Math.max(sessionPercent, ipPercent);
const remainingPercent = Math.round(100 - usedPercent);
```

**Форматирование времени:**
```typescript
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} сек`;
  const minutes = Math.ceil(seconds / 60);
  if (minutes === 1) return "1 минуту";
  if (minutes < 5) return `${minutes} минуты`;
  return `${minutes} минут`;
}
```

---

### Blocked State (429 ошибка)

**Когда:** лимит превышен

**Где показывать:** заменяет input area + suggestions становятся disabled

**Визуал:**
```
├─────────────────────────────────────────────────┤
│  [Расскажи об ML...]  [Где применял...]        │  ← DISABLED (opacity: 0.5)
│  [Опыт с LLM...]      [Как можно...]           │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │
│  │      🚫  Лимит использования исчерпан   │   │  ← BLOCKED BANNER
│  │                                         │   │
│  │      Попробуйте снова через 31 мин      │   │
│  │                                         │   │
│  │   ┌─────────────────────────────────┐   │   │
│  │   │█████████████░░░░░░░░░░░░░░░░░░░│   │   │  ← Progress bar
│  │   └─────────────────────────────────┘   │   │
│  │            ~48% до сброса               │   │
│  │                                         │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Стилизация:**
```css
/* Blocked banner */
.rate-limit-blocked {
  background: rgba(239, 68, 68, 0.1);     /* red-500/10 */
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 20px;
  margin: 12px;
  text-align: center;
}

.rate-limit-blocked-icon {
  color: #f87171;  /* red-400 */
  font-size: 24px;
  margin-bottom: 8px;
}

.rate-limit-blocked-title {
  color: #fca5a5;  /* red-300 */
  font-weight: 500;
  font-size: 15px;
}

.rate-limit-blocked-subtitle {
  color: #9ca3af;  /* gray-400 */
  font-size: 13px;
  margin-top: 4px;
}

/* Progress bar */
.rate-limit-progress {
  background: #374151;  /* gray-700 */
  border-radius: 4px;
  height: 6px;
  margin: 16px 0 8px;
  overflow: hidden;
}

.rate-limit-progress-bar {
  background: #22d3ee;  /* cyan-400 — основной акцент темы */
  height: 100%;
  transition: width 1s linear;
}

.rate-limit-progress-text {
  color: #6b7280;  /* gray-500 */
  font-size: 12px;
}
```

**Tailwind классы:**
```
/* Container */
bg-red-500/10 border border-red-500/30 rounded-xl p-5 mx-3 my-3 text-center

/* Icon */
text-red-400 text-2xl mb-2

/* Title */
text-red-300 font-medium text-[15px]

/* Subtitle */
text-gray-400 text-sm mt-1

/* Progress bar container */
bg-gray-700 rounded h-1.5 mt-4 mb-2 overflow-hidden

/* Progress bar fill */
bg-cyan-400 h-full transition-all duration-1000

/* Progress text */
text-gray-500 text-xs
```

**Поведение:**
- Quick suggestion кнопки: `opacity-50 pointer-events-none`
- Input area полностью скрыт или заменён на blocked banner
- Progress bar анимированно уменьшается (или увеличивается к 100%)
- При достижении 100% (время вышло) — автоматически убрать blocked state

---

### Состояние "Redis недоступен" (503)

**Где показывать:** заменяет весь контент чата (или как overlay)

**Визуал:**
```
┌─────────────────────────────────────────────────┐
│  AI-АГЕНТ                           ● offline  │  ← Статус меняется!
│  GigaChat + RAG по данным портфолио             │
├─────────────────────────────────────────────────┤
│                                                 │
│                                                 │
│         ⚡ AI-агент временно недоступен         │
│                                                 │
│         Попробуйте обновить страницу            │
│                                                 │
│              ┌────────────────┐                 │
│              │   Обновить     │                 │
│              └────────────────┘                 │
│                                                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Стилизация:**
```css
/* Offline indicator */
.status-offline {
  color: #6b7280;  /* gray-500 вместо green */
}

/* Service unavailable */
.service-unavailable {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.service-unavailable-icon {
  color: #9ca3af;  /* gray-400 */
  font-size: 32px;
  margin-bottom: 12px;
}

.service-unavailable-title {
  color: #d1d5db;  /* gray-300 */
  font-weight: 500;
  font-size: 16px;
}

.service-unavailable-subtitle {
  color: #6b7280;  /* gray-500 */
  font-size: 14px;
  margin-top: 4px;
}

/* Refresh button — стиль как у quick suggestions */
.refresh-button {
  background: transparent;
  border: 1px solid rgba(34, 211, 238, 0.3);  /* cyan-400/30 */
  color: #22d3ee;  /* cyan-400 */
  padding: 8px 20px;
  border-radius: 8px;
  margin-top: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-button:hover {
  background: rgba(34, 211, 238, 0.1);
  border-color: rgba(34, 211, 238, 0.5);
}
```

**Поведение:**
- Индикатор "online" → "offline" (серый)
- Весь чат (messages + input) заменяется на service unavailable screen
- Кнопка "Обновить" перезагружает страницу или вызывает `GET /rate-limit/status`

---

### Состояния кнопки "Отправить"

Для консистентности, обновить состояния кнопки:

| Состояние | Стиль | Текст |
|-----------|-------|-------|
| **Default (пусто)** | `opacity-50 cursor-not-allowed` | "Отправить" |
| **Активно (есть текст)** | `bg-cyan-500/20 border-cyan-400 text-cyan-400` | "Отправить" |
| **Ожидание ответа** | `bg-red-500/20 border-red-400 text-red-400` | "Стоп" |
| **Rate limited** | Скрыта (вместо неё blocked banner) | — |

---

### Иконки

Рекомендуемые иконки (Lucide или Heroicons):

| Состояние | Иконка | Альтернатива |
|-----------|--------|--------------|
| Warning | `AlertTriangle` | ⚠️ |
| Blocked | `Ban` или `XCircle` | 🚫 |
| Service unavailable | `Zap` или `WifiOff` | ⚡ |
| Refresh | `RefreshCw` | 🔄 |

---

## Frontend изменения

### Новые типы (lib/types.ts)

```typescript
interface RateLimitBucket {
  used: number;
  limit: number;
  remaining: number;
}

interface RateLimitInfo {
  session: RateLimitBucket;
  ip: RateLimitBucket;
  reset_in_seconds: number;
  show_warning: boolean;
}

interface RateLimitError {
  code: "RATE_LIMIT_EXCEEDED" | "SERVICE_UNAVAILABLE";
  message: string;
  details?: {
    exceeded_by: "session" | "ip";
    reset_in_seconds: number;
    reset_in_human: string;
  };
}

// Обновить AgentMessage
interface AgentStreamDone {
  type: "done";
  usage?: { tokens_used: number };
  rate_limit?: RateLimitInfo;
}
```

### Изменения в AgentDock.tsx

```typescript
// Новые состояния
const [rateLimitWarning, setRateLimitWarning] = useState<{
  remainingPercent: number;
  resetIn: string;
} | null>(null);

const [rateLimitBlocked, setRateLimitBlocked] = useState<{
  message: string;
  resetInSeconds: number;
} | null>(null);

// В обработчике стриминга
if (chunk.type === "done" && chunk.rate_limit) {
  if (chunk.rate_limit.show_warning) {
    const remaining = Math.min(
      chunk.rate_limit.session.remaining / chunk.rate_limit.session.limit,
      chunk.rate_limit.ip.remaining / chunk.rate_limit.ip.limit
    );
    setRateLimitWarning({
      remainingPercent: Math.round(remaining * 100),
      resetIn: formatDuration(chunk.rate_limit.reset_in_seconds)
    });
  } else {
    setRateLimitWarning(null);
  }
}

// Обработка 429 ошибки
if (response.status === 429) {
  const error = await response.json();
  setRateLimitBlocked({
    message: error.error.message,
    resetInSeconds: error.error.details.reset_in_seconds
  });
}
```

### Новый компонент RateLimitWarning.tsx

```typescript
interface Props {
  remainingPercent: number;
  resetIn: string;
}

export function RateLimitWarning({ remainingPercent, resetIn }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10
                 border border-yellow-500/20 rounded-lg text-sm"
    >
      <WarningIcon className="w-4 h-4 text-yellow-400" />
      <span className="text-yellow-400">
        Осталось ~{remainingPercent}% лимита. Сбросится через {resetIn}
      </span>
    </motion.div>
  );
}
```

### Новый компонент RateLimitBlocked.tsx

```typescript
interface Props {
  message: string;
  resetInSeconds: number;
}

export function RateLimitBlocked({ message, resetInSeconds }: Props) {
  const [secondsLeft, setSecondsLeft] = useState(resetInSeconds);

  // Countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsLeft(s => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const progress = 1 - (secondsLeft / resetInSeconds);

  return (
    <div className="flex flex-col items-center justify-center p-6
                    bg-red-500/10 border border-red-500/20 rounded-lg">
      <BlockedIcon className="w-8 h-8 text-red-400 mb-3" />
      <h3 className="text-red-400 font-medium mb-1">
        Достигнут лимит использования AI-агента
      </h3>
      <p className="text-gray-400 text-sm mb-4">
        Попробуйте снова через {formatDuration(secondsLeft)}
      </p>

      {/* Progress bar */}
      <div className="w-full max-w-xs h-2 bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-cyan-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}
```

---

## Тестирование

### Unit тесты

```python
# tests/test_rate_limit.py

def test_check_limit_session_exceeded():
    """Блокировка при превышении лимита сессии."""

def test_check_limit_ip_exceeded():
    """Блокировка при превышении лимита IP."""

def test_record_usage_increments_both():
    """Запись увеличивает оба счётчика."""

def test_ttl_set_on_first_increment():
    """TTL устанавливается при первом инкременте."""

def test_warning_threshold():
    """show_warning=true при ≥80% использования."""

def test_redis_unavailable_returns_false():
    """check_available() возвращает False при недоступном Redis."""
```

### Integration тесты

```python
def test_chat_blocked_on_limit():
    """Запрос к /chat/stream возвращает 429 при превышении."""

def test_chat_returns_rate_limit_info():
    """Успешный ответ содержит rate_limit в финальном chunk."""

def test_chat_503_when_redis_down():
    """Запрос возвращает 503 когда Redis недоступен."""
```

---

## План реализации

### Этап 1: Backend (rag-api-new)

1. Создать `app/rate_limit/` модуль
2. Добавить настройки в `settings.py`
3. Интегрировать в `routers/chat.py`
4. Написать unit тесты

### Этап 2: Frontend (frontend-new)

1. Добавить типы в `lib/types.ts`
2. Создать компоненты `RateLimitWarning.tsx` и `RateLimitBlocked.tsx`
3. Интегрировать в `AgentDock.tsx`
4. Обработка 429 и 503 ошибок

### Этап 3: Мониторинг

1. Логирование превышений (structured logging)
2. Метрики для Prometheus (опционально):
   - `rate_limit_exceeded_total{type="session|ip"}`
   - `rate_limit_tokens_used_total`

---

## Дополнительные требования

### GET эндпоинт для проверки статуса

**Endpoint:** `GET /api/v1/rate-limit/status`

**Query параметры:**
- `session_id` (required) — ID сессии из localStorage

**Ответ:**
```json
{
  "available": true,
  "rate_limit": {
    "session": { "used": 5000, "limit": 20000, "remaining": 15000 },
    "ip": { "used": 12000, "limit": 50000, "remaining": 38000 },
    "reset_in_seconds": 2450,
    "show_warning": false
  }
}
```

**Если заблокирован:**
```json
{
  "available": false,
  "rate_limit": {
    "session": { "used": 20000, "limit": 20000, "remaining": 0 },
    "ip": { "used": 25000, "limit": 50000, "remaining": 25000 },
    "reset_in_seconds": 1200,
    "show_warning": true,
    "exceeded_by": "session"
  }
}
```

**Использование на фронте:**
- Вызывать при монтировании AgentDock
- Если `available: false` → сразу показать RateLimitBlocked
- Если `show_warning: true` → показать RateLimitWarning

---

### Отключение для тестирования

Для dev/test окружения используйте существующую настройку:

```python
rate_limit_enabled: bool = False  # Полностью отключает rate limiting
```

```bash
RATE_LIMIT_ENABLED=false
```

> **Примечание:** Whitelist IP не реализуется — для тестов достаточно полного отключения.

---

### Логирование

**Что логировать:**

| Событие | Уровень | Данные |
|---------|---------|--------|
| Лимит превышен | WARNING | `ip`, `session_id`, `exceeded_by`, `used`, `limit` |
| Redis недоступен | ERROR | — |
| Использование записано | DEBUG | `session_id`, `tokens`, `new_total` |

**Формат (structured logging):**
```json
{
  "event": "rate_limit_exceeded",
  "ip": "85.140.10.*",
  "session_id": "abc123def456",
  "exceeded_by": "session",
  "used": 20150,
  "limit": 20000,
  "timestamp": "2025-01-23T14:30:00Z"
}
```

**Маскирование IP:**
- По умолчанию: маскированный формат `85.140.10.*` (последний октет заменяется на `*`)
- Настраивается через `rate_limit_log_ip_mode`:
  - `masked` (default) — `85.140.10.*`
  - `full` — `85.140.10.5` (для dev/debug)

**Настройка (settings.py):**
```python
rate_limit_log_ip_mode: Literal["masked", "full"] = "masked"
```

**Функция маскирования:**
```python
def mask_ip(ip: str) -> str:
    """Маскирует последний октет IPv4 или последние 64 бита IPv6."""
    if "." in ip:  # IPv4
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.*"
    elif ":" in ip:  # IPv6
        return ip.rsplit(":", 4)[0] + ":*:*:*:*"
    return ip
```

---

## Ссылки

- [Redis INCRBY](https://redis.io/commands/incrby/)
- [FastAPI HTTPException](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- Связанный файл: `docs/TZ_RAG_OPTIMIZATION.md` (оптимизация латентности)
