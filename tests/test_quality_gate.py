# tests/test_quality_gate.py
"""Tests for the retrieval quality gate."""

from __future__ import annotations

from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk, RetrievalResult
from credit_analyzer.retrieval.quality_gate import (
    GateDecision,
    check_retrieval_quality,
)


def _make_chunk(
    score: float = 0.8,
    text: str = "The Borrower shall maintain a Total Leverage Ratio of 4.50:1.00.",
) -> HybridChunk:
    return HybridChunk(
        chunk=Chunk(
            chunk_id="c1", text=text, section_id="7.11",
            section_title="Financial Covenants", article_number=7,
            article_title="NEGATIVE COVENANTS", section_type="financial_covenants",
            chunk_type="text", page_numbers=[45], defined_terms_present=[],
            chunk_index=0, token_count=30,
        ),
        score=score,
        source="both",
    )


class TestRetrievalQualityGate:
    """Tests for the quality gate heuristic."""

    def test_high_score_chunks_sufficient(self) -> None:
        """High-scoring chunks pass the gate."""
        result = RetrievalResult(
            chunks=[_make_chunk(0.85), _make_chunk(0.75), _make_chunk(0.65)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "What is the leverage ratio?")
        assert decision == GateDecision.SUFFICIENT

    def test_low_score_chunks_insufficient(self) -> None:
        """All low-scoring chunks fail the gate."""
        result = RetrievalResult(
            chunks=[_make_chunk(0.18), _make_chunk(0.16), _make_chunk(0.15)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "Are there J.Crew provisions?")
        assert decision == GateDecision.INSUFFICIENT

    def test_empty_results_insufficient(self) -> None:
        """No chunks at all fails the gate."""
        result = RetrievalResult(chunks=[], injected_definitions={})
        decision = check_retrieval_quality(result, "anything")
        assert decision == GateDecision.INSUFFICIENT

    def test_no_term_overlap_insufficient(self) -> None:
        """Chunks that don't overlap with query terms fail the gate."""
        chunk = _make_chunk(
            score=0.5,
            text="Administrative Agent shall mean JPMorgan Chase Bank, N.A.",
        )
        result = RetrievalResult(chunks=[chunk], injected_definitions={})
        decision = check_retrieval_quality(
            result, "What are the restricted payment baskets?",
        )
        assert decision == GateDecision.INSUFFICIENT
