"""
Plan Executor - executes QueryPlanV2 tool calls.

Orchestrates tool execution, handles failures, and aggregates results
into FactsPayload for Answer LLM.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import (
    QueryPlanV2,
    FactsPayload,
    FactItem,
    ToolCall,
    SourceInfo,
)
from ..tools.graph_query_tool import execute_graph_query
from ..tools.portfolio_search_tool import execute_portfolio_search
from ...utils.logging_utils import compact_json, truncate_text

logger = logging.getLogger(__name__)


class PlanExecutor:
    """
    Executes QueryPlanV2 and builds FactsPayload.

    Handles tool failures gracefully with fallback execution.
    """

    def __init__(self):
        """Initialize PlanExecutor."""
        pass

    def execute(self, plan: QueryPlanV2, question: str) -> FactsPayload:
        """
        Execute all tool calls from plan and aggregate results.

        Args:
            plan: QueryPlanV2 from Planner LLM
            question: Original user question

        Returns:
            FactsPayload with all facts and metadata
        """
        all_facts: list[FactItem] = []
        all_sources: list[SourceInfo] = []
        warnings: list[str] = []
        overall_confidence = float(plan.confidence or 0.0)
        found = False
        evidence_text = ""

        logger.info(
            "Executing plan: intents=%s, tool_calls=%d",
            [i.value for i in plan.intents],
            len(plan.tool_calls),
        )

        # Execute each tool call
        for i, tool_call in enumerate(plan.tool_calls):
            logger.info(
                "Tool call start %d/%d tool=%s args=%s",
                i + 1,
                len(plan.tool_calls),
                tool_call.tool,
                compact_json(tool_call.args, limit=2000),
            )
            try:
                facts, sources, success, confidence, evidence = self._execute_tool(
                    tool_call, question
                )
                all_facts.extend(facts)

                # Convert sources to SourceInfo
                for src in sources:
                    if not isinstance(src, dict):
                        continue
                    try:
                        source_id = src.get("id")
                        if source_id is None:
                            source_id = src.get("ref_id") or src.get("source") or ""
                        label = src.get("label")
                        if not label:
                            label = src.get("title") or src.get("name") or src.get("id") or source_id or ""
                        all_sources.append(
                            SourceInfo(
                                id=str(source_id),
                                label=str(label),
                                type=src.get("type"),
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            "SourceInfo parse failed: %s src=%s",
                            e,
                            compact_json(src, limit=2000),
                        )

                if success:
                    found = True
                    overall_confidence = max(overall_confidence, float(confidence or 0.0))
                    if evidence:
                        evidence_text = evidence

                logger.info(
                    "Tool call end %d/%d tool=%s facts=%d sources=%d found=%s confidence=%.2f evidence=%r",
                    i + 1,
                    len(plan.tool_calls),
                    tool_call.tool,
                    len(facts),
                    len(sources),
                    success,
                    confidence,
                    truncate_text(evidence, limit=400),
                )
                if facts:
                    preview = [
                        {"type": f.type, "text": truncate_text(f.text, limit=180)}
                        for f in facts[:3]
                    ]
                    logger.info(
                        "Tool facts preview tool=%s preview=%s",
                        tool_call.tool,
                        compact_json(preview, limit=2000),
                    )

            except Exception as e:
                logger.warning("Tool %s failed: %s", tool_call.tool, e)
                warnings.append(f"Инструмент {tool_call.tool} не сработал: {e}")

        # If no results and fallback enabled, try fallback
        if not found and plan.fallback.enabled:
            logger.info("Primary tools failed, trying fallback: %s", plan.fallback.tool)
            try:
                facts, sources, success, confidence, evidence = self._execute_fallback(
                    plan, question
                )
                all_facts.extend(facts)

                for src in sources:
                    if not isinstance(src, dict):
                        continue
                    try:
                        source_id = src.get("id")
                        if source_id is None:
                            source_id = src.get("ref_id") or src.get("source") or ""
                        label = src.get("label")
                        if not label:
                            label = src.get("title") or src.get("name") or src.get("id") or source_id or ""
                        all_sources.append(
                            SourceInfo(
                                id=str(source_id),
                                label=str(label),
                                type=src.get("type"),
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            "SourceInfo parse failed: %s src=%s",
                            e,
                            compact_json(src, limit=2000),
                        )

                if success:
                    found = True
                    overall_confidence = max(overall_confidence, float(confidence or 0.0) * 0.7)
                    logger.info(
                        "Fallback success tool=%s facts=%d sources=%d confidence=%.2f evidence=%r",
                        plan.fallback.tool,
                        len(facts),
                        len(sources),
                        confidence,
                        truncate_text(evidence, limit=400),
                    )
                    warnings.append("Использован резервный поиск")
                    if evidence:
                        evidence_text = evidence

            except Exception as e:
                logger.warning("Fallback failed: %s", e)
                warnings.append(f"Резервный поиск не сработал: {e}")

        # Apply limits
        limited_facts = all_facts[: plan.limits.max_items]

        # Group facts if needed
        groups = []
        if len(plan.intents) > 1 or plan.render_style.value == "grouped_bullets":
            groups = self._group_facts(limited_facts)

        # Deduplicate sources
        seen_source_ids: set[str] = set()
        unique_sources = []
        for src in all_sources:
            if src.id and src.id not in seen_source_ids:
                seen_source_ids.add(src.id)
                unique_sources.append(src)

        return FactsPayload(
            found=found,
            items=limited_facts,
            groups=groups,
            meta={
                "coverage": overall_confidence if found else 0.0,
                "total_facts": len(all_facts),
                "limited_to": plan.limits.max_items,
                "evidence": evidence_text,
            },
            sources=unique_sources[:10],
            query=question,
            intents=plan.intents,
            render_style=plan.render_style,
            answer_style=plan.answer_style,
            warnings=warnings,
        )

    def _execute_tool(
        self,
        tool_call: ToolCall,
        question: str,
    ) -> tuple[list[FactItem], list[dict], bool, float, str]:
        """
        Execute a single tool call.

        Returns:
            Tuple of (facts, sources, found, confidence, evidence_text)
        """
        if tool_call.tool == "graph_query_tool":
            intent = tool_call.args.get("intent", "general")
            entity_id = tool_call.args.get("entity_id")

            facts, sources, found, confidence = execute_graph_query(
                intent=intent,
                entity_id=entity_id,
            )
            return facts, sources, found, confidence, ""

        elif tool_call.tool == "portfolio_search_tool":
            query = tool_call.args.get("query", question)
            k = tool_call.args.get("k", 8)
            allowed_types = tool_call.args.get("allowed_types")

            facts, sources, found, confidence, evidence = execute_portfolio_search(
                query=query,
                k=k,
                allowed_types=allowed_types,
            )
            return facts, sources, found, confidence, evidence

        else:
            logger.warning("Unknown tool: %s", tool_call.tool)
            return [], [], False, 0.0, ""

    def _execute_fallback(
        self,
        plan: QueryPlanV2,
        question: str,
    ) -> tuple[list[FactItem], list[dict], bool, float, str]:
        """Execute fallback tool."""
        if plan.fallback.tool == "portfolio_search_tool":
            return execute_portfolio_search(
                query=question,
                k=8,
            )
        else:
            # Default to portfolio search
            return execute_portfolio_search(query=question, k=8)

    def _group_facts(self, facts: list[FactItem]) -> list[dict[str, Any]]:
        """Group facts by type."""
        groups: dict[str, list[dict]] = {}

        for fact in facts:
            key = fact.type
            if key not in groups:
                groups[key] = []
            groups[key].append({
                "text": fact.text,
                "metadata": fact.metadata,
            })

        return [
            {"title": title.title(), "items": items}
            for title, items in groups.items()
            if items
        ]
