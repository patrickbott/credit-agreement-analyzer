"""Tests for the hybrid_retriever module."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.retrieval.bm25_store import BM25Result, BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    normalize_scores,
)
from credit_analyzer.retrieval.vector_store import RetrievedChunk, VectorStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "abc",
    text: str = "The Borrower shall not incur Indebtedness.",
    section_type: str = "negative_covenants",
) -> Chunk:
    """Build a minimal Chunk for testing."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id="7.01",
        section_title="Indebtedness",
        article_number=7,
        article_title="NEGATIVE COVENANTS",
        section_type=section_type,
        chunk_type="text",
        page_numbers=[10],
        defined_terms_present=[],
        chunk_index=0,
        token_count=15,
    )


def _make_retriever(
    vector_results: list[RetrievedChunk] | None = None,
    bm25_results: list[BM25Result] | None = None,
    definitions: dict[str, str] | None = None,
) -> HybridRetriever:
    """Build a HybridRetriever with mocked dependencies."""
    mock_vector_store = MagicMock(spec=VectorStore)
    mock_vector_store.search.return_value = vector_results or []

    mock_bm25_store = MagicMock(spec=BM25Store)
    mock_bm25_store.search.return_value = bm25_results or []

    mock_embedder = MagicMock(spec=Embedder)
    mock_embedder.embed_query.return_value = [0.1] * 384

    defn_index = DefinitionsIndex(definitions=definitions or {})

    return HybridRetriever(
        vector_store=mock_vector_store,
        bm25_store=mock_bm25_store,
        embedder=mock_embedder,
        definitions_index=defn_index,
    )


# ---------------------------------------------------------------------------
# normalize_scores
# ---------------------------------------------------------------------------


def test_normalize_scores_basic() -> None:
    """Min-max normalization maps to [0, 1]."""
    result = normalize_scores([1.0, 3.0, 5.0])
    assert result == [0.0, 0.5, 1.0]


def test_normalize_scores_identical() -> None:
    """Identical scores all normalize to 1.0."""
    result = normalize_scores([2.0, 2.0, 2.0])
    assert result == [1.0, 1.0, 1.0]


def test_normalize_scores_empty() -> None:
    assert normalize_scores([]) == []


def test_normalize_scores_single() -> None:
    """Single score normalizes to 1.0."""
    assert normalize_scores([42.0]) == [1.0]


# ---------------------------------------------------------------------------
# Hybrid retrieval — merging
# ---------------------------------------------------------------------------


def test_vector_only_results() -> None:
    """When BM25 returns nothing, vector results are used."""
    chunk = _make_chunk(chunk_id="v1")
    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
    )

    result = retriever.retrieve("test query", "doc1", top_k=5)

    assert len(result.chunks) == 1
    assert result.chunks[0].chunk.chunk_id == "v1"
    assert result.chunks[0].source == "vector"


def test_bm25_only_results() -> None:
    """When vector returns nothing, BM25 results are used."""
    chunk = _make_chunk(chunk_id="b1")
    retriever = _make_retriever(
        bm25_results=[BM25Result(chunk=chunk, score=5.0)],
    )

    result = retriever.retrieve("test query", "doc1", top_k=5)

    assert len(result.chunks) == 1
    assert result.chunks[0].chunk.chunk_id == "b1"
    assert result.chunks[0].source == "bm25"


def test_both_sources_merged() -> None:
    """A chunk found by both sources gets source='both' and combined score."""
    chunk_v = _make_chunk(chunk_id="shared")
    chunk_b = _make_chunk(chunk_id="shared")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk_v, score=0.8)],
        bm25_results=[BM25Result(chunk=chunk_b, score=3.0)],
    )

    result = retriever.retrieve("test query", "doc1", top_k=5)

    assert len(result.chunks) == 1
    assert result.chunks[0].chunk.chunk_id == "shared"
    assert result.chunks[0].source == "both"


def test_deduplication_keeps_higher_combined() -> None:
    """When a chunk appears in both, its score is the sum of weighted normalized scores."""
    chunk = _make_chunk(chunk_id="dup")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        bm25_results=[BM25Result(chunk=chunk, score=5.0)],
    )

    result = retriever.retrieve("query", "doc1", top_k=5)

    assert len(result.chunks) == 1
    # Single result in each list -> normalized to 1.0 each
    # Combined: VECTOR_WEIGHT * 1.0 + BM25_WEIGHT * 1.0 = 0.6 + 0.4 = 1.0
    assert result.chunks[0].score > 0.5


def test_top_k_respected() -> None:
    """Only top_k results are returned even if more are available."""
    chunks_v = [
        RetrievedChunk(chunk=_make_chunk(chunk_id=f"v{i}"), score=0.9 - i * 0.1)
        for i in range(5)
    ]
    chunks_b = [
        BM25Result(chunk=_make_chunk(chunk_id=f"b{i}"), score=5.0 - i)
        for i in range(5)
    ]

    retriever = _make_retriever(vector_results=chunks_v, bm25_results=chunks_b)
    result = retriever.retrieve("query", "doc1", top_k=3)

    assert len(result.chunks) <= 3


def test_results_sorted_by_score() -> None:
    """Results are returned in descending score order."""
    retriever = _make_retriever(
        vector_results=[
            RetrievedChunk(chunk=_make_chunk(chunk_id="low"), score=0.1),
            RetrievedChunk(chunk=_make_chunk(chunk_id="high"), score=0.9),
        ],
    )

    result = retriever.retrieve("query", "doc1", top_k=5)
    scores = [hc.score for hc in result.chunks]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Definition injection
# ---------------------------------------------------------------------------


def test_definitions_injected() -> None:
    """Defined terms found in retrieved chunks are injected."""
    chunk = _make_chunk(
        chunk_id="c1",
        text="The Borrower may make Restricted Payments up to the Available Amount.",
    )

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={
            "Borrower": "the entity on the signature page",
            "Restricted Payments": "dividends, distributions, etc.",
            "Available Amount": "the sum of X and Y",
        },
    )

    result = retriever.retrieve("restricted payments", "doc1", top_k=5)

    assert "Borrower" in result.injected_definitions
    assert "Restricted Payments" in result.injected_definitions
    assert "Available Amount" in result.injected_definitions


def test_definitions_capped_at_max() -> None:
    """No more than MAX_DEFINITIONS_INJECTED definitions are returned."""
    # Build text mentioning many terms
    terms = {f"Term{i}": f"definition {i}" for i in range(20)}
    text = " ".join(terms.keys())
    chunk = _make_chunk(chunk_id="c1", text=text)

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions=terms,
    )

    result = retriever.retrieve("query", "doc1", top_k=5)

    from credit_analyzer.config import MAX_DEFINITIONS_INJECTED

    assert len(result.injected_definitions) <= MAX_DEFINITIONS_INJECTED


def test_no_definitions_when_disabled() -> None:
    """inject_definitions=False skips definition injection."""
    chunk = _make_chunk(chunk_id="c1", text="The Borrower shall comply.")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={"Borrower": "the company"},
    )

    result = retriever.retrieve("query", "doc1", inject_definitions=False)

    assert result.injected_definitions == {}


def test_empty_results_no_definitions() -> None:
    """No definitions injected when retrieval returns nothing."""
    retriever = _make_retriever(definitions={"Borrower": "the company"})
    result = retriever.retrieve("query", "doc1")

    assert result.chunks == []
    assert result.injected_definitions == {}


# ---------------------------------------------------------------------------
# Return type checks
# ---------------------------------------------------------------------------


def test_return_types() -> None:
    """Result has the expected types."""
    chunk = _make_chunk(chunk_id="c1")
    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
    )

    result = retriever.retrieve("query", "doc1")

    assert isinstance(result, RetrievalResult)
    assert isinstance(result.chunks[0], HybridChunk)
    assert isinstance(result.chunks[0].chunk, Chunk)
    assert isinstance(result.chunks[0].score, float)
    assert isinstance(result.injected_definitions, dict)
