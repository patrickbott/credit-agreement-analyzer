"""Tests for inline citation parsing, enrichment, and rendering."""

from __future__ import annotations

from credit_analyzer.generation.response_parser import (
    InlineCitation,
    enrich_inline_citations,
    extract_answer_body,
    parse_inline_citations,
)
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk
from credit_analyzer.ui.theme import render_inline_citations


def _make_chunk(section_id: str, section_title: str, text: str, score: float = 0.9) -> HybridChunk:
    """Create a minimal HybridChunk for testing."""
    chunk = Chunk(
        chunk_id="test123",
        text=text,
        section_id=section_id,
        section_title=section_title,
        article_number=1,
        article_title="Article I",
        section_type="covenants",
        chunk_type="text",
        page_numbers=[45, 46],
        defined_terms_present=[],
        chunk_index=0,
        token_count=50,
    )
    return HybridChunk(chunk=chunk, score=score, source="vector")


# ---------------------------------------------------------------------------
# parse_inline_citations
# ---------------------------------------------------------------------------


def test_parse_inline_citations_basic():
    text = (
        "The facility is $500M [1] with a leverage ratio of 4.5x [2].\n\n"
        "Confidence: HIGH\n"
        "References:\n"
        "[1] Section 2.01 (pp. 15-16)\n"
        "[2] Section 7.06(a) (pp. 45-46)\n"
        "Sources: Section 2.01 (pp. 15-16), Section 7.06(a) (pp. 45-46)\n"
    )
    citations = parse_inline_citations(text)
    assert len(citations) == 2
    assert citations[0].marker_number == 1
    assert citations[0].section_id == "2.01"
    assert citations[0].page_numbers == [15, 16]
    assert citations[1].marker_number == 2
    assert citations[1].section_id == "7.06(a)"
    assert citations[1].page_numbers == [45, 46]


def test_parse_inline_citations_empty():
    text = "No references here.\nConfidence: HIGH\nSources: Section 2.01"
    citations = parse_inline_citations(text)
    assert citations == []


def test_parse_inline_citations_deduplicates():
    text = (
        "References:\n"
        "[1] Section 2.01 (pp. 15)\n"
        "[1] Section 2.01 (pp. 15)\n"
        "[2] Section 3.01\n"
    )
    citations = parse_inline_citations(text)
    assert len(citations) == 2


def test_parse_inline_citations_sorted():
    text = (
        "References:\n"
        "[3] Section 9.01\n"
        "[1] Section 2.01\n"
        "[2] Section 7.06\n"
    )
    citations = parse_inline_citations(text)
    assert [c.marker_number for c in citations] == [1, 2, 3]


# ---------------------------------------------------------------------------
# enrich_inline_citations
# ---------------------------------------------------------------------------


def test_enrich_inline_citations():
    raw = [
        InlineCitation(marker_number=1, section_id="2.01", section_title="", page_numbers=[15], snippet=""),
    ]
    chunks = [_make_chunk("2.01", "Commitments", "The total commitment is $500,000,000.")]
    enriched = enrich_inline_citations(raw, chunks)
    assert len(enriched) == 1
    assert enriched[0].section_title == "Commitments"
    assert enriched[0].snippet != ""
    assert "500,000,000" in enriched[0].snippet


def test_enrich_inline_citations_no_match():
    raw = [
        InlineCitation(marker_number=1, section_id="99.99", section_title="", page_numbers=[], snippet=""),
    ]
    enriched = enrich_inline_citations(raw, [])
    assert len(enriched) == 1
    assert enriched[0].section_title == ""
    assert enriched[0].snippet == ""


# ---------------------------------------------------------------------------
# extract_answer_body strips references
# ---------------------------------------------------------------------------


def test_extract_answer_body_strips_references():
    text = (
        "The facility amount is $500M [1].\n\n"
        "References:\n"
        "[1] Section 2.01 (pp. 15-16)\n"
        "Confidence: HIGH\n"
        "Sources: Section 2.01 (pp. 15-16)\n"
    )
    body = extract_answer_body(text)
    assert "References:" not in body
    assert "Confidence:" not in body
    assert "[1]" in body  # markers stay in the body
    assert "$500M" in body


# ---------------------------------------------------------------------------
# render_inline_citations (HTML)
# ---------------------------------------------------------------------------


def test_render_inline_citations_with_tooltips():
    citations = [
        InlineCitation(
            marker_number=1,
            section_id="2.01",
            section_title="Commitments",
            page_numbers=[15, 16],
            snippet="Total commitment of $500M.",
        ),
    ]
    html = render_inline_citations("Amount is $500M [1].", citations)
    assert 'class="cite-marker"' in html
    assert 'class="cite-tooltip"' in html
    assert "Section 2.01 | Commitments" in html
    assert "15, 16" in html
    assert "Amount is $500M" in html


def test_render_inline_citations_no_citations():
    html = render_inline_citations("Plain text [1] here.", [])
    assert "cite-marker" not in html
    assert "[1]" in html  # markers left as escaped text


def test_render_inline_citations_unknown_marker():
    citations = [
        InlineCitation(
            marker_number=1,
            section_id="2.01",
            section_title="Test",
            page_numbers=[10],
            snippet="test",
        ),
    ]
    html = render_inline_citations("Claim [1] and unknown [3].", citations)
    assert 'class="cite-marker">[1]' in html  # [1] becomes tooltip
    # [3] still renders as superscript for visual consistency
    assert 'class="cite-marker">[3]' in html
    assert "cite-marker" in html
