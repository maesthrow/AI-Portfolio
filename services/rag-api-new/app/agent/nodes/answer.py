"""
Answer nodes for RAG agent.

Two nodes:
- answer_deterministic_node: For simple intents (not_found, contacts, technology_usage)
- answer_llm_node: For complex intents requiring natural language generation

The routing between them is handled by answer_router edge.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.answer.prompts import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_TEMPLATE,
    STYLE_INSTRUCTIONS,
    NOT_FOUND_RESPONSE,
    NOT_FOUND_BY_INTENT,
)
from app.agent.answer.answer_llm import AnswerLLM
from app.agent.render.renderer import RenderEngine, post_process_answer
from app.agent.planner.schemas import FactItem, FactsPayload
from app.utils.logging_utils import truncate_text

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def answer_deterministic_node(state: RAGState) -> dict:
    """
    Generate deterministic answer without LLM.

    Used for:
    - not_found: No facts available
    - contacts: Simple list of contacts
    - technology_usage: List of projects using a technology

    Args:
        state: Current RAGState with normalized_facts, plan, question

    Returns:
        Partial state update with:
        - answer: Generated answer text
        - answer_is_deterministic: True
    """
    normalized_facts = state.get("normalized_facts", [])
    plan = state.get("plan")
    question = state.get("question", "")

    logger.info(
        f"AnswerDeterministic: facts={len(normalized_facts)}, "
        f"intents={[i.value for i in (plan.intents or [])] if plan else []}"
    )

    # Handle not found case
    if not normalized_facts:
        intent = plan.intents[0].value if plan and plan.intents else "general_unstructured"
        answer = NOT_FOUND_BY_INTENT.get(intent, NOT_FOUND_RESPONSE)
        logger.info(f"AnswerDeterministic: not_found, intent={intent}")
        return {
            "answer": answer,
            "answer_is_deterministic": True,
        }

    # Try to answer technology_usage deterministically
    if plan and plan.intents:
        intent = plan.intents[0].value
        if intent == "technology_usage":
            answer = _answer_technology_usage(question, normalized_facts)
            if answer:
                logger.info(f"AnswerDeterministic: technology_usage answer generated")
                return {
                    "answer": answer,
                    "answer_is_deterministic": True,
                }

        # Contacts are simple lists
        if intent == "contacts":
            answer = _answer_contacts(normalized_facts)
            if answer:
                logger.info(f"AnswerDeterministic: contacts answer generated")
                return {
                    "answer": answer,
                    "answer_is_deterministic": True,
                }

    # Fallback: render facts as simple list
    renderer = RenderEngine()
    fact_items = [
        FactItem(type=f.type, text=f.text, metadata=f.metadata, source_id=f.entity_id)
        for f in normalized_facts
    ]
    answer = renderer.render(facts=fact_items, style=None, intents=None)

    logger.info(f"AnswerDeterministic: fallback render")
    return {
        "answer": answer,
        "answer_is_deterministic": True,
    }


def answer_llm_node(state: RAGState) -> dict:
    """
    Generate natural language answer using LLM.

    Used for complex intents that require natural phrasing:
    - project_details
    - experience_summary
    - general_unstructured
    - etc.

    Args:
        state: Current RAGState with normalized_facts, plan, question

    Returns:
        Partial state update with:
        - answer: Generated answer text
        - answer_is_deterministic: False
    """
    normalized_facts = state.get("normalized_facts", [])
    plan = state.get("plan")
    question = state.get("question", "")

    logger.info(
        f"AnswerLLM: facts={len(normalized_facts)}, question={question[:50]}..."
    )

    # Convert normalized_facts to FactItem for renderer
    fact_items = [
        FactItem(type=f.type, text=f.text, metadata=f.metadata, source_id=f.entity_id)
        for f in normalized_facts
    ]

    # Render facts
    renderer = RenderEngine()
    intents = plan.intents if plan else None
    render_style = plan.render_style if plan else None
    rendered_facts = renderer.render(facts=fact_items, style=render_style, intents=intents)

    # Add evidence_text as additional context if rendered_facts is short
    evidence_text = state.get("evidence_text", "")
    if evidence_text and len(rendered_facts) < 200:
        rendered_facts = f"{rendered_facts}\n\n--- Дополнительный контекст ---\n{evidence_text}"
        logger.info(f"AnswerLLM: added evidence_text ({len(evidence_text)} chars) as fallback")

    if not rendered_facts:
        # Fallback to not found
        intent = plan.intents[0].value if plan and plan.intents else "general_unstructured"
        answer = NOT_FOUND_BY_INTENT.get(intent, NOT_FOUND_RESPONSE)
        return {
            "answer": answer,
            "answer_is_deterministic": True,
        }

    # Get style instruction
    style_instruction = _get_style_instruction(plan)

    # Build context note from session (for follow-up questions)
    context_note = _build_context_note(state)

    # Build user prompt
    user_prompt = ANSWER_USER_TEMPLATE.format(
        question=question,
        facts=rendered_facts,
        style_instruction=style_instruction,
        warnings=context_note,
    )

    logger.info(
        f"AnswerLLM prompt: facts_len={len(rendered_facts)}, "
        f"style={style_instruction[:30]}..."
    )

    # DEBUG: Log rendered facts to see what's being passed to LLM
    logger.info(f"AnswerLLM rendered_facts:\n{rendered_facts[:1000]}")

    # Generate answer
    messages = [
        SystemMessage(content=ANSWER_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        # Lazy import to avoid circular imports
        from app.deps import answer_llm
        llm = answer_llm()
        response = llm.invoke(messages)
        raw_answer = response.content.strip()

        # Post-process to remove artifacts
        cleaned_answer, warnings = post_process_answer(raw_answer)

        if warnings:
            logger.warning(f"AnswerLLM post-process warnings: {warnings}")

        logger.info(
            f"AnswerLLM result: len={len(cleaned_answer)}, "
            f"preview={truncate_text(cleaned_answer, limit=200)}"
        )

        return {
            "answer": cleaned_answer,
            "answer_is_deterministic": False,
        }

    except Exception as e:
        logger.error(f"AnswerLLM failed: {e}")
        # Return rendered facts as fallback
        return {
            "answer": rendered_facts,
            "answer_is_deterministic": True,
        }


def _get_style_instruction(plan) -> str:
    """Get style instruction from plan."""
    instructions = []

    if plan:
        # Add render style instruction
        if plan.render_style:
            render_key = plan.render_style.value
            if render_key in STYLE_INSTRUCTIONS:
                instructions.append(STYLE_INSTRUCTIONS[render_key])

        # Add answer style instruction
        if plan.answer_style:
            answer_key = plan.answer_style.value
            if answer_key in STYLE_INSTRUCTIONS:
                instructions.append(STYLE_INSTRUCTIONS[answer_key])

    return "; ".join(instructions) if instructions else "Естественный русский язык"


def _answer_technology_usage(question: str, facts: list) -> str | None:
    """Deterministic answer for technology usage questions."""
    tech_to_projects: dict[str, list[str]] = {}

    for fact in facts:
        md = fact.metadata or {}

        # Get technology name
        tech_name = md.get("technology") or md.get("name")
        if fact.type in ("technology", "technology_usage") and tech_name:
            # Get project
            project = md.get("project") or md.get("project_name")
            if project:
                tech_to_projects.setdefault(str(tech_name), []).append(str(project))

    if not tech_to_projects:
        return None

    # Build answer
    lines = []
    for tech, projects in sorted(tech_to_projects.items()):
        unique_projects = list(dict.fromkeys(projects))  # dedupe preserving order
        if len(tech_to_projects) == 1:
            lines.append(f"Дмитрий применял {tech} в проектах:")
        else:
            lines.append(f"{tech}:")
        lines.extend([f"- {p}" for p in unique_projects])

    return "\n".join(lines) if lines else None


def _build_context_note(state: "RAGState") -> str:
    """Build context note from session state for follow-up questions."""
    validated_entities = state.get("validated_entities", {})
    if not validated_entities:
        return ""

    project = validated_entities.get("project")
    company = validated_entities.get("company")
    from_session = validated_entities.get("from_session", False)

    # Only add context note for follow-up questions (from_session=True)
    if not from_session:
        return ""

    notes = []
    if project:
        notes.append(f"проект: {project}")
    if company:
        notes.append(f"компания: {company}")

    if notes:
        return f"КОНТЕКСТ ВОПРОСА (обязательно упомяни в ответе): {', '.join(notes)}"

    return ""


def _answer_contacts(facts: list) -> str | None:
    """Deterministic answer for contacts."""
    contacts = []

    for fact in facts:
        md = fact.metadata or {}
        kind = md.get("kind", "")
        value = md.get("value", "")
        url = md.get("url", "")

        if kind and (value or url):
            if url:
                contacts.append(f"- {kind}: {url}")
            else:
                contacts.append(f"- {kind}: {value}")

    if not contacts:
        return None

    return "Контакты Дмитрия:\n" + "\n".join(contacts)
