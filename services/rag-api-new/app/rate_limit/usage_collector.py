"""
TokenUsageCollector - агрегация usage от всех LLM-вызовов.

Собирает токены от разных ролей (identity, planner, critic, answer, agent)
для корректного rate limiting в мультипровайдерной архитектуре.

Пример использования:
    collector = TokenUsageCollector()
    collector.add("planner", "deepseek", "deepseek-reasoner", usage_from_llm)
    collector.add("answer", "gigachat", "GigaChat-2", usage_from_llm)
    total = collector.total_tokens
    collector.log_summary(message_id)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RoleUsage:
    """Token usage для одной роли."""

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

        # Skip if no tokens extracted
        if prompt_tokens == 0 and completion_tokens == 0:
            return

        if role in self.usage_by_role:
            # Суммируем если была ретрай или несколько вызовов
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
            "TokenUsage added: role=%s provider=%s model=%s prompt=%d completion=%d",
            role,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
        )

    def _extract_tokens(self, usage: Any, *keys: str) -> int:
        """Извлечь значение токенов из usage объекта."""
        for key in keys:
            # Сначала пробуем как dict
            if isinstance(usage, dict) and key in usage:
                val = usage[key]
                if val is not None:
                    return int(val)
            # Затем как объект с атрибутами (LangChain UsageMetadata)
            else:
                val = getattr(usage, key, None)
                if val is not None:
                    return int(val)
        return 0

    def merge(self, other: TokenUsageCollector) -> None:
        """Merge another collector into this one."""
        for role, role_usage in other.usage_by_role.items():
            self.add(
                role=role,
                provider=role_usage.provider,
                model=role_usage.model,
                usage={
                    "prompt_tokens": role_usage.prompt_tokens,
                    "completion_tokens": role_usage.completion_tokens,
                },
            )

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
            },
        }

    def log_summary(self, message_id: str) -> None:
        """Логировать сводку по usage."""
        if not self.usage_by_role:
            return

        parts = [f"{role}={ru.total_tokens}" for role, ru in self.usage_by_role.items()]
        logger.info(
            "TokenUsage summary: message_id=%s total=%d breakdown=[%s]",
            message_id,
            self.total_tokens,
            ", ".join(parts),
        )
