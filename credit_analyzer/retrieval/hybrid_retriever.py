"""Hybrid retriever combining vector and BM25 search with definition injection."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from credit_analyzer.config import (
    BM25_WEIGHT,
    DEFINITION_UBIQUITY_THRESHOLD,
    MAX_DEFINITIONS_INJECTED,
    QA_DEFINITION_MAX_CHARS,
    VECTOR_WEIGHT,
)
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.retrieval.bm25_store import BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.vector_store import VectorStore

SourceLabel = Literal["vector", "bm25", "both", "definition"]


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


def _compute_term_document_frequency(
    chunks: Sequence[Chunk],
    definitions_index: DefinitionsIndex,
) -> dict[str, float]:
    """Compute fraction of chunks each defined term appears in.

    Used to automatically identify ubiquitous boilerplate terms like
    "Borrower" and "Lender" that appear in nearly every section.
    Agreement-agnostic: adapts to whatever document is indexed.

    Args:
        chunks: All chunks in the index.
        definitions_index: The definitions index for term matching.

    Returns:
        Mapping from term name to fraction of chunks containing it
        (0.0 to 1.0).
    """
    if not chunks:
        return {}

    term_counts: Counter[str] = Counter()
    for chunk in chunks:
        # Use a set so each chunk only counts once per term
        unique_terms = set(definitions_index.find_terms_in_text(chunk.text))
        term_counts.update(unique_terms)

    total = len(chunks)
    return {term: count / total for term, count in term_counts.items()}


class HybridRetriever:
    """Combines vector similarity and BM25 keyword search for retrieval.

    Merges results from both sources using weighted scores, deduplicates
    by chunk ID, and optionally injects relevant definitions from the
    agreement's definitions section.

    After the initial retrieval pass, the retriever promotes full
    definition chunks into the result set when those definitions are
    too long to inject as truncated text (e.g. pricing grids, ratio
    test tables).  Ubiquitous terms are identified automatically via
    corpus-level term frequency rather than a hardcoded stoplist.
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

        # Build a lookup from defined term name -> its full definition Chunk.
        self._definition_chunk_lookup: dict[str, Chunk] = {}
        for chunk in bm25_store.chunks:
            if chunk.chunk_type == "definition":
                for term in chunk.defined_terms_present:
                    if term not in self._definition_chunk_lookup:
                        self._definition_chunk_lookup[term] = chunk

        # Compute corpus-level term frequency for ubiquity detection.
        self._term_doc_freq = _compute_term_document_frequency(
            list(bm25_store.chunks), definitions_index,
        )
        self._ubiquitous_terms: frozenset[str] = frozenset(
            term
            for term, freq in self._term_doc_freq.items()
            if freq > DEFINITION_UBIQUITY_THRESHOLD
        )

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

        # Build lookup: chunk_id -> (weighted_score, source, chunk)
        merged: dict[str, tuple[float, SourceLabel, Chunk]] = {}

        for result, norm_score in zip(vector_results, vector_scores, strict=True):
            weighted = VECTOR_WEIGHT * norm_score
            merged[result.chunk.chunk_id] = (weighted, "vector", result.chunk)

        for result, norm_score in zip(bm25_results, bm25_scores, strict=True):
            weighted = BM25_WEIGHT * norm_score
            chunk_id = result.chunk.chunk_id

            if chunk_id in merged:
                existing_score, _, existing_chunk = merged[chunk_id]
                merged[chunk_id] = (existing_score + weighted, "both", existing_chunk)
            else:
                merged[chunk_id] = (weighted, "bm25", result.chunk)

        # Sort by combined score descending, take top_k
        sorted_items = sorted(merged.values(), key=lambda x: x[0], reverse=True)
        top_items = sorted_items[:top_k]

        hybrid_chunks = [
            HybridChunk(chunk=chunk, score=score, source=source)
            for score, source, chunk in top_items
        ]

        # Definition injection + expansion
        injected: dict[str, str] = {}
        if inject_definitions and hybrid_chunks:
            hybrid_chunks, injected = self._inject_and_expand_definitions(
                query, hybrid_chunks, top_k,
            )

        return RetrievalResult(chunks=hybrid_chunks, injected_definitions=injected)

    def _inject_and_expand_definitions(
        self,
        query: str,
        chunks: list[HybridChunk],
        top_k: int,
    ) -> tuple[list[HybridChunk], dict[str, str]]:
        """Find definitions for terms in retrieved chunks, with expansion.

        Three-phase approach:

        1. **Rank**: Score all defined terms found in retrieved chunks.
           Query mentions get a large boost.  Ubiquitous terms (computed
           from corpus-level document frequency, not a hardcoded list)
           are penalized unless the query explicitly asks about them.

        2. **Expand**: Recursively scan primary definitions for additional
           defined terms and add them to the candidate set.

        3. **Promote or Inject**: Long definitions whose full definition
           chunk is available get promoted into the result set as full
           chunks (preserving pricing grids, ratio tables, etc.).  All
           other relevant definitions are returned as truncated injected
           text.  Promotion is triggered by *any* long, non-ubiquitous
           definition referenced by a retrieved chunk -- it does not
           require the term to appear in the query.

        Args:
            query: The original user query, used for relevance scoring.
            chunks: The current retrieved chunks (may be modified).
            top_k: Maximum total chunks (including promoted definitions).

        Returns:
            Tuple of (updated chunks list, injected definitions dict).
        """
        # Pass 1: find and score terms
        query_terms = set(self._definitions_index.find_terms_in_text(query))

        chunk_term_counts: Counter[str] = Counter()
        for hc in chunks:
            terms = self._definitions_index.find_terms_in_text(hc.chunk.text)
            chunk_term_counts.update(terms)

        all_candidate_terms = set(chunk_term_counts.keys()) | query_terms
        if not all_candidate_terms:
            return chunks, {}

        term_scores: dict[str, float] = {}
        for term in all_candidate_terms:
            score = float(chunk_term_counts.get(term, 0))
            if term in query_terms:
                score += 100.0
            elif term in self._ubiquitous_terms:
                score -= 50.0
            term_scores[term] = score

        ranked_terms = sorted(
            term_scores.keys(), key=lambda t: term_scores[t], reverse=True,
        )

        # Pass 2: recursive expansion
        primary_terms = ranked_terms[:MAX_DEFINITIONS_INJECTED]
        primary_defs = self._definitions_index.get_definitions_for_terms(
            primary_terms
        )

        expansion_counts: Counter[str] = Counter()
        for defn_text in primary_defs.values():
            found = self._definitions_index.find_terms_in_text(defn_text)
            for term in found:
                if term not in primary_defs:
                    expansion_counts[term] += 1

        remaining_slots = MAX_DEFINITIONS_INJECTED - len(primary_defs)
        if remaining_slots > 0 and expansion_counts:
            expansion_terms = [
                term
                for term, _ in expansion_counts.most_common(remaining_slots)
            ]
            expansion_defs = self._definitions_index.get_definitions_for_terms(
                expansion_terms
            )
            primary_defs.update(expansion_defs)

        # Pass 3: promote long definitions as full chunks, inject the rest.
        # Promotion gate: definition is long AND has a chunk AND is not
        # ubiquitous (unless the query asks about it). No requirement
        # that the term appear in the query text itself.
        existing_chunk_ids = {hc.chunk.chunk_id for hc in chunks}
        promoted_terms: set[str] = set()
        injected: dict[str, str] = {}

        for term, defn_text in primary_defs.items():
            is_long = len(defn_text) > QA_DEFINITION_MAX_CHARS
            is_ubiquitous = term in self._ubiquitous_terms
            in_query = term in query_terms
            has_chunk = term in self._definition_chunk_lookup

            if is_long and has_chunk and (not is_ubiquitous or in_query):
                defn_chunk = self._definition_chunk_lookup[term]
                if defn_chunk.chunk_id not in existing_chunk_ids:
                    promoted_terms.add(term)
            elif not is_ubiquitous or in_query:
                injected[term] = defn_text

        # Insert promoted chunks
        if promoted_terms:
            scores = [hc.score for hc in chunks]
            median_score = sorted(scores)[len(scores) // 2] if scores else 0.5
            promotion_score = median_score * 0.95

            for term in promoted_terms:
                defn_chunk = self._definition_chunk_lookup[term]
                hybrid_defn = HybridChunk(
                    chunk=defn_chunk,
                    score=promotion_score,
                    source="definition",
                )

                if len(chunks) < top_k:
                    chunks.append(hybrid_defn)
                else:
                    # Replace the lowest-scoring non-promoted chunk
                    min_idx = -1
                    min_score = float("inf")
                    for i, hc in enumerate(chunks):
                        if hc.source != "definition" and hc.score < min_score:
                            min_score = hc.score
                            min_idx = i
                    if min_idx >= 0:
                        chunks[min_idx] = hybrid_defn

                existing_chunk_ids.add(defn_chunk.chunk_id)

        return chunks, injected
