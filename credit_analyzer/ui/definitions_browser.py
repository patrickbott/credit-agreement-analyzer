"""Helpers for the Definitions Browser tab."""

from __future__ import annotations

from credit_analyzer.processing.definitions import DefinitionsIndex


def filter_definitions(
    index: DefinitionsIndex,
    query: str,
) -> list[tuple[str, str]]:
    """Filter and sort definitions by search query.

    Searches both term names and definition text (case-insensitive).
    Returns list of (term, definition_text) tuples sorted alphabetically by term.
    """
    query_lower = query.strip().lower()
    results: list[tuple[str, str]] = []
    for term, entry in sorted(index.definitions.items()):
        if not query_lower or query_lower in term.lower() or query_lower in entry.text.lower():
            results.append((term, entry.text))
    return results


def paginate_definitions(
    items: list[tuple[str, str]],
    page: int = 0,
    per_page: int = 20,
) -> list[tuple[str, str]]:
    """Return a single page of definitions."""
    start = page * per_page
    return items[start : start + per_page]
