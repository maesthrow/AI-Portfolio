"""
EntityRegistry - реестр сущностей портфолио.

Обеспечивает маппинг алиасов (названий) на канонические slug'и.
Используется для извлечения сущностей из вопросов пользователя.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .search_types import Entity, EntityType


class EntityRegistry:
    """
    Реестр сущностей портфолио.

    Хранит маппинг alias -> (type, slug, name) для проектов,
    компаний, технологий и профиля.

    Заполняется при инициализации графа из ExportPayload.
    """

    def __init__(self):
        # alias (lowercase) -> (EntityType, slug, canonical_name)
        self._aliases: Dict[str, Tuple[EntityType, str, str]] = {}
        # type -> list of slugs
        self._by_type: Dict[EntityType, List[str]] = {t: [] for t in EntityType}

    def register(
        self,
        entity_type: EntityType,
        slug: str,
        name: str,
        aliases: List[str] | None = None,
    ) -> None:
        """
        Зарегистрировать сущность с алиасами.

        Args:
            entity_type: Тип сущности
            slug: Уникальный идентификатор
            name: Каноническое название
            aliases: Дополнительные алиасы (сокращения, варианты написания)
        """
        canonical = (entity_type, slug, name)

        # Регистрация по slug
        self._aliases[slug.lower()] = canonical

        # Регистрация по имени
        name_key = name.lower().strip()
        if name_key:
            self._aliases[name_key] = canonical

        # Регистрация дополнительных алиасов
        for alias in aliases or []:
            alias_key = alias.lower().strip()
            if alias_key:
                self._aliases[alias_key] = canonical

        # Отслеживание по типу
        if slug not in self._by_type[entity_type]:
            self._by_type[entity_type].append(slug)

    def find_entity(self, text: str) -> Entity | None:
        """
        Найти сущность по тексту.

        Сначала ищет точное совпадение, затем частичное.

        Args:
            text: Текст для поиска (название, slug, алиас)

        Returns:
            Entity или None если не найдено
        """
        key = text.lower().strip()
        if not key:
            return None

        # Точное совпадение
        if key in self._aliases:
            etype, slug, name = self._aliases[key]
            return Entity(type=etype, slug=slug, name=name, confidence=1.0)

        # Частичное совпадение (alias содержит key или key содержит alias)
        for alias, (etype, slug, name) in self._aliases.items():
            # Пропускаем слишком короткие алиасы для частичного поиска
            if len(alias) < 3 or len(key) < 3:
                continue
            if key in alias or alias in key:
                return Entity(type=etype, slug=slug, name=name, confidence=0.7)

        return None

    def extract_entities(self, question: str) -> List[Entity]:
        """
        Извлечь все упомянутые сущности из вопроса.

        Токенизирует вопрос и проверяет каждое слово/фразу.

        Args:
            question: Вопрос пользователя

        Returns:
            Список найденных сущностей (без дубликатов по slug)
        """
        found: List[Entity] = []
        seen_slugs: set = set()

        # Извлекаем слова и n-граммы
        words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9\-\.]+", question.lower())

        # Проверяем отдельные слова
        for word in words:
            if len(word) < 2:
                continue
            entity = self.find_entity(word)
            if entity and entity.slug not in seen_slugs:
                found.append(entity)
                seen_slugs.add(entity.slug)

        # Проверяем биграммы (два соседних слова)
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            entity = self.find_entity(bigram)
            if entity and entity.slug not in seen_slugs:
                found.append(entity)
                seen_slugs.add(entity.slug)

        return found

    def list_by_type(self, entity_type: EntityType) -> List[str]:
        """Получить список slug'ов по типу сущности."""
        return list(self._by_type.get(entity_type, []))

    def clear(self) -> None:
        """Очистить реестр."""
        self._aliases.clear()
        self._by_type = {t: [] for t in EntityType}

    def stats(self) -> Dict[str, int]:
        """Статистика по типам сущностей."""
        return {t.value: len(slugs) for t, slugs in self._by_type.items()}


# === Global singleton ===

_REGISTRY: EntityRegistry | None = None


def get_entity_registry() -> EntityRegistry:
    """Получить глобальный реестр сущностей."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = EntityRegistry()
    return _REGISTRY


def reset_entity_registry() -> EntityRegistry:
    """Сбросить и вернуть новый реестр."""
    global _REGISTRY
    _REGISTRY = EntityRegistry()
    return _REGISTRY
