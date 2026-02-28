"""Tests for the Q&A engine, prompts, and response parser."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.generation.prompts import (
    ConversationTurn,
    _format_page_numbers,
    build_context_prompt,
    truncate_definition,
)
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.response_parser import (
    SourceCitation,
    extract_answer_body,
    parse_confidence,
    parse_page_numbers,
    parse_sources_from_llm,
)
from credit_analyzer.llm.base import LLMResponse
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c1",
    text: str = "The Borrower shall maintain a Total Leverage Ratio not exceeding 4.50:1.00.",
    section_id: str = "7.11",
    section_title: str = "Financial Covenants",
    article_number: int = 7,
    article_title: str = "NEGATIVE COVENANTS",
    section_type: str = "financial_covenants",
    page_numbers: list[int] | None = None,
) -> Chunk:
    """Create a Chunk with sensible defaults for testing."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id=section_id,
        section_title=section_title,
        article_number=article_number,
        article_title=article_title,
        section_type=section_type,
        chunk_type="text",
        page_numbers=page_numbers or [45, 46],
        defined_terms_present=["Total Leverage Ratio"],
        chunk_index=0,
        token_count=30,
    )


def _make_hybrid_chunk(
    chunk_id: str = "c1",
    score: float = 0.85,
    **kwargs: object,
) -> HybridChunk:
    """Create a HybridChunk wrapping a Chunk for testing."""
    return HybridChunk(
        chunk=_make_chunk(chunk_id=chunk_id, **kwargs),  # type: ignore[arg-type]
        score=score,
        source="both",
    )


def _make_retrieval_result(
    chunks: list[HybridChunk] | None = None,
    definitions: dict[str, str] | None = None,
) -> RetrievalResult:
    """Create a RetrievalResult with sensible defaults."""
    if chunks is None:
        chunks = [_make_hybrid_chunk()]
    return RetrievalResult(
        chunks=chunks,
        injected_definitions=definitions or {},
    )


def _mock_llm_response(
    text: str = (
        "The Total Leverage Ratio must not exceed 4.50:1.00 per Section 7.11.\n\n"
        "Confidence: HIGH\n"
        "Sources: Section 7.11 (pp. 45-46)"
    ),
) -> LLMResponse:
    """Create a mock LLMResponse."""
    return LLMResponse(
        text=text,
        tokens_used=50,
        model="llama3:8b",
        duration_seconds=1.5,
    )


# ---------------------------------------------------------------------------
# truncate_definition
# ---------------------------------------------------------------------------


class TestTruncateDefinition:
    """Tests for definition truncation."""

    def test_short_definition_unchanged(self) -> None:
        """Definitions under the limit are returned as-is."""
        defn = "Total Leverage Ratio means X."
        assert truncate_definition(defn, 500) == defn

    def test_truncate_at_sentence_boundary(self) -> None:
        """Long definitions are cut at the last sentence boundary."""
        defn = "First sentence. Second sentence. Third sentence that is very long."
        result = truncate_definition(defn, 40)
        assert result == "First sentence. Second sentence."

    def test_truncate_with_ellipsis_fallback(self) -> None:
        """If no good sentence boundary, falls back to ellipsis."""
        defn = "A single very long sentence without any periods until the very end"
        result = truncate_definition(defn, 30)
        assert result.endswith("...")
        assert len(result) <= 33  # 30 + "..."


# ---------------------------------------------------------------------------
# parse_confidence
# ---------------------------------------------------------------------------


class TestParseConfidence:
    """Tests for confidence extraction from LLM output."""

    def test_parse_high(self) -> None:
        assert parse_confidence("answer text\n\nConfidence: HIGH") == "HIGH"

    def test_parse_medium(self) -> None:
        assert parse_confidence("some text\nConfidence: MEDIUM\n") == "MEDIUM"

    def test_parse_low(self) -> None:
        assert parse_confidence("Confidence: LOW") == "LOW"

    def test_case_insensitive(self) -> None:
        assert parse_confidence("confidence: high") == "HIGH"

    def test_missing_defaults_to_low(self) -> None:
        assert parse_confidence("No confidence line here.") == "LOW"

    def test_with_extra_whitespace(self) -> None:
        assert parse_confidence("  Confidence :  HIGH  ") == "HIGH"

    def test_markdown_bold_wrapped(self) -> None:
        """Claude often wraps in **bold**."""
        assert parse_confidence("answer\n\n**Confidence: HIGH**") == "HIGH"

    def test_markdown_bold_key_only(self) -> None:
        """**Confidence:** MEDIUM format."""
        assert parse_confidence("text\n**Confidence:** MEDIUM") == "MEDIUM"

    def test_markdown_bold_value_only(self) -> None:
        """Confidence: **HIGH** format."""
        assert parse_confidence("text\nConfidence: **HIGH**") == "HIGH"


# ---------------------------------------------------------------------------
# parse_page_numbers
# ---------------------------------------------------------------------------


class TestParsePageNumbers:
    """Tests for page number string parsing."""

    def test_single_page(self) -> None:
        assert parse_page_numbers("45") == [45]

    def test_range(self) -> None:
        assert parse_page_numbers("45-47") == [45, 46, 47]

    def test_comma_separated(self) -> None:
        assert parse_page_numbers("45, 50") == [45, 50]

    def test_mixed(self) -> None:
        assert parse_page_numbers("10-12, 20") == [10, 11, 12, 20]

    def test_invalid_ignored(self) -> None:
        assert parse_page_numbers("abc") == []

    def test_empty_string(self) -> None:
        assert parse_page_numbers("") == []


# ---------------------------------------------------------------------------
# parse_sources_from_llm
# ---------------------------------------------------------------------------


class TestParseSourcesFromLLM:
    """Tests for citation parsing from LLM text."""

    def test_single_citation(self) -> None:
        text = "Answer.\n\nSources: Section 7.11 (pp. 45-46)"
        citations = parse_sources_from_llm(text)
        assert len(citations) == 1
        assert citations[0].section_id == "7.11"
        assert citations[0].page_numbers == [45, 46]

    def test_markdown_bold_sources(self) -> None:
        """Claude wraps Sources in **bold**."""
        text = "Answer.\n\n**Sources:** Section 7.11 (pp. 45-46)"
        citations = parse_sources_from_llm(text)
        assert len(citations) == 1
        assert citations[0].section_id == "7.11"

    def test_markdown_bold_sources_full(self) -> None:
        """Full bold wrap on sources line."""
        text = "Answer.\n\n**Sources: Section 7.11 (pp. 45-46)**"
        citations = parse_sources_from_llm(text)
        assert len(citations) == 1
        assert citations[0].section_id == "7.11"

    def test_multiple_citations(self) -> None:
        text = "Answer.\nSources: Section 7.06 (pp. 40-42), Section 2.01 (pp. 10)"
        citations = parse_sources_from_llm(text)
        assert len(citations) == 2
        assert citations[0].section_id == "7.06"
        assert citations[1].section_id == "2.01"

    def test_no_sources_line(self) -> None:
        assert parse_sources_from_llm("Just an answer.") == []

    def test_citation_without_pages(self) -> None:
        text = "Sources: Section 7.11"
        citations = parse_sources_from_llm(text)
        assert len(citations) == 1
        assert citations[0].page_numbers == []


# ---------------------------------------------------------------------------
# extract_answer_body
# ---------------------------------------------------------------------------


class TestExtractAnswerBody:
    """Tests for stripping metadata from the LLM response."""

    def test_strips_confidence_and_sources(self) -> None:
        text = (
            "The ratio is 4.50x.\n\n"
            "Confidence: HIGH\n"
            "Sources: Section 7.11 (pp. 45)"
        )
        assert extract_answer_body(text) == "The ratio is 4.50x."

    def test_no_metadata(self) -> None:
        text = "Just an answer with no metadata."
        assert extract_answer_body(text) == text

    def test_confidence_only(self) -> None:
        text = "Answer here.\nConfidence: MEDIUM"
        assert extract_answer_body(text) == "Answer here."


# ---------------------------------------------------------------------------
# build_context_prompt
# ---------------------------------------------------------------------------


class TestBuildContextPrompt:
    """Tests for context assembly."""

    def test_basic_assembly(self) -> None:
        chunks = [_make_hybrid_chunk()]
        prompt = build_context_prompt(
            chunks=chunks, definitions={}, history=[], question="What is the leverage ratio?"
        )
        assert "CONTEXT FROM CREDIT AGREEMENT" in prompt
        assert "Section 7.11" in prompt
        assert "CURRENT QUESTION" in prompt
        assert "What is the leverage ratio?" in prompt

    def test_includes_definitions(self) -> None:
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={"Total Leverage Ratio": "means the ratio of X to Y"},
            history=[],
            question="Q?",
        )
        assert "RELEVANT DEFINITIONS" in prompt
        assert '"Total Leverage Ratio" means' in prompt

    def test_includes_history(self) -> None:
        history = [ConversationTurn(question="What is X?", answer="X is Y.")]
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=history,
            question="Follow up?",
        )
        assert "PREVIOUS Q&A" in prompt
        assert "What is X?" in prompt
        assert "X is Y." in prompt

    def test_no_definitions_section_when_empty(self) -> None:
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=[],
            question="Q?",
        )
        assert "RELEVANT DEFINITIONS" not in prompt

    def test_no_history_section_when_empty(self) -> None:
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=[],
            question="Q?",
        )
        assert "PREVIOUS Q&A" not in prompt


# ---------------------------------------------------------------------------
# SourceCitation
# ---------------------------------------------------------------------------


class TestSourceCitation:
    """Tests for the SourceCitation dataclass."""

    def test_fields(self) -> None:
        cite = SourceCitation(
            section_id="7.06",
            section_title="Restricted Payments",
            page_numbers=[40, 41],
            relevant_text_snippet="The Borrower shall not...",
        )
        assert cite.section_id == "7.06"
        assert cite.page_numbers == [40, 41]


# ---------------------------------------------------------------------------
# QAEngine
# ---------------------------------------------------------------------------


class TestQAEngine:
    """Tests for the QAEngine class."""

    @staticmethod
    def _make_engine(
        retrieval_result: RetrievalResult | None = None,
        llm_text: str | None = None,
    ) -> QAEngine:
        """Build a QAEngine with mocked retriever and LLM."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = retrieval_result or _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response(llm_text or (
            "The Total Leverage Ratio must not exceed 4.50:1.00 per Section 7.11.\n\n"
            "Confidence: HIGH\n"
            "Sources: Section 7.11 (pp. 45-46)"
        )))

        return QAEngine(retriever=retriever, llm=llm)

    def test_basic_ask(self) -> None:
        """A straightforward question returns a well-formed QAResponse."""
        engine = self._make_engine()
        resp = engine.ask("What is the leverage ratio?", "doc1")

        assert isinstance(resp, QAResponse)
        assert "4.50:1.00" in resp.answer
        assert resp.confidence == "HIGH"
        assert len(resp.sources) >= 1
        assert resp.sources[0].section_id == "7.11"

    def test_history_grows(self) -> None:
        """Conversation history accumulates across calls."""
        engine = self._make_engine()
        assert engine.history_length == 0

        engine.ask("Q1?", "doc1")
        assert engine.history_length == 1

        engine.ask("Q2?", "doc1")
        assert engine.history_length == 2

    def test_clear_history(self) -> None:
        """clear_history resets the conversation."""
        engine = self._make_engine()
        engine.ask("Q?", "doc1")
        assert engine.history_length == 1

        engine.clear_history()
        assert engine.history_length == 0

    def test_reformulation_on_followup(self) -> None:
        """When history exists, the LLM is called twice (reformulate + answer)."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(
            side_effect=[
                _mock_llm_response(),  # answer Q1
                LLMResponse(  # reformulation
                    text="standalone query about leverage ratio details",
                    tokens_used=10,
                    model="llama3:8b",
                    duration_seconds=0.3,
                ),
                _mock_llm_response(),  # answer Q2
            ]
        )

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("What is the leverage ratio?", "doc1")
        engine.ask("What about the step-downs?", "doc1")

        # Reformulation call + 2 answer calls = 3 total
        assert llm.complete.call_count == 3

    def test_no_reformulation_on_first_question(self) -> None:
        """First question should NOT trigger reformulation (no history)."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("What is the leverage ratio?", "doc1")

        assert llm.complete.call_count == 1

    def test_fallback_citations_when_no_sources_line(self) -> None:
        """If the LLM omits Sources:, citations are built from chunks."""
        engine = self._make_engine(
            llm_text="The ratio is 4.50x.\n\nConfidence: HIGH"
        )
        resp = engine.ask("Q?", "doc1")

        assert len(resp.sources) >= 1
        assert resp.sources[0].section_id == "7.11"
        assert resp.sources[0].section_title == "Financial Covenants"

    def test_confidence_defaults_to_low(self) -> None:
        """If LLM omits confidence, defaults to LOW."""
        engine = self._make_engine(llm_text="Some answer without confidence.")
        resp = engine.ask("Q?", "doc1")
        assert resp.confidence == "LOW"

    def test_multiple_chunks_in_context(self) -> None:
        """Multiple retrieved chunks appear in the assembled context."""
        chunks = [
            _make_hybrid_chunk(chunk_id="c1", section_id="7.11", score=0.9),
            _make_hybrid_chunk(
                chunk_id="c2",
                section_id="7.06",
                section_title="Restricted Payments",
                text="The Borrower shall not declare any dividend...",
                score=0.7,
            ),
        ]
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result(chunks=chunks)

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1")

        call_args = llm.complete.call_args
        user_prompt: str = call_args.kwargs["user_prompt"]
        assert "Section 7.11" in user_prompt
        assert "Section 7.06" in user_prompt

    def test_definitions_injected_in_prompt(self) -> None:
        """Injected definitions from retrieval appear in the prompt."""
        result = _make_retrieval_result(
            definitions={"Total Leverage Ratio": "means the ratio of Debt to EBITDA"},
        )
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = result

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1")

        user_prompt: str = llm.complete.call_args.kwargs["user_prompt"]
        assert "Total Leverage Ratio" in user_prompt
        assert "RELEVANT DEFINITIONS" in user_prompt

    def test_reformulation_failure_falls_back(self) -> None:
        """If reformulation LLM call fails, original question is used."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(
            side_effect=[
                _mock_llm_response(),  # Q1 answer
                RuntimeError("LLM unavailable"),  # reformulation fails
                _mock_llm_response(),  # Q2 answer
            ]
        )

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q1?", "doc1")
        resp = engine.ask("Q2?", "doc1")
        assert isinstance(resp, QAResponse)

    def test_retriever_called_with_correct_args(self) -> None:
        """Verify retriever is called with the right document_id, top_k, and exclude."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(
            retriever=retriever,
            llm=llm,
            max_context_chunks=7,
            section_types_exclude=("definitions", "miscellaneous"),
        )
        engine.ask("What is the revolver?", "ribbon_2024")

        retriever.retrieve.assert_called_once()
        call_kwargs = retriever.retrieve.call_args.kwargs
        assert call_kwargs["document_id"] == "ribbon_2024"
        assert call_kwargs["top_k"] == 7
        assert call_kwargs["section_types_exclude"] == ("definitions", "miscellaneous")

    def test_temperature_always_zero(self) -> None:
        """LLM calls always use temperature=0.0 for determinism."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1")

        for call in llm.complete.call_args_list:
            assert call.kwargs["temperature"] == 0.0

    def test_empty_retrieval_result(self) -> None:
        """Engine handles empty retrieval gracefully."""
        engine = self._make_engine(
            retrieval_result=RetrievalResult(chunks=[], injected_definitions={}),
            llm_text=(
                "I could not find this information in the sections I was able "
                "to retrieve from the agreement.\n\nConfidence: LOW"
            ),
        )
        resp = engine.ask("What is XYZ?", "doc1")
        assert resp.confidence == "LOW"
        assert len(resp.retrieved_chunks) == 0


# ---------------------------------------------------------------------------
# _format_page_numbers
# ---------------------------------------------------------------------------


class TestFormatPageNumbers:
    """Tests for compact page number formatting."""

    def test_single_page(self) -> None:
        assert _format_page_numbers([42]) == "42"

    def test_consecutive_range(self) -> None:
        assert _format_page_numbers([10, 11, 12, 13]) == "10-13"

    def test_multiple_ranges(self) -> None:
        assert _format_page_numbers([10, 11, 12, 20, 21]) == "10-12, 20-21"

    def test_mixed_singles_and_ranges(self) -> None:
        assert _format_page_numbers([5, 10, 11, 12, 20]) == "5, 10-12, 20"

    def test_empty(self) -> None:
        assert _format_page_numbers([]) == ""

    def test_deduplicates(self) -> None:
        assert _format_page_numbers([5, 5, 6, 6]) == "5-6"

    def test_sorts(self) -> None:
        assert _format_page_numbers([20, 10, 11]) == "10-11, 20"

    def test_long_range(self) -> None:
        """A 48-page range collapses to a single compact string."""
        pages = list(range(9, 57))  # pages 9-56
        result = _format_page_numbers(pages)
        assert result == "9-56"
        assert len(result) < 10  # much shorter than comma-separated


# ---------------------------------------------------------------------------
# Definition deduplication in build_context_prompt
# ---------------------------------------------------------------------------


class TestDefinitionDedup:
    """Tests for definition dedup in context assembly."""

    def test_definition_already_in_chunk_is_skipped(self) -> None:
        """Definitions whose text appears in a retrieved chunk are not injected."""
        defn_text = (
            '"Total Revolving Commitments": at any time, the aggregate amount '
            "of the Revolving Commitments then in effect."
        )
        chunk = _make_hybrid_chunk(
            chunk_id="c1",
            text=defn_text + " More text follows here.",
            section_id="2.4",
            section_title="Revolving Commitments",
        )
        prompt = build_context_prompt(
            chunks=[chunk],
            definitions={"Total Revolving Commitments": defn_text},
            history=[],
            question="What is the revolving commitment?",
        )
        # The definition section should not appear because it's already in the chunk
        assert "RELEVANT DEFINITIONS" not in prompt

    def test_novel_definition_is_included(self) -> None:
        """Definitions not present in chunks are still injected."""
        chunk = _make_hybrid_chunk(
            chunk_id="c1",
            text="Some unrelated chunk text about covenants.",
        )
        prompt = build_context_prompt(
            chunks=[chunk],
            definitions={"EBITDA": "Earnings before interest, taxes, depreciation."},
            history=[],
            question="Q?",
        )
        assert "RELEVANT DEFINITIONS" in prompt
        assert "EBITDA" in prompt


# ---------------------------------------------------------------------------
# Preamble injection
# ---------------------------------------------------------------------------


class TestPreambleInjection:
    """Tests for always-injected preamble context."""

    def test_preamble_appears_in_prompt(self) -> None:
        """Preamble text is injected at the top of the context."""
        preamble = (
            "CREDIT AGREEMENT dated March 3, 2020\n"
            "$350,000,000 Term Loan Facility\n"
            "$35,000,000 Revolving Credit Facility"
        )
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=[],
            question="What is the term loan size?",
            preamble_text=preamble,
        )
        assert "Preamble and Recitals" in prompt
        assert "$350,000,000" in prompt
        # Preamble should appear before the regular chunk context
        preamble_pos = prompt.index("Preamble")
        chunk_pos = prompt.index("Section 7.11")
        assert preamble_pos < chunk_pos

    def test_no_preamble_when_none(self) -> None:
        """No preamble section when preamble_text is None."""
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=[],
            question="Q?",
            preamble_text=None,
        )
        assert "Preamble" not in prompt

    def test_no_preamble_when_empty(self) -> None:
        """No preamble section when preamble_text is empty string."""
        prompt = build_context_prompt(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            history=[],
            question="Q?",
            preamble_text="",
        )
        assert "Preamble" not in prompt

    def test_engine_set_preamble(self) -> None:
        """QAEngine.set_preamble stores text and injects it into prompts."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.set_preamble("$350M term loan facility")
        engine.ask("What is the facility size?", "doc1")

        user_prompt: str = llm.complete.call_args.kwargs["user_prompt"]
        assert "$350M" in user_prompt
        assert "Preamble" in user_prompt
