"""Integration tests for the knowledge layer end-to-end flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.query_expansion import expand_query_with_concepts
from credit_analyzer.knowledge.registry import DomainRegistry
from credit_analyzer.llm.base import LLMResponse
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
)
from credit_analyzer.retrieval.quality_gate import GateDecision, check_retrieval_quality


def _make_chunk(text: str, score: float = 0.8) -> HybridChunk:
    return HybridChunk(
        chunk=Chunk(
            chunk_id="c1", text=text, section_id="7.01",
            section_title="Indebtedness", article_number=7,
            article_title="NEGATIVE COVENANTS", section_type="negative_covenants",
            chunk_type="text", page_numbers=[50], defined_terms_present=[],
            chunk_index=0, token_count=50,
        ),
        score=score,
        source="both",
    )


class TestKnowledgeLayerIntegration:
    """End-to-end tests for the knowledge layer."""

    def test_concept_expands_query(self) -> None:
        """Concept matching produces additional retrieval queries."""
        queries, concepts = expand_query_with_concepts(
            "Are there any J.Crew provisions in this agreement?"
        )
        assert len(queries) > 1
        assert len(concepts) >= 1
        assert concepts[0].concept_id == "j_crew_provision"
        all_text = " ".join(queries).lower()
        assert "intellectual property" in all_text or "unrestricted subsidiary" in all_text

    def test_quality_gate_triggers_on_low_scores(self) -> None:
        """Quality gate correctly identifies insufficient retrieval."""
        result = RetrievalResult(
            chunks=[_make_chunk("unrelated administrative text", score=0.18)],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "J.Crew provisions")
        assert decision == GateDecision.INSUFFICIENT

    def test_quality_gate_passes_on_good_results(self) -> None:
        """Quality gate passes when results are relevant and terms overlap."""
        result = RetrievalResult(
            chunks=[
                _make_chunk(
                    "transfer of intellectual property to unrestricted subsidiary",
                    score=0.75,
                ),
            ],
            injected_definitions={},
        )
        # Use a query whose terms actually overlap with the chunk text
        decision = check_retrieval_quality(
            result, "intellectual property transfer provisions",
        )
        assert decision == GateDecision.SUFFICIENT

    def test_quality_gate_insufficient_for_concept_queries(self) -> None:
        """Concept-level queries (J.Crew) fail term overlap even with good scores.

        This is the desired behavior — the document says "intellectual property"
        but the user said "J.Crew", so the gate correctly flags insufficient
        overlap, triggering escalation to the query decomposer.
        """
        result = RetrievalResult(
            chunks=[
                _make_chunk(
                    "transfer of intellectual property to unrestricted subsidiary",
                    score=0.75,
                ),
            ],
            injected_definitions={},
        )
        decision = check_retrieval_quality(result, "J.Crew provisions")
        assert decision == GateDecision.INSUFFICIENT

    def test_full_qa_flow_with_concepts(self) -> None:
        """Full QA flow with concept matching produces an answer."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = RetrievalResult(
            chunks=[_make_chunk("IP transfer provision text", score=0.7)],
            injected_definitions={},
        )

        llm = MagicMock()
        llm.complete = MagicMock(return_value=LLMResponse(
            text=(
                "The agreement contains provisions addressing IP transfers.\n\n"
                "Confidence: MEDIUM"
            ),
            tokens_used=50, model="test", duration_seconds=1.0,
        ))

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("Are there J.Crew provisions?", "doc1")

        assert isinstance(resp, QAResponse)
        assert resp.concepts_matched
        assert "j_crew_provision" in resp.concepts_matched

    def test_synonym_expansion_broadens_retrieval(self) -> None:
        """Synonym expansion adds canonical terms to retrieval."""
        registry = DomainRegistry()
        expanded = registry.expand_synonyms("what is the revolver")
        assert any(
            "revolving" in t.lower() for t in expanded
        ), f"Expected revolving synonym, got: {expanded}"

    def test_multiple_concepts_in_single_query(self) -> None:
        """Multiple concepts can be matched in a single query."""
        queries, concepts = expand_query_with_concepts(
            "Does this deal have J.Crew or Serta protections?"
        )
        concept_ids = {c.concept_id for c in concepts}
        assert "j_crew_provision" in concept_ids
        assert "serta_provision" in concept_ids
        assert len(queries) > 2  # Should have many expanded queries

    def test_simple_query_no_concept_match(self) -> None:
        """Simple queries produce no concept matches."""
        queries, concepts = expand_query_with_concepts(
            "What is the SOFR spread on the term loan?"
        )
        # Should not match named provisions
        named = {
            c.concept_id for c in concepts
            if c.concept_id in ("j_crew_provision", "serta_provision", "chewy_provision")
        }
        assert len(named) == 0

    def test_no_escalation_for_simple_queries(self) -> None:
        """Simple queries with no concept match never trigger escalation."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = RetrievalResult(
            chunks=[
                _make_chunk("SOFR spread is 300 basis points", score=0.85),
            ],
            injected_definitions={},
        )

        llm = MagicMock()
        llm.complete = MagicMock(return_value=LLMResponse(
            text="The SOFR spread is 300 bps.\n\nConfidence: HIGH",
            tokens_used=30, model="test", duration_seconds=0.5,
        ))

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("What is the SOFR spread?", "doc1")

        assert not resp.escalated
        assert not resp.concepts_matched
        # Only 1 LLM call (answer, no decomposition)
        assert llm.complete.call_count == 1

    def test_concept_query_escalates_on_term_mismatch(self) -> None:
        """Concept queries correctly escalate when document uses different language.

        This is the core value proposition: user says "J.Crew provisions" but the
        document says "intellectual property transfer to unrestricted subsidiary".
        The quality gate detects the term mismatch and triggers decomposition.
        """
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = RetrievalResult(
            chunks=[
                _make_chunk("intellectual property transfer clause", score=0.85),
            ],
            injected_definitions={},
        )

        llm = MagicMock()
        llm.complete = MagicMock(return_value=LLMResponse(
            text="The agreement includes IP protections.\n\nConfidence: HIGH",
            tokens_used=30, model="test", duration_seconds=0.5,
        ))

        engine = QAEngine(retriever=retriever, llm=llm)
        resp = engine.ask("Are there J.Crew provisions?", "doc1")

        assert resp.concepts_matched
        assert "j_crew_provision" in resp.concepts_matched
        assert resp.escalated
        # Should have made at least 2 LLM calls (decomposition + answer)
        assert llm.complete.call_count >= 2
