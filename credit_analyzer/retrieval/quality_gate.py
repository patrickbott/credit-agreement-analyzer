# credit_analyzer/retrieval/quality_gate.py
"""Retrieval quality gate — heuristic check for result sufficiency.

Determines whether retrieved chunks are likely sufficient to answer a
query, or whether the query should be escalated to the LLM decomposer
for more targeted retrieval.
"""

from __future__ import annotations

import enum
import re

from credit_analyzer.retrieval.hybrid_retriever import RetrievalResult

# Thresholds tuned for the credit analyzer's score distributions
_MIN_TOP_SCORE = 0.35          # Best chunk must score at least this
_MIN_MEAN_TOP3_SCORE = 0.25    # Mean of top-3 chunks must exceed this
_MIN_TERM_OVERLAP_RATIO = 0.3  # Fraction of query terms found in top chunks

_STOP_WORDS = frozenset({
    "what", "where", "when", "which", "how", "does", "this", "that",
    "there", "have", "been", "with", "from", "they", "their", "will",
    "would", "could", "should", "about", "into", "than", "then",
    "also", "just", "more", "some", "such", "only", "very", "most",
    "document", "agreement", "provision", "provisions", "section",
    "any", "are", "the", "and", "for", "not", "but",
})


class GateDecision(enum.Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


def check_retrieval_quality(
    result: RetrievalResult,
    query: str,
) -> GateDecision:
    """Check whether retrieval results are likely sufficient for the query.

    Uses a multi-signal heuristic:
    1. Score check: are the top chunks scoring high enough?
    2. Term overlap: do the retrieved chunks contain query-relevant terms?
    3. Chunk count: do we have a minimum number of chunks?

    Returns GateDecision.SUFFICIENT or GateDecision.INSUFFICIENT.
    """
    if not result.chunks:
        return GateDecision.INSUFFICIENT

    scores = sorted([hc.score for hc in result.chunks], reverse=True)

    # Signal 1: Top score too low
    if scores[0] < _MIN_TOP_SCORE:
        return GateDecision.INSUFFICIENT

    # Signal 2: Mean of top-3 too low
    top3 = scores[:3]
    if sum(top3) / len(top3) < _MIN_MEAN_TOP3_SCORE:
        return GateDecision.INSUFFICIENT

    # Signal 3: Query term overlap with retrieved text
    query_terms = _extract_query_terms(query)
    if query_terms:
        chunk_text = " ".join(
            hc.chunk.text.lower() for hc in result.chunks[:5]
        )
        found = sum(1 for t in query_terms if t in chunk_text)
        overlap_ratio = found / len(query_terms)
        if overlap_ratio < _MIN_TERM_OVERLAP_RATIO:
            return GateDecision.INSUFFICIENT

    return GateDecision.SUFFICIENT


def _extract_query_terms(query: str) -> list[str]:
    """Extract meaningful terms from a query for overlap checking."""
    words = re.findall(r"[a-zA-Z]{3,}", query.lower())
    return [w for w in words if w not in _STOP_WORDS]
