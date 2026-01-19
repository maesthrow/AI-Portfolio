"""
Entity ID parsing utilities.

Provides consistent parsing of entity IDs in format "type:key" (e.g., "company:aston").
This is P0 requirement to fix entity routing issues where entity_type was being lost.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EntityType = Literal["company", "project", "technology", "person"]

VALID_ENTITY_TYPES: frozenset[str] = frozenset({
    "company",
    "project",
    "technology",
    "person",
})


@dataclass(frozen=True, slots=True)
class ParsedEntityId:
    """Parsed entity ID with type and key separated."""

    entity_type: EntityType | None
    key: str
    raw: str

    @property
    def is_company(self) -> bool:
        """Check if this is a company entity."""
        return self.entity_type == "company"

    @property
    def is_project(self) -> bool:
        """Check if this is a project entity."""
        return self.entity_type == "project"

    @property
    def is_technology(self) -> bool:
        """Check if this is a technology entity."""
        return self.entity_type == "technology"


def parse_entity_id(entity_id: str | None) -> ParsedEntityId:
    """
    Parse entity ID string into structured ParsedEntityId.

    Handles formats:
    - "company:aston" → ParsedEntityId(entity_type="company", key="aston", raw="company:aston")
    - "project:t2" → ParsedEntityId(entity_type="project", key="t2", raw="project:t2")
    - "aston" → ParsedEntityId(entity_type=None, key="aston", raw="aston")
    - None → ParsedEntityId(entity_type=None, key="", raw="")

    Args:
        entity_id: Entity ID string, optionally prefixed with type

    Returns:
        ParsedEntityId with separated type and key
    """
    if not entity_id:
        return ParsedEntityId(entity_type=None, key="", raw="")

    raw = entity_id.strip()
    if not raw:
        return ParsedEntityId(entity_type=None, key="", raw="")

    if ":" in raw:
        parts = raw.split(":", 1)
        potential_type = parts[0].lower().strip()
        key = parts[1].strip()

        if potential_type in VALID_ENTITY_TYPES:
            return ParsedEntityId(
                entity_type=potential_type,  # type: ignore[arg-type]
                key=key,
                raw=raw,
            )

    # No valid type prefix found, treat entire string as key
    return ParsedEntityId(entity_type=None, key=raw, raw=raw)
