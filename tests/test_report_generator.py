"""Tests for report_generator module."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.generation.report_generator import (
    GeneratedReport,
    GeneratedSection,
    ReportGenerator,
    _build_extraction_context,
    _extract_borrower_name,
    _retrieve_for_section,
)
from credit_analyzer.generation.report_template import (
    ALL_REPORT_SECTIONS,
    ReportSectionTemplate,
    RetrievalQuery,
)
from credit_analyzer.llm.base import LLMResponse
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c1",
    text: str = "The Revolving Commitment is $50,000,000.",
    section_id: str = "2.01",
    section_title: str = "Revolving Commitments",
    section_type: str = "facility_terms",
    page_numbers: list[int] | None = None,
) -> Chunk:
    """Create a Chunk with sensible defaults."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id=section_id,
        section_title=section_title,
        article_number=2,
        article_title="THE FACILITIES",
        section_type=section_type,
        chunk_type="text",
        page_numbers=page_numbers or [10, 11],
        defined_terms_present=[],
        chunk_index=0,
        token_count=30,
    )


def _make_hybrid_chunk(
    chunk_id: str = "c1",
    score: float = 0.85,
    **kwargs: object,
) -> HybridChunk:
    """Create a HybridChunk for testing."""
    return HybridChunk(
        chunk=_make_chunk(chunk_id=chunk_id, **kwargs),  # type: ignore[arg-type]
        score=score,
        source="both",
    )


def _make_retrieval_result(
    chunks: list[HybridChunk] | None = None,
    definitions: dict[str, str] | None = None,
) -> RetrievalResult:
    """Create a RetrievalResult with defaults."""
    if chunks is None:
        chunks = [_make_hybrid_chunk()]
    return RetrievalResult(
        chunks=chunks,
        injected_definitions=definitions or {},
    )


def _mock_llm_response(text: str | None = None) -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        text=text or (
            "BORROWER: Ribbon Communications Operating Company, Inc.\n"
            "PARENT / HOLDINGS: Ribbon Communications Inc.\n"
            "SPONSOR: NOT FOUND\n"
            "PURPOSE: Refinancing of existing credit facilities.\n"
            "CLOSING DATE: March 3, 2020 (Section 5.01)\n"
            "GOVERNING LAW: New York (Section 10.12)\n\n"
            "Confidence: HIGH\n"
            "Sources: Section 1.01 (pp. 1-2), Section 5.01 (pp. 80)"
        ),
        tokens_used=120,
        model="claude-sonnet-4-20250514",
        duration_seconds=3.5,
    )


# ---------------------------------------------------------------------------
# _extract_borrower_name
# ---------------------------------------------------------------------------


class TestExtractBorrowerName:
    """Tests for borrower name extraction from Section 1 output."""

    def test_extracts_name(self) -> None:
        body = "BORROWER: Acme Corp LLC\nPARENT: Holdings Inc."
        assert _extract_borrower_name(body) == "Acme Corp LLC"

    def test_case_insensitive(self) -> None:
        body = "Borrower: Some Company Inc."
        assert _extract_borrower_name(body) == "Some Company Inc"

    def test_not_found_returns_none(self) -> None:
        body = "BORROWER: NOT FOUND"
        assert _extract_borrower_name(body) is None

    def test_missing_field_returns_none(self) -> None:
        body = "No borrower line here."
        assert _extract_borrower_name(body) is None

    def test_strips_trailing_period(self) -> None:
        body = "BORROWER: Acme Corp."
        assert _extract_borrower_name(body) == "Acme Corp"


# ---------------------------------------------------------------------------
# _build_extraction_context
# ---------------------------------------------------------------------------


class TestBuildExtractionContext:
    """Tests for the report-section context assembly."""

    def test_includes_context_and_task(self) -> None:
        chunks = [_make_hybrid_chunk()]
        result = _build_extraction_context(
            chunks=chunks,
            definitions={},
            extraction_prompt="Extract the facility details.",
        )
        assert "CONTEXT FROM CREDIT AGREEMENT" in result
        assert "EXTRACTION TASK" in result
        assert "Extract the facility details." in result

    def test_includes_preamble_when_provided(self) -> None:
        result = _build_extraction_context(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            extraction_prompt="Extract.",
            preamble_text="CREDIT AGREEMENT dated March 3, 2020",
            preamble_page_numbers=[1, 2, 3],
        )
        assert "Preamble" in result
        assert "Pages 1-3" in result
        assert "March 3, 2020" in result

    def test_no_preamble_when_none(self) -> None:
        result = _build_extraction_context(
            chunks=[_make_hybrid_chunk()],
            definitions={},
            extraction_prompt="Extract.",
        )
        assert "Preamble" not in result

    def test_includes_definitions(self) -> None:
        result = _build_extraction_context(
            chunks=[_make_hybrid_chunk()],
            definitions={"Revolver": "means the revolving credit facility"},
            extraction_prompt="Extract.",
        )
        assert "RELEVANT DEFINITIONS" in result
        assert "Revolver" in result

    def test_skips_duplicate_definitions(self) -> None:
        """Definitions whose text appears in chunks are excluded."""
        defn_text = "The Revolving Commitment is $50,000,000."
        chunk = _make_hybrid_chunk(text=defn_text)
        result = _build_extraction_context(
            chunks=[chunk],
            definitions={"Revolving Commitment": defn_text},
            extraction_prompt="Extract.",
        )
        assert "RELEVANT DEFINITIONS" not in result


# ---------------------------------------------------------------------------
# _retrieve_for_section
# ---------------------------------------------------------------------------


class TestRetrieveForSection:
    """Tests for multi-query retrieval with deduplication."""

    def test_single_query(self) -> None:
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        result = _retrieve_for_section(
            retriever,
            "doc1",
            (RetrievalQuery("test query"),),
            top_k=5,
        )
        assert len(result.chunks) == 1
        retriever.retrieve.assert_called_once()

    def test_multiple_queries_deduplicates(self) -> None:
        """Same chunk from two queries is only included once."""
        retriever = MagicMock(spec=HybridRetriever)
        # Both queries return the same chunk
        retriever.retrieve.return_value = _make_retrieval_result(
            chunks=[_make_hybrid_chunk(chunk_id="shared", score=0.8)]
        )

        result = _retrieve_for_section(
            retriever,
            "doc1",
            (
                RetrievalQuery("query 1"),
                RetrievalQuery("query 2"),
            ),
            top_k=10,
        )
        assert len(result.chunks) == 1

    def test_keeps_highest_score(self) -> None:
        """When same chunk appears with different scores, keeps the highest."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.side_effect = [
            _make_retrieval_result(
                chunks=[_make_hybrid_chunk(chunk_id="c1", score=0.5)]
            ),
            _make_retrieval_result(
                chunks=[_make_hybrid_chunk(chunk_id="c1", score=0.9)]
            ),
        ]

        result = _retrieve_for_section(
            retriever,
            "doc1",
            (RetrievalQuery("q1"), RetrievalQuery("q2")),
            top_k=5,
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.9

    def test_merges_definitions(self) -> None:
        """Definitions from multiple queries are merged."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.side_effect = [
            _make_retrieval_result(definitions={"TermA": "def A"}),
            _make_retrieval_result(definitions={"TermB": "def B"}),
        ]

        result = _retrieve_for_section(
            retriever,
            "doc1",
            (RetrievalQuery("q1"), RetrievalQuery("q2")),
            top_k=5,
        )
        assert "TermA" in result.injected_definitions
        assert "TermB" in result.injected_definitions

    def test_respects_top_k(self) -> None:
        """Result is limited to top_k chunks even after merging."""
        retriever = MagicMock(spec=HybridRetriever)
        many_chunks = [
            _make_hybrid_chunk(chunk_id=f"c{i}", score=0.9 - i * 0.01)
            for i in range(10)
        ]
        retriever.retrieve.return_value = _make_retrieval_result(chunks=many_chunks)

        result = _retrieve_for_section(
            retriever, "doc1", (RetrievalQuery("q"),), top_k=3,
        )
        assert len(result.chunks) == 3

    def test_passes_section_filter(self) -> None:
        """Section filter from RetrievalQuery is passed to retriever."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        _retrieve_for_section(
            retriever,
            "doc1",
            (RetrievalQuery("q", section_filter="negative_covenants"),),
            top_k=5,
        )
        call_kwargs = retriever.retrieve.call_args.kwargs
        assert call_kwargs["section_filter"] == "negative_covenants"


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------


class TestReportGenerator:
    """Tests for the ReportGenerator orchestrator."""

    @staticmethod
    def _make_generator(
        llm_text: str | None = None,
    ) -> ReportGenerator:
        """Build a generator with mocked retriever and LLM."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response(llm_text))

        return ReportGenerator(retriever=retriever, llm=llm)

    def test_generate_single_section(self) -> None:
        """Generate a single section and verify the result."""
        gen = self._make_generator()
        template = ReportSectionTemplate(
            section_number=1,
            title="Test Section",
            retrieval_queries=(RetrievalQuery("test"),),
            extraction_prompt="Extract test data.",
            max_generation_tokens=500,
        )
        report = gen.generate("doc1", sections=(template,))

        assert len(report.sections) == 1
        assert report.sections[0].status == "complete"
        assert report.sections[0].title == "Test Section"
        assert report.sections[0].confidence in ("HIGH", "MEDIUM", "LOW")
        assert report.total_duration_seconds > 0

    def test_generate_extracts_borrower_from_section_1(self) -> None:
        """Borrower name is extracted from Section 1 output."""
        gen = self._make_generator()
        report = gen.generate(
            "doc1",
            sections=(ALL_REPORT_SECTIONS[0],),
        )
        assert report.borrower_name == "Ribbon Communications Operating Company, Inc"

    def test_generate_handles_llm_error(self) -> None:
        """If the LLM call fails, section status is 'error'."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(side_effect=RuntimeError("model crashed"))

        gen = ReportGenerator(retriever=retriever, llm=llm)
        template = ReportSectionTemplate(
            section_number=1,
            title="Failing Section",
            retrieval_queries=(RetrievalQuery("test"),),
            extraction_prompt="Extract.",
        )
        report = gen.generate("doc1", sections=(template,))

        assert len(report.sections) == 1
        assert report.sections[0].status == "error"
        assert "model crashed" in report.sections[0].error_message

    def test_progress_callback_fires(self) -> None:
        """Progress callback is called for each section."""
        gen = self._make_generator()
        calls: list[tuple[str, float]] = []

        def on_progress(label: str, progress: float) -> None:
            calls.append((label, progress))

        gen.generate(
            "doc1",
            sections=(ALL_REPORT_SECTIONS[0],),
            progress_callback=on_progress,
        )
        assert len(calls) >= 2  # At least one section + "Report complete."
        assert calls[-1][0] == "Report complete."
        assert calls[-1][1] == 1.0

    def test_preamble_injection(self) -> None:
        """set_preamble stores text and it reaches the LLM prompt."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        gen = ReportGenerator(retriever=retriever, llm=llm)
        gen.set_preamble("$350M Term Loan Facility", page_numbers=[1, 2, 3])

        template = ReportSectionTemplate(
            section_number=1,
            title="Overview",
            retrieval_queries=(RetrievalQuery("q"),),
            extraction_prompt="Extract.",
            include_preamble=True,
        )
        gen.generate("doc1", sections=(template,))

        user_prompt: str = llm.complete.call_args.kwargs["user_prompt"]
        assert "$350M" in user_prompt
        assert "Pages 1-3" in user_prompt

    def test_no_preamble_when_section_skips_it(self) -> None:
        """Sections with include_preamble=False don't get preamble."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        gen = ReportGenerator(retriever=retriever, llm=llm)
        gen.set_preamble("$350M Term Loan Facility", page_numbers=[1, 2, 3])

        template = ReportSectionTemplate(
            section_number=5,
            title="Financial Covenants",
            retrieval_queries=(RetrievalQuery("q"),),
            extraction_prompt="Extract.",
            include_preamble=False,
        )
        gen.generate("doc1", sections=(template,))

        user_prompt: str = llm.complete.call_args.kwargs["user_prompt"]
        assert "$350M" not in user_prompt


# ---------------------------------------------------------------------------
# GeneratedReport.to_markdown
# ---------------------------------------------------------------------------


class TestGeneratedReportMarkdown:
    """Tests for the markdown export."""

    def test_basic_structure(self) -> None:
        """Markdown has title, disclaimer, and section headings."""
        gen = TestReportGenerator._make_generator()
        report = gen.generate(
            "doc1",
            sections=(ALL_REPORT_SECTIONS[0],),
        )
        md = report.to_markdown()

        assert "Credit Agreement Analysis:" in md
        assert "DISCLAIMER" in md
        assert "Section 1:" in md
        assert "Confidence:" in md

    def test_error_section_in_markdown(self) -> None:
        """Error sections show their error message."""
        from datetime import datetime

        report = GeneratedReport(
            borrower_name="Test",
            generated_at=datetime.now(),
            sections=[
                GeneratedSection(
                    section_number=1,
                    title="Failed",
                    body="",
                    confidence="LOW",
                    sources=[],
                    status="error",
                    error_message="LLM timeout",
                ),
            ],
        )
        md = report.to_markdown()
        assert "GENERATION ERROR" in md
        assert "LLM timeout" in md

    def test_total_duration_in_markdown(self) -> None:
        """Total generation time appears at the bottom."""
        gen = TestReportGenerator._make_generator()
        report = gen.generate("doc1", sections=(ALL_REPORT_SECTIONS[0],))
        md = report.to_markdown()
        assert "Total generation time:" in md


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------


class TestPDFExport:
    """Tests for PDF byte generation."""

    def test_produces_valid_pdf_bytes(self) -> None:
        """PDF output starts with the %PDF header."""
        from credit_analyzer.generation.pdf_export import report_to_pdf_bytes

        gen = TestReportGenerator._make_generator()
        report = gen.generate("doc1", sections=(ALL_REPORT_SECTIONS[0],))
        pdf_bytes = report_to_pdf_bytes(report)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 500

    def test_error_section_does_not_crash_pdf(self) -> None:
        """Reports with error sections still produce valid PDF."""
        from datetime import datetime

        from credit_analyzer.generation.pdf_export import report_to_pdf_bytes

        report = GeneratedReport(
            borrower_name="Test Corp",
            generated_at=datetime.now(),
            sections=[
                GeneratedSection(
                    section_number=1,
                    title="Overview",
                    body="BORROWER: Test Corp",
                    confidence="HIGH",
                    sources=[],
                    status="complete",
                    duration_seconds=1.0,
                    chunk_count=5,
                ),
                GeneratedSection(
                    section_number=2,
                    title="Broken",
                    body="",
                    confidence="LOW",
                    sources=[],
                    status="error",
                    error_message="LLM timeout",
                ),
            ],
        )
        pdf_bytes = report_to_pdf_bytes(report)
        assert pdf_bytes[:5] == b"%PDF-"
