"""
LLM Validation - валидация конфигурации LLM при старте приложения.
"""
from __future__ import annotations

import logging

from .exceptions import LLMConfigError
from .factory import parse_llm_id
from .providers import LLMProvider

logger = logging.getLogger(__name__)


def validate_llm_config() -> None:
    """
    Валидация конфигурации LLM при старте.

    Проверяет:
    1. Формат всех LLM ID (provider:model)
    2. Наличие credentials для используемых провайдеров

    Raises:
        LLMConfigError: При неверной конфигурации
    """
    from ..settings import get_settings

    s = get_settings()

    required_roles = [
        ("identity_llm", s.identity_llm, s.identity_temperature),
        ("planner_llm", s.planner_llm, s.planner_temperature),
        ("answer_llm", s.answer_llm, s.answer_temperature),
        ("critic_llm", s.critic_llm, s.critic_temperature),
        ("agent_llm", s.agent_llm, s.agent_temperature),
    ]

    providers_used: set[LLMProvider] = set()

    logger.info("Validating LLM configuration...")

    for role_name, llm_id, temperature in required_roles:
        try:
            provider, model = parse_llm_id(llm_id)
            providers_used.add(provider)
            logger.info("  %s: %s:%s (temp=%.2f)", role_name, provider.value, model, temperature)
        except LLMConfigError as e:
            raise LLMConfigError(f"Invalid {role_name}: {e}")

    # Проверка credentials для используемых провайдеров
    if LLMProvider.GIGACHAT in providers_used and not s.giga_auth_data:
        raise LLMConfigError(
            "GigaChat is used but giga_auth_data is not set. "
            "Set GIGA_AUTH_DATA environment variable with base64-encoded credentials."
        )

    if LLMProvider.DEEPSEEK in providers_used and not s.deepseek_api_key:
        raise LLMConfigError(
            "DeepSeek is used but deepseek_api_key is not set. "
            "Set DEEPSEEK_API_KEY environment variable."
        )

    providers_str = ", ".join(p.value for p in providers_used)
    logger.info("LLM configuration validated. Providers in use: %s", providers_str)
