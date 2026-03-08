"""Citation data models for credit agreement response parsing.

Contains dataclasses and type aliases used across the citation parsing
and building modules.  This module has NO internal imports to avoid
circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ConfidenceLevel",
    "InlineCitation",
    "SourceCitation",
]

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass
class SourceCitation:
    """A citation pointing back to a specific section of the credit agreement.

    Attributes:
        section_id: The section identifier (e.g. "7.06").
        section_title: Human-readable section title.
        page_numbers: Page numbers where the cited text appears.
        relevant_text_snippet: Brief excerpt from the source chunk.
    """

    section_id: str
    section_title: str
    page_numbers: list[int]
    relevant_text_snippet: str


@dataclass
class InlineCitation:
    """A numbered citation marker embedded in the LLM answer body.

    Attributes:
        marker_number: The citation number (1, 2, 3...).
        section_id: The section identifier (e.g. "7.06").
        section_title: Human-readable section title (filled by enrichment).
        page_numbers: Page numbers where the cited text appears.
        snippet: Source text excerpt for tooltip display.
    """

    marker_number: int
    section_id: str
    section_title: str
    page_numbers: list[int]
    snippet: str
