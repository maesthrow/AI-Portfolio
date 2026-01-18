"""
Grounding verifier node for RAG agent.

Checks that the generated answer only mentions entities
that exist in the FactBundle.

This is a deterministic node (no LLM call).
Prevents hallucinations by detecting:
- Speculation markers (probably, possibly, etc.)
- Entities not present in FactBundle
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.grounding.grounding_verifier import GroundingVerifier
from app.agent.planner.schemas_v3 import FactBundle, GroundingResult

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def grounding_verifier_node(state: RAGState) -> dict:
    """
    Verify that answer is grounded in facts.

    Checks:
    1. No speculation markers (probably, possibly, etc.)
    2. All mentioned entities exist in FactBundle
    3. Calculates confidence and suggests action

    Actions:
    - accept: Answer is fully grounded
    - rewrite: Some entities are ungrounded, need LLM rewrite
    - refuse: Too many ungrounded entities, return safe response

    Args:
        state: Current RAGState with answer and fact_bundle

    Returns:
        Partial state update with:
        - grounding_result: GroundingResult object
        - grounding_action: "accept" | "rewrite" | "refuse"
    """
    answer = state.get("answer", "")
    fact_bundle = state.get("fact_bundle")
    answer_is_deterministic = state.get("answer_is_deterministic", False)

    # Skip grounding for deterministic answers (they're already grounded)
    if answer_is_deterministic:
        logger.info("Grounding: skipping for deterministic answer")
        return {
            "grounding_result": GroundingResult(
                grounded=True,
                confidence=1.0,
                action="accept",
            ),
            "grounding_action": "accept",
        }

    if not answer:
        logger.info("Grounding: empty answer, accepting")
        return {
            "grounding_result": GroundingResult(
                grounded=True,
                confidence=1.0,
                action="accept",
            ),
            "grounding_action": "accept",
        }

    # Create empty bundle if none provided
    if not fact_bundle:
        fact_bundle = FactBundle(
            facts=[],
            technologies=[],
            companies=[],
            projects=[],
            roles=[],
            dates=[],
        )

    logger.info(
        f"Grounding: verifying answer len={len(answer)}, "
        f"bundle: techs={len(fact_bundle.technologies)}, "
        f"companies={len(fact_bundle.companies)}, "
        f"projects={len(fact_bundle.projects)}"
    )

    verifier = GroundingVerifier()
    result = verifier.verify(answer, fact_bundle)

    logger.info(
        f"Grounding result: grounded={result.grounded}, "
        f"confidence={result.confidence:.2f}, action={result.action}, "
        f"ungrounded={result.ungrounded_entities}"
    )

    return {
        "grounding_result": result,
        "grounding_action": result.action,
    }
