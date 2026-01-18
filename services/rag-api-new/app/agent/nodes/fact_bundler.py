"""
FactBundler node for RAG agent.

Extracts named entities from normalized facts for grounding verification.
Creates FactBundle with:
- technologies: All mentioned technology names
- companies: All mentioned company names
- projects: All mentioned project names
- roles: All mentioned role titles
- dates: All mentioned dates/periods

This is a deterministic node (no LLM call).
The FactBundle is used by grounding_verifier to check for hallucinations.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.normalizer.fact_bundle import FactBundleBuilder
from app.agent.planner.schemas import FactItem

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def fact_bundler_node(state: RAGState) -> dict:
    """
    Build FactBundle from normalized facts.

    Extracts all named entities for grounding verification.
    Any entity mentioned in the answer must exist in the FactBundle.

    Args:
        state: Current RAGState with normalized_facts

    Returns:
        Partial state update with:
        - fact_bundle: FactBundle with extracted entities
    """
    normalized_facts = state.get("normalized_facts", [])

    if not normalized_facts:
        logger.info("FactBundler: no facts to process")
        from app.agent.planner.schemas_v3 import FactBundle
        return {
            "fact_bundle": FactBundle(
                facts=[],
                technologies=[],
                companies=[],
                projects=[],
                roles=[],
                dates=[],
            ),
        }

    # Convert FactBundleItem back to FactItem for the builder
    # (builder expects FactItem, normalized_facts are FactBundleItem)
    fact_items = []
    for nf in normalized_facts:
        fact_items.append(FactItem(
            type=nf.type,
            text=nf.text,
            metadata=nf.metadata,
            source_id=nf.entity_id,
        ))

    logger.info(f"FactBundler processing: facts={len(fact_items)}")

    builder = FactBundleBuilder()
    bundle = builder.build(fact_items)

    logger.info(
        f"FactBundler result: technologies={len(bundle.technologies)}, "
        f"companies={len(bundle.companies)}, projects={len(bundle.projects)}, "
        f"roles={len(bundle.roles)}, dates={len(bundle.dates)}"
    )

    return {
        "fact_bundle": bundle,
    }
