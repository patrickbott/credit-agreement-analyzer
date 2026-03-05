"""Tests for the bm25_store module."""

from __future__ import annotations

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.bm25_store import BM25Result, BM25Store, tokenize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "abc123",
    text: str = "The Borrower shall not incur indebtedness.",
    section_type: str = "negative_covenants",
    section_id: str = "7.01",
) -> Chunk:
    """Build a minimal Chunk for testing."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id=section_id,
        section_title="Test Section",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        section_type=section_type,
        chunk_type="text",
        page_numbers=[10],
        defined_terms_present=[],
        chunk_index=0,
        token_count=15,
    )


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def test_tokenize_basic() -> None:
    """Tokenizer lowercases and splits on whitespace."""
    tokens = tokenize("The Borrower shall NOT incur")
    assert tokens == ["the", "borrower", "shall", "not", "incur"]


def test_tokenize_strips_punctuation() -> None:
    """Punctuation at token edges is stripped."""
    tokens = tokenize('"EBITDA," means (earnings).')
    assert "ebitda" in tokens
    assert "means" in tokens
    assert "earnings" in tokens


def test_tokenize_preserves_dollar_amounts() -> None:
    """Dollar amounts and ratios are preserved as tokens."""
    tokens = tokenize("not to exceed $50,000,000 or 4.50x")
    assert "$50,000,000" in tokens
    assert "4.50x" in tokens


def test_tokenize_empty() -> None:
    assert tokenize("") == []
    assert tokenize("   ") == []


# ---------------------------------------------------------------------------
# BM25Store
# ---------------------------------------------------------------------------


def test_build_and_search() -> None:
    """Basic search returns the most relevant chunk."""
    chunks = [
        _make_chunk(chunk_id="c1", text="Revolving commitment is fifty million dollars"),
        _make_chunk(chunk_id="c2", text="The Borrower shall not incur any indebtedness"),
        _make_chunk(chunk_id="c3", text="EBITDA means earnings before interest taxes depreciation"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("indebtedness borrower", top_k=3)
    assert len(results) > 0
    assert isinstance(results[0], BM25Result)
    assert results[0].chunk.chunk_id == "c2"
    assert results[0].score > 0.0


def test_search_respects_top_k() -> None:
    """Search returns at most top_k results."""
    chunks = [
        _make_chunk(chunk_id=f"c{i}", text=f"Term {i} means something about debt number {i}")
        for i in range(10)
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("debt", top_k=3)
    assert len(results) <= 3


def test_search_with_section_filter() -> None:
    """Section filter restricts results to matching section_type."""
    chunks = [
        _make_chunk(chunk_id="c1", text="incurrence basket for liens", section_type="negative_covenants"),
        _make_chunk(chunk_id="c2", text="revolving facility commitment amount", section_type="facility_terms"),
        _make_chunk(chunk_id="c3", text="restricted payments covenant", section_type="negative_covenants"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("incurrence basket", top_k=5, section_filter="negative_covenants")
    assert len(results) >= 1
    for r in results:
        assert r.chunk.section_type == "negative_covenants"


def test_search_filter_no_matches() -> None:
    """Section filter that matches nothing returns empty list."""
    store = BM25Store()
    store.build_index([_make_chunk(section_type="negative_covenants")])

    results = store.search("debt", section_filter="definitions")
    assert results == []


def test_search_empty_store() -> None:
    """Searching before building an index returns empty list."""
    store = BM25Store()
    assert store.search("anything") == []


def test_search_empty_index() -> None:
    """Building from empty chunks then searching returns empty list."""
    store = BM25Store()
    store.build_index([])
    assert store.search("anything") == []


def test_search_empty_query() -> None:
    """Empty query string returns empty list."""
    store = BM25Store()
    store.build_index([_make_chunk()])
    assert store.search("") == []
    assert store.search("   ") == []


def test_search_no_zero_score_results() -> None:
    """Results with zero BM25 score are excluded."""
    chunks = [
        _make_chunk(chunk_id="c1", text="apples and oranges"),
        _make_chunk(chunk_id="c2", text="restricted payments basket"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("restricted payments", top_k=5)
    for r in results:
        assert r.score > 0.0


def test_rebuild_index_replaces_old() -> None:
    """Building a new index replaces the previous one."""
    store = BM25Store()

    store.build_index([_make_chunk(chunk_id="old", text="old content about liens and security interests")])
    results = store.search("liens security")
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "old"

    store.build_index([_make_chunk(chunk_id="new", text="new content about liens and security interests")])
    results = store.search("liens security")
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "new"


def test_scores_sorted_descending() -> None:
    """Results are returned in descending score order."""
    chunks = [
        _make_chunk(chunk_id="c1", text="debt"),
        _make_chunk(chunk_id="c2", text="debt debt debt indebtedness"),
        _make_chunk(chunk_id="c3", text="debt indebtedness"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("debt indebtedness", top_k=3)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_with_section_types_exclude() -> None:
    """Excluding section types filters out matching chunks."""
    chunks = [
        _make_chunk(chunk_id="c1", text="debt indebtedness covenants", section_type="negative_covenants"),
        _make_chunk(chunk_id="c2", text="debt means defined term", section_type="definitions"),
        _make_chunk(chunk_id="c3", text="debt general provisions", section_type="miscellaneous"),
        _make_chunk(chunk_id="c4", text="debt financial covenants ratio", section_type="financial_covenants"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    results = store.search("debt", top_k=5, section_types_exclude=["definitions", "miscellaneous"])
    result_ids = {r.chunk.chunk_id for r in results}
    # definitions and miscellaneous should be excluded
    assert "c2" not in result_ids
    assert "c3" not in result_ids
    # negative_covenants and financial_covenants should remain
    assert "c1" in result_ids
    assert "c4" in result_ids


def test_search_section_filter_takes_precedence_over_exclude() -> None:
    """section_filter takes precedence over section_types_exclude."""
    chunks = [
        _make_chunk(chunk_id="c1", text="debt", section_type="definitions"),
        _make_chunk(chunk_id="c2", text="debt", section_type="negative_covenants"),
    ]

    store = BM25Store()
    store.build_index(chunks)

    # section_filter=definitions should be used, section_types_exclude ignored
    results = store.search(
        "debt", top_k=5, section_filter="definitions", section_types_exclude=["definitions"]
    )
    assert len(results) == 1
    assert results[0].chunk.section_type == "definitions"
