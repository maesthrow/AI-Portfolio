"""Tests for switchable embedding provider (TEI / GigaChat)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock heavy external dependencies that may not be installed outside Docker.
# Only adds mocks for packages that aren't already available.
# ---------------------------------------------------------------------------


def _ensure_mock(name: str) -> MagicMock:
    """Register a MagicMock in sys.modules if the real module isn't present."""
    if name in sys.modules and not isinstance(sys.modules[name], MagicMock):
        return sys.modules[name]          # real module — leave it
    if name not in sys.modules:
        sys.modules[name] = MagicMock()
    return sys.modules[name]


# Core external deps used directly by app.deps
_ensure_mock("torch")
_ensure_mock("sentence_transformers")
_ensure_mock("sqlalchemy")

# langchain core
_ensure_mock("langchain")
_ensure_mock("langchain.agents")
_ensure_mock("langchain_core")
_ensure_mock("langchain_core.embeddings")
_ensure_mock("langchain_core.language_models")

# langchain_openai — OpenAIEmbeddings must be a real class for isinstance()
class _FakeOpenAIEmbeddings:
    """Stand-in for OpenAIEmbeddings when langchain_openai isn't installed."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


_oa = _ensure_mock("langchain_openai")
if isinstance(_oa, MagicMock):
    _oa.OpenAIEmbeddings = _FakeOpenAIEmbeddings

# langchain_postgres & langchain_gigachat
_ensure_mock("langchain_postgres")
_ensure_mock("langchain_gigachat")

# langgraph (required transitively via app.agent.graph → graph_state)
for _lg in (
    "langgraph",
    "langgraph.graph",
    "langgraph.graph.state",
    "langgraph.graph.message",
    "langgraph.prebuilt",
    "langgraph.checkpoint",
    "langgraph.checkpoint.memory",
):
    _ensure_mock(_lg)

# ---------------------------------------------------------------------------


class TestSettings:
    """Test embedding_provider settings field."""

    def test_default_provider_is_tei(self):
        from app.settings import Settings

        s = Settings(
            database_url="postgresql+psycopg://u:p@localhost:5432/db",
            redis_url="redis://localhost:6379/0",
        )
        assert s.embedding_provider == "tei"

    def test_gigachat_provider_accepted(self):
        from app.settings import Settings

        s = Settings(
            embedding_provider="gigachat",
            database_url="postgresql+psycopg://u:p@localhost:5432/db",
            redis_url="redis://localhost:6379/0",
        )
        assert s.embedding_provider == "gigachat"


class TestEmbeddingsFactory:
    """Test embeddings() factory switching."""

    def _make_settings(self, **overrides):
        mock = MagicMock()
        mock.embedding_provider = overrides.get("embedding_provider", "tei")
        mock.embedding_model = overrides.get("embedding_model", "text-embedding-3-large")
        mock.tei_base_url = overrides.get("tei_base_url", "http://tei:80/v1")
        mock.giga_auth_data = overrides.get("giga_auth_data", None)
        return mock

    def test_gigachat_provider_requires_auth(self):
        """EMBEDDING_PROVIDER=gigachat without GIGA_AUTH_DATA raises RuntimeError."""
        import app.deps as deps

        mock_s = self._make_settings(embedding_provider="gigachat", giga_auth_data=None)
        deps.embeddings.cache_clear()
        try:
            with patch.object(deps, "settings", return_value=mock_s):
                with pytest.raises(RuntimeError, match="GIGA_AUTH_DATA"):
                    deps.embeddings()
        finally:
            deps.embeddings.cache_clear()

    def test_tei_provider_creates_openai_embeddings(self):
        """EMBEDDING_PROVIDER=tei returns OpenAIEmbeddings."""
        from langchain_openai import OpenAIEmbeddings
        import app.deps as deps

        mock_s = self._make_settings(embedding_provider="tei")
        deps.embeddings.cache_clear()
        try:
            with patch.object(deps, "settings", return_value=mock_s):
                result = deps.embeddings()
                assert isinstance(result, OpenAIEmbeddings)
        finally:
            deps.embeddings.cache_clear()

    def test_gigachat_provider_creates_gigachat_embeddings(self):
        """EMBEDDING_PROVIDER=gigachat with valid creds returns GigaChatEmbeddings."""
        import app.deps as deps

        mock_s = self._make_settings(
            embedding_provider="gigachat",
            giga_auth_data="dGVzdDp0ZXN0",
            embedding_model="Embeddings",
        )
        mock_gc_emb = MagicMock()
        deps.embeddings.cache_clear()
        try:
            with (
                patch.object(deps, "settings", return_value=mock_s),
                patch("langchain_gigachat.GigaChatEmbeddings", return_value=mock_gc_emb) as mock_cls,
            ):
                result = deps.embeddings()
                assert result is mock_gc_emb
                mock_cls.assert_called_once_with(
                    credentials="dGVzdDp0ZXN0",
                    model="Embeddings",
                    verify_ssl_certs=False,
                    timeout=60,
                )
        finally:
            deps.embeddings.cache_clear()


class TestDimensionDetection:
    """Test _detect_embedding_dim()."""

    def test_detect_embedding_dim(self):
        """Returns length of test embedding vector."""
        import app.deps as deps

        mock_emb = MagicMock()
        mock_emb.embed_query.return_value = [0.1] * 1024

        old_dim = deps._embedding_dim
        deps._embedding_dim = None
        try:
            with patch.object(deps, "embeddings", return_value=mock_emb):
                dim = deps._detect_embedding_dim()
                assert dim == 1024
                mock_emb.embed_query.assert_called_once_with("test")
        finally:
            deps._embedding_dim = old_dim

    def test_detect_embedding_dim_cached(self):
        """Returns cached value without calling embed_query again."""
        import app.deps as deps

        old_dim = deps._embedding_dim
        deps._embedding_dim = 768
        try:
            dim = deps._detect_embedding_dim()
            assert dim == 768
        finally:
            deps._embedding_dim = old_dim


class TestGetEmbeddingDim:
    """Test get_embedding_dim() getter."""

    def test_returns_none_before_detection(self):
        import app.deps as deps

        old_dim = deps._embedding_dim
        deps._embedding_dim = None
        try:
            assert deps.get_embedding_dim() is None
        finally:
            deps._embedding_dim = old_dim

    def test_returns_cached_value(self):
        import app.deps as deps

        old_dim = deps._embedding_dim
        deps._embedding_dim = 1024
        try:
            assert deps.get_embedding_dim() == 1024
        finally:
            deps._embedding_dim = old_dim
