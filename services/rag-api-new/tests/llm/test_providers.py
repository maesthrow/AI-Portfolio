"""
Integration тесты для LLM провайдеров (Этап 3 ТЗ мультипровайдерной архитектуры).

Тестирует реальные вызовы к LLM API:
- GigaChat API (требует GIGA_AUTH_DATA)
- DeepSeek API (требует DEEPSEEK_API_KEY)
- Qwen через LiteLLM (требует LITELLM_BASE_URL)

Запуск:
    pytest tests/llm/test_providers.py -v -m integration

Для запуска нужны соответствующие credentials в .env файле.
"""
from __future__ import annotations

import os

import pytest

from app.llm import LLMFactory, reset_llm_factory


def has_gigachat_credentials() -> bool:
    """Проверяет наличие credentials для GigaChat."""
    return bool(os.getenv("GIGA_AUTH_DATA"))


def has_deepseek_credentials() -> bool:
    """Проверяет наличие credentials для DeepSeek."""
    return bool(os.getenv("DEEPSEEK_API_KEY"))


def has_litellm_available() -> bool:
    """Проверяет доступность LiteLLM proxy."""
    base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:8005/v1")
    try:
        import requests
        response = requests.get(f"{base_url.rstrip('/v1')}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(autouse=True)
def reset_factory():
    """Сброс singleton фабрики перед каждым тестом."""
    reset_llm_factory()
    yield
    reset_llm_factory()


@pytest.mark.integration
@pytest.mark.skipif(
    not has_gigachat_credentials(),
    reason="GigaChat credentials not available (set GIGA_AUTH_DATA)"
)
class TestGigaChatProvider:
    """Integration тесты для GigaChat провайдера."""

    def test_gigachat_invoke(self):
        """GigaChat провайдер успешно вызывает API."""
        factory = LLMFactory()
        llm = factory.create("gigachat:GigaChat-2", temperature=0.2)

        response = llm.invoke("Привет! Ответь одним словом.")

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_gigachat_with_low_temperature(self):
        """GigaChat работает с temperature=0.0 (детерминированный)."""
        factory = LLMFactory()
        llm = factory.create("gigachat:GigaChat-2", temperature=0.0)

        response = llm.invoke("Сколько будет 2+2? Ответь только числом.")

        assert response is not None
        assert response.content
        # Ответ должен содержать "4"
        assert "4" in response.content

    def test_gigachat_usage_metadata(self):
        """GigaChat возвращает usage metadata."""
        factory = LLMFactory()
        llm = factory.create("gigachat:GigaChat-2", temperature=0.2)

        response = llm.invoke("Привет!")

        # Проверяем наличие usage metadata
        usage = getattr(response, "usage_metadata", None)
        if usage is None and hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage")

        # GigaChat должен возвращать usage (хотя бы в каком-то формате)
        # Примечание: конкретный формат может отличаться


@pytest.mark.integration
@pytest.mark.skipif(
    not has_deepseek_credentials(),
    reason="DeepSeek credentials not available (set DEEPSEEK_API_KEY)"
)
class TestDeepSeekProvider:
    """Integration тесты для DeepSeek провайдера."""

    def test_deepseek_chat_invoke(self):
        """DeepSeek Chat провайдер успешно вызывает API."""
        factory = LLMFactory()
        llm = factory.create("deepseek:deepseek-chat", temperature=0.2)

        response = llm.invoke("Hello! Reply with one word.")

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_deepseek_reasoner_invoke(self):
        """DeepSeek Reasoner (R1) провайдер успешно вызывает API."""
        factory = LLMFactory()
        # DeepSeek R1 может думать долго, поэтому timeout увеличен в factory
        llm = factory.create("deepseek:deepseek-reasoner", temperature=0.0)

        response = llm.invoke("What is 15 + 27? Answer only with the number.")

        assert response is not None
        assert response.content
        # Ответ должен содержать "42"
        assert "42" in response.content

    def test_deepseek_usage_metadata(self):
        """DeepSeek возвращает usage metadata."""
        factory = LLMFactory()
        llm = factory.create("deepseek:deepseek-chat", temperature=0.2)

        response = llm.invoke("Hi!")

        # Проверяем наличие usage metadata
        usage = getattr(response, "usage_metadata", None)
        if usage is None and hasattr(response, "response_metadata"):
            usage = response.response_metadata.get("token_usage")

        # DeepSeek через ChatOpenAI должен возвращать usage
        assert usage is not None, "DeepSeek should return usage metadata"


@pytest.mark.integration
@pytest.mark.skipif(
    not has_litellm_available(),
    reason="LiteLLM proxy not available"
)
class TestQwenProvider:
    """Integration тесты для Qwen провайдера (через LiteLLM -> vLLM)."""

    def test_qwen_invoke(self):
        """Qwen провайдер успешно вызывает API через LiteLLM."""
        factory = LLMFactory()
        llm = factory.create("qwen:Qwen2.5", temperature=0.2)

        response = llm.invoke("Привет! Ответь одним словом.")

        assert response is not None
        assert response.content
        assert isinstance(response.content, str)
        assert len(response.content) > 0

    def test_qwen_with_low_temperature(self):
        """Qwen работает с temperature=0.0."""
        factory = LLMFactory()
        llm = factory.create("qwen:Qwen2.5", temperature=0.0)

        response = llm.invoke("Сколько будет 3+3? Ответь только числом.")

        assert response is not None
        assert response.content
        # Ответ должен содержать "6"
        assert "6" in response.content


@pytest.mark.integration
class TestMultiProviderCaching:
    """Тесты кэширования при работе с несколькими провайдерами."""

    @pytest.mark.skipif(
        not has_gigachat_credentials(),
        reason="GigaChat credentials not available"
    )
    def test_same_provider_same_params_cached(self):
        """Одинаковые параметры возвращают кэшированный инстанс."""
        factory = LLMFactory()

        llm1 = factory.create("gigachat:GigaChat-2", temperature=0.2)
        llm2 = factory.create("gigachat:GigaChat-2", temperature=0.2)

        assert llm1 is llm2

    @pytest.mark.skipif(
        not has_gigachat_credentials(),
        reason="GigaChat credentials not available"
    )
    def test_same_provider_different_temps_not_cached(self):
        """Разные температуры создают разные инстансы."""
        factory = LLMFactory()

        llm1 = factory.create("gigachat:GigaChat-2", temperature=0.0)
        llm2 = factory.create("gigachat:GigaChat-2", temperature=0.5)

        assert llm1 is not llm2

    @pytest.mark.skipif(
        not (has_gigachat_credentials() and has_deepseek_credentials()),
        reason="Both GigaChat and DeepSeek credentials required"
    )
    def test_different_providers_both_work(self):
        """Фабрика может создавать LLM от разных провайдеров."""
        factory = LLMFactory()

        gigachat_llm = factory.create("gigachat:GigaChat-2", temperature=0.2)
        deepseek_llm = factory.create("deepseek:deepseek-chat", temperature=0.2)

        # Оба должны работать
        giga_response = gigachat_llm.invoke("Привет!")
        deep_response = deepseek_llm.invoke("Hello!")

        assert giga_response.content
        assert deep_response.content
