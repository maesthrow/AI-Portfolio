"""
Normalization utilities for tools.

Shared fuzzy matching functions for project and company names.
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def normalize_project_name(name: str) -> str:
    """
    Normalize project name to slug-like format.

    Uses fuzzy matching against actual project slugs from graph.
    """
    name_lower = name.lower().strip()

    # Step 1: Russian → English transliteration
    russian_mappings = {
        "т2": "t2",
        "портфолио": "portfolio",
        "алор": "alor",
        "тейл": "tail",
        "скио": "skio",
        "гиперкипер": "hyperkeeper",
    }
    translated = russian_mappings.get(name_lower, name_lower)

    # Step 1b: Replace common Russian words/abbreviations
    ru_to_en_replacements = {
        "ии": "ai",
        "мл": "ml",
        "бд": "db",
        "портфолио": "portfolio",
        "брокер": "broker",
        "агент": "agent",
    }
    for ru, en in ru_to_en_replacements.items():
        if ru in translated:
            translated = translated.replace(ru, en)

    logger.info(
        "normalize_project_name: input='%s', translated='%s'",
        name, translated
    )

    # Step 2: Get actual project slugs from graph
    try:
        from ...graph.store import get_graph_store
        from ...graph.schema import NodeType

        store = get_graph_store()
        projects = store.get_nodes_by_type(NodeType.PROJECT)
        slugs = [p.slug.lower() for p in projects]

        logger.info(
            "normalize_project_name: found %d project slugs: %s",
            len(slugs), slugs[:10]
        )

        if not slugs:
            logger.warning("No project slugs found in graph, using input as-is")
            return translated.replace(" ", "-")

        # Step 3: Find best match using improved matching
        best_match = None
        best_ratio = 0.0

        for slug in slugs:
            # Check exact match first (highest priority)
            if translated == slug:
                logger.info("normalize_project_name: exact match '%s'", slug)
                return slug

            # Check prefix match: "t2" is prefix of "t2-ml"
            # This is high confidence because user likely means the full project
            if slug.startswith(translated + "-") or slug.startswith(translated + "_"):
                # Prefix match gets high score (0.85)
                ratio = 0.85
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                logger.debug(
                    "normalize_project_name: prefix match '%s' -> '%s', ratio=%.2f",
                    translated, slug, ratio
                )
                continue

            # Check if input is substring of slug (e.g., "portfolio" in "ai-portfolio")
            if translated in slug:
                # Substring match: score based on coverage
                ratio = 0.7 + (len(translated) / len(slug)) * 0.2
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                logger.debug(
                    "normalize_project_name: substring match '%s' in '%s', ratio=%.2f",
                    translated, slug, ratio
                )
                continue

            # Check if slug is substring of input (e.g., "t2" contains no slugs)
            if slug in translated:
                ratio = 0.6 + (len(slug) / len(translated)) * 0.2
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                continue

            # Fuzzy match using SequenceMatcher (for typos, etc.)
            ratio = SequenceMatcher(None, translated, slug).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = slug

        # Use match if confidence is high enough (> 0.5)
        if best_match and best_ratio > 0.5:
            logger.info(
                "normalize_project_name: matched '%s' -> '%s' (ratio=%.2f)",
                name, best_match, best_ratio
            )
            return best_match

        # Fallback: return normalized input
        logger.warning(
            "normalize_project_name: no good match for '%s', best was '%s' (ratio=%.2f)",
            name, best_match, best_ratio
        )
        return translated.replace(" ", "-")

    except Exception as e:
        logger.error(
            "normalize_project_name: failed to get slugs for fuzzy matching: %s",
            e, exc_info=True
        )
        return translated.replace(" ", "-")


def normalize_company_name(name: str) -> str:
    """
    Normalize company name to slug-like format.

    Uses fuzzy matching against actual company slugs from graph.
    """
    name_lower = name.lower().strip()

    # Step 1: Russian → English transliteration
    russian_mappings = {
        "астон": "aston",
        "астоне": "aston",
        "астона": "aston",
        "спарго": "spargo",
        "спарге": "spargo",
        "спарго технологии": "spargo",
        "алор": "alor",
        "фриланс": "freelance",
    }
    translated = russian_mappings.get(name_lower, name_lower)

    # Step 1b: Replace common Russian words/abbreviations
    ru_to_en_replacements = {
        "ии": "ai",
        "мл": "ml",
        "бд": "db",
        "портфолио": "portfolio",
        "брокер": "broker",
        "агент": "agent",
        "технологии": "technologies",
    }
    for ru, en in ru_to_en_replacements.items():
        if ru in translated:
            translated = translated.replace(ru, en)

    logger.info(
        "normalize_company_name: input='%s', translated='%s'",
        name, translated
    )

    # Step 2: Get actual company slugs from graph
    try:
        from ...graph.store import get_graph_store
        from ...graph.schema import NodeType

        store = get_graph_store()
        companies = store.get_nodes_by_type(NodeType.COMPANY)
        slugs = [c.slug.lower() for c in companies]

        logger.info(
            "normalize_company_name: found %d company slugs: %s",
            len(slugs), slugs[:10]
        )

        if not slugs:
            logger.warning("No company slugs found in graph, using input as-is")
            return translated.replace(" ", "-")

        # Step 3: Find best match using improved matching
        best_match = None
        best_ratio = 0.0

        for slug in slugs:
            # Exact match (highest priority)
            if translated == slug:
                logger.info("normalize_company_name: exact match '%s'", slug)
                return slug

            # Prefix match
            if slug.startswith(translated + "-") or slug.startswith(translated + "_"):
                ratio = 0.85
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                continue

            # Substring: input in slug
            if translated in slug:
                ratio = 0.7 + (len(translated) / len(slug)) * 0.2
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                continue

            # Substring: slug in input
            if slug in translated:
                ratio = 0.6 + (len(slug) / len(translated)) * 0.2
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = slug
                continue

            # Fuzzy match
            ratio = SequenceMatcher(None, translated, slug).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = slug

        if best_match and best_ratio > 0.5:
            logger.info(
                "normalize_company_name: matched '%s' -> '%s' (ratio=%.2f)",
                name, best_match, best_ratio
            )
            return best_match

        logger.warning(
            "normalize_company_name: no good match for '%s', best was '%s' (ratio=%.2f)",
            name, best_match, best_ratio
        )
        return translated.replace(" ", "-")

    except Exception as e:
        logger.error(
            "normalize_company_name: failed to get slugs for fuzzy matching: %s",
            e, exc_info=True
        )
        return translated.replace(" ", "-")
