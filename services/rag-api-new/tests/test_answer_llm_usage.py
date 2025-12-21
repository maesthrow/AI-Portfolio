from __future__ import annotations

from dataclasses import dataclass

import pytest

pytest.importorskip("langchain_core")

from app.agent.answer.answer_llm import AnswerLLM
from app.agent.planner.schemas import FactsPayload, IntentV2, RenderStyle, AnswerStyle
from app.agent.tools.portfolio_search_tool import _evidence_to_facts


@dataclass
class _LLMResponse:
    content: str


class _DummyLLM:
    def __init__(self, content: str | None = None, fail_if_called: bool = False):
        self._content = content or ""
        self._fail = fail_if_called

    def invoke(self, _messages):
        if self._fail:
            raise AssertionError("LLM invoke() must not be called for deterministic path")
        return _LLMResponse(content=self._content)


EVIDENCE = (
    "[technology] psycopg: psycopg\n\n"
    "[technology] RAG: RAG\n"
    "Используется в: t2 — Нейросети, AI-Portfolio\n\n"
    "[technology] ReAct: ReAct\n"
    "Используется в: ReAct-Agent\n"
)


def test_evidence_to_facts_parses_blocks():
    facts = _evidence_to_facts(EVIDENCE)
    assert len(facts) >= 2
    assert any(f.type == "technology" for f in facts)
    assert any("Используется в:" in f.text for f in facts)


def test_answer_llm_technology_usage_is_deterministic():
    payload = FactsPayload(
        found=True,
        items=[],
        meta={"coverage": 0.85, "evidence": EVIDENCE},
        query="Где применял RAG?",
        intents=[IntentV2.TECHNOLOGY_USAGE],
        render_style=RenderStyle.GROUPED_BULLETS,
        answer_style=AnswerStyle.NATURAL_RU,
    )

    llm = _DummyLLM(fail_if_called=True)
    answer = AnswerLLM(llm).generate(payload)

    assert "Дмитрий" in answer
    assert "RAG" in answer
    assert "t2 — Нейросети" in answer
    assert "AI-Portfolio" in answer


def test_answer_llm_recovers_when_llm_returns_not_found():
    payload = FactsPayload(
        found=True,
        items=_evidence_to_facts(EVIDENCE),
        meta={"coverage": 0.85, "evidence": EVIDENCE},
        query="Где применял RAG?",
        intents=[IntentV2.TECHNOLOGY_USAGE, IntentV2.GENERAL_UNSTRUCTURED],
        render_style=RenderStyle.GROUPED_BULLETS,
        answer_style=AnswerStyle.NATURAL_RU,
    )

    llm = _DummyLLM(content="Такой информации нет в портфолио.")
    answer = AnswerLLM(llm).generate(payload)

    assert "RAG" in answer
    assert "t2 — Нейросети" in answer
    assert "AI-Portfolio" in answer
