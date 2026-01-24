"""
LLM Providers - перечисление и конфигурация провайдеров.
"""
from dataclasses import dataclass
from enum import Enum


class LLMProvider(str, Enum):
    """
    Поддерживаемые LLM-провайдеры.

    - GIGACHAT: GigaChat API (напрямую через langchain_gigachat)
    - DEEPSEEK: DeepSeek API (напрямую через ChatOpenAI)
    - QWEN: Qwen через LiteLLM proxy -> vLLM (локальный)
    """

    GIGACHAT = "gigachat"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


@dataclass
class ProviderConfig:
    """
    Конфигурация провайдера.

    Attributes:
        name: Идентификатор провайдера
        requires_api_key: Требуется ли API ключ
        default_max_tokens: Максимум токенов по умолчанию
        supports_structured_output: Поддерживает ли structured output
    """

    name: LLMProvider
    requires_api_key: bool
    default_max_tokens: int
    supports_structured_output: bool


# Конфигурации провайдеров
PROVIDER_CONFIGS: dict[LLMProvider, ProviderConfig] = {
    LLMProvider.GIGACHAT: ProviderConfig(
        name=LLMProvider.GIGACHAT,
        requires_api_key=True,  # giga_auth_data
        default_max_tokens=1024,
        supports_structured_output=True,
    ),
    LLMProvider.DEEPSEEK: ProviderConfig(
        name=LLMProvider.DEEPSEEK,
        requires_api_key=True,  # deepseek_api_key
        default_max_tokens=1024,
        supports_structured_output=True,
    ),
    LLMProvider.QWEN: ProviderConfig(
        name=LLMProvider.QWEN,
        requires_api_key=False,  # Локальный через LiteLLM
        default_max_tokens=1024,
        supports_structured_output=True,
    ),
}
