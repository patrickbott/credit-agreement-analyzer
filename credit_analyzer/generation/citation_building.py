"""Citation building and enrichment functions.

Builds, enriches, and deduplicates citations by matching LLM output
markers to retrieved context chunks.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from credit_analyzer.generation.citation_models import (
    InlineCitation,
    SourceCitation,
)
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk

__all__ = [
    "build_citations_from_chunks",
    "citations_from_chunks",
    "enrich_citations",
    "enrich_inline_citations",
    "inline_citations_from_sources",
]

# ---------------------------------------------------------------------------
# Snippet helpers
# ---------------------------------------------------------------------------

_SNIPPET_MAX_CHARS: int = 200


def _make_snippet(text: str, *, max_chars: int = _SNIPPET_MAX_CHARS) -> str:
    """Extract a short, single-line preview from chunk text."""
    snippet = text[:max_chars].replace("\n", " ").strip()
    if len(text) > max_chars:
        snippet += "..."
    return snippet


def _make_targeted_snippet(
    text: str, keywords: list[str], max_chars: int = 300
) -> str:
    """Extract a snippet centered on the first keyword match in the text.

    Falls back to the first *max_chars* characters if no keyword is found.
    """
    if not keywords:
        return _make_snippet(text, max_chars=max_chars)

    text_lower = text.lower()
    best_pos: int | None = None
    for kw in keywords:
        pos = text_lower.find(kw.lower())
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_pos = pos

    if best_pos is None:
        return _make_snippet(text, max_chars=max_chars)

    # Center a window around the match
    half = max_chars // 2
    start = max(0, best_pos - half)
    end = min(len(text), start + max_chars)
    # Re-adjust start if we hit the end
    start = max(0, end - max_chars)

    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def _section_lookup_candidates(section_id: str) -> list[str]:
    """Return exact and parent section IDs for citation enrichment."""
    candidates = [section_id]
    current = section_id
    trailing_group = re.compile(r"\([A-Za-z0-9]+\)$")
    while trailing_group.search(current):
        current = trailing_group.sub("", current)
        candidates.append(current)
    return candidates


# ---------------------------------------------------------------------------
# Enrichment functions
# ---------------------------------------------------------------------------


def enrich_citations(
    citations: Sequence[SourceCitation],
    chunks: Sequence[HybridChunk],
) -> list[SourceCitation]:
    """Fill in section_title and relevant_text_snippet from retrieved chunks.

    For each citation, finds the best matching chunk by section_id and
    populates the missing fields.  Deduplicates citations that share the
    same section_id, merging their page numbers.

    Args:
        citations: Parsed citations (may have empty title/snippet).
        chunks: The retrieved chunks that provided context.

    Returns:
        Enriched, deduplicated citations.
    """
    section_chunks: dict[str, HybridChunk] = {}
    for hc in chunks:
        sid = hc.chunk.section_id
        if sid not in section_chunks or hc.score > section_chunks[sid].score:
            section_chunks[sid] = hc

    seen_sections: dict[str, int] = {}  # section_id -> index in enriched
    enriched: list[SourceCitation] = []

    for cite in citations:
        hc = None
        for candidate_id in _section_lookup_candidates(cite.section_id):
            hc = section_chunks.get(candidate_id)
            if hc is not None:
                break

        if cite.section_id in seen_sections:
            # Merge page numbers into existing citation
            idx = seen_sections[cite.section_id]
            existing = enriched[idx]
            merged_pages = sorted(set(existing.page_numbers + cite.page_numbers))
            enriched[idx] = SourceCitation(
                section_id=existing.section_id,
                section_title=existing.section_title,
                page_numbers=merged_pages,
                relevant_text_snippet=existing.relevant_text_snippet,
            )
            continue

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

        seen_sections[cite.section_id] = len(enriched) - 1

    return enriched


def enrich_inline_citations(
    citations: Sequence[InlineCitation],
    chunks: Sequence[HybridChunk],
    body: str = "",
) -> list[InlineCitation]:
    """Fill in section_title and snippet from retrieved chunks.

    When *body* is provided, searches chunk text for keywords near each
    marker to produce a more relevant snippet.
    """
    # Collect ALL chunks per section (not just the best), so we can search
    # for the most relevant chunk when a section has many chunks.
    section_all_chunks: dict[str, list[HybridChunk]] = {}
    for hc in chunks:
        sid = hc.chunk.section_id
        section_all_chunks.setdefault(sid, []).append(hc)

    # Build marker -> nearby keywords from the body text
    marker_keywords: dict[int, list[str]] = {}
    if body:
        for m in re.finditer(r"\[(\d+)\]", body):
            num = int(m.group(1))
            # Grab ~80 chars before the marker for keyword extraction
            window_start = max(0, m.start() - 80)
            window = body[window_start:m.start()]
            # Extract dollar amounts, percentages, ratios, and key terms
            keywords = re.findall(
                r"\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?|"
                r"\d+\.\d+[x%]|"
                r"\d+(?:\.\d+)?%|"
                r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",
                window,
            )
            if keywords:
                marker_keywords[num] = keywords

    enriched: list[InlineCitation] = []
    for cite in citations:
        matched_chunks: list[HybridChunk] = []
        for candidate_id in _section_lookup_candidates(cite.section_id):
            matched_chunks = section_all_chunks.get(candidate_id, [])
            if matched_chunks:
                break

        if not matched_chunks:
            enriched.append(cite)
            continue

        # Pick the best chunk -- prefer one containing keywords near the marker
        best_hc = max(matched_chunks, key=lambda hc: hc.score)
        keywords = marker_keywords.get(cite.marker_number, [])
        if keywords and len(matched_chunks) > 1:
            # Score each chunk by how many keywords it contains
            def _keyword_score(hc: HybridChunk, _kws: list[str] = keywords) -> int:
                text_lower = hc.chunk.text.lower()
                return sum(1 for kw in _kws if kw.lower() in text_lower)

            best_by_keywords = max(matched_chunks, key=_keyword_score)
            if _keyword_score(best_by_keywords) > 0:
                best_hc = best_by_keywords

        # Prefer LLM-provided quote; fall back to keyword-targeted snippet
        snippet = cite.snippet
        if not snippet:
            snippet = _make_targeted_snippet(best_hc.chunk.text, keywords)

        enriched.append(
            InlineCitation(
                marker_number=cite.marker_number,
                section_id=cite.section_id,
                section_title=best_hc.chunk.section_title,
                page_numbers=cite.page_numbers or list(best_hc.chunk.page_numbers),
                snippet=snippet,
            )
        )

    return enriched


_BODY_MARKER_RE = re.compile(r"\[(\d+)\]")


def build_citations_from_chunks(
    body: str,
    chunks: Sequence[HybridChunk],
) -> tuple[list[InlineCitation], str]:
    """Build inline citations by mapping [N] markers to numbered context chunks.

    The context prompt numbers chunks [Source 1], [Source 2], etc.
    The LLM uses [1], [2] in its answer. We map N -> chunks[N-1].

    Citations are renumbered sequentially (1, 2, 3...) in the order they
    first appear in the body, and the body text is updated to match.

    Returns:
        A tuple of (citations, renumbered_body).
    """
    if not chunks:
        return [], body

    # Collect unique source numbers in order of first appearance.
    seen_order: list[int] = []
    seen_set: set[int] = set()
    for m in _BODY_MARKER_RE.finditer(body):
        num = int(m.group(1))
        if num not in seen_set:
            idx = num - 1
            if 0 <= idx < len(chunks):
                seen_order.append(num)
                seen_set.add(num)

    if not seen_order:
        return [], body

    # Build old_num -> new_num mapping (sequential starting from 1).
    renumber_map: dict[int, int] = {}
    for new_num, old_num in enumerate(seen_order, 1):
        renumber_map[old_num] = new_num

    # Build citations with new numbering.
    citations: list[InlineCitation] = []
    for old_num in seen_order:
        idx = old_num - 1
        hc = chunks[idx]
        citations.append(InlineCitation(
            marker_number=renumber_map[old_num],
            section_id=hc.chunk.section_id,
            section_title=hc.chunk.section_title,
            page_numbers=list(hc.chunk.page_numbers),
            snippet=_make_snippet(hc.chunk.text),
        ))

    # Rewrite markers in body text.
    def _replace_marker(m: re.Match[str]) -> str:
        num = int(m.group(1))
        new = renumber_map.get(num)
        if new is not None:
            return f"[{new}]"
        return m.group(0)  # Leave unmatched markers as-is

    renumbered_body = _BODY_MARKER_RE.sub(_replace_marker, body)

    return citations, renumbered_body


# Section reference that may appear near a [N] marker in body text.
_NEARBY_SECTION_RE = re.compile(
    r"Section\s+([\d.]+(?:\([A-Za-z0-9]+\))*)",
    re.IGNORECASE,
)


def inline_citations_from_sources(
    body: str,
    sources: Sequence[SourceCitation],
) -> list[InlineCitation]:
    """Build inline citations by matching [N] markers to nearby Section refs.

    Scans the text around each [N] marker for a ``Section X.XX`` mention
    and maps it to the corresponding SourceCitation.  Falls back to
    positional mapping (marker N -> source N) only when no nearby section
    reference is found.
    """
    if not sources:
        return []

    # Build lookup from section_id -> SourceCitation
    source_by_id: dict[str, SourceCitation] = {}
    for src in sources:
        if src.section_id not in source_by_id:
            source_by_id[src.section_id] = src

    citations: list[InlineCitation] = []
    seen: set[int] = set()

    for m in _BODY_MARKER_RE.finditer(body):
        num = int(m.group(1))
        if num in seen:
            continue
        seen.add(num)

        # Look for "Section X.XX" within ~120 chars before the marker
        window_start = max(0, m.start() - 120)
        window = body[window_start:m.start()]
        sec_matches = list(_NEARBY_SECTION_RE.finditer(window))

        matched_src: SourceCitation | None = None
        if sec_matches:
            # Use the closest (last) section reference before the marker
            nearest_sid = sec_matches[-1].group(1)
            matched_src = source_by_id.get(nearest_sid)
            # Try parent section if subsection not found
            if matched_src is None:
                for candidate in _section_lookup_candidates(nearest_sid):
                    matched_src = source_by_id.get(candidate)
                    if matched_src is not None:
                        break

        # Positional fallback
        if matched_src is None:
            idx = num - 1
            if 0 <= idx < len(sources):
                matched_src = sources[idx]

        if matched_src is not None:
            citations.append(
                InlineCitation(
                    marker_number=num,
                    section_id=matched_src.section_id,
                    section_title=matched_src.section_title,
                    page_numbers=list(matched_src.page_numbers),
                    snippet=matched_src.relevant_text_snippet,
                )
            )

    citations.sort(key=lambda c: c.marker_number)
    return citations


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
