"""Tests for inline citation parsing, enrichment, and rendering."""

from __future__ import annotations

from credit_analyzer.generation.response_parser import (
    InlineCitation,
    build_citations_from_chunks,
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
# build_citations_from_chunks (new primary path)
# ---------------------------------------------------------------------------


def test_build_citations_from_chunks_basic():
    chunks = [
        _make_chunk("2.01", "Commitments", "The aggregate Commitments are $500,000,000."),
        _make_chunk("7.06", "Financial Covenants", "Total Leverage Ratio of 4.50:1.00."),
    ]
    body = "The facility is $500M [1] with a leverage ratio of 4.5x [2]."
    citations, new_body = build_citations_from_chunks(body, chunks)
    assert len(citations) == 2
    assert citations[0].marker_number == 1
    assert citations[0].section_id == "2.01"
    assert citations[0].section_title == "Commitments"
    assert citations[0].page_numbers == [45, 46]
    assert "500,000,000" in citations[0].snippet
    assert citations[1].marker_number == 2
    assert citations[1].section_id == "7.06"
    # Body unchanged when already sequential
    assert new_body == body


def test_build_citations_from_chunks_out_of_range():
    chunks = [
        _make_chunk("2.01", "Commitments", "Text."),
    ]
    body = "Claim [1] and out-of-range [5]."
    citations, new_body = build_citations_from_chunks(body, chunks)
    assert len(citations) == 1
    assert citations[0].marker_number == 1
    # Out-of-range marker left as-is
    assert "[5]" in new_body


def test_build_citations_from_chunks_empty():
    citations, _body = build_citations_from_chunks("No markers.", [])
    assert citations == []


def test_build_citations_from_chunks_deduplicates():
    chunks = [
        _make_chunk("2.01", "Commitments", "Text."),
    ]
    body = "First [1] and again [1]."
    citations, _ = build_citations_from_chunks(body, chunks)
    assert len(citations) == 1


def test_build_citations_from_chunks_renumbers_sequentially():
    """Sparse markers like [3], [7], [12] get renumbered to [1], [2], [3]."""
    chunks = [
        _make_chunk("1.01", "Definitions", "Text A."),
        _make_chunk("2.01", "Commitments", "Text B."),
        _make_chunk("3.01", "Conditions", "Text C."),
        _make_chunk("4.01", "Representations", "Text D."),
        _make_chunk("5.01", "Covenants", "Text E."),
        _make_chunk("6.01", "Events of Default", "Text F."),
        _make_chunk("7.06", "Financial Covenants", "Text G."),
    ]
    body = "Claim A [3] then claim B [7] then claim C [5]."
    citations, new_body = build_citations_from_chunks(body, chunks)
    # Should renumber to 1, 2, 3 in order of appearance
    assert [c.marker_number for c in citations] == [1, 2, 3]
    assert citations[0].section_id == "3.01"  # was [3]
    assert citations[1].section_id == "7.06"  # was [7]
    assert citations[2].section_id == "5.01"  # was [5]
    # Body markers renumbered
    assert "[1]" in new_body
    assert "[2]" in new_body
    assert "[3]" in new_body
    assert "[7]" not in new_body


def test_build_citations_from_chunks_already_sequential():
    """When markers are already 1, 2, 3, body is unchanged."""
    chunks = [
        _make_chunk("2.01", "Commitments", "Text A."),
        _make_chunk("7.06", "Financial Covenants", "Text B."),
        _make_chunk("9.01", "Events of Default", "Text C."),
    ]
    body = "First [1] then second [2] then third [3]."
    citations, new_body = build_citations_from_chunks(body, chunks)
    assert [c.marker_number for c in citations] == [1, 2, 3]
    assert new_body == body


# ---------------------------------------------------------------------------
# parse_inline_citations (legacy, still kept in module)
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


def test_parse_inline_citations_with_quotes():
    text = (
        "References:\n"
        '[1] Section 2.01 (pp. 15-16) -- "The aggregate Commitments are $500,000,000"\n'
        '[2] Section 7.06(a) (pp. 45) -- "a Total Leverage Ratio of 4.50:1.00"\n'
    )
    citations = parse_inline_citations(text)
    assert len(citations) == 2
    assert citations[0].snippet == "The aggregate Commitments are $500,000,000"
    assert citations[1].snippet == "a Total Leverage Ratio of 4.50:1.00"


def test_parse_inline_citations_mixed_quote_and_no_quote():
    text = (
        "References:\n"
        '[1] Section 2.01 (pp. 15) -- "Total commitment of $500M"\n'
        "[2] Section 7.06 (pp. 45)\n"
    )
    citations = parse_inline_citations(text)
    assert len(citations) == 2
    assert citations[0].snippet == "Total commitment of $500M"
    assert citations[1].snippet == ""


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


def test_render_inline_citations_with_footnotes():
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
    # Superscript marker in body
    assert 'class="cite-marker"' in html
    # Footnotes section rendered below
    assert 'class="cite-footnotes"' in html
    assert "Section 2.01 | Commitments" in html
    assert "15, 16" in html
    assert "Total commitment of &#36;500M." in html
    assert "Amount is &#36;500M" in html
    # No tooltip markup
    assert "cite-tooltip" not in html


def test_render_inline_citations_no_citations():
    html = render_inline_citations("Plain text [1] here.", [])
    assert "cite-marker" not in html
    assert "cite-footnotes" not in html
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
    assert 'class="cite-marker">[1]' in html
    assert 'class="cite-marker">[3]' in html
    # [1] has a footnote entry, [3] does not
    assert "Section 2.01 | Test" in html
    assert 'class="cite-footnotes"' in html
