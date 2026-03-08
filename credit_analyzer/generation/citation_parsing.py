"""Citation parsing functions for LLM response text.

Extracts confidence levels, source citations, inline citations, and
answer bodies from the structured LLM responses produced by the Q&A
and report prompts.
"""

from __future__ import annotations

import logging
import re

from credit_analyzer.generation.citation_models import (
    ConfidenceLevel,
    InlineCitation,
    SourceCitation,
)

logger = logging.getLogger(__name__)

__all__ = [
    "extract_answer_body",
    "parse_confidence",
    "parse_inline_citations",
    "parse_page_numbers",
    "parse_sources_from_llm",
]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches "Confidence: HIGH" (case-insensitive, tolerant of whitespace).
# Also handles markdown bold like **Confidence: HIGH** or **Confidence:** HIGH.
_CONFIDENCE_RE = re.compile(
    r"(?:^|\n)\s*\*{0,2}Confidence\*{0,2}\s*:\s*\*{0,2}\s*(HIGH|MEDIUM|LOW)\b",
    re.IGNORECASE,
)

# Matches "Sources: Section 7.06 (pp. 45-46), ...".
# Also handles markdown bold like **Sources:** ...
_SOURCES_LINE_RE = re.compile(
    r"(?:^|\n)\s*\*{0,2}Sources?\*{0,2}\s*:\s*\*{0,2}\s*(.+)",
    re.IGNORECASE,
)

# Individual citation like "Section 7.06 (pp. 45-46)" or "Section 7.06"
_CITATION_RE = re.compile(
    r"Section\s+([\d.]+(?:\([A-Za-z0-9]+\))*)\s*(?:\(pp?\.\s*([\d,\s\-]+)\))?",
    re.IGNORECASE,
)

# Matches a "References:" block containing numbered citation lines.
# Tolerant of blank lines and optional whitespace between header and entries.
_REFERENCES_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*\*{0,2}References?\*{0,2}\s*:\s*\n\s*\n?((?:\s*\[\d+\]\s*.+\n?\s*\n?)+)",
    re.IGNORECASE,
)

# Individual reference line: [1] Section 7.06(a) (pp. 45-46) -- "quote"
# Group 1: marker number, 2: section id, 3: page numbers, 4: optional quote
_REFERENCE_LINE_RE = re.compile(
    r"\[(\d+)\]\s*Section\s+([\d.]+(?:\([A-Za-z0-9]+\))*)\s*"
    r"(?:\(pp?\.\s*([\d,\s\-]+)\))?"
    r'(?:\s*--\s*["\u201c](.+?)["\u201d])?',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Parsing functions
# ---------------------------------------------------------------------------


def parse_confidence(text: str) -> ConfidenceLevel:
    """Extract the confidence level from the LLM response text.

    Args:
        text: Full LLM response text.

    Returns:
        The parsed confidence level, defaulting to ``LOW`` if not found.
    """
    match = _CONFIDENCE_RE.search(text)
    if match:
        raw = match.group(1).upper()
        if raw in ("HIGH", "MEDIUM", "LOW"):
            return raw  # type: ignore[return-value]
    logger.debug("No confidence level found in LLM response; defaulting to LOW.")
    return "LOW"


def parse_page_numbers(pages_str: str) -> list[int]:
    """Parse a page number string like ``'45-46, 50'`` into a sorted int list.

    Args:
        pages_str: Comma/hyphen-separated page references.

    Returns:
        Sorted list of unique page numbers.
    """
    pages: set[int] = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
                pages.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                pages.add(int(part))
            except ValueError:
                continue
    return sorted(pages)


def parse_sources_from_llm(text: str) -> list[SourceCitation]:
    """Parse source citations from the LLM's ``Sources:`` line.

    Args:
        text: Full LLM response text.

    Returns:
        List of parsed SourceCitation objects (title and snippet are empty
        until enriched from retrieved chunks).
    """
    match = _SOURCES_LINE_RE.search(text)
    if not match:
        return []

    sources_text = match.group(1)
    citations: list[SourceCitation] = []

    for cite_match in _CITATION_RE.finditer(sources_text):
        section_id = cite_match.group(1)
        page_str = cite_match.group(2)
        page_numbers = parse_page_numbers(page_str) if page_str else []
        citations.append(
            SourceCitation(
                section_id=section_id,
                section_title="",
                page_numbers=page_numbers,
                relevant_text_snippet="",
            )
        )

    return citations


def parse_inline_citations(text: str) -> list[InlineCitation]:
    """Parse the References block to build an inline citation index.

    Returns an ordered list of InlineCitation objects. Returns an empty
    list if no References block is found (backwards-compatible fallback).
    """
    match = _REFERENCES_BLOCK_RE.search(text)
    if not match:
        return []

    refs_text = match.group(1)
    citations: list[InlineCitation] = []
    seen_numbers: set[int] = set()

    for ref_match in _REFERENCE_LINE_RE.finditer(refs_text):
        num = int(ref_match.group(1))
        if num in seen_numbers:
            continue
        seen_numbers.add(num)
        section_id = ref_match.group(2)
        page_str = ref_match.group(3)
        page_numbers = parse_page_numbers(page_str) if page_str else []
        quote = (ref_match.group(4) or "").strip()
        citations.append(
            InlineCitation(
                marker_number=num,
                section_id=section_id,
                section_title="",
                page_numbers=page_numbers,
                snippet=quote,
            )
        )

    citations.sort(key=lambda c: c.marker_number)
    return citations


def extract_answer_body(text: str) -> str:
    """Strip the Confidence and Sources metadata lines from the answer.

    Args:
        text: Full LLM response text.

    Returns:
        The answer portion with trailing metadata removed.
    """
    earliest_idx = len(text)
    for pattern in (_CONFIDENCE_RE, _SOURCES_LINE_RE, _REFERENCES_BLOCK_RE):
        match = pattern.search(text)
        if match and match.start() < earliest_idx:
            earliest_idx = match.start()

    return text[:earliest_idx].strip()
