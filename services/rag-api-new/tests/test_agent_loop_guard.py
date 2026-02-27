"""Tests for anti-loop measures in the RAG agent pipeline.

Validates:
- System prompt contains explicit anti-loop instructions (FR-001)
- Tool result contains only 'answer' + 'found' keys (FR-002)
- Safety-net settings: agent_timeout=90, recursion_limit=6 (FR-003, FR-004)

NOTE: Uses file-based parsing (not module imports) to avoid requiring
heavy dependencies (langchain, fastapi) in the local test environment.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

# Base path for all source files
_APP_DIR = Path(__file__).parent.parent / "app"


class TestAgentSystemPrompt:
    """Verify system prompt contains anti-loop instructions (FR-001)."""

    @staticmethod
    def _read_prompt() -> str:
        """Extract AGENT_SYSTEM_PROMPT string from graph.py source."""
        source = (_APP_DIR / "agent" / "graph.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "AGENT_SYSTEM_PROMPT"
                and isinstance(node.value, (ast.Constant, ast.JoinedStr))
            ):
                if isinstance(node.value, ast.Constant):
                    return node.value.value
        raise AssertionError("AGENT_SYSTEM_PROMPT not found in graph.py")

    def test_prompt_forbids_repeated_tool_calls(self):
        """System prompt MUST explicitly forbid repeated tool invocations."""
        prompt = self._read_prompt()
        assert "НИКОГДА не вызывай portfolio_rag_tool повторно" in prompt

    def test_prompt_requires_immediate_response(self):
        """System prompt MUST instruct to respond immediately after tool result."""
        prompt = self._read_prompt()
        assert "СРАЗУ отвечай пользователю" in prompt


class TestToolResultReduction:
    """Verify tool_result contains only answer + found (FR-002, SC-004).

    Uses AST parsing of rag_tool.py to ensure all return dicts inside
    portfolio_rag_tool have exactly {'answer', 'found'} keys.
    This catches regressions if someone adds extra fields back.
    """

    def test_tool_result_has_only_answer_and_found(self):
        """All return dicts in portfolio_rag_tool MUST have exactly {answer, found}."""
        source_path = _APP_DIR / "agent" / "rag_tool.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))

        # Find the portfolio_rag_tool async function
        func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "portfolio_rag_tool":
                func = node
                break

        assert func is not None, "portfolio_rag_tool function not found in rag_tool.py"

        # Collect all return statements that return a dict literal
        allowed_keys = {"answer", "found"}
        dict_returns_found = 0

        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                keys = set()
                for key in node.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
                dict_returns_found += 1
                assert keys == allowed_keys, (
                    f"Tool return dict has unexpected keys: {keys}. "
                    f"Expected exactly {allowed_keys}."
                )

        assert dict_returns_found >= 2, (
            f"Expected at least 2 dict return statements (success + error), "
            f"found {dict_returns_found}"
        )


class TestSafetyNetSettings:
    """Verify recursion_limit and timeout settings (FR-003, FR-004)."""

    def test_agent_timeout_default(self):
        """Default agent timeout MUST be 90 seconds."""
        from app.settings import Settings

        s = Settings()
        assert s.agent_timeout == 90

    def test_recursion_limit_is_6(self):
        """Recursion limit in chat_stream config MUST be 6."""
        source = (_APP_DIR / "routers" / "chat.py").read_text(encoding="utf-8")
        match = re.search(r'"recursion_limit":\s*(\d+)', source)
        assert match is not None, "recursion_limit not found in chat.py source"
        assert int(match.group(1)) == 6, (
            f"recursion_limit is {match.group(1)}, expected 6"
        )
