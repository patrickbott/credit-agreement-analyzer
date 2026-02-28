"""Hybrid retriever combining vector and BM25 search with definition injection."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from credit_analyzer.config import (
    BM25_WEIGHT,
    MAX_DEFINITIONS_INJECTED,
    SECTION_TYPE_BOOST,
    VECTOR_WEIGHT,
)
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.retrieval.bm25_store import BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.vector_store import VectorStore

SourceLabel = Literal["vector", "bm25", "both"]


@dataclass
class HybridChunk:
    """A chunk from hybrid retrieval with combined score and source attribution.

    Attributes:
        chunk: The original Chunk object.
        score: The combined weighted score from vector and/or BM25.
        source: Which retrieval method(s) found this chunk.
    """

    chunk: Chunk
    score: float
    source: SourceLabel


@dataclass
class RetrievalResult:
    """Result of a hybrid retrieval query.

    Attributes:
        chunks: Ranked, deduplicated chunks with combined scores.
        injected_definitions: Definitions auto-injected based on terms
            found across the retrieved chunks.
    """

    chunks: list[HybridChunk]
    injected_definitions: dict[str, str]


def normalize_scores(scores: Sequence[float]) -> list[float]:
    """Min-max normalize a list of scores to [0, 1].

    If all scores are identical, returns 1.0 for each.

    Args:
        scores: Raw scores to normalize.

    Returns:
        Normalized scores in the same order.
    """
    if not scores:
        return []
    min_s = min(scores)
    max_s = max(scores)
    span = max_s - min_s
    if span == 0.0:
        return [1.0] * len(scores)
    return [(s - min_s) / span for s in scores]


# ---------------------------------------------------------------------------
# Query -> section_type intent mapping
# ---------------------------------------------------------------------------

# Patterns that signal the user is asking about a particular section type.
# Each entry is (compiled regex, section_type).  First match wins.
_QUERY_INTENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"financial\s+covenant", re.IGNORECASE),
        "financial_covenants",
    ),
    (
        re.compile(
            r"leverage\s+ratio|coverage\s+ratio|consolidated\s+net",
            re.IGNORECASE,
        ),
        "financial_covenants",
    ),
    (
        re.compile(
            r"negative\s+covenant|restricted\s+payment"
            r"|lien|indebtedness|investment\s+basket",
            re.IGNORECASE,
        ),
        "negative_covenants",
    ),
    (
        re.compile(
            r"affirmative\s+covenant|reporting|deliver.+financial",
            re.IGNORECASE,
        ),
        "affirmative_covenants",
    ),
    (
        re.compile(
            r"event.+of.+default|breach|acceleration|cross.default",
            re.IGNORECASE,
        ),
        "events_of_default",
    ),
    (
        re.compile(
            r"revolving|term\s+loan|commitment|facility\s+size"
            r"|incremental|prepayment|interest\s+rate"
            r"|pricing|spread|margin|fee|amortization",
            re.IGNORECASE,
        ),
        "facility_terms",
    ),
    (re.compile(r"representation|warrant", re.IGNORECASE), "representations"),
    (
        re.compile(r"condition.+precedent|closing\s+condition", re.IGNORECASE),
        "conditions",
    ),
    (re.compile(r"guaranty|guarantee", re.IGNORECASE), "guaranty"),
    (
        re.compile(r"collateral|security\s+interest|pledge", re.IGNORECASE),
        "collateral",
    ),
)


def detect_query_section_type(query: str) -> str | None:
    """Detect which section type a query is most likely asking about.

    Args:
        query: The user's question.

    Returns:
        A section_type string if a match is found, or ``None``.
    """
    for pattern, section_type in _QUERY_INTENT_PATTERNS:
        if pattern.search(query):
            return section_type
    return None


class HybridRetriever:
    """Combines vector similarity and BM25 keyword search for retrieval.

    Merges results from both sources using weighted scores, deduplicates
    by chunk ID, and optionally injects relevant definitions from the
    agreement's definitions section.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_store: BM25Store,
        embedder: Embedder,
        definitions_index: DefinitionsIndex,
    ) -> None:
        self._vector_store = vector_store
        self._bm25_store = bm25_store
        self._embedder = embedder
        self._definitions_index = definitions_index

    def retrieve(
        self,
        query: str,
        document_id: str,
        top_k: int = 5,
        section_filter: str | None = None,
        section_types_exclude: Sequence[str] | None = None,
        inject_definitions: bool = True,
    ) -> RetrievalResult:
        """Run hybrid retrieval for a query.

        Args:
            query: The search query string.
            document_id: The document collection to search.
            top_k: Maximum number of chunks to return.
            section_filter: If provided, restrict to this section_type.
                Takes precedence over section_types_exclude.
            section_types_exclude: If provided and section_filter is None,
                exclude chunks whose section_type is in this list.
            inject_definitions: Whether to auto-inject definitions for
                terms found in retrieved chunks.

        Returns:
            RetrievalResult with ranked chunks and optional definitions.
        """
        # Fetch more than top_k from each source so merging has enough to work with
        fetch_k = top_k * 2

        # Vector search
        query_embedding = self._embedder.embed_query(query)
        vector_results = self._vector_store.search(
            document_id,
            query_embedding,
            top_k=fetch_k,
            section_filter=section_filter,
            section_types_exclude=section_types_exclude,
        )

        # BM25 search
        bm25_results = self._bm25_store.search(
            query,
            top_k=fetch_k,
            section_filter=section_filter,
            section_types_exclude=section_types_exclude,
        )

        # Normalize scores
        vector_scores = normalize_scores([r.score for r in vector_results])
        bm25_scores = normalize_scores([r.score for r in bm25_results])

        # Detect query intent for section type boosting
        intent_type = detect_query_section_type(query)

        # Build lookup: chunk_id -> (weighted_score, source, chunk)
        merged: dict[str, tuple[float, SourceLabel, Chunk]] = {}

        for result, norm_score in zip(vector_results, vector_scores, strict=True):
            weighted = VECTOR_WEIGHT * norm_score
            merged[result.chunk.chunk_id] = (weighted, "vector", result.chunk)

        for result, norm_score in zip(bm25_results, bm25_scores, strict=True):
            weighted = BM25_WEIGHT * norm_score
            chunk_id = result.chunk.chunk_id

            if chunk_id in merged:
                # Found in both -- combine scores
                existing_score, _, existing_chunk = merged[chunk_id]
                merged[chunk_id] = (existing_score + weighted, "both", existing_chunk)
            else:
                merged[chunk_id] = (weighted, "bm25", result.chunk)

        # Apply section type boost
        if intent_type is not None:
            boosted: dict[str, tuple[float, SourceLabel, Chunk]] = {}
            for chunk_id, (score, source, chunk) in merged.items():
                if chunk.section_type == intent_type:
                    score += SECTION_TYPE_BOOST
                boosted[chunk_id] = (score, source, chunk)
            merged = boosted

        # Sort by combined score descending, take top_k
        sorted_items = sorted(merged.values(), key=lambda x: x[0], reverse=True)
        top_items = sorted_items[:top_k]

        hybrid_chunks = [
            HybridChunk(chunk=chunk, score=score, source=source)
            for score, source, chunk in top_items
        ]

        # Definition injection
        injected: dict[str, str] = {}
        if inject_definitions and hybrid_chunks:
            injected = self._inject_definitions(hybrid_chunks)

        return RetrievalResult(chunks=hybrid_chunks, injected_definitions=injected)

    def _inject_definitions(
        self,
        chunks: Sequence[HybridChunk],
    ) -> dict[str, str]:
        """Find and return definitions for terms appearing in retrieved chunks.

        Prioritizes terms by frequency across all retrieved chunks, capped
        at MAX_DEFINITIONS_INJECTED.

        Args:
            chunks: The retrieved chunks to scan for defined terms.

        Returns:
            Dict mapping term names to their definition text.
        """
        # Count term frequency across all chunks
        term_counts: Counter[str] = Counter()
        for hc in chunks:
            terms = self._definitions_index.find_terms_in_text(hc.chunk.text)
            term_counts.update(terms)

        if not term_counts:
            return {}

        # Take the most frequent terms up to the cap
        top_terms = [term for term, _ in term_counts.most_common(MAX_DEFINITIONS_INJECTED)]

        return self._definitions_index.get_definitions_for_terms(top_terms)
