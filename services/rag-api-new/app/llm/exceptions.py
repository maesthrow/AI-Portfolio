"""
LLM Exceptions - исключения для мультипровайдерной архитектуры.
"""


class LLMConfigError(Exception):
    """
    Ошибка конфигурации LLM.

    Возникает при:
    - Неверном формате llm_id (ожидается "provider:model")
    - Неизвестном провайдере
    - Отсутствующих credentials для провайдера
    """

    pass


class LLMProviderError(Exception):
    """
    Ошибка провайдера LLM.

    Возникает при:
    - Недоступности API провайдера
    - Timeout при запросе
    - Ошибках аутентификации runtime
    """

    pass
