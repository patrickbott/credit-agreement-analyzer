"""Tests for the hybrid_retriever module."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionEntry, DefinitionsIndex
from credit_analyzer.retrieval.bm25_store import BM25Result, BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    _query_term_overlap,  # type: ignore[reportPrivateUsage]
    merge_multi_query_results,
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
    indexed_chunks: list[Chunk] | None = None,
) -> HybridRetriever:
    """Build a HybridRetriever with mocked dependencies.

    Args:
        indexed_chunks: Chunks exposed via bm25_store.chunks. Used for
            both definition chunk lookup (chunk_type="definition") and
            corpus-level term frequency computation.
    """
    mock_vector_store = MagicMock(spec=VectorStore)
    mock_vector_store.search.return_value = vector_results or []

    mock_bm25_store = MagicMock(spec=BM25Store)
    mock_bm25_store.search.return_value = bm25_results or []
    # Expose chunks property for definition chunk lookup + term frequency
    captured_chunks = indexed_chunks or []
    type(mock_bm25_store).chunks = property(
        lambda self: captured_chunks
    )

    mock_embedder = MagicMock(spec=Embedder)
    mock_embedder.embed_query.return_value = [0.1] * 384

    defn_entries = {
        term: DefinitionEntry(text=text)
        for term, text in (definitions or {}).items()
    }
    defn_index = DefinitionsIndex(definitions=defn_entries)

    return HybridRetriever(
        vector_store=mock_vector_store,
        bm25_store=mock_bm25_store,
        embedder=mock_embedder,
        definitions_index=defn_index,
    )


def _make_ubiquitous_corpus(term: str, total: int = 8) -> list[Chunk]:
    """Build corpus chunks where a term appears in >25% of them.

    Creates ``total`` chunks with the term in the first ``total - 1``
    (well above the 25% threshold).
    """
    chunks: list[Chunk] = []
    for i in range(total):
        text = f"The {term} shall comply." if i < total - 1 else "Unrelated text."
        chunks.append(
            _make_chunk(chunk_id=f"corpus_{i}", text=text)
        )
    return chunks


# ---------------------------------------------------------------------------
# Hybrid retrieval — merging (RRF)
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
    """When a chunk appears in both, its RRF score is the sum from both methods."""
    chunk = _make_chunk(chunk_id="dup")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        bm25_results=[BM25Result(chunk=chunk, score=5.0)],
    )

    result = retriever.retrieve("query", "doc1", top_k=5)

    assert len(result.chunks) == 1
    # Rank 0 in both lists -> RRF score = 2 * 1/(60+1) ≈ 0.0328
    assert result.chunks[0].score > 0.0


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

    # Provide a corpus where "Borrower" appears in >25% of chunks,
    # making it automatically ubiquitous via corpus frequency.
    corpus = _make_ubiquitous_corpus("Borrower")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={
            "Borrower": "the entity on the signature page",
            "Restricted Payments": "dividends, distributions, etc.",
            "Available Amount": "the sum of X and Y",
        },
        indexed_chunks=corpus,
    )

    result = retriever.retrieve("restricted payments", "doc1", top_k=5)

    # "Borrower" is ubiquitous (>25% of corpus) and deprioritized
    assert "Borrower" not in result.injected_definitions
    assert "Restricted Payments" in result.injected_definitions
    assert "Available Amount" in result.injected_definitions


def test_ubiquitous_term_injected_when_in_query() -> None:
    """Ubiquitous terms ARE injected when the query mentions them."""
    chunk = _make_chunk(
        chunk_id="c1",
        text="The Borrower shall maintain compliance.",
    )

    corpus = _make_ubiquitous_corpus("Borrower")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={
            "Borrower": "the entity on the signature page",
        },
        indexed_chunks=corpus,
    )

    result = retriever.retrieve("Who is the Borrower?", "doc1", top_k=5)

    assert "Borrower" in result.injected_definitions


def test_non_ubiquitous_term_always_injected() -> None:
    """Terms with low corpus frequency are injected regardless of query."""
    chunk = _make_chunk(
        chunk_id="c1",
        text="The Applicable Margin determines interest rates.",
    )

    # Corpus where "Applicable Margin" appears in only 1 of 8 chunks (12.5%)
    corpus = [_make_chunk(chunk_id="c_other", text="Unrelated text.")] * 7
    corpus.append(
        _make_chunk(chunk_id="c_am", text="Applicable Margin is defined here.")
    )

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={"Applicable Margin": "the spread over SOFR"},
        indexed_chunks=corpus,
    )

    # Query does NOT mention the term, but it should still be injected
    result = retriever.retrieve("What is the interest rate?", "doc1", top_k=5)
    assert "Applicable Margin" in result.injected_definitions


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


def test_section_types_exclude_passed_to_stores() -> None:
    """section_types_exclude is forwarded to both vector and BM25 stores."""
    chunk = _make_chunk(chunk_id="c1")
    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
    )

    exclude = ["definitions", "miscellaneous"]
    retriever.retrieve("query", "doc1", section_types_exclude=exclude)

    # Verify vector store received the exclude parameter
    call_kwargs = retriever._vector_store.search.call_args  # type: ignore[union-attr]
    assert call_kwargs.kwargs.get("section_types_exclude") == exclude  # type: ignore[reportUnknownMemberType]

    # Verify BM25 store received the exclude parameter
    bm25_kwargs = retriever._bm25_store.search.call_args  # type: ignore[union-attr]
    assert bm25_kwargs.kwargs.get("section_types_exclude") == exclude  # type: ignore[reportUnknownMemberType]


# ---------------------------------------------------------------------------
# Recursive definition expansion
# ---------------------------------------------------------------------------


def _make_definition_chunk(
    term: str,
    text: str,
    chunk_id: str = "defn_chunk",
) -> Chunk:
    """Build a definition Chunk for promotion tests."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id="1.1",
        section_title="Defined Terms",
        article_number=1,
        article_title="DEFINITIONS",
        section_type="definitions",
        chunk_type="definition",
        page_numbers=[15],
        defined_terms_present=[term],
        chunk_index=0,
        token_count=250,
    )


def test_definition_chunk_promotion_with_query_mention() -> None:
    """Long definitions mentioned in query are promoted to full chunks."""
    chunk = _make_chunk(
        chunk_id="c1",
        text="Interest shall accrue at SOFR plus the Applicable Margin.",
    )

    long_defn = "x" * 1000  # exceeds QA_DEFINITION_MAX_CHARS
    defn_chunk = _make_definition_chunk("Applicable Margin", long_defn, "defn_am")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={"Applicable Margin": long_defn},
        indexed_chunks=[defn_chunk],
    )

    result = retriever.retrieve(
        "What is the Applicable Margin?", "doc1", top_k=5,
    )

    chunk_ids = [hc.chunk.chunk_id for hc in result.chunks]
    assert "defn_am" in chunk_ids
    assert "Applicable Margin" not in result.injected_definitions


def test_definition_chunk_promotion_without_query_mention() -> None:
    """Long definitions are promoted even when NOT in the query.

    This is the core Fix A test: a retrieved chunk references
    'Applicable Margin' but the query only says 'interest rate'.
    The definition is long (pricing grid) and should be promoted
    as a full chunk rather than truncated.
    """
    chunk = _make_chunk(
        chunk_id="c1",
        text="Interest shall accrue at SOFR plus the Applicable Margin.",
    )

    long_defn = "x" * 1000
    defn_chunk = _make_definition_chunk("Applicable Margin", long_defn, "defn_am")

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={"Applicable Margin": long_defn},
        indexed_chunks=[defn_chunk],
    )

    # Query does NOT mention "Applicable Margin" -- just "interest rate"
    result = retriever.retrieve(
        "What is the interest rate?", "doc1", top_k=5,
    )

    chunk_ids = [hc.chunk.chunk_id for hc in result.chunks]
    assert "defn_am" in chunk_ids
    assert "Applicable Margin" not in result.injected_definitions


def test_ubiquitous_long_definition_not_promoted() -> None:
    """Ubiquitous long definitions are NOT promoted unless in query."""
    chunk = _make_chunk(
        chunk_id="c1",
        text="The Borrower shall comply with covenants.",
    )

    long_defn = "x" * 1000
    defn_chunk = _make_definition_chunk("Borrower", long_defn, "defn_borr")

    # Corpus makes "Borrower" ubiquitous (>25%)
    corpus = _make_ubiquitous_corpus("Borrower")
    corpus.append(defn_chunk)  # also include the definition chunk

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions={"Borrower": long_defn},
        indexed_chunks=corpus,
    )

    # Query does NOT mention "Borrower"
    result = retriever.retrieve("What are the covenants?", "doc1", top_k=5)

    chunk_ids = [hc.chunk.chunk_id for hc in result.chunks]
    assert "defn_borr" not in chunk_ids
    assert "Borrower" not in result.injected_definitions


def test_recursive_definition_expansion() -> None:
    """Definitions referenced inside other definitions are also injected."""
    # Chunk text mentions "Applicable Margin" but not "Leverage Ratio"
    chunk = _make_chunk(
        chunk_id="c1",
        text="Interest shall accrue at SOFR plus the Applicable Margin.",
    )

    # "Applicable Margin" definition references "Leverage Ratio"
    definitions = {
        "Applicable Margin": (
            "the rate determined by the Leverage Ratio grid"
        ),
        "Leverage Ratio": "Consolidated Net Debt divided by EBITDA",
        "EBITDA": "earnings before interest taxes depreciation",
        "Unrelated Term": "something not referenced anywhere",
    }

    retriever = _make_retriever(
        vector_results=[RetrievedChunk(chunk=chunk, score=0.9)],
        definitions=definitions,
    )

    result = retriever.retrieve("interest rate", "doc1")

    # Primary pass: "Applicable Margin" found in chunk text
    assert "Applicable Margin" in result.injected_definitions
    # Expansion pass: "Leverage Ratio" found inside Applicable Margin definition
    assert "Leverage Ratio" in result.injected_definitions
    # "Unrelated Term" not referenced by anything in the chain
    assert "Unrelated Term" not in result.injected_definitions


# ---------------------------------------------------------------------------
# _query_term_overlap — synonym-aware sibling filter
# ---------------------------------------------------------------------------


def test_query_term_overlap_exact_match() -> None:
    """Direct word match passes the filter."""
    assert _query_term_overlap("What is the spread?", "The spread is 2.5%.")


def test_query_term_overlap_synonym_match() -> None:
    """Synonym expansion: 'spread' matches sibling text containing 'margin'."""
    assert _query_term_overlap(
        "What is the SOFR spread?",
        "The applicable margin shall be determined by the pricing grid.",
    )


def test_query_term_overlap_synonym_reverse() -> None:
    """Synonym expansion works in the other direction too."""
    assert _query_term_overlap(
        "What is the margin?",
        "The spread over SOFR is set forth in the table below.",
    )


def test_query_term_overlap_covenant_synonym() -> None:
    """'covenant' matches 'restriction'."""
    assert _query_term_overlap(
        "What are the covenants?",
        "The following restrictions shall apply to the Borrower.",
    )


def test_query_term_overlap_unrelated_rejected() -> None:
    """Completely unrelated sibling text is rejected."""
    assert not _query_term_overlap(
        "What is the SOFR spread?",
        "Tax returns shall be filed annually with the applicable authority.",
    )


def test_query_term_overlap_empty_query_passes() -> None:
    """If query has no usable words (all short or stop words), allow through."""
    assert _query_term_overlap("is it?", "Some chunk text about anything.")


def test_query_term_overlap_debt_synonym() -> None:
    """'debt' matches 'indebtedness'."""
    assert _query_term_overlap(
        "What are the debt limits?",
        "The Borrower shall not incur Indebtedness in excess of the amount.",
    )


# ---------------------------------------------------------------------------
# Sibling expansion with query filter
# ---------------------------------------------------------------------------


def _make_sibling_chunks(
    section_id: str,
    texts: list[str],
) -> list[Chunk]:
    """Build a sequence of chunks in the same section."""
    chunks: list[Chunk] = []
    for i, text in enumerate(texts):
        chunks.append(
            Chunk(
                chunk_id=f"{section_id}_chunk_{i}",
                text=text,
                section_id=section_id,
                section_title="Test Section",
                article_number=7,
                article_title="TEST ARTICLE",
                section_type="negative_covenants",
                chunk_type="text",
                page_numbers=[10 + i],
                defined_terms_present=[],
                chunk_index=i,
                token_count=50,
            )
        )
    return chunks


def test_sibling_expansion_allows_synonym_match() -> None:
    """Sibling with synonym vocabulary is included via expansion."""
    section_chunks = _make_sibling_chunks("sec_7.01", [
        "The spread over SOFR shall be as set forth below.",
        "The applicable margin is determined by the leverage ratio grid.",
        "Tax withholding provisions apply to all payments.",
    ])

    retriever = _make_retriever(
        vector_results=[
            RetrievedChunk(chunk=section_chunks[0], score=0.9),
        ],
        indexed_chunks=section_chunks,
    )

    result = retriever.retrieve(
        "What is the SOFR spread?", "doc1", top_k=5,
    )

    chunk_ids = [hc.chunk.chunk_id for hc in result.chunks]
    # Sibling about margin should be included (synonym of spread)
    assert "sec_7.01_chunk_1" in chunk_ids
    # Sibling about tax withholding should be excluded (unrelated)
    assert "sec_7.01_chunk_2" not in chunk_ids


def test_sibling_expansion_blocks_unrelated() -> None:
    """Completely unrelated sibling is filtered out."""
    section_chunks = _make_sibling_chunks("sec_7.01", [
        "The Borrower shall not incur Indebtedness.",
        "Notices shall be sent to the address specified herein.",
    ])

    retriever = _make_retriever(
        vector_results=[
            RetrievedChunk(chunk=section_chunks[0], score=0.9),
        ],
        indexed_chunks=section_chunks,
    )

    result = retriever.retrieve(
        "What are the debt limits?", "doc1", top_k=5,
    )

    chunk_ids = [hc.chunk.chunk_id for hc in result.chunks]
    assert "sec_7.01_chunk_0" in chunk_ids
    # Notices sibling should be filtered out
    assert "sec_7.01_chunk_1" not in chunk_ids


# ---------------------------------------------------------------------------
# Round-robin merge
# ---------------------------------------------------------------------------


def test_round_robin_preserves_diversity() -> None:
    """Niche query results are not crowded out by a dominant query."""
    q1_chunks = [
        HybridChunk(chunk=_make_chunk(chunk_id=f"q1_c{i}"), score=0.9, source="vector")
        for i in range(10)
    ]
    q2_chunks = [
        HybridChunk(chunk=_make_chunk(chunk_id=f"q2_c{i}"), score=0.3, source="bm25")
        for i in range(3)
    ]

    result = merge_multi_query_results(
        per_query_results=[q1_chunks, q2_chunks],
        per_query_definitions=[{}, {}],
        top_k=5,
    )

    merged_ids = {hc.chunk.chunk_id for hc in result.chunks}
    assert len(result.chunks) == 5
    q2_in_merged = merged_ids & {f"q2_c{i}" for i in range(3)}
    assert len(q2_in_merged) >= 2


def test_round_robin_deduplicates() -> None:
    """Shared chunk IDs across queries appear only once."""
    shared = HybridChunk(chunk=_make_chunk(chunk_id="shared"), score=0.8, source="both")
    q1 = [shared, HybridChunk(chunk=_make_chunk(chunk_id="q1_only"), score=0.7, source="vector")]
    q2 = [
        HybridChunk(chunk=_make_chunk(chunk_id="shared"), score=0.6, source="bm25"),
        HybridChunk(chunk=_make_chunk(chunk_id="q2_only"), score=0.5, source="bm25"),
    ]

    result = merge_multi_query_results(
        per_query_results=[q1, q2],
        per_query_definitions=[{}, {}],
        top_k=10,
    )

    ids = [hc.chunk.chunk_id for hc in result.chunks]
    assert ids.count("shared") == 1
    assert "q1_only" in ids
    assert "q2_only" in ids


def test_round_robin_respects_top_k() -> None:
    """Merged result never exceeds top_k."""
    q1 = [HybridChunk(chunk=_make_chunk(chunk_id=f"a{i}"), score=0.9, source="vector") for i in range(10)]
    q2 = [HybridChunk(chunk=_make_chunk(chunk_id=f"b{i}"), score=0.8, source="bm25") for i in range(10)]

    result = merge_multi_query_results(
        per_query_results=[q1, q2],
        per_query_definitions=[{}, {}],
        top_k=6,
    )
    assert len(result.chunks) == 6
