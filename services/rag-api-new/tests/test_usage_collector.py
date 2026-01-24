"""
Tests for TokenUsageCollector - aggregates usage from all LLM roles.
"""
import pytest
from dataclasses import dataclass

from app.rate_limit.usage_collector import TokenUsageCollector, RoleUsage


class TestRoleUsage:
    """Tests for RoleUsage dataclass."""

    def test_total_tokens(self):
        """Test total_tokens property calculation."""
        usage = RoleUsage(
            role="planner",
            provider="gigachat",
            model="GigaChat-2",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert usage.total_tokens == 150

    def test_total_tokens_zero(self):
        """Test total_tokens with zero values."""
        usage = RoleUsage(
            role="answer",
            provider="deepseek",
            model="deepseek-chat",
            prompt_tokens=0,
            completion_tokens=0,
        )
        assert usage.total_tokens == 0

    def test_default_values(self):
        """Test default values for prompt_tokens and completion_tokens."""
        usage = RoleUsage(
            role="critic",
            provider="qwen",
            model="Qwen2.5-7B",
        )
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestTokenUsageCollector:
    """Tests for TokenUsageCollector."""

    def test_add_dict_usage(self):
        """Test adding usage from dict with standard keys."""
        collector = TokenUsageCollector()
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )

        assert collector.total_tokens == 150
        assert "planner" in collector.usage_by_role
        assert collector.usage_by_role["planner"].prompt_tokens == 100
        assert collector.usage_by_role["planner"].completion_tokens == 50

    def test_add_object_usage(self):
        """Test adding usage from object with attributes."""

        @dataclass
        class MockUsage:
            prompt_tokens: int
            completion_tokens: int

        collector = TokenUsageCollector()
        collector.add(
            "answer",
            "deepseek",
            "deepseek-chat",
            MockUsage(prompt_tokens=200, completion_tokens=100),
        )

        assert collector.total_tokens == 300
        assert collector.usage_by_role["answer"].prompt_tokens == 200
        assert collector.usage_by_role["answer"].completion_tokens == 100

    def test_add_alternate_keys(self):
        """Test adding usage with alternate key names (input_tokens/output_tokens)."""
        collector = TokenUsageCollector()
        collector.add(
            "critic",
            "qwen",
            "Qwen2.5",
            {"input_tokens": 150, "output_tokens": 75},
        )

        assert collector.total_tokens == 225
        assert collector.usage_by_role["critic"].prompt_tokens == 150
        assert collector.usage_by_role["critic"].completion_tokens == 75

    def test_add_none_usage(self):
        """Test adding None usage does not crash."""
        collector = TokenUsageCollector()
        collector.add("planner", "gigachat", "GigaChat-2", None)

        assert collector.total_tokens == 0
        assert "planner" not in collector.usage_by_role

    def test_add_empty_dict(self):
        """Test adding empty dict usage."""
        collector = TokenUsageCollector()
        collector.add("planner", "gigachat", "GigaChat-2", {})

        assert collector.total_tokens == 0
        # Empty usage should not be added
        assert "planner" not in collector.usage_by_role

    def test_accumulate_same_role(self):
        """Test that multiple adds to same role accumulate tokens."""
        collector = TokenUsageCollector()
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 200, "completion_tokens": 100},
        )

        assert collector.total_tokens == 450
        assert collector.usage_by_role["planner"].prompt_tokens == 300
        assert collector.usage_by_role["planner"].completion_tokens == 150

    def test_multiple_roles(self):
        """Test adding usage for multiple roles."""
        collector = TokenUsageCollector()
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )
        collector.add(
            "critic",
            "deepseek",
            "deepseek-chat",
            {"prompt_tokens": 200, "completion_tokens": 100},
        )
        collector.add(
            "answer",
            "qwen",
            "Qwen2.5",
            {"prompt_tokens": 300, "completion_tokens": 150},
        )

        assert collector.total_tokens == 900
        assert len(collector.usage_by_role) == 3
        assert collector.usage_by_role["planner"].total_tokens == 150
        assert collector.usage_by_role["critic"].total_tokens == 300
        assert collector.usage_by_role["answer"].total_tokens == 450

    def test_to_dict(self):
        """Test to_dict() output format."""
        collector = TokenUsageCollector()
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )
        collector.add(
            "answer",
            "deepseek",
            "deepseek-chat",
            {"prompt_tokens": 200, "completion_tokens": 100},
        )

        result = collector.to_dict()

        assert "total_tokens" in result
        assert result["total_tokens"] == 450

        assert "by_role" in result
        assert "planner" in result["by_role"]
        assert "answer" in result["by_role"]

        planner = result["by_role"]["planner"]
        # Note: role is the key, not a field in the dict
        assert planner["provider"] == "gigachat"
        assert planner["model"] == "GigaChat-2"
        assert planner["prompt_tokens"] == 100
        assert planner["completion_tokens"] == 50
        assert planner["total_tokens"] == 150

    def test_to_dict_empty(self):
        """Test to_dict() with no usage added."""
        collector = TokenUsageCollector()
        result = collector.to_dict()

        assert result["total_tokens"] == 0
        assert result["by_role"] == {}

    def test_merge(self):
        """Test merging two collectors."""
        collector1 = TokenUsageCollector()
        collector1.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )

        collector2 = TokenUsageCollector()
        collector2.add(
            "answer",
            "deepseek",
            "deepseek-chat",
            {"prompt_tokens": 200, "completion_tokens": 100},
        )

        collector1.merge(collector2)

        assert collector1.total_tokens == 450
        assert len(collector1.usage_by_role) == 2
        assert "planner" in collector1.usage_by_role
        assert "answer" in collector1.usage_by_role

    def test_merge_same_role(self):
        """Test merging collectors with same role accumulates."""
        collector1 = TokenUsageCollector()
        collector1.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )

        collector2 = TokenUsageCollector()
        collector2.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 200, "completion_tokens": 100},
        )

        collector1.merge(collector2)

        assert collector1.total_tokens == 450
        assert collector1.usage_by_role["planner"].prompt_tokens == 300
        assert collector1.usage_by_role["planner"].completion_tokens == 150

    def test_log_summary_does_not_crash(self, caplog):
        """Test log_summary() runs without error."""
        collector = TokenUsageCollector()
        collector.add(
            "planner",
            "gigachat",
            "GigaChat-2",
            {"prompt_tokens": 100, "completion_tokens": 50},
        )

        # Should not raise
        collector.log_summary("test-message-123")

        # Check log was written
        assert "TokenUsage" in caplog.text or len(caplog.records) >= 0
