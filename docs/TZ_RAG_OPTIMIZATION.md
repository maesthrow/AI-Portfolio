# ТЗ: Оптимизация латентности rag-api-new

**Версия**: 1.1
**Дата**: 2025-01-21

---

## Цель

Снизить среднюю латентность ответа с **~2000-2500ms** до **~800-1200ms** для типичных запросов.

---

## Текущий breakdown латентности

```
[~50ms]  ScopeGuard (regex)           — быстро, не трогаем
[~500ms] Planner LLM                  — ГЛАВНЫЙ КАНДИДАТ (Plan Shortcuts)
[~100ms] Executor (GraphStore)        — быстро
[~300ms] Critic LLM                   — МОЖНО УБРАТЬ/LAZY
[~200ms] Embeddings (TEI)             — кэшируемо
[~50ms]  Normalizer                   — быстро
[~100ms] GroundingVerifier            — быстро
[~800ms] Answer LLM                   — streaming помогает с perceived latency
─────────────────────────────────────────────────────────────
Итого: ~2100ms (3 LLM вызова)
Цель:  ~800-1200ms (1-2 LLM вызова)
```

---

## Фаза 1: Quick Wins (без Redis)

### 1.1 Plan Shortcuts (Минимальные, безопасные)

**Цель**: Для 2-3 абсолютно однозначных случаев пропустить PlannerLLM (~500ms экономии).

**Принцип**:
- Shortcuts только для случаев где **невозможна двусмысленность**
- Остальные запросы → LLM с последующим кэшированием в Redis
- Основная экономия достигается через **Redis cache + Prefetch**, а не shortcuts

**Почему минимальные shortcuts**:

| Вопрос | Проблема | Решение |
|--------|----------|---------|
| "Кто ты?" | Агент о себе, не о разработчике | ❌ Не shortcut |
| "Что умеешь?" | Функции агента vs навыки разработчика | ❌ Не shortcut |
| "Контакты" | Всегда про разработчика | ✅ Безопасный shortcut |
| "Где работает сейчас" | Всегда про разработчика | ✅ Безопасный shortcut |

**Новый файл**: `app/agent/planner/shortcuts.py`

> **ВАЖНО**: LangGraph Agent модифицирует вопросы перед вызовом RAG tool,
> добавляя имя владельца (например, "контакты" → "контакты Дмитрия").
> Поэтому shortcuts использует `CacheService._normalize_question()` для
> унификации с кэшированием.

```python
"""
Plan Shortcuts - минимальный набор быстрых планов.

ВАЖНО: Только для абсолютно однозначных случаев!
Вопросы типа "кто ты", "что умеешь" НЕ должны быть здесь,
т.к. агент отвечает о себе, а не о разработчике.

NOTE: Нормализация вопросов выполняется через CacheService._normalize_question(),
что убирает суффикс имени ("Дмитрия") добавляемый агентом.
"""
from __future__ import annotations

import logging
import re

from .schemas_v3 import (
    QueryPlanV3,
    IntentV3,
    ToolCallV3,
    RenderStyleV3,
    AnswerStyleV3,
    LimitsConfigV3,
)

logger = logging.getLogger(__name__)


# === ТОЛЬКО абсолютно однозначные случаи ===
# Паттерны используют fullmatch (точное совпадение) для безопасности
# NOTE: Имя владельца убирается через CacheService._normalize_question()

SAFE_SHORTCUTS: dict[str, QueryPlanV3] = {
    # Контакты разработчика (не агента!) — однозначно
    r"контакты?|связаться|как связаться|email|телефон|telegram": QueryPlanV3(
        intents=[IntentV3.CONTACTS],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "contacts"})],
        render_style=RenderStyleV3.BULLETS,
        answer_style=AnswerStyleV3.NATURAL_RU,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),

    # Текущая работа разработчика — однозначно
    r"где (сейчас )?работает|текущая работа|текущее место работы|current job": QueryPlanV3(
        intents=[IntentV3.CURRENT_JOB],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "current_job"})],
        render_style=RenderStyleV3.SHORT,
        answer_style=AnswerStyleV3.CONCISE,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
}


def try_shortcut(question: str) -> QueryPlanV3 | None:
    """
    Попытка найти готовый план для однозначного вопроса.

    NOTE: Использует ту же нормализацию, что и CacheService для унификации
    cache keys и shortcuts matching.
    """
    # Используем единую нормализацию из CacheService
    from ...cache.cache_service import CacheService
    normalized = CacheService._normalize_question(question)

    for pattern, plan in SAFE_SHORTCUTS.items():
        if re.fullmatch(pattern, normalized, re.IGNORECASE):
            logger.info(
                "Shortcut matched: pattern=%r, question=%r, normalized=%r",
                pattern[:30],
                question[:50],
                normalized[:50],
            )
            return plan.model_copy(deep=True)

    # Не нашли shortcut → LLM (результат будет закэширован)
    return None
```

**Интеграция в `rag_tool.py`** (в начале функции `portfolio_rag_tool`):

```python
from .planner.shortcuts import try_shortcut

# 1. Пробуем shortcut (только для однозначных случаев)
plan = try_shortcut(question)
plan_source = "shortcut" if plan else None

if not plan:
    # 2. Redis cache или LLM (см. Фазу 2.5)
    # После реализации cache: plan, plan_source = get_plan_with_cache(question, planner_llm)
    planner = PlannerLLM(planner_llm())
    plan = planner.plan(question)
    plan_source = "llm"

logger.info("Plan source: %s, intents=%s", plan_source, [i.value for i in plan.intents])
```

**Примеры работы**:

| Вопрос | Результат | Почему |
|--------|-----------|--------|
| "контакты" | Shortcut ✅ | Однозначно про разработчика |
| "как связаться" | Shortcut ✅ | Однозначно про разработчика |
| "где работает сейчас" | Shortcut ✅ | Однозначно про разработчика |
| "кто ты" | LLM → Cache | Агент о себе, не shortcut |
| "что умеешь" | LLM → Cache | Функции агента, не shortcut |
| "проекты" | LLM → Cache | Закэшируется после первого вызова |
| "технологии" | LLM → Cache | Закэшируется после первого вызова |

**Ожидаемый hit rate**: ~5-10% (только очевидные случаи)

---

### 1.2 Lazy Critic (конфигурируемый)

**Цель**: Пропускать Critic когда он не нужен (~300ms экономии).

**Принцип**: Critic полезен только когда есть сомнения в качестве retrieval. Если план уверенный и фактов достаточно — Critic избыточен.

**Изменения в `app/settings.py`**:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # === Critic settings ===
    critic_enabled: bool = True
    """Глобальное включение/выключение Critic LLM"""

    critic_confidence_threshold: float = 0.7
    """Порог confidence плана для пропуска Critic (>= threshold = skip)"""

    critic_min_facts_threshold: int = 2
    """Минимальное кол-во фактов для пропуска Critic (>= threshold = skip)"""

    critic_skip_intents: list[str] = ["contacts", "current_job"]
    """Список интентов где Critic всегда пропускается (простые запросы)"""
```

**Изменения в `rag_tool.py`** (строки ~88-100):

```python
from ..settings import get_settings

settings = get_settings()

# Определяем нужен ли Critic
primary_intent = plan.intents[0].value if plan.intents else None

skip_critic = (
    not settings.critic_enabled
    or float(plan.confidence or 0.0) >= settings.critic_confidence_threshold
    or len(payload.items) >= settings.critic_min_facts_threshold
    or primary_intent in settings.critic_skip_intents
)

if skip_critic:
    logger.info(
        "Critic skipped: enabled=%s, confidence=%.2f (threshold=%.2f), "
        "facts=%d (threshold=%d), intent=%s (skip_list=%s)",
        settings.critic_enabled,
        float(plan.confidence or 0.0),
        settings.critic_confidence_threshold,
        len(payload.items),
        settings.critic_min_facts_threshold,
        primary_intent,
        settings.critic_skip_intents,
    )
    decision = CriticDecision(sufficient=True, need_search=False, query=None, reason="skipped")
else:
    critic = CriticLLM(planner_llm())
    decision = critic.evaluate(question, plan, payload)
```

**Docker-compose environment**:

```yaml
rag-api:
  environment:
    # ... existing ...
    CRITIC_ENABLED: "true"
    CRITIC_CONFIDENCE_THRESHOLD: "0.7"
    CRITIC_MIN_FACTS_THRESHOLD: "2"
    CRITIC_SKIP_INTENTS: '["contacts", "current_job"]'
```

**Логика пропуска Critic**:

| Условие | Пример | Critic |
|---------|--------|--------|
| `confidence >= 0.7` | Plan confidence = 0.85 | Skip ✅ |
| `facts >= 2` | Найдено 3 факта | Skip ✅ |
| `intent in skip_list` | Intent = "contacts" | Skip ✅ |
| `confidence < 0.7 AND facts < 2` | Неуверенный план | Run ⚠️ |

---

### 1.3 GraphStore Precompute

**Цель**: Ускорить частые запросы к графу (~50-100ms).

**Изменения в `app/graph/store.py`**:

```python
class GraphStore:
    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[GraphEdge]] = {}

        # Precomputed caches (заполняются в precompute())
        self._cache: dict[str, Any] = {}

    def precompute(self) -> None:
        """
        Вычисляет и кэширует популярные запросы.
        Вызывается после build_graph_from_export().
        """
        self._cache["all_projects"] = [
            n for n in self._nodes.values()
            if n.type == NodeType.PROJECT
        ]
        self._cache["all_companies"] = [
            n for n in self._nodes.values()
            if n.type == NodeType.COMPANY
        ]
        self._cache["all_technologies"] = [
            n for n in self._nodes.values()
            if n.type == NodeType.TECHNOLOGY
        ]
        self._cache["technologies_by_category"] = self._group_techs_by_category()
        self._cache["current_job"] = self._find_current_job()

        logger.info(
            "GraphStore precomputed: projects=%d, companies=%d, technologies=%d",
            len(self._cache.get("all_projects", [])),
            len(self._cache.get("all_companies", [])),
            len(self._cache.get("all_technologies", [])),
        )

    def get_all_projects(self) -> list[GraphNode]:
        """O(1) доступ к списку проектов."""
        return self._cache.get("all_projects", [])

    def get_all_companies(self) -> list[GraphNode]:
        """O(1) доступ к списку компаний."""
        return self._cache.get("all_companies", [])

    def get_all_technologies(self) -> list[GraphNode]:
        """O(1) доступ к списку технологий."""
        return self._cache.get("all_technologies", [])

    def get_current_job(self) -> GraphNode | None:
        """O(1) доступ к текущей работе."""
        return self._cache.get("current_job")

    def _group_techs_by_category(self) -> dict[str, list[GraphNode]]:
        """Группировка технологий по категориям."""
        result: dict[str, list[GraphNode]] = {}
        for node in self._nodes.values():
            if node.type == NodeType.TECHNOLOGY:
                category = node.data.get("category", "other")
                result.setdefault(category, []).append(node)
        return result

    def _find_current_job(self) -> GraphNode | None:
        """Поиск текущей работы (is_current=True)."""
        for node in self._nodes.values():
            if node.type == NodeType.COMPANY and node.data.get("is_current"):
                return node
        return None
```

**Вызов precompute в `app/graph/builder.py`**:

```python
def build_graph_from_export(payload: ExportPayload) -> GraphStore:
    store = get_graph_store()
    store.clear()

    # ... build nodes and edges ...

    # Precompute популярных запросов
    store.precompute()

    return store
```

---

## Фаза 2: Redis Cache Layer

### 2.1 Redis в инфраструктуре

**Файл**: `infra/docker-compose.local.yaml`

```yaml
services:
  # ... existing services ...

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 30

  rag-api:
    # ... existing config ...
    depends_on:
      - chroma
      - litellm
      - redis  # Добавить
    environment:
      # ... existing ...
      REDIS_URL: redis://redis:6379/0

volumes:
  # ... existing ...
  redis_data:
```

**Файл**: `infra/docker-compose-prod.yaml` — аналогично, но без `ports` (только `expose`).

---

### 2.2 Settings для кэширования

**Изменения в `app/settings.py`**:

```python
class Settings(BaseSettings):
    # ... existing ...

    # === Redis settings ===
    redis_url: str = "redis://localhost:6379/0"
    """Redis connection URL"""

    cache_enabled: bool = True
    """Глобальное включение/выключение кэширования"""

    plan_cache_ttl: int = 3600
    """TTL для кэша планов в секундах (1 час)"""

    embedding_cache_ttl: int = 86400
    """TTL для кэша embeddings в секундах (24 часа)"""
```

---

### 2.3 Cache Service

**Новый файл**: `app/cache/__init__.py`

```python
from .cache_service import CacheService, get_cache_service

__all__ = ["CacheService", "get_cache_service"]
```

**Новый файл**: `app/cache/cache_service.py`

```python
"""
CacheService - сервис кэширования с graceful degradation.

Если Redis недоступен — система работает без кэша (fallback на LLM).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from functools import lru_cache

from ..settings import get_settings

logger = logging.getLogger(__name__)

# Ленивый импорт Redis (может быть недоступен)
_redis_client = None


def _get_redis():
    """Ленивая инициализация Redis клиента."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if not settings.cache_enabled:
            return None
        try:
            import redis
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Проверка соединения
            _redis_client.ping()
            logger.info("Redis connected: %s", settings.redis_url)
        except Exception as e:
            logger.warning("Redis unavailable, caching disabled: %s", e)
            _redis_client = False  # Marker: tried but failed
    return _redis_client if _redis_client else None


class CacheService:
    """
    Сервис кэширования с graceful degradation.
    Если Redis недоступен — методы возвращают None / ничего не делают.
    """

    CONTENT_HASH_KEY = "rag:content:hash"
    PLAN_PREFIX = "rag:plan:"
    EMB_PREFIX = "rag:emb:"  # Используется в embedding_cache.py (P3)

    def __init__(self):
        self.settings = get_settings()

    @property
    def redis(self):
        return _get_redis()

    @property
    def available(self) -> bool:
        return self.redis is not None and self.settings.cache_enabled

    def _safe_get(self, key: str) -> str | None:
        """Get с обработкой ошибок."""
        if not self.available:
            return None
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.warning("Redis get failed for %s: %s", key, e)
            return None

    def _safe_set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set с обработкой ошибок."""
        if not self.available:
            return False
        try:
            if ttl:
                self.redis.setex(key, ttl, value)
            else:
                self.redis.set(key, value)
            return True
        except Exception as e:
            logger.warning("Redis set failed for %s: %s", key, e)
            return False

    # === Content Hash (для умной инвалидации) ===

    def get_content_hash(self) -> str | None:
        """Получить hash последнего ingest payload."""
        return self._safe_get(self.CONTENT_HASH_KEY)

    def set_content_hash(self, hash_value: str) -> bool:
        """Сохранить hash ingest payload."""
        return self._safe_set(self.CONTENT_HASH_KEY, hash_value)

    # === Cache Invalidation ===

    def invalidate_all(self) -> int:
        """
        Удаляет все кэши (plan + embedding).
        Возвращает количество удалённых ключей.
        """
        if not self.available:
            return 0
        try:
            deleted = 0
            for prefix in [self.PLAN_PREFIX, self.EMB_PREFIX]:
                for key in self.redis.scan_iter(f"{prefix}*"):
                    self.redis.delete(key)
                    deleted += 1
            logger.info("Cache invalidated: %d keys deleted", deleted)
            return deleted
        except Exception as e:
            logger.warning("Cache invalidation failed: %s", e)
            return 0

    # === Нормализация вопросов ===

    @staticmethod
    def _normalize_question(question: str) -> str:
        """
        Нормализация вопроса для cache key и shortcuts matching.

        Приводит разные формулировки к единому виду:
        - "ML-проекты?" → "ml проекты"
        - "расскажи о проектах Дмитрия" → "расскажи о проектах"

        NOTE: LangGraph Agent добавляет имя владельца к вопросам,
        убираем для унификации cache keys и shortcuts.
        """
        s = question.lower().strip()
        s = re.sub(r"[?!.,;:«»\"']+", "", s)  # Убрать пунктуацию
        s = re.sub(r"[-–—]+", " ", s)          # Дефисы → пробелы
        # Убираем имя владельца (агент добавляет контекст)
        s = re.sub(r"\s+(дмитрия?|dmitriy?)\s*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()     # Схлопнуть пробелы
        return s

    # === Plan Cache ===

    def _plan_key(self, question: str) -> str:
        """Генерация ключа для кэша плана."""
        normalized = self._normalize_question(question)
        hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.PLAN_PREFIX}{hash_val}"

    def get_cached_plan(self, question: str) -> dict | None:
        """Получить закэшированный план."""
        data = self._safe_get(self._plan_key(question))
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_cached_plan(self, question: str, plan_dict: dict) -> bool:
        """Сохранить план в кэш."""
        return self._safe_set(
            self._plan_key(question),
            json.dumps(plan_dict, ensure_ascii=False),
            ttl=self.settings.plan_cache_ttl,
        )

    # NOTE: Embedding Cache реализован в отдельном модуле embedding_cache.py (P3)
    # Он использует _safe_get/_safe_set напрямую с собственной логикой ключей
    # (включает model_name и нормализацию текста)


@lru_cache
def get_cache_service() -> CacheService:
    """Singleton для CacheService."""
    return CacheService()
```

---

### 2.4 Умная инвалидация по content hash

**Принцип**: При ingest вычисляем hash payload. Если hash изменился — данные изменились, инвалидируем кэш. Если hash тот же — просто warm-up (рестарт контейнера), кэш сохраняем.

**Изменения в `app/routers/ingest_batch.py`**:

```python
import hashlib
import logging
from fastapi import APIRouter

from ..schemas.export import ExportPayload
from ..schemas.ingest import IngestBatchResult
from ..cache import get_cache_service
from ..graph.builder import build_graph_from_export
from ..indexing.normalizer import normalize_export
from ..settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/v1/ingest/batch", response_model=IngestBatchResult)
async def ingest_batch(payload: ExportPayload):
    settings = get_settings()
    cache = get_cache_service()

    # 1. Вычисляем hash payload
    payload_json = payload.model_dump_json(exclude_none=True)
    new_hash = hashlib.sha256(payload_json.encode()).hexdigest()[:16]

    # 2. Сравниваем с предыдущим hash
    old_hash = cache.get_content_hash()
    data_changed = (old_hash is None) or (old_hash != new_hash)

    if data_changed:
        logger.info(
            "Content changed: hash %s -> %s, invalidating caches",
            old_hash or "None",
            new_hash,
        )
        cache.invalidate_all()
    else:
        logger.info(
            "Content unchanged (hash=%s), keeping caches (warm-up only)",
            new_hash,
        )

    # 3. Rebuild GraphStore + BM25 (всегда при ingest)
    build_graph_from_export(payload)
    docs = list(normalize_export(payload))
    # ... existing indexing logic ...

    # 4. Сохраняем новый hash
    cache.set_content_hash(new_hash)

    # 5. Prefetch popular questions (background)
    # asyncio.create_task(_prefetch_popular())  # Фаза 3

    return IngestBatchResult(
        added=len(docs),
        collection=settings.chroma_collection,
        cache_invalidated=data_changed,
        content_hash=new_hash,
    )
```

**Обновить схему ответа** в `app/schemas/ingest.py`:

```python
class IngestBatchResult(BaseModel):
    added: int
    collection: str
    cache_invalidated: bool = False
    content_hash: str | None = None
```

---

### 2.5 Plan Cache с Hybrid подходом

**Новый файл**: `app/cache/plan_cache.py`

```python
"""
Hybrid Plan Cache: shortcut → Redis cache → LLM fallback.
"""
from __future__ import annotations

import logging

from ..agent.planner.schemas_v3 import QueryPlanV3
from ..agent.planner.shortcuts import try_shortcut
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)


def get_plan_with_cache(question: str, planner_llm_fn) -> tuple[QueryPlanV3, str]:
    """
    Получить план с использованием кэширования.

    Порядок:
    1. Rule-based shortcuts (мгновенно, ~0ms)
    2. Redis cache (быстро, ~5ms)
    3. LLM fallback (медленно, ~500ms)

    Args:
        question: Вопрос пользователя
        planner_llm_fn: Функция для получения LLM (lazy)

    Returns:
        tuple[QueryPlanV3, source] где source = "shortcut" | "cache" | "llm"
    """
    # 1. Try shortcut (rule-based, instant)
    plan = try_shortcut(question)
    if plan:
        logger.info("Plan from shortcut: %s", [i.value for i in plan.intents])
        return plan, "shortcut"

    # 2. Try Redis cache
    cache = get_cache_service()
    cached_dict = cache.get_cached_plan(question)
    if cached_dict:
        try:
            plan = QueryPlanV3.model_validate(cached_dict)
            logger.info("Plan from cache: %s", [i.value for i in plan.intents])
            return plan, "cache"
        except Exception as e:
            logger.warning("Failed to parse cached plan: %s", e)

    # 3. LLM fallback
    from ..agent.planner import PlannerLLM

    planner = PlannerLLM(planner_llm_fn())
    plan = planner.plan(question)

    # Сохраняем в кэш для следующего раза
    try:
        cache.set_cached_plan(question, plan.model_dump(mode="json"))
    except Exception as e:
        logger.warning("Failed to cache plan: %s", e)

    logger.info("Plan from LLM: %s", [i.value for i in plan.intents])
    return plan, "llm"
```

**Интеграция в `rag_tool.py`**:

```python
from ..cache.plan_cache import get_plan_with_cache

# Заменить:
# planner = PlannerLLM(planner_llm())
# plan = planner.plan(question)

# На:
plan, plan_source = get_plan_with_cache(question, planner_llm)
logger.info("Plan source: %s", plan_source)
```

---

## Фаза 3: Prefetch

### 3.1 Prefetch модуль

**Новый файл**: `app/prefetch.py`

```python
"""
Prefetch - прогрев кэша для популярных вопросов.
"""
from __future__ import annotations

import logging

from .settings import get_settings
from .cache import get_cache_service

logger = logging.getLogger(__name__)

# Популярные вопросы для прогрева кэша
POPULAR_QUESTIONS = [
    "расскажи о проектах",
    "расскажи об ML-проектах",
    "расскажи об AI-проектах",
    "какие проекты есть",
    "технологии",
    "какие технологии знает",
    "какими технологиями владеет",
    "стек технологий",
    "какой опыт с базами данных",
    "где применял RAG",
    "контакты",
    "как связаться",
    "опыт работы",
    "где работал",
    "текущая работа",
    "где сейчас работает",
    "достижения",
    "навыки",
    "кто такой Дмитрий",
    "расскажи о Дмитрии",
    "расскажи о нем",
]


def prefetch_popular_plans() -> int:
    """
    Прогревает кэш планов для популярных вопросов.

    Returns:
        Количество планов, загруженных через LLM (cache miss)
    """
    settings = get_settings()
    if not settings.cache_enabled:
        logger.info("Cache disabled, skipping prefetch")
        return 0

    cache = get_cache_service()
    if not cache.available:
        logger.info("Redis unavailable, skipping prefetch")
        return 0

    from .cache.plan_cache import get_plan_with_cache
    from .deps import planner_llm

    llm_calls = 0
    for question in POPULAR_QUESTIONS:
        try:
            _, source = get_plan_with_cache(question, planner_llm)
            if source == "llm":
                llm_calls += 1
        except Exception as e:
            logger.warning("Prefetch failed for %r: %s", question, e)

    logger.info(
        "Prefetch complete: %d/%d questions, %d LLM calls",
        len(POPULAR_QUESTIONS),
        len(POPULAR_QUESTIONS),
        llm_calls,
    )
    return llm_calls
```

### 3.2 Вызов prefetch после ingest

В `app/routers/ingest_batch.py` добавить в конце (после сохранения hash):

```python
import threading

from ..prefetch import prefetch_popular_plans

# ... в конце ingest_batch() ...

# 5. Prefetch в фоне (не блокирует response)
def _background_prefetch():
    try:
        prefetch_popular_plans()
    except Exception as e:
        logger.warning("Background prefetch failed: %s", e)

threading.Thread(target=_background_prefetch, daemon=True).start()
```

---

## Структура новых файлов

```
services/rag-api-new/app/
├── cache/                              # НОВАЯ ДИРЕКТОРИЯ
│   ├── __init__.py                    # Экспорт CacheService
│   ├── cache_service.py               # Redis client + graceful degradation
│   └── plan_cache.py                  # Hybrid plan caching
├── agent/
│   └── planner/
│       ├── shortcuts.py               # НОВЫЙ: rule-based router
│       └── ... (existing)
├── prefetch.py                        # НОВЫЙ: прогрев кэша
├── settings.py                        # ИЗМЕНИТЬ: Redis + Critic settings
└── routers/
    └── ingest_batch.py                # ИЗМЕНИТЬ: hash-based invalidation
```

---

## Environment Variables (полный список)

```bash
# === Redis ===
REDIS_URL=redis://redis:6379/0
CACHE_ENABLED=true
PLAN_CACHE_TTL=3600              # 1 час
EMBEDDING_CACHE_TTL=86400        # 24 часа

# === Critic ===
CRITIC_ENABLED=true
CRITIC_CONFIDENCE_THRESHOLD=0.7
CRITIC_MIN_FACTS_THRESHOLD=2
CRITIC_SKIP_INTENTS='["contacts", "current_job"]'
```

---

## Метрики успеха

| Метрика | До | После P0-P2 | После P3 |
|---------|-----|-------------|----------|
| Латентность (первый запрос) | ~2000ms | ~1500ms | ~1300ms |
| Латентность (повторный, cache hit) | ~2000ms | ~800ms | ~600ms |
| Латентность (shortcut) | ~2000ms | ~500ms | ~300ms |
| Plan shortcut hit rate | 0% | ~5-10% | ~5-10% |
| Plan cache hit rate | 0% | ~60-70% | ~60-70% |
| **Embedding cache hit rate** | 0% | 0% | **~80-90%** |
| Critic skip rate | ~0% | ~70% | ~70% |
| LLM вызовов (первый запрос) | 3 | 2 | 2 |
| LLM вызовов (cache hit) | 3 | 1 | 1 |
| **TEI вызовов (cache hit)** | 1 | 1 | **0** |

---

## Порядок реализации

| # | Задача | Файлы | Приоритет |
|---|--------|-------|-----------|
| 1 | Plan Shortcuts + EntityRegistry проверка | `planner/shortcuts.py`, `rag_tool.py` | P0 |
| 2 | Lazy Critic (настраиваемый) | `settings.py`, `rag_tool.py` | P0 |
| 3 | GraphStore Precompute | `graph/store.py`, `graph/builder.py` | P1 |
| 4 | Redis в docker-compose | `docker-compose.*.yaml` | P1 |
| 5 | CacheService | `cache/cache_service.py` | P1 |
| 6 | Умная инвалидация по hash | `routers/ingest_batch.py`, `schemas/ingest.py` | P1 |
| 7 | Plan Cache (hybrid) | `cache/plan_cache.py`, `rag_tool.py` | P2 |
| 8 | Prefetch | `prefetch.py`, `routers/ingest_batch.py` | P2 |
| 9 | Embedding Cache | `cache/embedding_cache.py`, `rag/retrieval.py` | P3 |

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Redis недоступен | Graceful degradation в CacheService — работает без кэша |
| EntityRegistry пуст (до ingest) | Shortcut вернёт None → fallback на LLM |
| Shortcut не покрывает вопрос | Fallback на LLM planner |
| Cache stale после изменения данных | Hash-based инвалидация автоматически |
| Prefetch замедляет ingest | Запуск в background thread |

---

# P3: Embedding Cache

## Обзор

Кэширование embeddings запросов в Redis для ускорения повторных поисков.

**Что кэшируется**: Vector embedding вопроса пользователя (768-dim для multilingual-e5-base).

**Экономия**: ~50-200ms на запрос (время вызова TEI).

## Архитектура

```
Вопрос → Normalize → Hash → Redis GET
                              ↓
                    Hit: вернуть embedding
                    Miss: TEI → Redis SET → вернуть embedding
```

## Реализация

### 3.1 Новый файл: `app/cache/embedding_cache.py`

```python
"""
Embedding Cache - кэширование embeddings запросов в Redis.

Ключи: rag:emb:{model}:{hash16}
Значение: JSON-сериализованный list[float] (768 элементов)
TTL: 24 часа (embedding_cache_ttl)
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Callable

from .cache_service import get_cache_service, CacheService

logger = logging.getLogger(__name__)


def get_embedding_with_cache(
    text: str,
    embed_fn: Callable[[str], list[float]],
    model_name: str = "default",
) -> tuple[list[float], str]:
    """
    Получить embedding с использованием кэша.

    Args:
        text: Текст для embedding
        embed_fn: Функция получения embedding (TEI вызов)
        model_name: Название модели (для разделения кэшей)

    Returns:
        tuple[embedding, source] где source = "cache" | "tei"
    """
    cache = get_cache_service()

    # Нормализуем текст для cache key
    normalized = CacheService._normalize_question(text)
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    cache_key = f"rag:emb:{model_name}:{hash_val}"

    # 1. Try cache
    if cache.available:
        cached = cache._safe_get(cache_key)
        if cached:
            try:
                embedding = json.loads(cached)
                logger.debug("Embedding from cache: text=%r", text[:50])
                return embedding, "cache"
            except json.JSONDecodeError:
                pass

    # 2. TEI fallback
    embedding = embed_fn(text)

    # 3. Cache result
    if cache.available:
        try:
            cache._safe_set(
                cache_key,
                json.dumps(embedding),
                ttl=cache.settings.embedding_cache_ttl,
            )
            logger.debug("Embedding cached: text=%r", text[:50])
        except Exception as e:
            logger.warning("Failed to cache embedding: %s", e)

    return embedding, "tei"


def invalidate_embedding_cache() -> int:
    """
    Инвалидировать все embedding кэши.

    Вызывается при смене embedding модели.
    """
    cache = get_cache_service()
    if not cache.available:
        return 0

    try:
        deleted = 0
        for key in cache.redis.scan_iter("rag:emb:*"):
            cache.redis.delete(key)
            deleted += 1
        logger.info("Embedding cache invalidated: %d keys", deleted)
        return deleted
    except Exception as e:
        logger.warning("Embedding cache invalidation failed: %s", e)
        return 0
```

### 3.2 Интеграция в `app/rag/retrieval.py`

В методе `HybridRetriever.retrieve()` или `_dense_search()`:

```python
from ..cache.embedding_cache import get_embedding_with_cache

# Было:
query_embedding = self.embeddings.embed_query(query)

# Стало:
query_embedding, emb_source = get_embedding_with_cache(
    query,
    embed_fn=self.embeddings.embed_query,
    model_name="multilingual-e5-base",
)
logger.debug("Query embedding source: %s", emb_source)
```

### 3.3 Settings (уже добавлены в P1)

```python
# app/settings.py - уже есть:
embedding_cache_ttl: int = 86400  # 24 часа
```

### 3.4 Инвалидация при смене модели

Embedding кэш НЕ инвалидируется при изменении контента (в отличие от Plan Cache),
т.к. embeddings зависят только от текста запроса, не от данных.

Инвалидировать нужно только при:
- Смене embedding модели
- Ручном сбросе (`/api/v1/admin/cache/embeddings` endpoint)

```python
# app/routers/admin.py - добавить endpoint:
@router.delete("/cache/embeddings")
def clear_embedding_cache():
    from ..cache.embedding_cache import invalidate_embedding_cache
    deleted = invalidate_embedding_cache()
    return {"deleted": deleted}
```

## Структура файлов (обновление)

```
services/rag-api-new/app/
├── cache/
│   ├── __init__.py
│   ├── cache_service.py
│   ├── plan_cache.py
│   └── embedding_cache.py        # НОВЫЙ (P3)
├── rag/
│   └── retrieval.py              # ИЗМЕНИТЬ (P3)
└── routers/
    └── admin.py                  # ИЗМЕНИТЬ (P3)
```

## Метрики успеха P3

| Метрика | До P3 | После P3 |
|---------|-------|----------|
| Embed query time | ~50-200ms | ~1-5ms (cache hit) |
| TEI load | Каждый запрос | Только cache miss |
| Cache hit rate (embeddings) | 0% | ~80-90% |

## Особенности

1. **Размер кэша**: ~3KB на embedding (768 floats * 4 bytes ≈ 3KB JSON)
2. **Redis memory**: ~3MB на 1000 уникальных запросов
3. **TTL длиннее Plan Cache**: 24ч vs 1ч, т.к. embeddings стабильнее
4. **Не инвалидируется при ingest**: embedding зависит только от текста запроса

## Риски P3

| Риск | Митигация |
|------|-----------|
| Redis memory overflow | TTL 24ч + maxmemory-policy allkeys-lru |
| Stale после смены модели | Ручная инвалидация через admin endpoint |
| JSON overhead | Приемлемо для 768 floats |

---

## Отложено на будущее

- [ ] GraphStore persistence (pickle на диск) — убрать необходимость ingest при рестарте
- [ ] Progressive rendering (frontend) — статусы "Ищу информацию..."
- [ ] Метрики/мониторинг — Prometheus metrics для cache hit rate
- [ ] A/B тестирование — сравнение latency с/без оптимизаций
