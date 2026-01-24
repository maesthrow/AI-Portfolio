# ТЗ: Мультипровайдерная архитектура LLM

**Версия**: 1.3
**Дата**: 2025-01-24

**Изменения v1.3:**
- Добавлена функция `get_provider_info()` в factory.py
- Добавлено описание изменений в `plan_cache.py` для возврата usage
- Добавлено изменение сигнатуры `PlannerLLM.plan()` → возвращает `(plan, usage)`
- Убрана секция "Обратная совместимость" (не нужна при полной миграции)
- Исправлены имена функций в примерах rag_tool.py

**Изменения v1.2:**
- Добавлена секция "Интеграция с Rate Limiting"
- Описан TokenUsageCollector для агрегации usage от всех LLM
- Добавлен план по сбору токенов от planner, critic, answer, identity

**Изменения v1.1:**
- Добавлена 5-я роль `identity_llm` для ответов на identity-вопросы
- Обновлены примеры конфигурации
- Добавлен `classifier.py` в план интеграции

---

## Цель

Реализовать гибкую систему настройки LLM-моделей для RAG-агента, позволяющую:
1. Использовать разные LLM-провайдеры (GigaChat, DeepSeek R1, Qwen) для разных этапов пайплайна
2. Легко переключать модели через конфигурацию без изменения кода
3. Оптимизировать качество/стоимость за счёт выбора подходящей модели для каждой роли

---

## Контекст

### Текущая архитектура

Сейчас **одна модель** (`chat_model`) используется для всех LLM-вызовов:

```
settings.chat_model = "GigaChat-2"
         ↓
    ВСЕ роли используют её
```

### Проблема

- Нельзя использовать DeepSeek R1 для planning (где он силён в reasoning)
- Нельзя оставить GigaChat для генерации ответов (где он силён в русском)
- Нет возможности оптимизировать стоимость (дешёвые модели для простых задач)

---

## LLM-вызовы в пайплайне

При обработке одного запроса происходят следующие LLM-вызовы:

| # | Роль | Файл | Назначение | Текущая temp |
|---|------|------|------------|--------------|
| 1 | **identity** | `agent/identity/classifier.py:138` | Ответы на "кто ты?", "что умеешь?" | 0.3 |
| 2 | **agent** | `agent/graph.py:151` | Оркестрация ReAct-агента | 0.2 |
| 3 | **planner** | `agent/planner/planner_llm.py:105` | Генерация QueryPlanV3 | 0.0 |
| 4 | **critic** | `agent/critic/critic_llm.py:95` | Оценка достаточности фактов | 0.2 |
| 5 | **answer** | `agent/answer/answer_llm.py:142` | Генерация ответа пользователю | 0.2 |

**Примечание:** Identity-вызов происходит только при семантическом совпадении с identity-вопросами (threshold >= 0.94). Это fast path — остальной пайплайн пропускается.

---

## Требования

### Функциональные

1. **Три провайдера LLM:**
   - `gigachat` — GigaChat API (напрямую через `langchain_gigachat`)
   - `deepseek` — DeepSeek API (напрямую через `ChatOpenAI`)
   - `qwen` — Qwen через LiteLLM → vLLM (локальный)

2. **Пять ролей с независимой настройкой:**
   - `identity` — ответы на identity-вопросы ("кто ты?", "что умеешь?")
   - `planner` — планирование запроса (structured output)
   - `answer` — генерация ответа пользователю
   - `critic` — оценка достаточности фактов
   - `agent` — оркестрация ReAct-агента

3. **Формат указания модели:** `provider:model_name`
   - Примеры: `gigachat:GigaChat-2`, `deepseek:deepseek-reasoner`, `qwen:Qwen2.5`

4. **Температура задаётся отдельно** для каждой роли

5. **Graceful degradation:**
   - Если провайдер недоступен → логировать ошибку, вернуть понятное сообщение
   - Валидация конфигурации при старте приложения

### Нефункциональные

- Минимальное влияние на латентность (фабрика LLM кэшируется)
- Обратная совместимость: старый формат `chat_model=GigaChat` должен работать
- Логирование выбранных моделей при старте

---

## Архитектура

### Схема подключения провайдеров

```
┌─────────────────────────────────────────────────────────────────┐
│                        rag-api-new                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  gigachat:model ──► GigaChat() ─────────────► GigaChat API     │
│                     (langchain_gigachat)       (напрямую)       │
│                                                                 │
│  deepseek:model ──► ChatOpenAI() ───────────► DeepSeek API     │
│                     (base_url=api.deepseek)    (напрямую)       │
│                                                                 │
│  qwen:model ──────► ChatOpenAI() ──► LiteLLM ──► vLLM          │
│                     (base_url=litellm)         (локальный)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Схема ролей

```
┌─────────────────────────────────────────────────────────────────┐
│                     Запрос пользователя                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  IDENTITY CHECK (semantic matching, threshold >= 0.94)          │
│  └─ Если identity-вопрос ("кто ты?", "что умеешь?"):           │
│     ┌───────────────────────────────────────────────────────┐   │
│     │  IDENTITY LLM                                         │   │
│     │  ├─ Роль: identity                                    │   │
│     │  ├─ Модель: settings.identity_llm                     │   │
│     │  │         (default: deepseek:deepseek-chat)          │   │
│     │  ├─ Temperature: settings.identity_temperature (0.3)  │   │
│     │  └─ Назначение: Простой ответ о возможностях агента   │   │
│     └───────────────────────────────────────────────────────┘   │
│     └─► FAST PATH: сразу возврат ответа, пайплайн пропускается │
└─────────────────────────────────────────────────────────────────┘
                              │ (если НЕ identity-вопрос)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  AGENT LLM                                                      │
│  ├─ Роль: agent                                                 │
│  ├─ Модель: settings.agent_llm (default: gigachat:GigaChat-2)  │
│  ├─ Temperature: settings.agent_temperature (default: 0.2)      │
│  └─ Назначение: ReAct orchestration, tool calling              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (вызов portfolio_rag_tool)
┌─────────────────────────────────────────────────────────────────┐
│  PLANNER LLM                                                    │
│  ├─ Роль: planner                                               │
│  ├─ Модель: settings.planner_llm (default: deepseek:deepseek-reasoner)
│  ├─ Temperature: settings.planner_temperature (default: 0.0)    │
│  └─ Назначение: QueryPlanV3 generation, structured output      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CRITIC LLM (условно)                                           │
│  ├─ Роль: critic                                                │
│  ├─ Модель: settings.critic_llm (default: deepseek:deepseek-reasoner)
│  ├─ Temperature: settings.critic_temperature (default: 0.2)     │
│  └─ Назначение: Evaluate fact sufficiency                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ANSWER LLM                                                     │
│  ├─ Роль: answer                                                │
│  ├─ Модель: settings.answer_llm (default: gigachat:GigaChat-2) │
│  ├─ Temperature: settings.answer_temperature (default: 0.2)     │
│  └─ Назначение: User-facing response generation                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ответ пользователю                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Настройки (settings.py)

### Credentials провайдеров

```python
# === Provider: GigaChat ===
giga_auth_data: str | None = None
"""Base64-encoded credentials для GigaChat API."""

# === Provider: DeepSeek ===
deepseek_api_key: str | None = None
"""API ключ для DeepSeek."""

deepseek_base_url: str = "https://api.deepseek.com/v1"
"""Base URL для DeepSeek API."""

# === Provider: Qwen (через LiteLLM) ===
litellm_base_url: str = "http://localhost:8005/v1"
"""Base URL для LiteLLM proxy."""

litellm_api_key: str = "sk-local-any"
"""API ключ для LiteLLM."""
```

### Роли LLM

```python
# === LLM Roles (формат: "provider:model") ===

identity_llm: str = "deepseek:deepseek-chat"
"""LLM для identity-вопросов ("кто ты?", "что умеешь?").
DeepSeek Chat дешевле, задача простая."""

planner_llm: str = "deepseek:deepseek-reasoner"
"""LLM для планирования запросов. DeepSeek R1 хорош для reasoning."""

answer_llm: str = "gigachat:GigaChat-2"
"""LLM для генерации ответов. GigaChat хорош для русского языка."""

critic_llm: str = "deepseek:deepseek-reasoner"
"""LLM для оценки достаточности фактов."""

agent_llm: str = "gigachat:GigaChat-2"
"""LLM для ReAct-агента (orchestration)."""
```

### Температуры

```python
# === LLM Temperatures ===

identity_temperature: float = 0.3
"""Температура для Identity (чуть выше для естественности)."""

planner_temperature: float = 0.0
"""Температура для Planner (0.0 = детерминированный)."""

answer_temperature: float = 0.2
"""Температура для Answer (баланс точности и естественности)."""

critic_temperature: float = 0.2
"""Температура для Critic."""

agent_temperature: float = 0.2
"""Температура для Agent."""
```

---

## Реализация

### Структура файлов

```
services/rag-api-new/app/
├── llm/                        # НОВЫЙ модуль
│   ├── __init__.py
│   ├── factory.py              # LLMFactory, get_provider_info()
│   ├── providers.py            # Enum LLMProvider, ProviderConfig
│   └── exceptions.py           # LLMConfigError, LLMProviderError
├── cache/
│   └── plan_cache.py           # Обновить: возвращать (plan, source, usage)
├── rate_limit/
│   └── usage_collector.py      # НОВЫЙ: TokenUsageCollector
├── deps.py                     # Обновить: использовать LLMFactory
└── settings.py                 # Добавить настройки ролей
```

### providers.py

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable
from langchain_core.language_models import BaseChatModel


class LLMProvider(str, Enum):
    """Поддерживаемые LLM-провайдеры."""
    GIGACHAT = "gigachat"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


@dataclass
class ProviderConfig:
    """Конфигурация провайдера."""
    name: LLMProvider
    requires_api_key: bool
    default_max_tokens: int
    supports_structured_output: bool
```

### factory.py

```python
from functools import lru_cache
from typing import Optional
import logging

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_gigachat import GigaChat

from .providers import LLMProvider
from .exceptions import LLMConfigError
from ..settings import get_settings

logger = logging.getLogger(__name__)


def parse_llm_id(llm_id: str) -> tuple[LLMProvider, str]:
    """
    Парсит строку формата 'provider:model'.

    Args:
        llm_id: Строка вида "gigachat:GigaChat-2" или "deepseek:deepseek-reasoner"

    Returns:
        Tuple (provider, model_name)

    Raises:
        LLMConfigError: Если формат неверный или провайдер неизвестен
    """
    if ":" not in llm_id:
        raise LLMConfigError(
            f"Invalid LLM ID format: '{llm_id}'. Expected 'provider:model'"
        )

    provider_str, model = llm_id.split(":", 1)

    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise LLMConfigError(
            f"Unknown provider: '{provider_str}'. Valid providers: {valid}"
        )

    return provider, model


class LLMFactory:
    """
    Фабрика для создания LLM-инстансов.

    Поддерживает кэширование по (provider, model, temperature).
    """

    def __init__(self):
        self._cache: dict[tuple, BaseChatModel] = {}
        self._settings = get_settings()

    def create(
        self,
        llm_id: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        Создаёт или возвращает кэшированный LLM.

        Args:
            llm_id: Идентификатор вида "provider:model"
            temperature: Температура генерации
            max_tokens: Максимум токенов (опционально)

        Returns:
            BaseChatModel instance
        """
        cache_key = (llm_id, temperature, max_tokens)

        if cache_key in self._cache:
            return self._cache[cache_key]

        provider, model = parse_llm_id(llm_id)

        llm = self._create_for_provider(provider, model, temperature, max_tokens)
        self._cache[cache_key] = llm

        logger.info(
            "Created LLM: provider=%s, model=%s, temperature=%.2f",
            provider.value, model, temperature
        )

        return llm

    def _create_for_provider(
        self,
        provider: LLMProvider,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Создаёт LLM для конкретного провайдера."""

        if provider == LLMProvider.GIGACHAT:
            return self._create_gigachat(model, temperature, max_tokens)

        elif provider == LLMProvider.DEEPSEEK:
            return self._create_deepseek(model, temperature, max_tokens)

        elif provider == LLMProvider.QWEN:
            return self._create_qwen(model, temperature, max_tokens)

        raise LLMConfigError(f"Provider not implemented: {provider}")

    def _create_gigachat(
        self,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Создаёт GigaChat LLM (напрямую)."""

        if not self._settings.giga_auth_data:
            raise LLMConfigError(
                "GigaChat requires giga_auth_data to be set"
            )

        return GigaChat(
            credentials=self._settings.giga_auth_data,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            verify_ssl_certs=False,
        )

    def _create_deepseek(
        self,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Создаёт DeepSeek LLM (напрямую через OpenAI-совместимый API)."""

        if not self._settings.deepseek_api_key:
            raise LLMConfigError(
                "DeepSeek requires deepseek_api_key to be set"
            )

        return ChatOpenAI(
            api_key=self._settings.deepseek_api_key,
            base_url=str(self._settings.deepseek_base_url),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            timeout=120,  # DeepSeek R1 может думать долго
        )

    def _create_qwen(
        self,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """Создаёт Qwen LLM (через LiteLLM proxy)."""

        return ChatOpenAI(
            api_key=self._settings.litellm_api_key or "EMPTY",
            base_url=str(self._settings.litellm_base_url),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            timeout=60,
        )


# Singleton instance
_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """Возвращает singleton LLMFactory."""
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory


def get_provider_info(llm_id: str) -> tuple[str, str]:
    """
    Извлечь provider и model из llm_id для логирования/usage.

    Args:
        llm_id: Строка вида "gigachat:GigaChat-2"

    Returns:
        Tuple (provider_name, model_name) как строки
    """
    provider, model = parse_llm_id(llm_id)
    return provider.value, model
```

### Обновление deps.py

```python
from .llm.factory import get_llm_factory
from .settings import get_settings


@lru_cache()
def identity_llm() -> BaseChatModel:
    """LLM для Identity (ответы на 'кто ты?', 'что умеешь?')."""
    s = get_settings()
    factory = get_llm_factory()
    return factory.create(
        llm_id=s.identity_llm,
        temperature=s.identity_temperature,
        max_tokens=512,
    )


@lru_cache()
def planner_llm() -> BaseChatModel:
    """LLM для Planner (планирование запросов)."""
    s = get_settings()
    factory = get_llm_factory()
    return factory.create(
        llm_id=s.planner_llm,
        temperature=s.planner_temperature,
        max_tokens=1024,
    )


@lru_cache()
def answer_llm() -> BaseChatModel:
    """LLM для Answer (генерация ответов)."""
    s = get_settings()
    factory = get_llm_factory()
    return factory.create(
        llm_id=s.answer_llm,
        temperature=s.answer_temperature,
        max_tokens=1024,
    )


@lru_cache()
def critic_llm() -> BaseChatModel:
    """LLM для Critic (оценка достаточности)."""
    s = get_settings()
    factory = get_llm_factory()
    return factory.create(
        llm_id=s.critic_llm,
        temperature=s.critic_temperature,
        max_tokens=512,
    )


@lru_cache()
def agent_llm() -> BaseChatModel:
    """LLM для Agent (ReAct orchestration)."""
    s = get_settings()
    factory = get_llm_factory()
    return factory.create(
        llm_id=s.agent_llm,
        temperature=s.agent_temperature,
        max_tokens=512,
    )
```

### Обновление plan_cache.py

Функция `get_plan_with_cache` должна возвращать usage от PlannerLLM:

```python
# app/cache/plan_cache.py

from typing import Any

def get_plan_with_cache(
    question: str,
    planner_llm_fn,
) -> tuple[QueryPlanV3, str, Any]:
    """
    Получить план с кэшированием.

    Returns:
        tuple[plan, source, usage]:
        - plan: QueryPlanV3
        - source: "shortcut" | "cache" | "llm"
        - usage: dict с токенами или None (для shortcut/cache)
    """
    normalized = normalize_question(question)

    # 1. Shortcut (детерминированный) — usage = None
    shortcut_plan = try_shortcut(normalized)
    if shortcut_plan:
        logger.info("Plan from shortcut: %r", normalized[:50])
        return shortcut_plan, "shortcut", None

    # 2. Cache — usage = None (уже потрачено ранее)
    cache = get_cache_service()
    cache_key = f"plan:{_hash_question(normalized)}"

    cached = cache.get(cache_key)
    if cached:
        try:
            plan = QueryPlanV3.model_validate_json(cached)
            logger.info("Plan from cache: %r", normalized[:50])
            return plan, "cache", None
        except Exception as e:
            logger.warning("Cache parse error: %s", e)

    # 3. LLM — возвращаем usage
    planner = PlannerLLM(planner_llm_fn())
    plan, usage = planner.plan(question)  # ← изменённая сигнатура

    # Сохранить в кэш
    try:
        cache.set(cache_key, plan.model_dump_json(), ttl=settings().plan_cache_ttl)
    except Exception as e:
        logger.warning("Cache set error: %s", e)

    return plan, "llm", usage
```

**Изменение сигнатуры PlannerLLM.plan():**

```python
# app/agent/planner/planner_llm.py

class PlannerLLM:
    def plan(self, question: str) -> tuple[QueryPlanV3, Any]:
        """
        Сгенерировать план запроса.

        Returns:
            tuple[plan, usage]: План и usage metadata от LLM
        """
        messages = self._build_messages(question)
        response = self.llm.invoke(messages)

        # Извлечь usage
        usage = getattr(response, "usage_metadata", None)
        if usage is None and hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage")

        plan = self._parse_response(response)
        return plan, usage
```

---

## Примеры конфигурации

### Пример 1: DeepSeek для reasoning, GigaChat для ответов

```bash
# .env
IDENTITY_LLM=deepseek:deepseek-chat       # Дешёвая модель для простых ответов
PLANNER_LLM=deepseek:deepseek-reasoner    # Сильный reasoning
ANSWER_LLM=gigachat:GigaChat-2            # Хороший русский
CRITIC_LLM=deepseek:deepseek-reasoner     # Reasoning для оценки
AGENT_LLM=gigachat:GigaChat-2             # Надёжный для orchestration

DEEPSEEK_API_KEY=sk-xxx
GIGA_AUTH_DATA=base64xxx
```

### Пример 2: Всё на GigaChat (как сейчас)

```bash
# .env
IDENTITY_LLM=gigachat:GigaChat-2
PLANNER_LLM=gigachat:GigaChat-2
ANSWER_LLM=gigachat:GigaChat-2
CRITIC_LLM=gigachat:GigaChat-2
AGENT_LLM=gigachat:GigaChat-2

GIGA_AUTH_DATA=base64xxx
```

### Пример 3: Локальный Qwen для всего

```bash
# .env
IDENTITY_LLM=qwen:Qwen2.5
PLANNER_LLM=qwen:Qwen2.5
ANSWER_LLM=qwen:Qwen2.5
CRITIC_LLM=qwen:Qwen2.5
AGENT_LLM=qwen:Qwen2.5

LITELLM_BASE_URL=http://localhost:8005/v1
```

### Пример 4: Гибридный (максимальная оптимизация стоимости)

```bash
# .env
IDENTITY_LLM=deepseek:deepseek-chat       # Самая дешёвая, задача простая
PLANNER_LLM=deepseek:deepseek-reasoner    # Сильный reasoning
ANSWER_LLM=gigachat:GigaChat-2            # Хороший русский
CRITIC_LLM=qwen:Qwen2.5                   # Бесплатный локальный
AGENT_LLM=gigachat:GigaChat-2             # Надёжный для orchestration
```

---

## Валидация при старте

При запуске приложения проверять:

1. **Формат LLM ID** — корректный `provider:model`
2. **Credentials провайдера** — заданы необходимые ключи
3. **Доступность провайдера** — опциональный health check

```python
def validate_llm_config():
    """Валидация конфигурации LLM при старте."""
    s = get_settings()

    required_roles = [
        ("identity_llm", s.identity_llm),
        ("planner_llm", s.planner_llm),
        ("answer_llm", s.answer_llm),
        ("critic_llm", s.critic_llm),
        ("agent_llm", s.agent_llm),
    ]

    providers_used = set()

    for role_name, llm_id in required_roles:
        try:
            provider, model = parse_llm_id(llm_id)
            providers_used.add(provider)
            logger.info(f"{role_name}: {provider.value}:{model}")
        except LLMConfigError as e:
            raise LLMConfigError(f"Invalid {role_name}: {e}")

    # Проверка credentials для используемых провайдеров
    if LLMProvider.GIGACHAT in providers_used and not s.giga_auth_data:
        raise LLMConfigError("GigaChat used but giga_auth_data not set")

    if LLMProvider.DEEPSEEK in providers_used and not s.deepseek_api_key:
        raise LLMConfigError("DeepSeek used but deepseek_api_key not set")
```

---

## Логирование

### При старте приложения

```
INFO: LLM Configuration:
INFO:   identity_llm: deepseek:deepseek-chat (temp=0.3)
INFO:   planner_llm: deepseek:deepseek-reasoner (temp=0.0)
INFO:   answer_llm: gigachat:GigaChat-2 (temp=0.2)
INFO:   critic_llm: deepseek:deepseek-reasoner (temp=0.2)
INFO:   agent_llm: gigachat:GigaChat-2 (temp=0.2)
INFO: Providers in use: deepseek, gigachat
```

### При создании LLM

```
INFO: Created LLM: provider=deepseek, model=deepseek-reasoner, temperature=0.00
```

### При ошибке провайдера

```
ERROR: LLM provider error: provider=deepseek, error=Connection timeout
```

---

## Тестирование

### Unit тесты

```python
# tests/llm/test_factory.py

def test_parse_llm_id_valid():
    """Парсинг корректного LLM ID."""
    provider, model = parse_llm_id("gigachat:GigaChat-2")
    assert provider == LLMProvider.GIGACHAT
    assert model == "GigaChat-2"


def test_parse_llm_id_invalid_format():
    """Ошибка при неверном формате."""
    with pytest.raises(LLMConfigError, match="Invalid LLM ID format"):
        parse_llm_id("gigachat")


def test_parse_llm_id_unknown_provider():
    """Ошибка при неизвестном провайдере."""
    with pytest.raises(LLMConfigError, match="Unknown provider"):
        parse_llm_id("openai:gpt-4")


def test_factory_caches_llm():
    """Фабрика кэширует LLM инстансы."""
    factory = LLMFactory()
    llm1 = factory.create("gigachat:GigaChat-2", 0.2)
    llm2 = factory.create("gigachat:GigaChat-2", 0.2)
    assert llm1 is llm2


def test_factory_different_temps_different_instances():
    """Разные температуры = разные инстансы."""
    factory = LLMFactory()
    llm1 = factory.create("gigachat:GigaChat-2", 0.0)
    llm2 = factory.create("gigachat:GigaChat-2", 0.5)
    assert llm1 is not llm2
```

### Integration тесты

```python
# tests/llm/test_providers.py

@pytest.mark.integration
def test_gigachat_provider():
    """GigaChat провайдер работает."""
    factory = LLMFactory()
    llm = factory.create("gigachat:GigaChat-2", 0.2)
    response = llm.invoke("Привет")
    assert response.content


@pytest.mark.integration
def test_deepseek_provider():
    """DeepSeek провайдер работает."""
    factory = LLMFactory()
    llm = factory.create("deepseek:deepseek-reasoner", 0.2)
    response = llm.invoke("Hello")
    assert response.content
```

---

## План реализации

### Этап 1: Инфраструктура (backend)

1. Создать модуль `app/llm/` с factory и providers
2. Добавить новые настройки в `settings.py`
3. Добавить исключения `LLMConfigError`, `LLMProviderError`
4. Написать unit тесты для factory

### Этап 2: Интеграция

1. Обновить `deps.py` — использовать `LLMFactory`
2. Обновить `agent/graph.py` — использовать `agent_llm()`
3. Обновить `agent/planner/planner_llm.py` — возвращать `(plan, usage)`
4. Обновить `agent/critic/critic_llm.py` — использовать `critic_llm()`, возвращать usage
5. Обновить `agent/answer/answer_llm.py` — возвращать usage
6. Обновить `agent/identity/classifier.py` — использовать `identity_llm()`, возвращать usage
7. Обновить `cache/plan_cache.py` — возвращать `(plan, source, usage)`
8. Добавить валидацию конфигурации при старте

### Этап 3: Документация и тестирование

1. Обновить `.env.example` с новыми переменными
2. Обновить `CLAUDE.md` с описанием архитектуры
3. Написать integration тесты для провайдеров
4. Проверить работу с разными конфигурациями

---

## Интеграция с Rate Limiting

### Текущая проблема

Сейчас rate limiting **НЕ учитывает** токены от всех LLM-вызовов:

```
┌─────────────────────────────────────────────────────────────────┐
│  chat.py: event_generator()                                     │
│  └─ Собирает usage только из on_chat_model_end (agent LLM)     │
│                                                                 │
│  Что НЕ учитывается:                                           │
│  ├─ identity_llm (fast path) — токены не записываются!         │
│  ├─ planner_llm (внутри rag_tool) — токены теряются!           │
│  ├─ critic_llm (внутри rag_tool) — токены теряются!            │
│  └─ answer_llm (внутри rag_tool) — токены теряются!            │
└─────────────────────────────────────────────────────────────────┘
```

**Результат:** В rate limiter записываются только токены от agent LLM (~500-800), а реальное потребление может быть 3000-5000 токенов.

### Анализ текущего кода

**chat.py (строки 323-341):**
```python
# Сейчас: записывается только usage от последнего on_chat_model_end
formatted_usage = _format_usage(usage)  # ← только agent LLM
if formatted_usage:
    total_tokens = formatted_usage.get("total_tokens") or 0
    final_rate_limit = limiter.record_usage(client_ip, total_tokens)
```

**rag_tool.py (строки 74, 127, 238):**
```python
plan, plan_source = get_plan_with_cache(question, planner_llm)  # ← usage теряется
critic = CriticLLM(planner_llm())  # ← usage теряется
answer = answer_gen.generate(payload)  # ← usage теряется
```

**identity fast path (chat.py строки 223-234):**
```python
response = await generate_identity_response(req.question)
# ← usage вообще не собирается и не записывается в rate limiter!
```

### Требования

1. **Собирать usage от ВСЕХ LLM-вызовов** в рамках одного запроса
2. **Агрегировать токены** от разных моделей (простое суммирование)
3. **Записывать суммарный usage** в rate limiter
4. **Логировать детализацию** по ролям для мониторинга

### Решение: TokenUsageCollector

**Новый класс** для агрегации usage в рамках запроса:

```python
# app/rate_limit/usage_collector.py

from dataclasses import dataclass, field
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class RoleUsage:
    """Usage для одной роли."""
    role: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TokenUsageCollector:
    """
    Собирает usage со всех LLM-вызовов в рамках одного запроса.

    Используется для корректного подсчёта токенов при rate limiting
    в мультипровайдерной архитектуре.
    """
    usage_by_role: dict[str, RoleUsage] = field(default_factory=dict)

    def add(self, role: str, provider: str, model: str, usage: Any) -> None:
        """
        Добавить usage от LLM-вызова.

        Args:
            role: Роль LLM (identity, planner, critic, answer, agent)
            provider: Провайдер (gigachat, deepseek, qwen)
            model: Название модели
            usage: Объект usage (dict или LangChain UsageMetadata)
        """
        if not usage:
            return

        prompt_tokens = self._extract_tokens(usage, "prompt_tokens", "input_tokens")
        completion_tokens = self._extract_tokens(usage, "completion_tokens", "output_tokens")

        if role in self.usage_by_role:
            # Суммируем если была ретрай
            self.usage_by_role[role].prompt_tokens += prompt_tokens
            self.usage_by_role[role].completion_tokens += completion_tokens
        else:
            self.usage_by_role[role] = RoleUsage(
                role=role,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        logger.debug(
            "TokenUsage added: role=%s provider=%s prompt=%d completion=%d",
            role, provider, prompt_tokens, completion_tokens
        )

    def _extract_tokens(self, usage: Any, *keys: str) -> int:
        """Извлечь значение токенов из usage объекта."""
        for key in keys:
            if isinstance(usage, dict) and key in usage:
                return int(usage[key] or 0)
            val = getattr(usage, key, None)
            if val is not None:
                return int(val)
        return 0

    @property
    def total_tokens(self) -> int:
        """Суммарное количество токенов от всех ролей."""
        return sum(ru.total_tokens for ru in self.usage_by_role.values())

    def to_dict(self) -> dict:
        """Сериализация для логирования и ответа."""
        return {
            "total_tokens": self.total_tokens,
            "by_role": {
                role: {
                    "provider": ru.provider,
                    "model": ru.model,
                    "prompt_tokens": ru.prompt_tokens,
                    "completion_tokens": ru.completion_tokens,
                    "total_tokens": ru.total_tokens,
                }
                for role, ru in self.usage_by_role.items()
            }
        }

    def log_summary(self, message_id: str) -> None:
        """Логировать сводку по usage."""
        parts = [f"{role}={ru.total_tokens}" for role, ru in self.usage_by_role.items()]
        logger.info(
            "TokenUsage summary: message_id=%s total=%d breakdown=[%s]",
            message_id, self.total_tokens, ", ".join(parts)
        )
```

### Изменения в rag_tool.py

**Возвращать usage в результате:**

```python
@tool("portfolio_rag_tool")
def portfolio_rag_tool(question: str) -> dict:
    from ..rate_limit.usage_collector import TokenUsageCollector
    from ..llm.factory import get_provider_info

    collector = TokenUsageCollector()

    try:
        # 1. Plan
        plan, plan_source, planner_usage = get_plan_with_cache(question, planner_llm)
        if planner_usage:
            collector.add("planner", *get_provider_info(settings().planner_llm), planner_usage)

        # ... executor ...

        # 2. Critic (если вызывается)
        if not skip_critic:
            critic = CriticLLM(planner_llm())
            decision, critic_usage = critic.evaluate(question, plan, payload)
            if critic_usage:
                collector.add("critic", *get_provider_info(settings().critic_llm), critic_usage)

        # ... normalizer, render ...

        # 3. Answer
        answer_gen = AnswerLLM(answer_llm())
        answer, answer_usage = answer_gen.generate(payload)
        if answer_usage:
            collector.add("answer", *get_provider_info(settings().answer_llm), answer_usage)

        return {
            "answer": answer,
            # ... остальные поля ...
            "usage": collector.to_dict(),  # ← НОВОЕ: возвращаем usage
        }
```

### Изменения в chat.py

**Агрегировать usage от agent + rag_tool:**

```python
async def event_generator():
    collector = TokenUsageCollector()

    # ... streaming events ...

    # Обработка on_tool_end — извлечь usage от rag_tool
    elif kind == "on_tool_end":
        data = event.get("data") or {}
        tool_output = data.get("output")
        if isinstance(tool_output, dict) and "usage" in tool_output:
            rag_usage = tool_output["usage"]
            # Добавляем все роли из rag_tool
            for role, role_data in (rag_usage.get("by_role") or {}).items():
                collector.add(
                    role,
                    role_data.get("provider", "unknown"),
                    role_data.get("model", "unknown"),
                    role_data,
                )

    # Обработка on_chat_model_end — добавить usage от agent
    elif kind == "on_chat_model_end":
        # ... extract usage ...
        if usage:
            s = settings()
            provider, model = parse_llm_id(s.agent_llm)
            collector.add("agent", provider, model, usage)

    # В конце — записать суммарный usage в rate limiter
    if limiter.settings.rate_limit_enabled:
        total_tokens = collector.total_tokens
        if total_tokens > 0:
            final_rate_limit = limiter.record_usage(client_ip, total_tokens)
            collector.log_summary(message_id)
```

**Identity fast path — тоже записывать:**

```python
async def identity_generator():
    yield json.dumps({"type": "start", ...}) + "\n"

    response, usage = await generate_identity_response_with_usage(req.question)

    yield json.dumps({"type": "delta", "content": response}) + "\n"

    # Записать usage в rate limiter
    if limiter.settings.rate_limit_enabled and usage:
        total_tokens = (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
        if total_tokens > 0:
            final_rate_limit = limiter.record_usage(client_ip, total_tokens)

    yield json.dumps({
        "type": "end",
        "usage": usage,
        "rate_limit": final_rate_limit.model_dump() if final_rate_limit else None,
    }) + "\n"
```

### Изменения в LLM-классах

Каждый LLM-класс должен возвращать usage:

**PlannerLLM:**
```python
def plan(self, question: str) -> tuple[QueryPlanV3, Any]:
    response = self.llm.invoke(messages)
    usage = getattr(response, "usage_metadata", None)
    return plan, usage
```

**AnswerLLM:**
```python
def generate(self, payload: ExecutorPayload) -> tuple[str, Any]:
    response = self.llm.invoke(messages)
    usage = getattr(response, "usage_metadata", None)
    return answer, usage
```

**CriticLLM:**
```python
def evaluate(self, ...) -> tuple[CriticDecision, Any]:
    response = self.llm.invoke(messages)
    usage = getattr(response, "usage_metadata", None)
    return decision, usage
```

**classifier.py (identity):**
```python
async def generate_identity_response(question: str) -> tuple[str, dict | None]:
    response = await llm.ainvoke(messages)
    usage = getattr(response, "usage_metadata", None)
    return response.content, _format_usage(usage)
```

### Логирование

**При каждом запросе:**
```
INFO: TokenUsage summary: message_id=abc123 total=3847 breakdown=[planner=1200, critic=650, answer=1500, agent=497]
INFO: Rate limit recorded: ip=85.140.10.* tokens=3847 new_total=12500
```

**Детальный формат в ответе:**
```json
{
  "type": "end",
  "usage": {
    "total_tokens": 3847,
    "by_role": {
      "planner": {"provider": "deepseek", "model": "deepseek-reasoner", "total_tokens": 1200},
      "critic": {"provider": "deepseek", "model": "deepseek-reasoner", "total_tokens": 650},
      "answer": {"provider": "gigachat", "model": "GigaChat-2", "total_tokens": 1500},
      "agent": {"provider": "gigachat", "model": "GigaChat-2", "total_tokens": 497}
    }
  },
  "rate_limit": {...}
}
```

### Обоснование подхода

**Почему простое суммирование, а не раздельные лимиты?**

1. **Цель rate limit** — защита от злоупотреблений, а не точный биллинг
2. **Токены сопоставимы** — разница между токенизаторами ±20-30%
3. **Простота** — не нужно менять схему Redis и UI фронтенда
4. **Можно улучшить позже** — если понадобится точность, добавить лимит по стоимости

**Альтернативы (для будущего):**
- Раздельные счётчики по провайдерам
- Лимит по стоимости ($/час)
- Нормализация токенов с коэффициентами

### Структура файлов (дополнение)

```
services/rag-api-new/app/
├── rate_limit/
│   ├── __init__.py
│   ├── limiter.py           # Существующий
│   ├── schemas.py           # Существующий
│   └── usage_collector.py   # НОВЫЙ: TokenUsageCollector
```

### План реализации (дополнение к Этапу 2)

**Этап 2.5: Интеграция с Rate Limiting**

1. Создать `app/rate_limit/usage_collector.py`
2. Обновить `PlannerLLM.plan()` — возвращать usage
3. Обновить `AnswerLLM.generate()` — возвращать usage
4. Обновить `CriticLLM.evaluate()` — возвращать usage
5. Обновить `generate_identity_response()` — возвращать usage
6. Обновить `rag_tool.py` — собирать и возвращать агрегированный usage
7. Обновить `chat.py` — агрегировать usage от agent + rag_tool
8. Обновить `chat.py` — записывать usage для identity fast path
9. Добавить тесты для TokenUsageCollector

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| DeepSeek API нестабилен | Средняя | Fallback на GigaChat, retry logic |
| Разные модели дают разное качество | Высокая | A/B тестирование, метрики качества |
| Увеличение сложности конфигурации | Низкая | Хорошие defaults, валидация при старте |
| DeepSeek R1 медленный (думает) | Высокая | Увеличить timeout до 120s, показывать "думает..." |
| Неточный подсчёт токенов (разные токенизаторы) | Средняя | Простое суммирование достаточно для rate limit; точный биллинг — отдельная задача |

---

## Метрики успеха

1. **Гибкость**: Можно настроить любую комбинацию провайдеров
2. **Производительность**: Латентность не увеличилась (кэширование работает)
3. **Качество**: A/B тест показывает улучшение для DeepSeek R1 на planning
4. **Стабильность**: Нет ошибок из-за неверной конфигурации (валидация)

---

## Ссылки

- [DeepSeek API Documentation](https://platform.deepseek.com/docs)
- [LangChain ChatOpenAI](https://python.langchain.com/docs/integrations/chat/openai)
- [LangChain GigaChat](https://python.langchain.com/docs/integrations/chat/gigachat)
- Связанные файлы:
  - `services/rag-api-new/app/deps.py`
  - `services/rag-api-new/app/settings.py`
  - `services/rag-api-new/app/llm/factory.py` (новый)
  - `services/rag-api-new/app/llm/providers.py` (новый)
  - `services/rag-api-new/app/llm/exceptions.py` (новый)
  - `services/rag-api-new/app/cache/plan_cache.py`
  - `services/rag-api-new/app/agent/identity/classifier.py`
  - `services/rag-api-new/app/agent/planner/planner_llm.py`
  - `services/rag-api-new/app/agent/answer/answer_llm.py`
  - `services/rag-api-new/app/agent/critic/critic_llm.py`
  - `services/rag-api-new/app/agent/graph.py`
  - `services/rag-api-new/app/agent/rag_tool.py`
  - `services/rag-api-new/app/routers/chat.py`
  - `services/rag-api-new/app/rate_limit/limiter.py`
  - `services/rag-api-new/app/rate_limit/usage_collector.py` (новый)
