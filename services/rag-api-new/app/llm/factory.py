"""
LLM Factory - фабрика для создания LLM-инстансов разных провайдеров.

Поддерживает:
- GigaChat (напрямую через langchain_gigachat)
- DeepSeek (напрямую через ChatOpenAI)
- Qwen (через LiteLLM proxy)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from langchain_core.language_models import BaseChatModel
from langchain_gigachat import GigaChat
from langchain_openai import ChatOpenAI

from .exceptions import LLMConfigError
from .providers import LLMProvider

if TYPE_CHECKING:
    from ..settings import Settings

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

    Examples:
        >>> parse_llm_id("gigachat:GigaChat-2")
        (LLMProvider.GIGACHAT, "GigaChat-2")

        >>> parse_llm_id("deepseek:deepseek-reasoner")
        (LLMProvider.DEEPSEEK, "deepseek-reasoner")
    """
    if ":" not in llm_id:
        raise LLMConfigError(
            f"Invalid LLM ID format: '{llm_id}'. Expected 'provider:model' (e.g., 'gigachat:GigaChat-2')"
        )

    provider_str, model = llm_id.split(":", 1)

    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise LLMConfigError(f"Unknown provider: '{provider_str}'. Valid providers: {valid}")

    return provider, model


def get_provider_info(llm_id: str) -> tuple[str, str]:
    """
    Извлечь provider и model из llm_id для логирования/usage.

    Args:
        llm_id: Строка вида "gigachat:GigaChat-2"

    Returns:
        Tuple (provider_name, model_name) как строки

    Examples:
        >>> get_provider_info("deepseek:deepseek-chat")
        ("deepseek", "deepseek-chat")
    """
    provider, model = parse_llm_id(llm_id)
    return provider.value, model


class LLMFactory:
    """
    Фабрика для создания LLM-инстансов.

    Поддерживает кэширование по (provider, model, temperature, max_tokens).
    Каждый уникальный набор параметров создаёт отдельный инстанс.

    Usage:
        factory = get_llm_factory()
        llm = factory.create("gigachat:GigaChat-2", temperature=0.2)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Инициализация фабрики.

        Args:
            settings: Настройки приложения. Если не указаны, загружаются автоматически.
        """
        self._cache: dict[tuple, BaseChatModel] = {}
        self._settings = settings

    @property
    def settings(self) -> Settings:
        """Ленивая загрузка настроек."""
        if self._settings is None:
            from ..settings import get_settings

            self._settings = get_settings()
        return self._settings

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

        Raises:
            LLMConfigError: При неверном формате или отсутствии credentials
        """
        cache_key = (llm_id, temperature, max_tokens)

        if cache_key in self._cache:
            return self._cache[cache_key]

        provider, model = parse_llm_id(llm_id)

        llm = self._create_for_provider(provider, model, temperature, max_tokens)
        self._cache[cache_key] = llm

        logger.info(
            "Created LLM: provider=%s, model=%s, temperature=%.2f, max_tokens=%s",
            provider.value,
            model,
            temperature,
            max_tokens,
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
        """
        Создаёт GigaChat LLM (напрямую через API).

        Raises:
            LLMConfigError: Если giga_auth_data не задан
        """
        if not self.settings.giga_auth_data:
            raise LLMConfigError(
                "GigaChat requires giga_auth_data to be set. "
                "Set GIGA_AUTH_DATA environment variable with base64-encoded credentials."
            )

        return GigaChat(
            credentials=self.settings.giga_auth_data,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            verify_ssl_certs=False,
            timeout=90,  # Увеличенный таймаут для стабильности
        )

    def _create_deepseek(
        self,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> BaseChatModel:
        """
        Создаёт DeepSeek LLM (напрямую через OpenAI-совместимый API).

        Raises:
            LLMConfigError: Если deepseek_api_key не задан
        """
        if not self.settings.deepseek_api_key:
            raise LLMConfigError(
                "DeepSeek requires deepseek_api_key to be set. "
                "Set DEEPSEEK_API_KEY environment variable."
            )

        return ChatOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=str(self.settings.deepseek_base_url),
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
        """Создаёт Qwen LLM (через LiteLLM proxy -> vLLM)."""
        return ChatOpenAI(
            api_key=self.settings.litellm_api_key or "EMPTY",
            base_url=str(self.settings.litellm_base_url),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            timeout=60,
        )

    def clear_cache(self) -> None:
        """Очистить кэш LLM инстансов."""
        self._cache.clear()
        logger.info("LLM cache cleared")


# Singleton instance
_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """
    Возвращает singleton LLMFactory.

    Returns:
        LLMFactory instance
    """
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory


def reset_llm_factory() -> None:
    """
    Сбросить singleton фабрики.

    Используется в тестах для изоляции.
    """
    global _factory
    if _factory is not None:
        _factory.clear_cache()
    _factory = None
