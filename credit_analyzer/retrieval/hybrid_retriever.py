"""Hybrid retriever combining vector and BM25 search with definition injection."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from credit_analyzer.config import (
    DEFINITION_UBIQUITY_THRESHOLD,
    MAX_DEFINITIONS_INJECTED,
    MIN_RETRIEVAL_SCORE,
    QA_DEFINITION_MAX_CHARS,
    RERANK_CANDIDATES_MULTIPLIER,
    RRF_K,
    SIBLING_EXPANSION_MAX_TOKENS,
)
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.retrieval.bm25_store import BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.reranker import Reranker
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

    Merges results from both sources using Reciprocal Rank Fusion (RRF),
    reranks candidates with a cross-encoder, applies a minimum relevance
    threshold, deduplicates by chunk ID, and optionally injects relevant
    definitions from the agreement's definitions section.

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
        reranker: Reranker | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._bm25_store = bm25_store
        self._embedder = embedder
        self._definitions_index = definitions_index
        self._reranker = reranker

        # Build a lookup from defined term name -> its full definition Chunk.
        self._definition_chunk_lookup: dict[str, Chunk] = {}
        for chunk in bm25_store.chunks:
            if chunk.chunk_type == "definition":
                for term in chunk.defined_terms_present:
                    if term not in self._definition_chunk_lookup:
                        self._definition_chunk_lookup[term] = chunk

        # Build section -> chunks index for sibling expansion.
        # Keyed by section_id, sorted by chunk_index within each section.
        section_chunks: dict[str, list[Chunk]] = {}
        for chunk in bm25_store.chunks:
            section_chunks.setdefault(chunk.section_id, []).append(chunk)
        for section_id in section_chunks:
            section_chunks[section_id].sort(key=lambda c: c.chunk_index)
        self._section_chunks: dict[str, list[Chunk]] = section_chunks

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
        # Over-fetch candidates for reranking when a reranker is available.
        rerank_k = top_k * RERANK_CANDIDATES_MULTIPLIER if self._reranker else top_k
        fetch_k = rerank_k * 2

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

        # --- Reciprocal Rank Fusion (RRF) ---
        # RRF uses rank position rather than raw scores, making it
        # distribution-agnostic and robust to differences between
        # cosine similarity and BM25 score distributions.
        rrf_scores: dict[str, float] = {}
        source_map: dict[str, SourceLabel] = {}
        chunk_map: dict[str, Chunk] = {}

        for rank, result in enumerate(vector_results):
            cid = result.chunk.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
            source_map[cid] = "vector"
            chunk_map[cid] = result.chunk

        for rank, result in enumerate(bm25_results):
            cid = result.chunk.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
            if cid in source_map:
                source_map[cid] = "both"
            else:
                source_map[cid] = "bm25"
            if cid not in chunk_map:
                chunk_map[cid] = result.chunk

        # Sort by RRF score descending, take top rerank_k candidates
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
        candidate_ids = sorted_ids[:rerank_k]

        hybrid_chunks = [
            HybridChunk(
                chunk=chunk_map[cid],
                score=rrf_scores[cid],
                source=source_map[cid],
            )
            for cid in candidate_ids
        ]

        # --- Cross-encoder reranking ---
        if self._reranker and hybrid_chunks:
            hybrid_chunks = self._reranker.rerank(query, hybrid_chunks, top_k)
        else:
            hybrid_chunks = hybrid_chunks[:top_k]

        # --- Minimum relevance threshold ---
        # Drop chunks below the threshold, but always keep at least 3.
        _MIN_CHUNKS_FLOOR = 3
        if len(hybrid_chunks) > _MIN_CHUNKS_FLOOR:
            filtered = [hc for hc in hybrid_chunks if hc.score >= MIN_RETRIEVAL_SCORE]
            if len(filtered) < _MIN_CHUNKS_FLOOR:
                filtered = hybrid_chunks[:_MIN_CHUNKS_FLOOR]
            hybrid_chunks = filtered

        # Sibling expansion: pull in adjacent chunks from the same
        # section to capture tables, sub-clauses, and content that
        # was split across chunk boundaries.
        hybrid_chunks = self._expand_siblings(hybrid_chunks, top_k)

        # Definition injection + expansion
        injected: dict[str, str] = {}
        if inject_definitions and hybrid_chunks:
            hybrid_chunks, injected = self._inject_and_expand_definitions(
                query, hybrid_chunks, top_k,
            )

        return RetrievalResult(chunks=hybrid_chunks, injected_definitions=injected)

    def _expand_siblings(
        self,
        chunks: list[HybridChunk],
        top_k: int,
    ) -> list[HybridChunk]:
        """Pull in sibling chunks from the same section as retrieved chunks.

        When a chunk is retrieved from a multi-chunk section, important
        context (tables, sub-clauses, continuation text) may be in
        adjacent chunks that didn't score high enough individually.
        This is especially common for small table chunks next to the
        text that references them.

        Siblings are added up to a per-section token budget to avoid
        flooding the context with low-value content from large sections.
        Only non-definition sections are expanded (definition chunks
        are handled by the promotion system instead).

        Args:
            chunks: The current retrieved chunks.
            top_k: Maximum total chunks allowed.

        Returns:
            Updated chunks list with siblings inserted.
        """
        if not chunks or SIBLING_EXPANSION_MAX_TOKENS <= 0:
            return chunks

        existing_ids = {hc.chunk.chunk_id for hc in chunks}

        # Track which sections we've already seen and their token budgets.
        section_tokens_added: dict[str, int] = {}
        siblings_to_add: list[HybridChunk] = []

        for hc in chunks:
            section_id = hc.chunk.section_id
            # Skip definition chunks -- handled by promotion.
            if hc.chunk.chunk_type == "definition":
                continue
            if section_id in section_tokens_added:
                continue  # Already expanded this section.

            section_siblings = self._section_chunks.get(section_id, [])
            if len(section_siblings) <= 1:
                continue  # Single-chunk section, nothing to expand.

            section_tokens_added[section_id] = 0
            budget = SIBLING_EXPANSION_MAX_TOKENS

            for sibling in section_siblings:
                if sibling.chunk_id in existing_ids:
                    continue
                if sibling.token_count > budget:
                    continue
                siblings_to_add.append(
                    HybridChunk(
                        chunk=sibling,
                        score=hc.score * 0.9,
                        source=hc.source,
                    )
                )
                existing_ids.add(sibling.chunk_id)
                section_tokens_added[section_id] += sibling.token_count
                budget -= sibling.token_count
                if budget <= 0:
                    break

        if not siblings_to_add:
            return chunks

        # Add siblings, respecting top_k by replacing lowest-scoring
        # chunks if we're at capacity.
        result = list(chunks)
        for sibling_hc in siblings_to_add:
            if len(result) < top_k:
                result.append(sibling_hc)
            else:
                # Find the lowest-scoring non-sibling, non-definition chunk
                # to replace.  Don't evict chunks from other sections.
                min_idx = -1
                min_score = float("inf")
                for i, existing in enumerate(result):
                    if (
                        existing.source != "definition"
                        and existing.chunk.section_id
                        != sibling_hc.chunk.section_id
                        and existing.score < min_score
                    ):
                        min_score = existing.score
                        min_idx = i
                if min_idx >= 0 and sibling_hc.score >= min_score:
                    result[min_idx] = sibling_hc

        return result

    def _inject_and_expand_definitions(
        self,
        query: str,
        chunks: list[HybridChunk],
        top_k: int,
    ) -> tuple[list[HybridChunk], dict[str, str]]:
        """Find definitions for terms in retrieved chunks, with expansion.

        Three-phase approach:

        1. **Rank**: Score all defined terms found in retrieved chunks.
           Frequency is log-dampened so high-count generic terms don't
           crowd out low-count specific terms.  Terms that appear in
           chunk metadata (``defined_terms_present``) get a boost for
           being structurally important to the retrieved sections.
           Query mentions get a large boost.  Ubiquitous terms (computed
           from corpus-level document frequency) are penalized unless the
           query explicitly asks about them.

        2. **Expand**: Recursively scan two sources for additional
           defined terms: (a) definitions of the top-ranked primary
           terms, and (b) definitions of chunk metadata terms that
           scored too low for the primary cut but are structurally
           referenced in the retrieved sections.  This captures
           reference chains where a low-frequency bridge term
           connects to important sub-definitions.

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
        # Also track which terms appear in chunk metadata as explicit
        # defined-term references (the chunker's find_terms_in_text
        # populates `defined_terms_present` on each chunk).  A term
        # in this set was deliberately referenced by the section text,
        # not just incidentally containing a common word.
        metadata_terms: set[str] = set()
        for hc in chunks:
            terms = self._definitions_index.find_terms_in_text(hc.chunk.text)
            chunk_term_counts.update(terms)
            metadata_terms.update(hc.chunk.defined_terms_present)

        all_candidate_terms = set(chunk_term_counts.keys()) | query_terms

        # Query-keyword boosting: find defined terms whose names
        # contain significant words from the query.  This ensures
        # terms like "Fixed Incremental Amount" and "Ratio Incremental
        # Amount" get boosted when the query mentions "incremental",
        # even if those exact defined term names don't appear in the
        # retrieved chunk text.
        _QUERY_KW_MIN_LEN = 4
        _QUERY_KW_STOP = frozenset({
            "what", "which", "where", "when", "that", "this", "these",
            "those", "about", "with", "from", "have", "does", "will",
            "would", "could", "should", "shall", "being", "been",
            "were", "some", "more", "most", "also", "only", "than",
            "then", "into", "over", "under", "such", "each", "every",
            "other", "both", "either", "neither", "between", "through",
            "during", "before", "after", "there", "their", "your",
            "tell", "explain", "describe", "section", "article",
        })
        query_keywords = {
            w.lower()
            for w in re.split(r"\W+", query)
            if len(w) >= _QUERY_KW_MIN_LEN and w.lower() not in _QUERY_KW_STOP
        }
        query_keyword_terms: set[str] = set()
        if query_keywords:
            for term in self._definitions_index.definitions:
                term_lower = term.lower()
                if any(kw in term_lower for kw in query_keywords):
                    query_keyword_terms.add(term)
                    all_candidate_terms.add(term)

        if not all_candidate_terms:
            return chunks, {}

        term_scores: dict[str, float] = {}
        for term in all_candidate_terms:
            # Use log2 to dampen frequency so high-frequency generic
            # terms (Indebtedness, Obligations) don't crowd out
            # low-frequency specific terms (Available Incremental
            # Amount, Fixed Incremental Amount).  A term appearing
            # once scores ~1.0; one appearing 20 times scores ~4.4.
            raw_count = chunk_term_counts.get(term, 0)
            score = math.log2(raw_count + 1) if raw_count > 0 else 0.0
            if term in query_terms:
                score += 100.0
            elif term in self._ubiquitous_terms:
                score -= 50.0
            # Boost terms that appear in chunk metadata as explicit
            # defined-term references.  These are structurally
            # important to the retrieved sections (e.g. "Available
            # Incremental Amount" referenced in Section 2.27) and
            # are more likely to contain the specific provisions the
            # user needs than high-frequency generic terms.
            if term in metadata_terms and term not in self._ubiquitous_terms:
                score += 3.0
            # Boost terms whose names contain significant query
            # keywords.  Ensures "Fixed Incremental Amount" is
            # boosted when the query mentions "incremental", even
            # if the exact term isn't in retrieved chunk text.
            if term in query_keyword_terms and term not in query_terms:
                score += 10.0
            term_scores[term] = score

        # Boost long definitions that need chunk promotion.  Short
        # definitions survive truncation fine; long ones (pricing grids,
        # ratio tables) lose critical content.  A single mention of a
        # long definition in a retrieved chunk should outrank several
        # mentions of a short definition that will be injected intact.
        for term in all_candidate_terms:
            defn = self._definitions_index.lookup(term)
            if (
                defn is not None
                and len(defn) > QA_DEFINITION_MAX_CHARS
                and term in self._definition_chunk_lookup
                and term not in self._ubiquitous_terms
                and chunk_term_counts.get(term, 0) > 0
            ):
                term_scores[term] += 15.0

        ranked_terms = sorted(
            term_scores.keys(), key=lambda t: term_scores[t], reverse=True,
        )

        # Pass 2: recursive expansion from two sources:
        #   (a) definitions of the top-ranked primary terms, and
        #   (b) chunk metadata terms that didn't make the primary cut.
        # Source (b) catches terms like "Available Incremental Amount"
        # that appear in a retrieved chunk's text but score too low
        # on frequency to make the top-N.  Following their definition
        # text chains to related terms (e.g. Fixed Incremental Amount)
        # ensures the LLM gets the full reference tree.
        primary_terms = ranked_terms[:MAX_DEFINITIONS_INJECTED]
        primary_defs = self._definitions_index.get_definitions_for_terms(
            primary_terms
        )

        expansion_counts: Counter[str] = Counter()
        # (a) Scan primary definitions for cross-references.
        for defn_text in primary_defs.values():
            found = self._definitions_index.find_terms_in_text(defn_text)
            for term in found:
                if term not in primary_defs:
                    expansion_counts[term] += 1

        # (b) Scan definitions of metadata terms that didn't make
        # the primary cut.  These are terms explicitly referenced
        # in chunk text (structurally important) but ranked below
        # top-N due to low corpus frequency.
        metadata_only = metadata_terms - set(primary_terms)
        for term in metadata_only:
            if term in self._ubiquitous_terms:
                continue
            defn_text = self._definitions_index.lookup(term)
            if defn_text is None:
                continue
            # Add the metadata term itself as an expansion candidate.
            if term not in primary_defs:
                expansion_counts[term] += 1
            # Follow its cross-references too.
            found = self._definitions_index.find_terms_in_text(defn_text)
            for ref_term in found:
                if ref_term not in primary_defs:
                    expansion_counts[ref_term] += 1

        # Expansion budget: the primary budget often fills completely,
        # leaving zero slots for metadata-sourced terms.  Give
        # expansion a minimum of 6 additional slots so structurally
        # important terms (and their cross-references) aren't starved.
        _EXPANSION_MIN_SLOTS = 6
        remaining_slots = max(
            MAX_DEFINITIONS_INJECTED - len(primary_defs),
            _EXPANSION_MIN_SLOTS,
        )
        if remaining_slots > 0:
            # Direct metadata terms get guaranteed priority over
            # cross-references.  Without this, terms like "Available
            # Incremental Amount" (structurally referenced in a
            # retrieved chunk but low corpus frequency) get buried
            # by dozens of cross-refs from scanning 50+ metadata
            # definitions.  We fill slots in two tiers:
            #   Tier 1: direct metadata terms (guaranteed slots)
            #   Tier 2: cross-references (fill remaining capacity)
            direct_metadata_expansion: list[str] = sorted(
                (
                    term
                    for term in metadata_only
                    if (
                        term not in self._ubiquitous_terms
                        and term in expansion_counts
                    )
                ),
                key=lambda t: term_scores.get(t, 0.0),
                reverse=True,
            )
            tier1_terms = direct_metadata_expansion[:remaining_slots]
            tier1_defs = self._definitions_index.get_definitions_for_terms(
                tier1_terms
            )
            primary_defs.update(tier1_defs)

            # Fill remaining slots with cross-references.
            tier2_slots = remaining_slots - len(tier1_defs)
            if tier2_slots > 0 and expansion_counts:
                tier2_terms = [
                    term
                    for term, _ in expansion_counts.most_common(
                        tier2_slots + len(tier1_terms)
                    )
                    if term not in tier1_defs and term not in primary_defs
                ][:tier2_slots]
                tier2_defs = (
                    self._definitions_index.get_definitions_for_terms(
                        tier2_terms
                    )
                )
                primary_defs.update(tier2_defs)

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
