"""
Identity question handling module.

Semantic matching + LLM response for "кто ты", "ты кто" style questions.
"""
from .classifier import is_identity_question, generate_identity_response

__all__ = ["is_identity_question", "generate_identity_response"]
