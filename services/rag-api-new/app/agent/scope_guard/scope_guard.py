"""
ScopeGuard - защита от оффтопа.

Определяет, относится ли вопрос к портфолио или это оффтоп.
При оффтопе возвращает вежливый отказ с примерами вопросов по теме.

P0 требование: любые запросы не про портфолио → вежливый отказ.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from .schemas import ScopeDecision

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


# Suggested portfolio prompts for out-of-scope responses
SUGGESTED_PROMPTS_RU = [
    "Какие проекты есть в портфолио?",
    "Где применял RAG?",
    "Какие технологии знает Дмитрий?",
    "Расскажи про опыт работы",
    "Какие достижения на проектах?",
]

SUGGESTED_PROMPTS_EN = [
    "What projects are in the portfolio?",
    "Where did he use RAG?",
    "What technologies does Dmitry know?",
    "Tell me about work experience",
]


# Patterns for off-topic detection (case-insensitive)
OFF_TOPIC_PATTERNS = [
    # Fairy tales, stories
    r"\bсказк[уаи]\b",
    r"\bрасскажи\s+(?:мне\s+)?сказку\b",
    r"\bстих[иа]?\b",
    r"\bанекдот\b",
    r"\bшутк[уаи]\b",
    r"\bпритч[уаи]\b",

    # Code generation requests not about portfolio
    r"\bнапиши\s+(?:мне\s+)?(?:код|программу|скрипт)\b",
    r"\bсгенерируй\s+(?:мне\s+)?(?:код|программу)\b",
    r"\bwrite\s+(?:me\s+)?(?:code|program|script)\b",

    # General knowledge questions
    r"\bчто\s+такое\s+(?:любовь|жизнь|смысл)\b",
    r"\bкто\s+(?:такой|такая)\s+(?:путин|байден|трамп|маск|навальный)\b",
    r"\bрасскажи\s+(?:о|про)\s+(?:погоде|новостях|политике)\b",
    r"\bпогод[ауе]\s+(?:в\s+|на\s+)?\w+\b",  # Weather in/at location
    r"\bweather\s+(?:in|at)\s+\w+\b",

    # Entertainment
    r"\bпоиграем\b",
    r"\bдавай\s+поиграем\b",
    r"\blet'?s?\s+play\b",
    r"\bplay\s+a\s+game\b",

    # Role-play requests
    r"\bпритворись\b",
    r"\bпредставь\s+(?:что\s+)?ты\b",
    r"\bact\s+like\b",
    r"\bpretend\s+(?:to\s+be|you'?re)\b",
    r"\bролевая\b",

    # Harmful content
    r"\bкак\s+(?:взломать|украсть|обмануть)\b",
    r"\bhow\s+to\s+(?:hack|steal|cheat)\b",
    r"\bкак\s+сделать\s+(?:бомбу|оружие|наркотики)\b",
]

# Patterns for small talk (allowed but responded differently)
SMALL_TALK_PATTERNS = [
    r"^(?:привет|здравствуй|hi|hello|hey)[\s!.,]*$",
    r"^(?:как\s+дела|what'?s?\s+up|how\s+are\s+you)[\s?!.,]*$",
    r"^(?:спасибо|thanks|thank\s+you)[\s!.,]*$",
    r"^(?:пока|bye|goodbye|до\s+свидания)[\s!.,]*$",
]

# Patterns for portfolio-related questions
PORTFOLIO_PATTERNS = [
    # Projects
    r"\bпроект[ауыеов]?\b",
    r"\bproject[s]?\b",

    # Technologies
    r"\bтехнолог[ияий]\b",
    r"\btechnolog[yies]\b",
    r"\bстек\b",
    r"\bstack\b",
    r"\bязык[иа]?\b",
    r"\blanguage[s]?\b",
    r"\bбаз[ауы]?\s*данных\b",
    r"\bdatabase[s]?\b",
    r"\bdb\b",

    # Experience
    r"\bопыт\b",
    r"\bexperience\b",
    r"\bработ[аыу]\b",
    r"\bwork\b",
    r"\bкомпани[яиейю]\b",
    r"\bcompan[yies]\b",
    r"\bдолжност[ьи]\b",
    r"\bposition[s]?\b",
    r"\bрол[ьи]\b",
    r"\brole[s]?\b",

    # Achievements
    r"\bдостижени[яей]\b",
    r"\bachievement[s]?\b",

    # Skills
    r"\bнавык[иа]?\b",
    r"\bskill[s]?\b",
    r"\bумен[ияей]\b",
    r"\babilit[yies]\b",

    # Contacts
    r"\bконтакт[ыа]?\b",
    r"\bcontact[s]?\b",
    r"\bсвяз[ьи]\b",
    r"\bсвязаться\b",

    # Portfolio keywords
    r"\bпортфолио\b",
    r"\bportfolio\b",
    r"\bрезюме\b",
    r"\bresume\b",
    r"\bcv\b",

    # Person references
    r"\bдмитри[йя]?\b",
    r"\bdmitr[iy]\b",
    r"\bавтор[ау]?\b",
    r"\bauthor\b",
    r"\bразработчик[ау]?\b",
    r"\bdeveloper\b",

    # Specific technologies often asked about
    r"\brag\b",
    r"\bpython\b",
    r"\bfastapi\b",
    r"\blangchain\b",
    r"\bланг(?:чейн|граф)\b",
    r"\blangraph\b",
    r"\bchroma(?:db)?\b",
    r"\bpostgres(?:ql)?\b",
    r"\bdocker\b",
]


class ScopeGuard:
    """
    Guard for detecting out-of-scope questions.

    Uses pattern matching for fast detection with optional LLM fallback.
    """

    def __init__(self, llm: BaseChatModel | None = None):
        """
        Initialize ScopeGuard.

        Args:
            llm: Optional LLM for complex classification
        """
        self.llm = llm

        # Compile patterns
        self._off_topic_patterns = [
            re.compile(p, re.IGNORECASE) for p in OFF_TOPIC_PATTERNS
        ]
        self._small_talk_patterns = [
            re.compile(p, re.IGNORECASE) for p in SMALL_TALK_PATTERNS
        ]
        self._portfolio_patterns = [
            re.compile(p, re.IGNORECASE) for p in PORTFOLIO_PATTERNS
        ]

    def evaluate(
        self,
        question: str,
        thread_context: str | None = None,
    ) -> ScopeDecision:
        """
        Evaluate if question is within portfolio scope.

        Args:
            question: User's question
            thread_context: Optional conversation context

        Returns:
            ScopeDecision with in_scope flag and suggestions
        """
        if not question or not question.strip():
            return ScopeDecision(
                in_scope=True,
                reason="empty_question_allowed",
                category="portfolio"
            )

        q = question.strip()
        q_lower = q.lower()

        # 1. Check for harmful content patterns
        for pattern in self._off_topic_patterns:
            if pattern.search(q_lower):
                # Check if it's harmful
                if any(kw in q_lower for kw in ["взломать", "украсть", "бомбу", "hack", "steal"]):
                    return ScopeDecision(
                        in_scope=False,
                        reason="harmful_content_detected",
                        category="harmful",
                        suggested_prompts=SUGGESTED_PROMPTS_RU[:3]
                    )

                return ScopeDecision(
                    in_scope=False,
                    reason=f"off_topic_pattern_matched: {pattern.pattern[:50]}",
                    category="off_topic",
                    suggested_prompts=SUGGESTED_PROMPTS_RU[:3]
                )

        # 2. Check for small talk
        for pattern in self._small_talk_patterns:
            if pattern.match(q_lower):
                return ScopeDecision(
                    in_scope=True,  # Small talk is allowed
                    reason="small_talk_detected",
                    category="small_talk",
                    suggested_prompts=[]
                )

        # 3. Check for portfolio-related patterns
        portfolio_score = 0
        for pattern in self._portfolio_patterns:
            if pattern.search(q_lower):
                portfolio_score += 1

        if portfolio_score > 0:
            return ScopeDecision(
                in_scope=True,
                reason=f"portfolio_patterns_matched: {portfolio_score}",
                category="portfolio",
                suggested_prompts=[]
            )

        # 4. Default: allow with low confidence
        # Most questions without clear signals should be allowed
        # to let the RAG pipeline handle them
        logger.debug("ScopeGuard: no patterns matched, allowing by default")
        return ScopeDecision(
            in_scope=True,
            reason="no_off_topic_patterns_default_allow",
            category="portfolio",
            suggested_prompts=[]
        )

    def get_refusal_response(
        self,
        decision: ScopeDecision,
        lang: str = "ru"
    ) -> str:
        """
        Generate polite refusal response for out-of-scope questions.

        Args:
            decision: ScopeDecision from evaluate()
            lang: Response language (ru/en)

        Returns:
            Polite refusal with suggested prompts
        """
        if decision.category == "harmful":
            if lang == "ru":
                return "Извините, я не могу помочь с этим запросом. Я здесь, чтобы рассказать о портфолио Дмитрия."
            return "Sorry, I can't help with that request. I'm here to tell you about Dmitry's portfolio."

        if lang == "ru":
            prompts = decision.suggested_prompts or SUGGESTED_PROMPTS_RU[:3]
            suggestions = "\n".join(f"• {p}" for p in prompts)
            return (
                "Я — AI-ассистент портфолио Дмитрия и отвечаю только на вопросы о его проектах, "
                "опыте и навыках.\n\n"
                f"Попробуйте спросить:\n{suggestions}"
            )

        prompts = decision.suggested_prompts or SUGGESTED_PROMPTS_EN[:3]
        suggestions = "\n".join(f"• {p}" for p in prompts)
        return (
            "I'm Dmitry's portfolio AI assistant and I only answer questions about his projects, "
            "experience, and skills.\n\n"
            f"Try asking:\n{suggestions}"
        )


# Singleton instance
_scope_guard: ScopeGuard | None = None


def get_scope_guard() -> ScopeGuard:
    """Get or create ScopeGuard singleton."""
    global _scope_guard
    if _scope_guard is None:
        _scope_guard = ScopeGuard()
    return _scope_guard
