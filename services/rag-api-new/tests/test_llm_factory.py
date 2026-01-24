"""
Unit тесты для LLM Factory (Этап 1 ТЗ мультипровайдерной архитектуры).

Тестирует:
- parse_llm_id: парсинг формата "provider:model"
- get_provider_info: извлечение provider и model
- LLMFactory: создание и кэширование LLM инстансов
- Валидация credentials
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm import (
    LLMConfigError,
    LLMFactory,
    LLMProvider,
    get_provider_info,
    parse_llm_id,
    reset_llm_factory,
)


class TestParseLLMId:
    """Тесты для parse_llm_id."""

    def test_parse_valid_gigachat(self):
        """Парсинг корректного GigaChat ID."""
        provider, model = parse_llm_id("gigachat:GigaChat-2")
        assert provider == LLMProvider.GIGACHAT
        assert model == "GigaChat-2"

    def test_parse_valid_deepseek(self):
        """Парсинг корректного DeepSeek ID."""
        provider, model = parse_llm_id("deepseek:deepseek-reasoner")
        assert provider == LLMProvider.DEEPSEEK
        assert model == "deepseek-reasoner"

    def test_parse_valid_qwen(self):
        """Парсинг корректного Qwen ID."""
        provider, model = parse_llm_id("qwen:Qwen2.5")
        assert provider == LLMProvider.QWEN
        assert model == "Qwen2.5"

    def test_parse_case_insensitive_provider(self):
        """Provider парсится case-insensitive."""
        provider, model = parse_llm_id("GIGACHAT:Model")
        assert provider == LLMProvider.GIGACHAT

        provider, model = parse_llm_id("DeepSeek:model")
        assert provider == LLMProvider.DEEPSEEK

    def test_parse_model_with_colon(self):
        """Модель может содержать двоеточие."""
        provider, model = parse_llm_id("deepseek:some:model:name")
        assert provider == LLMProvider.DEEPSEEK
        assert model == "some:model:name"

    def test_parse_invalid_format_no_colon(self):
        """Ошибка при отсутствии двоеточия."""
        with pytest.raises(LLMConfigError, match="Invalid LLM ID format"):
            parse_llm_id("gigachat")

    def test_parse_invalid_format_empty(self):
        """Ошибка при пустой строке."""
        with pytest.raises(LLMConfigError, match="Invalid LLM ID format"):
            parse_llm_id("")

    def test_parse_unknown_provider(self):
        """Ошибка при неизвестном провайдере."""
        with pytest.raises(LLMConfigError, match="Unknown provider"):
            parse_llm_id("openai:gpt-4")

    def test_parse_unknown_provider_lists_valid(self):
        """Ошибка содержит список валидных провайдеров."""
        with pytest.raises(LLMConfigError) as exc_info:
            parse_llm_id("claude:opus")

        error_msg = str(exc_info.value)
        assert "gigachat" in error_msg
        assert "deepseek" in error_msg
        assert "qwen" in error_msg


class TestGetProviderInfo:
    """Тесты для get_provider_info."""

    def test_returns_string_tuple(self):
        """Возвращает tuple из строк."""
        provider, model = get_provider_info("deepseek:deepseek-chat")
        assert provider == "deepseek"
        assert model == "deepseek-chat"
        assert isinstance(provider, str)
        assert isinstance(model, str)

    def test_provider_is_lowercase(self):
        """Provider всегда в lowercase."""
        provider, model = get_provider_info("GIGACHAT:Model")
        assert provider == "gigachat"

    def test_model_preserves_case(self):
        """Model сохраняет регистр."""
        provider, model = get_provider_info("qwen:Qwen2.5-Instruct")
        assert model == "Qwen2.5-Instruct"


class TestLLMFactory:
    """Тесты для LLMFactory."""

    def setup_method(self):
        """Сброс singleton перед каждым тестом."""
        reset_llm_factory()

    def test_factory_caches_same_params(self):
        """Фабрика кэширует LLM инстансы с одинаковыми параметрами."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = "test-credentials"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.GigaChat") as mock_gigachat:
            mock_llm = MagicMock()
            mock_gigachat.return_value = mock_llm

            llm1 = factory.create("gigachat:GigaChat-2", temperature=0.2)
            llm2 = factory.create("gigachat:GigaChat-2", temperature=0.2)

            assert llm1 is llm2
            assert mock_gigachat.call_count == 1  # Создан только один раз

    def test_factory_different_temps_different_instances(self):
        """Разные температуры создают разные инстансы."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = "test-credentials"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.GigaChat") as mock_gigachat:
            # Return new MagicMock each call to simulate different instances
            mock_gigachat.side_effect = lambda **kwargs: MagicMock()

            llm1 = factory.create("gigachat:GigaChat-2", temperature=0.0)
            llm2 = factory.create("gigachat:GigaChat-2", temperature=0.5)

            assert llm1 is not llm2
            assert mock_gigachat.call_count == 2

    def test_factory_different_max_tokens_different_instances(self):
        """Разные max_tokens создают разные инстансы."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = "test-credentials"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.GigaChat") as mock_gigachat:
            # Return new MagicMock each call to simulate different instances
            mock_gigachat.side_effect = lambda **kwargs: MagicMock()

            llm1 = factory.create("gigachat:GigaChat-2", temperature=0.2, max_tokens=512)
            llm2 = factory.create("gigachat:GigaChat-2", temperature=0.2, max_tokens=1024)

            assert llm1 is not llm2

    def test_factory_clear_cache(self):
        """clear_cache очищает кэш."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = "test-credentials"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.GigaChat") as mock_gigachat:
            mock_gigachat.return_value = MagicMock()

            factory.create("gigachat:GigaChat-2", temperature=0.2)
            factory.clear_cache()
            factory.create("gigachat:GigaChat-2", temperature=0.2)

            assert mock_gigachat.call_count == 2  # Создан дважды

    def test_missing_gigachat_credentials(self):
        """Ошибка при отсутствии giga_auth_data."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = None

        factory = LLMFactory(settings=mock_settings)

        with pytest.raises(LLMConfigError, match="giga_auth_data"):
            factory.create("gigachat:GigaChat-2", temperature=0.2)

    def test_missing_deepseek_credentials(self):
        """Ошибка при отсутствии deepseek_api_key."""
        mock_settings = MagicMock()
        mock_settings.deepseek_api_key = None

        factory = LLMFactory(settings=mock_settings)

        with pytest.raises(LLMConfigError, match="deepseek_api_key"):
            factory.create("deepseek:deepseek-reasoner", temperature=0.2)

    def test_qwen_no_credentials_required(self):
        """Qwen не требует API ключ (локальный через LiteLLM)."""
        mock_settings = MagicMock()
        mock_settings.litellm_api_key = None
        mock_settings.litellm_base_url = "http://localhost:8005/v1"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()

            # Не должно вызвать ошибку
            llm = factory.create("qwen:Qwen2.5", temperature=0.2)
            assert llm is not None


class TestLLMFactoryProviders:
    """Тесты для создания LLM разных провайдеров."""

    def setup_method(self):
        """Сброс singleton перед каждым тестом."""
        reset_llm_factory()

    def test_create_gigachat(self):
        """Создание GigaChat LLM."""
        mock_settings = MagicMock()
        mock_settings.giga_auth_data = "test-credentials"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.GigaChat") as mock_gigachat:
            mock_llm = MagicMock()
            mock_gigachat.return_value = mock_llm

            llm = factory.create("gigachat:GigaChat-Pro", temperature=0.3, max_tokens=2048)

            mock_gigachat.assert_called_once_with(
                credentials="test-credentials",
                model="GigaChat-Pro",
                temperature=0.3,
                max_tokens=2048,
                verify_ssl_certs=False,
            )
            assert llm is mock_llm

    def test_create_deepseek(self):
        """Создание DeepSeek LLM."""
        mock_settings = MagicMock()
        mock_settings.deepseek_api_key = "sk-test-key"
        mock_settings.deepseek_base_url = "https://api.deepseek.com/v1"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.ChatOpenAI") as mock_openai:
            mock_llm = MagicMock()
            mock_openai.return_value = mock_llm

            llm = factory.create("deepseek:deepseek-reasoner", temperature=0.0)

            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]

            assert call_kwargs["api_key"] == "sk-test-key"
            assert call_kwargs["base_url"] == "https://api.deepseek.com/v1"
            assert call_kwargs["model"] == "deepseek-reasoner"
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["timeout"] == 120  # DeepSeek R1 timeout

    def test_create_qwen(self):
        """Создание Qwen LLM через LiteLLM."""
        mock_settings = MagicMock()
        mock_settings.litellm_api_key = "sk-local"
        mock_settings.litellm_base_url = "http://litellm:4000/v1"

        factory = LLMFactory(settings=mock_settings)

        with patch("app.llm.factory.ChatOpenAI") as mock_openai:
            mock_llm = MagicMock()
            mock_openai.return_value = mock_llm

            llm = factory.create("qwen:Qwen2.5-7B", temperature=0.2)

            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]

            assert call_kwargs["base_url"] == "http://litellm:4000/v1"
            assert call_kwargs["model"] == "Qwen2.5-7B"
            assert call_kwargs["timeout"] == 60  # Standard timeout


class TestLLMProviderEnum:
    """Тесты для LLMProvider enum."""

    def test_provider_values(self):
        """Проверка значений провайдеров."""
        assert LLMProvider.GIGACHAT.value == "gigachat"
        assert LLMProvider.DEEPSEEK.value == "deepseek"
        assert LLMProvider.QWEN.value == "qwen"

    def test_provider_is_string_enum(self):
        """LLMProvider наследует от str."""
        assert isinstance(LLMProvider.GIGACHAT, str)
        assert LLMProvider.GIGACHAT == "gigachat"

    def test_all_providers_count(self):
        """Всего 3 провайдера."""
        assert len(LLMProvider) == 3
