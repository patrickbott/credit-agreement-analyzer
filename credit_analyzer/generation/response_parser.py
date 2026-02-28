"""Response parsing for LLM output in credit agreement Q&A.

Extracts confidence levels, source citations, and answer bodies from
the structured LLM responses produced by the Q&A and report prompts.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from credit_analyzer.retrieval.hybrid_retriever import HybridChunk

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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
    r"Section\s+([\d.]+)\s*(?:\(pp?\.\s*([\d,\s\-]+)\))?",
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


def enrich_citations(
    citations: Sequence[SourceCitation],
    chunks: Sequence[HybridChunk],
) -> list[SourceCitation]:
    """Fill in section_title and relevant_text_snippet from retrieved chunks.

    For each citation, finds the best matching chunk by section_id and
    populates the missing fields.

    Args:
        citations: Parsed citations (may have empty title/snippet).
        chunks: The retrieved chunks that provided context.

    Returns:
        Enriched citations. Citations with no matching chunk are kept as-is.
    """
    section_chunks: dict[str, HybridChunk] = {}
    for hc in chunks:
        sid = hc.chunk.section_id
        if sid not in section_chunks or hc.score > section_chunks[sid].score:
            section_chunks[sid] = hc

    enriched: list[SourceCitation] = []
    for cite in citations:
        hc = section_chunks.get(cite.section_id)
        if hc is not None:
            snippet = _make_snippet(hc.chunk.text)
            enriched.append(
                SourceCitation(
                    section_id=cite.section_id,
                    section_title=hc.chunk.section_title,
                    page_numbers=cite.page_numbers or list(hc.chunk.page_numbers),
                    relevant_text_snippet=snippet,
                )
            )
        else:
            enriched.append(cite)

    return enriched


def extract_answer_body(text: str) -> str:
    """Strip the Confidence and Sources metadata lines from the answer.

    Args:
        text: Full LLM response text.

    Returns:
        The answer portion with trailing metadata removed.
    """
    earliest_idx = len(text)
    for pattern in (_CONFIDENCE_RE, _SOURCES_LINE_RE):
        match = pattern.search(text)
        if match and match.start() < earliest_idx:
            earliest_idx = match.start()

    return text[:earliest_idx].strip()


def citations_from_chunks(
    chunks: Sequence[HybridChunk],
) -> list[SourceCitation]:
    """Build fallback citations directly from retrieved chunks.

    Used when the LLM response does not include a parseable ``Sources:`` line.

    Args:
        chunks: The retrieved chunks.

    Returns:
        One SourceCitation per unique section among the chunks.
    """
    seen: set[str] = set()
    citations: list[SourceCitation] = []
    for hc in chunks:
        sid = hc.chunk.section_id
        if sid in seen:
            continue
        seen.add(sid)
        citations.append(
            SourceCitation(
                section_id=sid,
                section_title=hc.chunk.section_title,
                page_numbers=list(hc.chunk.page_numbers),
                relevant_text_snippet=_make_snippet(hc.chunk.text),
            )
        )
    return citations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SNIPPET_MAX_CHARS: int = 200


def _make_snippet(text: str) -> str:
    """Create a short text snippet from a chunk's full text.

    Args:
        text: The full chunk text.

    Returns:
        A truncated, single-line snippet.
    """
    snippet = text[:_SNIPPET_MAX_CHARS].replace("\n", " ").strip()
    if len(text) > _SNIPPET_MAX_CHARS:
        snippet += "..."
    return snippet
