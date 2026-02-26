"""
Agent Tools - full LLM-based RAG pipeline with hardening.

Implements the enhanced pipeline:
1. Planner LLM -> Executor -> Normalizer
2. FactBundle extraction for grounding
3. Answer LLM -> GroundingVerifier

Note: Off-topic rejection is handled by agent's system prompt (see graph.py).
Agent decides whether to call this tool or respond directly.
"""
from __future__ import annotations

import asyncio
import logging
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

from ..deps import settings
from ..llm import get_provider_info
from ..rate_limit import TokenUsageCollector
from ..utils.logging_utils import truncate_text

logger = logging.getLogger(__name__)


def _emit_status(stage: str, text: str, config: RunnableConfig) -> None:
    """Put a pipeline status event onto the queue from config.

    Uses an asyncio.Queue passed via config["configurable"]["_status_queue"]
    to deliver status events to the streaming response in chat.py.
    This bypasses the LangChain event system entirely for reliability.
    Failures are silently ignored to never break the RAG pipeline.
    """
    queue = (config.get("configurable") or {}).get("_status_queue")
    if queue is None:
        return
    try:
        queue.put_nowait({"stage": stage, "text": text})
    except Exception:
        pass


@tool("portfolio_rag_tool")
async def portfolio_rag_tool(question: str, *, config: RunnableConfig) -> dict:
    """
    Полноценный RAG-инструмент с LLM-планированием и защитой от галлюцинаций.

    Улучшенный пайплайн (TZ v3):
    1. Planner LLM анализирует вопрос и создаёт QueryPlan
    2. Executor выполняет tool_calls и собирает факты
    3. Normalizer + FactBundle - детерминированная фильтрация
    4. Answer LLM генерирует ответ
    5. GroundingVerifier - проверка на галлюцинации

    NOTE: Контроль темы (off-topic rejection) выполняется агентом до вызова этого инструмента.
    Агент сам решает вызывать ли этот инструмент или ответить напрямую (приветствия, оффтоп).

    Используй для любых вопросов о портфолио:
    - проекты, компании, технологии
    - опыт работы, достижения
    - контакты, навыки

    Args:
        question: Вопрос о портфолио на русском или английском

    Returns:
        Словарь с полями:
        - answer: финальный ответ пользователю
        - rendered_facts: отформатированные факты
        - sources: источники информации
        - confidence: уверенность
        - found: найдены ли данные
        - intents: определённые намерения
    """
    logger.info("portfolio_rag_tool: question=%r", question[:100])

    # Import dependencies
    from ..deps import planner_llm, answer_llm, critic_llm
    from .planner import PlannerLLM
    from .executor import PlanExecutor
    from .render import RenderEngine
    from .answer import AnswerLLM
    from .critic import CriticLLM, CriticDecision
    from .tools.portfolio_search_tool import execute_portfolio_search
    from .planner.schemas import SourceInfo
    from .normalizer import FactNormalizer
    from .normalizer.fact_bundle import build_fact_bundle
    from .grounding import GroundingVerifier

    # Usage collector for rate limiting
    collector = TokenUsageCollector()

    try:
        # 1. Plan (shortcut -> cache -> LLM fallback)
        from ..cache import try_plan_fast, get_plan_with_cache

        # Fast path: shortcut + cache (<5ms) — no "planning" status
        plan, plan_source = await asyncio.to_thread(try_plan_fast, question)
        planner_usage = None

        if not plan:
            # Slow path: LLM planner needed — show "planning" status
            _emit_status("planning", "Составляю план поиска...", config)
            plan, plan_source, planner_usage = await asyncio.to_thread(
                get_plan_with_cache, question, planner_llm
            )

        # Record planner usage if available (only for LLM path)
        if planner_usage:
            s = settings()
            provider, model = get_provider_info(s.planner_llm)
            collector.add("planner", provider, model, planner_usage)

        logger.info("Plan source: %s", plan_source)
        logger.info(
            "Plan created: intents=%s, entities=%d, tool_calls=%d, confidence=%.2f",
            [i.value for i in plan.intents],
            len(plan.entities),
            len(plan.tool_calls),
            plan.confidence,
        )

        # 2. Execute
        _emit_status("searching", "Ищу в базе знаний...", config)

        executor = PlanExecutor()
        payload = await asyncio.to_thread(executor.execute, plan, question)

        # 2.1 Self-check: if retrieval is insufficient, run hybrid search and merge context
        try:
            # Determine if Critic should be skipped (Lazy Critic)
            cfg = settings()
            primary_intent_value = plan.intents[0].value if plan.intents else None
            plan_confidence = float(plan.confidence or 0.0)
            facts_count = len(payload.items)

            skip_critic = (
                not cfg.critic_enabled
                or plan_confidence >= cfg.critic_confidence_threshold
                or facts_count >= cfg.critic_min_facts_threshold
                or primary_intent_value in cfg.critic_skip_intents
            )

            if plan_confidence < 0.5:
                # Low confidence always triggers search, regardless of skip settings
                decision = CriticDecision(
                    sufficient=False,
                    need_search=True,
                    query=question,
                    reason="low_plan_confidence",
                )
                logger.info("Self-check forcing hybrid search due to low plan confidence=%.2f", plan_confidence)
            elif skip_critic:
                logger.info(
                    "Critic skipped: enabled=%s, confidence=%.2f (threshold=%.2f), "
                    "facts=%d (threshold=%d), intent=%s (skip_list=%s)",
                    cfg.critic_enabled,
                    plan_confidence,
                    cfg.critic_confidence_threshold,
                    facts_count,
                    cfg.critic_min_facts_threshold,
                    primary_intent_value,
                    cfg.critic_skip_intents,
                )
                decision = CriticDecision(sufficient=True, need_search=False, query="", reason="skipped")
            else:
                _emit_status("verifying", "Проверяю полноту данных...", config)
                critic_instance = CriticLLM(critic_llm())
                decision, critic_usage = await asyncio.to_thread(
                    critic_instance.evaluate, question, plan, payload
                )

                # Record critic usage
                if critic_usage:
                    provider, model = get_provider_info(cfg.critic_llm)
                    collector.add("critic", provider, model, critic_usage)

            search_already_used = any(tc.tool == "portfolio_search_tool" for tc in (plan.tool_calls or []))
            if decision.need_search and not search_already_used:
                search_query = (decision.query or "").strip() or question
                logger.info("Self-check triggering portfolio_search_tool query=%r", truncate_text(search_query, limit=200))
                facts2, sources2, found2, confidence2, evidence2 = await asyncio.to_thread(
                    execute_portfolio_search,
                    query=search_query,
                    k=8,
                )

                if found2 and facts2:
                    merged_items = (payload.items or []) + facts2
                    payload.items = merged_items[: plan.limits.max_items]  # effective_max_items applied in normalizer below

                # Merge sources (dedupe by id)
                existing_ids = {src.id for src in (payload.sources or []) if src.id}
                for src in sources2:
                    if not isinstance(src, dict):
                        continue
                    try:
                        source_id = src.get("id")
                        if source_id is None:
                            source_id = src.get("ref_id") or src.get("source") or ""
                        label = src.get("label") or src.get("title") or src.get("name") or src.get("id") or source_id or ""
                        si = SourceInfo(id=str(source_id), label=str(label), type=src.get("type"))
                        if si.id and si.id not in existing_ids:
                            payload.sources.append(si)
                            existing_ids.add(si.id)
                    except Exception as e:
                        logger.warning("Self-check source merge failed: %s", e)

                if found2:
                    payload.found = True
                    payload.warnings.append("Self-check: использован дополнительный гибридный поиск")

                if isinstance(payload.meta, dict):
                    payload.meta["coverage"] = max(float(payload.meta.get("coverage") or 0.0), float(confidence2 or 0.0))
                    if evidence2:
                        payload.meta["evidence"] = evidence2

        except Exception as e:
            logger.warning("Self-check skipped due to error: %s", e)

        logger.info(
            "Execution complete: found=%s, items=%d, confidence=%.2f",
            payload.found,
            len(payload.items),
            payload.meta.get("coverage", 0.0),
        )

        # 3. Normalize facts (deterministic filtering by intent)
        normalizer = FactNormalizer()
        primary_intent = plan.intents[0] if plan.intents else None
        intent_str = primary_intent.value if primary_intent else "general_unstructured"

        # For technology_overview, return the full technology set (~20 items).
        # The planner default max_items (10–12) is too low for a complete overview.
        _effective_max_items = plan.limits.max_items
        if intent_str == "technology_overview":
            _effective_max_items = max(_effective_max_items, 20)

        # Extract tech_filter from plan (QueryPlanV3 feature)
        tech_filter_for_normalizer = None
        if hasattr(plan, 'tech_filter') and plan.tech_filter:
            tech_filter_for_normalizer = plan.tech_filter

        normalizer_output = normalizer.normalize(
            facts=payload.items,
            intent=intent_str,
            tech_filter=tech_filter_for_normalizer,
            max_items=_effective_max_items,
        )

        # Update payload with normalized facts
        from .planner.schemas import FactItem
        normalized_facts = [
            FactItem(
                type=fi.type,
                text=fi.text,
                metadata=fi.metadata or {},
                source_id=fi.entity_id,
            )
            for fi in normalizer_output.filtered_facts
        ]
        payload.items = normalized_facts

        if normalizer_output.rules_applied:
            payload.warnings.append(f"Normalizer: {', '.join(normalizer_output.rules_applied)}")

        logger.info(
            "Normalizer: %d facts after filtering, rules=%s",
            len(normalized_facts),
            normalizer_output.rules_applied,
        )

        # 4. Build FactBundle for grounding verification
        fact_bundle = build_fact_bundle(payload.items)

        logger.info(
            "FactBundle: techs=%d, companies=%d, projects=%d",
            len(fact_bundle.technologies),
            len(fact_bundle.companies),
            len(fact_bundle.projects),
        )

        # 5. Render (deterministic)
        renderer = RenderEngine()
        rendered = renderer.render(
            facts=payload.items,
            style=payload.render_style,
            intents=payload.intents,
            max_items=_effective_max_items,
        )

        # 6. Answer (LLM)
        _emit_status("answering", "Формирую ответ...", config)

        answer_gen = AnswerLLM(answer_llm())
        answer, answer_usage = await asyncio.to_thread(answer_gen.generate, payload)

        # Record answer usage
        if answer_usage:
            s = settings()
            provider, model = get_provider_info(s.answer_llm)
            collector.add("answer", provider, model, answer_usage)

        # 7. Grounding verification - check for hallucinations
        grounding_verifier = GroundingVerifier()
        grounding_result = grounding_verifier.verify(answer, fact_bundle)

        if not grounding_result.grounded:
            logger.warning(
                "Grounding check failed: action=%s, ungrounded=%s, confidence=%.2f",
                grounding_result.action,
                grounding_result.ungrounded_entities,
                grounding_result.confidence,
            )
            payload.warnings.append(
                f"Grounding: {grounding_result.action}, ungrounded={grounding_result.ungrounded_entities}"
            )

            if grounding_result.action == "refuse":
                # Too many hallucinations - return safe response
                answer = "На основе имеющихся данных портфолио не удалось найти достоверную информацию по вашему запросу. Попробуйте уточнить вопрос."
                payload.warnings.append("Grounding: answer refused due to hallucinations")
            elif grounding_result.action == "rewrite" and grounding_result.suggested_rewrite:
                # Use rewritten answer without hallucinations
                answer = grounding_result.suggested_rewrite
                payload.warnings.append("Grounding: answer rewritten to remove ungrounded entities")

        # Log usage summary
        collector.log_summary(f"rag_tool_{id(question)}")

        return {
            "answer": answer,
            "rendered_facts": rendered,
            "items": [item.model_dump() for item in payload.items],
            "sources": [src.model_dump() for src in payload.sources],
            "confidence": payload.meta.get("coverage", 0.0),
            "found": payload.found,
            "intents": [i.value for i in payload.intents],
            "warnings": payload.warnings,
            "grounded": grounding_result.grounded,
            "usage": collector.to_dict(),
        }

    except Exception as e:
        logger.error("portfolio_rag_tool failed: %s", e, exc_info=True)
        return {
            "answer": "Произошла ошибка при обработке запроса. Попробуйте переформулировать вопрос.",
            "rendered_facts": "",
            "items": [],
            "sources": [],
            "confidence": 0.0,
            "found": False,
            "intents": [],
            "warnings": [str(e)],
            "usage": collector.to_dict(),
        }
