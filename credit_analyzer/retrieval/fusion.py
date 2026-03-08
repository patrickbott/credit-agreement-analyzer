"""Fusion and merging utilities for hybrid retrieval results."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from credit_analyzer.processing.chunker import Chunk
    from credit_analyzer.processing.definitions import DefinitionsIndex
    from credit_analyzer.retrieval.hybrid_retriever import HybridChunk, RetrievalResult


def merge_multi_query_results(
    per_query_results: list[list[HybridChunk]],
    per_query_definitions: list[dict[str, str]],
    top_k: int,
) -> RetrievalResult:
    """Merge results from multiple queries using round-robin interleaving.

    Ensures each query contributes proportionally to the final result set,
    preventing dominant queries from crowding out niche but important results.

    Args:
        per_query_results: Lists of HybridChunks, one list per query.
        per_query_definitions: Injected definitions dicts, one per query.
        top_k: Maximum number of chunks in the merged result.

    Returns:
        Merged RetrievalResult with round-robin interleaved chunks and
        combined definitions.
    """
    # Import at runtime to avoid circular imports (HybridChunk and
    # RetrievalResult are defined in hybrid_retriever which imports us).
    from credit_analyzer.retrieval.hybrid_retriever import RetrievalResult as _RR

    seen_ids: set[str] = set()
    merged: list[HybridChunk] = []
    all_definitions: dict[str, str] = {}

    for defs in per_query_definitions:
        all_definitions.update(defs)

    # Round-robin: take one chunk from each query in turn
    max_rank = max((len(r) for r in per_query_results), default=0)
    for rank in range(max_rank):
        if len(merged) >= top_k:
            break
        for q_results in per_query_results:
            if rank < len(q_results):
                hc = q_results[rank]
                if hc.chunk.chunk_id not in seen_ids:
                    seen_ids.add(hc.chunk.chunk_id)
                    merged.append(hc)
                    if len(merged) >= top_k:
                        break

    return _RR(chunks=merged, injected_definitions=all_definitions)


def compute_term_document_frequency(
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
