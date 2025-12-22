"""Schemas for ScopeGuard module."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScopeDecision(BaseModel):
    """
    Result of ScopeGuard evaluation.

    Determines if question is within portfolio scope.
    """
    in_scope: bool = Field(
        description="Whether question is about the portfolio"
    )
    reason: str = Field(
        default="",
        description="Reason for decision (for debugging)"
    )
    suggested_prompts: list[str] = Field(
        default_factory=list,
        description="Suggested portfolio questions if out of scope"
    )
    category: Literal["portfolio", "small_talk", "off_topic", "harmful"] = Field(
        default="portfolio",
        description="Question category"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "in_scope": False,
                "reason": "Request for fairy tale - not portfolio related",
                "suggested_prompts": [
                    "Какие проекты есть в портфолио?",
                    "Какие технологии использует Дмитрий?",
                    "Расскажи про опыт работы"
                ],
                "category": "off_topic"
            }
        }
