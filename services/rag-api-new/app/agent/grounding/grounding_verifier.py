"""
GroundingVerifier - проверка ответа на галлюцинации.

P0 требование: каждая именованная сущность в ответе должна
присутствовать в FactBundle.

Принцип работы:
1. FactBundle содержит ВСЕ известные сущности из данных портфолио
2. Из ответа LLM извлекаем потенциальные сущности (CamelCase, кавычки)
3. Проверяем что каждая сущность есть в FactBundle
4. Если нет - это галлюцинация, нужен rewrite или отказ

Хардкод минимален:
- Только стоп-слова (общеупотребительные термины)
- Только маркеры неуверенности (языковые паттерны)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from ..planner.schemas_v3 import FactBundle, GroundingResult

logger = logging.getLogger(__name__)


@dataclass
class GroundingConfig:
    """
    Конфигурация для GroundingVerifier.

    Можно расширять через settings или передавать кастомный конфиг.
    """

    # Минимальная длина слова для проверки как сущности
    min_entity_length: int = 3

    # Маркеры неуверенности в ответе (языковые паттерны, не данные)
    # Это конечный список, расширяется только при необходимости
    speculation_markers_ru: tuple[str, ...] = (
        "вероятно",
        "возможно",
        "предположительно",
        "скорее всего",
        "наверное",
        "похоже",
        "видимо",
    )

    speculation_markers_en: tuple[str, ...] = (
        "probably",
        "possibly",
        "perhaps",
        "maybe",
        "likely",
        "might",
        "seems",
    )

    # Порог уверенности для различных действий
    rewrite_threshold: float = 0.5  # Если confidence < этого - rewrite
    refuse_threshold: float = 0.3   # Если confidence < этого - refuse

    # Максимум ungrounded entities до refuse
    max_ungrounded_for_rewrite: int = 3


# Стоп-слова: общеупотребительные термины которые НЕ являются
# конкретными сущностями портфолио. Это языковые стоп-слова,
# аналогично стоп-словам в NLP (the, a, is и т.д.)
#
# Принцип: если слово встречается практически в любом тексте
# о разработке/IT - оно не сущность.
_STOP_WORDS = frozenset({
    # Общие термины разработки (не конкретные технологии)
    "api", "rest", "http", "https", "json", "xml", "html", "css",
    "sql", "orm", "crud", "mvc", "mvp", "solid", "dry", "kiss",

    # Роли и процессы
    "developer", "разработчик", "backend", "frontend", "fullstack",
    "devops", "engineer", "инженер", "architect", "архитектор",

    # Общие слова о работе
    "проект", "project", "компания", "company", "опыт", "experience",
    "работа", "work", "job", "задача", "task", "система", "system",

    # Персона портфолио (всегда в scope)
    "дмитрий", "dmitry", "dmitrii",
})


class GroundingVerifier:
    """
    Проверяет что ответ LLM основан только на фактах из FactBundle.

    Использует:
    1. Сравнение извлечённых сущностей с FactBundle
    2. Детекцию маркеров неуверенности
    3. Минимальный набор стоп-слов для фильтрации шума
    """

    def __init__(self, config: GroundingConfig | None = None):
        self.config = config or GroundingConfig()
        self._build_speculation_patterns()

    def _build_speculation_patterns(self) -> None:
        """Компилируем regex для маркеров неуверенности."""
        markers = (
            list(self.config.speculation_markers_ru) +
            list(self.config.speculation_markers_en)
        )
        # Создаём один паттерн для всех маркеров
        pattern = r'\b(' + '|'.join(re.escape(m) for m in markers) + r')\b'
        self._speculation_re = re.compile(pattern, re.IGNORECASE)

    def verify(
        self,
        answer: str,
        fact_bundle: FactBundle,
    ) -> GroundingResult:
        """
        Проверить что ответ основан на фактах.

        Args:
            answer: Сгенерированный ответ LLM
            fact_bundle: Бандл фактов с извлечёнными сущностями

        Returns:
            GroundingResult с результатом проверки
        """
        if not answer or not answer.strip():
            return GroundingResult(grounded=True, confidence=1.0, action="accept")

        # 1. Проверка на маркеры неуверенности
        speculation = self._find_speculation(answer)
        if speculation:
            logger.info("Grounding: speculation markers found: %s", speculation)
            return GroundingResult(
                grounded=False,
                ungrounded_entities=speculation,
                confidence=0.4,
                action="rewrite",
                suggested_rewrite=self._remove_speculation(answer, speculation),
            )

        # 2. Извлечь потенциальные сущности из ответа
        candidates = self._extract_entity_candidates(answer)

        # 3. Получить известные сущности из фактов
        known_entities = self._build_known_entities(fact_bundle)

        # 4. Найти ungrounded сущности
        ungrounded = self._find_ungrounded(candidates, known_entities, fact_bundle)

        if not ungrounded:
            return GroundingResult(grounded=True, confidence=1.0, action="accept")

        # 5. Определить action на основе количества ungrounded
        confidence = self._calculate_confidence(len(ungrounded), len(candidates))
        action = self._determine_action(confidence, len(ungrounded))

        logger.info(
            "Grounding: %d/%d ungrounded, confidence=%.2f, action=%s",
            len(ungrounded), len(candidates), confidence, action
        )

        return GroundingResult(
            grounded=False,
            ungrounded_entities=ungrounded,
            confidence=confidence,
            action=action,
            suggested_rewrite=self._suggest_rewrite(answer, ungrounded)
            if action == "rewrite" else None,
        )

    def _find_speculation(self, text: str) -> list[str]:
        """Найти маркеры неуверенности в тексте."""
        matches = self._speculation_re.findall(text)
        return list(set(matches))

    def _extract_entity_candidates(self, text: str) -> set[str]:
        """
        Извлечь потенциальные сущности из текста.

        Используем простые паттерны без ML:
        - CamelCase/PascalCase (PostgreSQL, FastAPI, LangChain)
        - Слова в кавычках
        - UPPER_CASE (SQL, API, AWS)
        """
        candidates = set()

        # 1. Слова в кавычках - явно указанные названия
        quoted = re.findall(r'[«"\']([\w\s\-\.]+)[»"\']', text)
        for q in quoted:
            q = q.strip()
            if len(q) >= self.config.min_entity_length:
                candidates.add(q)

        # 2. CamelCase/PascalCase - типичный паттерн для технологий
        # PostgreSQL, FastAPI, LangChain, ChromaDB, etc.
        camel = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]*)+)\b', text)
        candidates.update(camel)

        # 3. Слова с цифрами - версии, технологии (Python3, Vue2, ES6)
        with_nums = re.findall(r'\b([A-Za-z]+\d+(?:\.\d+)*)\b', text)
        candidates.update(with_nums)

        # 4. ALL_CAPS слова длиной > 2 (SQL, API, AWS, но не I, A)
        upper = re.findall(r'\b([A-Z]{3,})\b', text)
        candidates.update(upper)

        # Фильтруем стоп-слова
        return {c for c in candidates if c.lower() not in _STOP_WORDS}

    def _build_known_entities(self, bundle: FactBundle) -> set[str]:
        """Построить множество известных сущностей из FactBundle."""
        known = set()

        # Добавляем все из bundle (уже в lowercase)
        known.update(t.lower() for t in bundle.technologies)
        known.update(c.lower() for c in bundle.companies)
        known.update(p.lower() for p in bundle.projects)
        known.update(r.lower() for r in bundle.roles)

        # Также добавляем сущности из текстов фактов
        for fact in bundle.facts:
            md = fact.metadata or {}
            for key in ("name", "technology", "project", "company"):
                val = md.get(key)
                if val and isinstance(val, str):
                    known.add(val.lower())

        return known

    def _find_ungrounded(
        self,
        candidates: set[str],
        known: set[str],
        bundle: FactBundle,
    ) -> list[str]:
        """
        Найти сущности которых нет в фактах.

        Использует нечёткое сравнение для частичных совпадений.
        """
        ungrounded = []

        for candidate in candidates:
            c_lower = candidate.lower()

            # Точное совпадение
            if c_lower in known:
                continue

            # Частичное совпадение (PostgreSQL содержит postgres)
            if self._fuzzy_match(c_lower, known):
                continue

            # Проверка в текстах фактов
            if self._in_fact_texts(c_lower, bundle):
                continue

            ungrounded.append(candidate)

        return ungrounded

    def _fuzzy_match(self, candidate: str, known: set[str]) -> bool:
        """Проверить частичное совпадение."""
        for k in known:
            # Одно содержит другое
            if candidate in k or k in candidate:
                return True
            # Общий корень (python, python3)
            if len(candidate) > 4 and len(k) > 4:
                if candidate[:4] == k[:4]:
                    return True
        return False

    def _in_fact_texts(self, candidate: str, bundle: FactBundle) -> bool:
        """Проверить наличие в текстах фактов."""
        for fact in bundle.facts:
            if candidate in fact.text.lower():
                return True
        return False

    def _calculate_confidence(self, ungrounded_count: int, total_count: int) -> float:
        """Рассчитать confidence на основе соотношения."""
        if total_count == 0:
            return 1.0

        grounded_ratio = 1.0 - (ungrounded_count / max(total_count, 1))
        # Штраф за каждую ungrounded сущность
        penalty = ungrounded_count * 0.15
        return max(0.0, min(1.0, grounded_ratio - penalty))

    def _determine_action(
        self,
        confidence: float,
        ungrounded_count: int,
    ) -> Literal["accept", "rewrite", "refuse"]:
        """Определить действие на основе confidence и количества."""
        if ungrounded_count > self.config.max_ungrounded_for_rewrite:
            return "refuse"
        if confidence < self.config.refuse_threshold:
            return "refuse"
        if confidence < self.config.rewrite_threshold:
            return "rewrite"
        return "rewrite"  # Даже при высоком confidence, если есть ungrounded - rewrite

    def _remove_speculation(self, text: str, markers: list[str]) -> str:
        """Удалить маркеры неуверенности из текста."""
        result = text
        for marker in markers:
            # Удаляем маркер с окружающими пробелами/запятыми
            pattern = rf'\s*,?\s*{re.escape(marker)}\s*,?\s*'
            result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', result).strip()

    def _suggest_rewrite(self, text: str, ungrounded: list[str]) -> str:
        """
        Предложить переписанный текст без ungrounded сущностей.

        Удаляем предложения содержащие ungrounded сущности.
        """
        # Разбиваем на предложения
        sentences = re.split(r'(?<=[.!?])\s+', text)
        filtered = []

        for sentence in sentences:
            s_lower = sentence.lower()
            has_ungrounded = any(u.lower() in s_lower for u in ungrounded)
            if not has_ungrounded:
                filtered.append(sentence)

        if filtered:
            return ' '.join(filtered)

        # Все предложения содержат ungrounded - возвращаем safe response
        return "На основе имеющихся данных портфолио не удалось найти запрошенную информацию."


def verify_grounding(answer: str, fact_bundle: FactBundle) -> GroundingResult:
    """Convenience function для проверки grounding."""
    return GroundingVerifier().verify(answer, fact_bundle)
