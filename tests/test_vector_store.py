"""Tests for the vector_store module."""

from __future__ import annotations

from pathlib import Path

import pytest

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.vector_store import (
    RetrievedChunk,
    VectorStore,
    chunk_to_metadata,
    metadata_to_chunk,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "abc123",
    text: str = "The Borrower shall not incur indebtedness.",
    section_id: str = "7.01",
    section_type: str = "negative_covenants",
    article_number: int = 7,
    chunk_index: int = 0,
) -> Chunk:
    """Build a minimal Chunk for testing."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id=section_id,
        section_title="Indebtedness",
        article_number=article_number,
        article_title="NEGATIVE COVENANTS",
        section_type=section_type,
        chunk_type="text",
        page_numbers=[10, 11],
        defined_terms_present=["Borrower", "Indebtedness"],
        chunk_index=chunk_index,
        token_count=15,
    )


def _fake_embedding(dim: int = 384, seed: int = 0) -> list[float]:
    """Create a deterministic embedding vector that varies by seed.

    Different seeds produce vectors pointing in different directions,
    which is necessary for cosine similarity to distinguish them.
    """
    import math

    return [math.sin((i + 1) * (seed + 1) * 0.1) for i in range(dim)]


# ---------------------------------------------------------------------------
# Metadata round-trip tests (no ChromaDB needed)
# ---------------------------------------------------------------------------


def test_chunk_to_metadata_keys() -> None:
    """Metadata dict has all expected keys with correct types."""
    chunk = _make_chunk()
    meta = chunk_to_metadata(chunk)

    assert meta["section_id"] == "7.01"
    assert meta["article_number"] == 7
    assert meta["section_type"] == "negative_covenants"
    assert meta["page_numbers"] == "10|11"
    assert meta["defined_terms"] == "Borrower|Indebtedness"
    # All values must be primitives
    for value in meta.values():
        assert isinstance(value, (str, int, float, bool))


def test_metadata_to_chunk_round_trip() -> None:
    """Converting to metadata and back preserves all fields."""
    original = _make_chunk()
    meta = chunk_to_metadata(original)
    restored = metadata_to_chunk(original.chunk_id, original.text, meta)

    assert restored.chunk_id == original.chunk_id
    assert restored.text == original.text
    assert restored.section_id == original.section_id
    assert restored.section_title == original.section_title
    assert restored.article_number == original.article_number
    assert restored.article_title == original.article_title
    assert restored.section_type == original.section_type
    assert restored.chunk_type == original.chunk_type
    assert restored.page_numbers == original.page_numbers
    assert restored.defined_terms_present == original.defined_terms_present
    assert restored.chunk_index == original.chunk_index
    assert restored.token_count == original.token_count


def test_metadata_to_chunk_empty_lists() -> None:
    """Chunks with empty page_numbers and defined_terms round-trip correctly."""
    chunk = _make_chunk()
    chunk.page_numbers = []
    chunk.defined_terms_present = []
    meta = chunk_to_metadata(chunk)
    restored = metadata_to_chunk(chunk.chunk_id, chunk.text, meta)

    assert restored.page_numbers == []
    assert restored.defined_terms_present == []


# ---------------------------------------------------------------------------
# Integration tests (real ChromaDB, ephemeral directory)
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> VectorStore:
    """Create a VectorStore backed by a temporary directory."""
    return VectorStore(persist_directory=str(tmp_path / "chroma"))


def test_create_and_list_collection(store: VectorStore) -> None:
    """Creating a collection makes it visible in list_documents."""
    store.create_collection("test_doc")
    docs = store.list_documents()
    assert "test_doc" in docs


def test_add_and_search(store: VectorStore) -> None:
    """Added chunks can be retrieved by similarity search."""
    store.create_collection("doc1")

    chunks = [
        _make_chunk(chunk_id="c1", text="Revolving commitment is $50M", section_type="facility_terms"),
        _make_chunk(chunk_id="c2", text="The Borrower shall not incur debt", section_type="negative_covenants"),
        _make_chunk(chunk_id="c3", text="EBITDA means earnings before interest", section_type="definitions"),
    ]
    # Give different embeddings so cosine similarity can distinguish them
    embeddings = [
        _fake_embedding(seed=1),
        _fake_embedding(seed=2),
        _fake_embedding(seed=3),
    ]

    store.add_chunks("doc1", chunks, embeddings)

    # Query with an embedding matching c1's
    results = store.search("doc1", _fake_embedding(seed=1), top_k=3)

    assert len(results) == 3
    assert isinstance(results[0], RetrievedChunk)
    assert results[0].chunk.chunk_id == "c1"
    assert results[0].score > 0.0


def test_search_with_section_filter(store: VectorStore) -> None:
    """Section filter restricts results to matching section_type."""
    store.create_collection("doc2")

    chunks = [
        _make_chunk(chunk_id="c1", section_type="facility_terms"),
        _make_chunk(chunk_id="c2", section_type="negative_covenants"),
        _make_chunk(chunk_id="c3", section_type="negative_covenants"),
    ]
    embeddings = [
        _fake_embedding(seed=1),
        _fake_embedding(seed=2),
        _fake_embedding(seed=3),
    ]

    store.add_chunks("doc2", chunks, embeddings)

    results = store.search("doc2", _fake_embedding(seed=2), top_k=5, section_filter="negative_covenants")

    assert len(results) == 2
    for r in results:
        assert r.chunk.section_type == "negative_covenants"


def test_search_empty_collection(store: VectorStore) -> None:
    """Searching an empty collection returns an empty list."""
    store.create_collection("empty_doc")
    results = store.search("empty_doc", _fake_embedding(), top_k=5)
    assert results == []


def test_add_chunks_length_mismatch(store: VectorStore) -> None:
    """Mismatched chunks and embeddings raises ValueError."""
    store.create_collection("doc_err")
    with pytest.raises(ValueError, match="same length"):
        store.add_chunks("doc_err", [_make_chunk()], [])


def test_add_empty_chunks(store: VectorStore) -> None:
    """Adding zero chunks is a no-op."""
    store.create_collection("doc_empty")
    store.add_chunks("doc_empty", [], [])
    results = store.search("doc_empty", _fake_embedding(), top_k=5)
    assert results == []


def test_delete_collection(store: VectorStore) -> None:
    """Deleting a collection removes it from list_documents."""
    store.create_collection("to_delete")
    assert "to_delete" in store.list_documents()

    store.delete_collection("to_delete")
    assert "to_delete" not in store.list_documents()


def test_search_score_range(store: VectorStore) -> None:
    """Similarity scores should be between 0 and 1."""
    store.create_collection("doc_scores")
    store.add_chunks(
        "doc_scores",
        [_make_chunk(chunk_id="c1")],
        [_fake_embedding()],
    )

    results = store.search("doc_scores", _fake_embedding(), top_k=1)

    assert len(results) == 1
    # Allow small floating-point overshoot from cosine distance calculation
    assert -0.01 <= results[0].score <= 1.01


def test_create_collection_idempotent(store: VectorStore) -> None:
    """Calling create_collection twice does not error or duplicate."""
    store.create_collection("idem")
    store.add_chunks("idem", [_make_chunk(chunk_id="c1")], [_fake_embedding()])

    store.create_collection("idem")  # should not wipe data
    results = store.search("idem", _fake_embedding(), top_k=1)
    assert len(results) == 1


def test_search_with_section_types_exclude(store: VectorStore) -> None:
    """Excluding section types filters out matching chunks."""
    store.create_collection("excl")
    chunks = [
        _make_chunk(chunk_id="c1", section_type="negative_covenants"),
        _make_chunk(chunk_id="c2", section_type="definitions"),
        _make_chunk(chunk_id="c3", section_type="miscellaneous"),
    ]
    embeddings = [_fake_embedding(seed=i) for i in range(3)]
    store.add_chunks("excl", chunks, embeddings)

    results = store.search(
        "excl",
        _fake_embedding(seed=0),
        top_k=5,
        section_types_exclude=["definitions", "miscellaneous"],
    )
    result_types = {r.chunk.section_type for r in results}
    assert "definitions" not in result_types
    assert "miscellaneous" not in result_types
    assert len(results) >= 1
