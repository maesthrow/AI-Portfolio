"""
Answer module - LLM-based answer generation.

Generates user-facing answers from FactsPayload with strict rules.
"""
from .answer_llm import AnswerLLM

__all__ = ["AnswerLLM"]
