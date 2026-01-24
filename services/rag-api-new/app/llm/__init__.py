"""
LLM Module - мультипровайдерная архитектура для LLM.

Поддерживаемые провайдеры:
- GigaChat (напрямую через langchain_gigachat)
- DeepSeek (напрямую через ChatOpenAI)
- Qwen (через LiteLLM proxy -> vLLM)

Usage:
    from app.llm import get_llm_factory, parse_llm_id

    factory = get_llm_factory()
    llm = factory.create("gigachat:GigaChat-2", temperature=0.2)
"""
from .exceptions import LLMConfigError, LLMProviderError
from .factory import (
    LLMFactory,
    get_llm_factory,
    get_provider_info,
    parse_llm_id,
    reset_llm_factory,
)
from .providers import PROVIDER_CONFIGS, LLMProvider, ProviderConfig

__all__ = [
    # Factory
    "LLMFactory",
    "get_llm_factory",
    "reset_llm_factory",
    "parse_llm_id",
    "get_provider_info",
    # Providers
    "LLMProvider",
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    # Exceptions
    "LLMConfigError",
    "LLMProviderError",
]
