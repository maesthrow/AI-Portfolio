"""
Answer LLM - generates user-facing answers from facts.

Uses strict prompting to prevent hallucinations and ensure consistent formatting.
Based on ТЗ section 8.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import SystemMessage, HumanMessage

from ..planner.schemas import FactsPayload, RenderStyle, AnswerStyle
from ..render.renderer import RenderEngine, post_process_answer
from ...utils.logging_utils import truncate_text
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_TEMPLATE,
    STYLE_INSTRUCTIONS,
    NOT_FOUND_RESPONSE,
    NOT_FOUND_BY_INTENT,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class AnswerLLM:
    """
    Generates user-facing answer from FactsPayload.

    Uses strict prompting to prevent hallucinations and
    ensure consistent formatting.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        temperature: float = 0.3,
    ):
        """
        Initialize AnswerLLM.

        Args:
            llm: LangChain chat model
            temperature: Generation temperature (0.3 for balance)
        """
        self.llm = llm
        self.temperature = temperature
        self.renderer = RenderEngine()

    def generate(self, payload: FactsPayload) -> tuple[str, Any, bool]:
        """
        Generate answer from FactsPayload.

        Uses deterministic rendering for structured facts,
        then LLM for natural phrasing.

        Args:
            payload: FactsPayload from Executor

        Returns:
            tuple[str, usage, deterministic_used]: User-facing answer string,
                usage metadata (None if deterministic), and whether deterministic path was used
        """
        logger.info(
            "Answer input: found=%s items=%d sources=%d intents=%s render_style=%s answer_style=%s coverage=%.2f evidence=%r",
            payload.found,
            len(payload.items),
            len(payload.sources),
            [i.value for i in (payload.intents or [])],
            getattr(payload.render_style, "value", payload.render_style),
            getattr(payload.answer_style, "value", payload.answer_style),
            float((payload.meta or {}).get("coverage") or 0.0),
            truncate_text((payload.meta or {}).get("evidence"), limit=400),
        )

        evidence_text = (payload.meta or {}).get("evidence")
        evidence_text = evidence_text if isinstance(evidence_text, str) else str(evidence_text or "")
        evidence_text = evidence_text.strip()

        # Handle not found case (no facts and no evidence context)
        if not payload.items and not evidence_text and not payload.found:
            logger.info("Answer not-found: query=%r", truncate_text(payload.query, limit=400))
            return self._get_not_found_response(payload), None, False

        # For some intents we can answer deterministically from evidence/facts.
        # This avoids LLM "false not-found" responses when evidence is present.
        deterministic = self._try_deterministic_answer(payload, evidence_text=evidence_text)
        if deterministic:
            logger.info("Answer deterministic_used=True preview=%r", truncate_text(deterministic, limit=800))
            return deterministic, None, True

        # Pre-render facts for context.
        # For technology_overview, render all facts (portfolio has ~20 techs).
        intents_values = [i.value for i in (payload.intents or [])]
        _render_max_items = 20 if "technology_overview" in intents_values else 10
        if payload.items:
            rendered_facts = self.renderer.render(
                facts=payload.items,
                style=payload.render_style,
                intents=payload.intents,
                max_items=_render_max_items,
            )
        else:
            rendered_facts = evidence_text
        logger.info("Answer rendered_facts=%r", truncate_text(rendered_facts, limit=2000))

        if not rendered_facts:
            logger.info("Answer not-found (empty context): query=%r", truncate_text(payload.query, limit=400))
            return self._get_not_found_response(payload), None, False

        # Get style instruction
        style_instruction = self._get_style_instruction(payload)

        # Format warnings
        warnings_text = ""
        if payload.warnings:
            warnings_text = f"Предупреждения: {'; '.join(payload.warnings)}"

        # Build user prompt
        user_prompt = ANSWER_USER_TEMPLATE.format(
            question=payload.query,
            facts=rendered_facts,
            style_instruction=style_instruction,
            warnings=warnings_text,
        )
        logger.info(
            "Answer prompt: system_len=%d user_len=%d user_preview=%r",
            len(ANSWER_SYSTEM_PROMPT or ""),
            len(user_prompt or ""),
            truncate_text(user_prompt, limit=2000),
        )

        # Generate answer
        messages = [
            SystemMessage(content=ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            usage = self._extract_usage(response)
            answer = response.content.strip()
            logger.info("Answer raw_preview=%r", truncate_text(answer, limit=800))

            # Post-process to remove any remaining artifacts
            cleaned_answer, warnings = post_process_answer(answer)

            if warnings:
                logger.warning("Post-process removed artifacts: %s", warnings)

            # Guardrail: if LLM produced a generic "not found", but we actually have evidence,
            # prefer a deterministic extraction over a misleading answer.
            intents = [i.value for i in (payload.intents or [])]
            if (
                self._looks_like_not_found(cleaned_answer)
                and "technology_usage" in intents
                and (payload.items or evidence_text)
            ):
                recovered = self._answer_technology_usage(
                    question=payload.query,
                    facts=payload.items,
                    evidence_text=evidence_text or rendered_facts,
                )
                if recovered:
                    logger.info(
                        "Answer recovered_from_evidence=True llm_answer=%r recovered_preview=%r",
                        truncate_text(cleaned_answer, limit=200),
                        truncate_text(recovered, limit=800),
                    )
                    return recovered, usage, True

            logger.info("Answer final_preview=%r", truncate_text(cleaned_answer, limit=800))
            return cleaned_answer, usage, False

        except Exception as e:
            logger.error("Answer generation failed: %s", e)
            # Return rendered facts as fallback
            return rendered_facts, None, False

    def _get_not_found_response(self, payload: FactsPayload) -> str:
        """Get appropriate not-found response based on intent."""
        if payload.intents:
            intent = payload.intents[0].value
            return NOT_FOUND_BY_INTENT.get(intent, NOT_FOUND_RESPONSE)
        return NOT_FOUND_RESPONSE

    def _get_style_instruction(self, payload: FactsPayload) -> str:
        """Get style instruction for the answer."""
        instructions = []

        # Add render style instruction
        render_key = payload.render_style.value
        if render_key in STYLE_INSTRUCTIONS:
            instructions.append(STYLE_INSTRUCTIONS[render_key])

        # Add answer style instruction
        answer_key = payload.answer_style.value
        if answer_key in STYLE_INSTRUCTIONS:
            instructions.append(STYLE_INSTRUCTIONS[answer_key])

        return "; ".join(instructions) if instructions else "Естественный русский язык"

    def _extract_usage(self, response: Any) -> Any:
        """Extract usage_metadata from LLM response."""
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata
        if hasattr(response, "response_metadata"):
            rm = response.response_metadata or {}
            return rm.get("token_usage") or rm.get("usage")
        return None

    def _try_deterministic_answer(self, payload: FactsPayload, evidence_text: str) -> str | None:
        """
        Build an answer without calling the LLM when it can be derived reliably
        from provided facts/evidence (no hallucinations possible).
        """
        intents = [i.value for i in (payload.intents or [])]
        if intents == ["technology_usage"]:
            return self._answer_technology_usage(question=payload.query, facts=payload.items, evidence_text=evidence_text)
        # Детерминированная генерация для контактов (сохраняет markdown links)
        if intents == ["contacts"]:
            return self._answer_contacts(facts=payload.items)
        # Детерминированная генерация для публикаций (сохраняет markdown links)
        if any("publication" in i for i in intents):
            return self._answer_publications(facts=payload.items)
        # Детерминированная генерация для деталей проекта (сохраняет markdown links + полный контекст)
        if intents == ["project_details"] or set(intents) == {"project_details", "project_achievements"}:
            return self._answer_project_details(facts=payload.items)
        # Детерминированная генерация для листинга проектов (граф уже отфильтровал нужные)
        if intents == ["project_list"] or "project_list" in intents:
            return self._answer_project_list(facts=payload.items)
        return None

    def _recover_from_evidence(self, payload: FactsPayload, rendered_facts: str, evidence_text: str) -> str | None:
        intents = [i.value for i in (payload.intents or [])]
        if "technology_usage" not in intents:
            return None
        return self._answer_technology_usage(
            question=payload.query,
            facts=payload.items,
            evidence_text=evidence_text or rendered_facts,
        )

    @staticmethod
    def _looks_like_not_found(answer: str) -> bool:
        a = (answer or "").strip().lower()
        if not a:
            return True
        # Common "not found" phrasings (LLM sometimes shortens the configured templates).
        needles = (
            "такой информации нет",
            "нет в портфолио",
            "не упоминается в портфолио",
            "не нашлось",
            "не найдено",
        )
        return (len(a) <= 200) and any(n in a for n in needles)

    def _answer_technology_usage(self, question: str, facts: list, evidence_text: str) -> str | None:
        """
        Deterministically answer "where was technology used" questions.

        Uses ONLY provided facts/evidence:
        - Graph facts: metadata {technology, project}
        - Hybrid evidence: lines like "Используется в: <projects...>"
        - Filtered fact bullets: achievements already filtered by normalizer

        After normalizer content filtering, facts contain only relevant bullets.
        The answer includes project names AND specific achievements.
        """
        q = (question or "").strip()
        if not q:
            return None

        tech_to_projects: dict[str, list[str]] = {}

        # 1) Structured facts (graph path)
        for fact in facts or []:
            md = getattr(fact, "metadata", None) or {}
            tech = md.get("technology")
            proj = md.get("project")
            if tech and proj:
                tech_to_projects.setdefault(str(tech), []).append(str(proj))

        # 2) Metadata-rich facts (hybrid path, if present)
        for fact in facts or []:
            md = getattr(fact, "metadata", None) or {}
            name = md.get("name") or md.get("title")
            project_names = self._extract_project_names_from_metadata(md)
            if name and project_names:
                tech_to_projects.setdefault(str(name), []).extend(project_names)

            # Also try to parse the fact text directly (works when page_content includes usage line).
            text = getattr(fact, "text", "") or ""
            extracted = self._extract_usage_from_text(text)
            if extracted:
                tech_name, projects = extracted
                if tech_name and projects:
                    tech_to_projects.setdefault(tech_name, []).extend(projects)

        # 3) Raw evidence text (fallback path)
        if evidence_text:
            extracted = self._extract_usage_from_evidence(evidence_text)
            for tech_name, projects in extracted.items():
                tech_to_projects.setdefault(tech_name, []).extend(projects)

        # Normalize + dedupe
        normalized: dict[str, list[str]] = {}
        for tech, projects in tech_to_projects.items():
            cleaned_projects = []
            seen = set()
            for p in projects:
                p2 = (p or "").strip()
                if not p2:
                    continue
                if p2 not in seen:
                    seen.add(p2)
                    cleaned_projects.append(p2)
            if cleaned_projects:
                normalized[tech.strip()] = cleaned_projects

        if not normalized:
            return None

        # Choose technologies relevant to the question (avoid dumping unrelated evidence).
        ql = q.lower()
        mentioned = {t for t in normalized.keys() if t.lower() in ql}

        # Cross-language matching via TECH_ABBREVIATIONS:
        # e.g. question "опыт с компьютерным зрением" should match "Computer Vision"
        if not mentioned:
            from ..normalizer.normalizer import TECH_ABBREVIATIONS
            for tech in normalized.keys():
                tl = tech.lower()
                # Check if any abbreviation/translation of this tech appears in question
                for canonical, abbrevs in TECH_ABBREVIATIONS.items():
                    if canonical.lower() == tl:
                        if any(a.lower() in ql for a in abbrevs):
                            mentioned.add(tech)
                            break
                    elif tl in (a.lower() for a in abbrevs):
                        if canonical.lower() in ql:
                            mentioned.add(tech)
                            break

        # If nothing matched, use loose token matching.
        if not mentioned:
            tokens = {t.lower() for t in re.findall(r"[\w#+\-.]{2,}", ql)}
            for tech in normalized.keys():
                tl = tech.lower()
                if tl in tokens:
                    mentioned.add(tech)
                    continue
                # token-in-name match for short abbreviations (RAG, LLM, etc.)
                if any(tok and tok in tl for tok in tokens if len(tok) >= 3):
                    mentioned.add(tech)

        # If still nothing, but only one tech has usage info, assume it's the target.
        if not mentioned and len(normalized) == 1:
            mentioned = set(normalized.keys())

        if not mentioned:
            return None

        # --- Extract achievements from filtered facts ---
        # After normalizer content filtering, fact bullets are already relevant.
        # Group achievements by project name for rich output.
        project_achievements: dict[str, list[str]] = {}
        for fact in facts or []:
            md = getattr(fact, "metadata", None) or {}
            proj_name = md.get("name") or md.get("project") or ""
            company = md.get("company_name") or ""
            period = md.get("period") or ""

            text = getattr(fact, "text", "") or ""
            bullets = [
                line.strip()
                for line in text.split("\n")
                if line.strip().startswith("- ") or line.strip().startswith("\u2022 ")
            ]
            if bullets and proj_name:
                key = proj_name
                if company and period:
                    key = f"{proj_name} ({company}, {period})"
                elif company:
                    key = f"{proj_name} ({company})"
                project_achievements.setdefault(key, []).extend(bullets)

        # Dedupe achievements per project (exact match)
        for key in project_achievements:
            seen_bullets: set[str] = set()
            unique: list[str] = []
            for b in project_achievements[key]:
                if b not in seen_bullets:
                    seen_bullets.add(b)
                    unique.append(b)
            project_achievements[key] = unique

        # Same-project merge: the same project may appear from different data
        # sources (experience_project vs standalone project) with different
        # metadata suffixes, e.g. "t2 — Нейросети (Aston, 2024 — 2025)"
        # and "t2 — Нейросети (t2 (проект в Aston))".
        # Merge by base project name, keeping the most informative key.
        if len(project_achievements) > 1:
            base_groups: dict[str, list[str]] = {}
            for key in project_achievements:
                base = re.split(r"\s*\(", key, maxsplit=1)[0].strip()
                base_groups.setdefault(base, []).append(key)

            if any(len(keys) > 1 for keys in base_groups.values()):
                merged: dict[str, list[str]] = {}
                for base, keys in base_groups.items():
                    if len(keys) == 1:
                        merged[keys[0]] = project_achievements[keys[0]]
                    else:
                        # Pick the most informative key (with year/period)
                        best = sorted(
                            keys,
                            key=lambda k: (
                                0 if re.search(r"\d{4}", k) else 1,
                                0 if "(" in k else 1,
                                k,
                            ),
                        )[0]
                        combined: list[str] = []
                        for k in keys:
                            combined.extend(project_achievements[k])
                        # Dedupe within merged entry
                        seen_m: set[str] = set()
                        unique_m: list[str] = []
                        for b in combined:
                            if b not in seen_m:
                                seen_m.add(b)
                                unique_m.append(b)
                        merged[best] = unique_m
                project_achievements = merged

        # Cross-project dedup: when the same achievement text appears under
        # different project keys (e.g. company-level vs project-level), keep
        # it only in the most specific entry.
        if len(project_achievements) > 1:
            def _key_specificity(k: str) -> tuple:
                has_year = bool(re.search(r"\d{4}", k))
                has_parens = "(" in k
                return (0 if has_year else 1, 0 if has_parens else 1, k)

            ordered_keys = sorted(project_achievements.keys(), key=_key_specificity)
            global_seen: set[str] = set()
            for key in ordered_keys:
                filtered = []
                for b in project_achievements[key]:
                    norm = re.sub(r"^[-•]\s*", "", b.strip()).strip().lower()
                    if norm not in global_seen:
                        global_seen.add(norm)
                        filtered.append(b)
                project_achievements[key] = filtered

            project_achievements = {
                k: v for k, v in project_achievements.items() if v
            }

        # --- Render answer ---
        lines: list[str] = []
        for tech in sorted(mentioned, key=lambda x: x.lower()):
            projects = normalized.get(tech, [])
            if not projects:
                continue
            if len(mentioned) == 1:
                lines.append(f"Дмитрий применял {tech} в проектах:")
            else:
                lines.append(f"{tech}:")

            if project_achievements:
                # Rich answer: project names with achievements
                for proj_key, achievements in project_achievements.items():
                    lines.append(f"\n**{proj_key}**:")
                    lines.extend(achievements)
            else:
                # Fallback: plain project name list (no filtered bullets available)
                lines.extend([f"- {p}" for p in projects])

        return "\n".join(lines).strip() if lines else None

    def _deterministic_render(self, facts: list, preamble: str = "") -> str | None:
        """
        Детерминированный рендеринг фактов с опциональной преамбулой.
        Общий метод для contacts, publications и подобных интентов.
        """
        if not facts:
            return None
        rendered = self.renderer.render(
            facts=facts,
            style=RenderStyle.BULLETS,
            intents=[],
        )
        if not rendered:
            return None
        return f"{preamble}\n{rendered}" if preamble else rendered

    def _answer_contacts(self, facts: list) -> str | None:
        """Детерминированная генерация ответа для контактов."""
        if len(facts or []) == 1:
            preamble = "Контакт Дмитрия:"
        else:
            preamble = "С Дмитрием можно связаться несколькими способами:"
        return self._deterministic_render(facts, preamble=preamble)

    def _answer_project_details(self, facts: list) -> str | None:
        """Детерминированная генерация ответа для деталей проекта."""
        if not facts:
            return None
        preamble = "Проекты:" if len(facts) > 1 else ""
        return self._deterministic_render(facts, preamble=preamble)

    def _answer_project_list(self, facts: list) -> str | None:
        """Детерминированная генерация ответа для списка проектов."""
        if not facts:
            return None
        preamble = "Проекты:" if len(facts) > 1 else ""
        return self._deterministic_render(facts, preamble=preamble)

    def _answer_publications(self, facts: list) -> str | None:
        """Детерминированная генерация ответа для публикаций."""
        return self._deterministic_render(facts, preamble="Публикации Дмитрия:")

    @staticmethod
    def _extract_project_names_from_metadata(md: dict) -> list[str]:
        if not isinstance(md, dict):
            return []

        val = md.get("project_names")
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            # Sometimes stored as JSON string.
            s = val.strip()
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass

        return []

    @staticmethod
    def _extract_usage_from_text(text: str) -> tuple[str | None, list[str]] | None:
        """
        Parse a single text block like:
          "RAG\\nИспользуется в: t2 — Нейросети, AI-Portfolio"
        """
        if not text:
            return None
        t = str(text).strip()
        if not t:
            return None

        # First line is often the technology name for technology docs.
        first_line = t.splitlines()[0].strip() if t.splitlines() else ""

        m = re.search(r"(?:используется\s+в|used\s+in)\s*:\s*(.+)", t, flags=re.IGNORECASE)
        if not m:
            return None
        tail = m.group(1).strip()
        if not tail:
            return None
        projects = [p.strip() for p in re.split(r"[;,]", tail) if p.strip()]
        return (first_line or None, projects)

    def _extract_usage_from_evidence(self, evidence_text: str) -> dict[str, list[str]]:
        """
        Parse pack_context() output, best-effort.

        Expected block format:
          [technology] RAG: RAG\\nИспользуется в: t2 — Нейросети, AI-Portfolio
        Blocks are separated by blank lines.
        """
        out: dict[str, list[str]] = {}
        blocks = re.split(r"\n\s*\n", evidence_text.strip())
        for block in blocks:
            b = block.strip()
            if not b:
                continue
            # Try to get title from header.
            tech_name = None
            m_header = re.match(r"^\[(?P<type>[^\]]+)\]\s*(?P<title>[^:]+)\s*:\s*(?P<body>.*)$", b, flags=re.DOTALL)
            body = b
            if m_header:
                ttype = (m_header.group("type") or "").strip().lower()
                if ttype != "technology":
                    continue
                tech_name = (m_header.group("title") or "").strip()
                body = (m_header.group("body") or "").strip()

            extracted = self._extract_usage_from_text(body)
            if extracted:
                inferred_name, projects = extracted
                name = tech_name or inferred_name
                if name and projects:
                    out.setdefault(name, []).extend(projects)
        return out


def create_answer_llm(llm: BaseChatModel, temperature: float = 0.3) -> AnswerLLM:
    """
    Factory function to create AnswerLLM.

    Args:
        llm: Base LLM (will be configured with temperature)
        temperature: Answer temperature (default 0.3)

    Returns:
        Configured AnswerLLM instance
    """
    # Try to set temperature if supported
    if hasattr(llm, "temperature"):
        llm.temperature = temperature
    elif hasattr(llm, "model_kwargs"):
        llm.model_kwargs["temperature"] = temperature

    return AnswerLLM(llm=llm, temperature=temperature)
