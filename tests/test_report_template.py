"""Tests for report_template module."""

from __future__ import annotations

from credit_analyzer.generation.report_template import (
    ALL_REPORT_SECTIONS,
    ReportSectionTemplate,
    RetrievalQuery,
    get_extraction_system_prompt,
)


class TestRetrievalQuery:
    """Tests for the RetrievalQuery data class."""

    def test_basic_query(self) -> None:
        rq = RetrievalQuery(query="test query")
        assert rq.query == "test query"
        assert rq.section_filter is None

    def test_query_with_filter(self) -> None:
        rq = RetrievalQuery(query="test", section_filter="negative_covenants")
        assert rq.section_filter == "negative_covenants"


class TestReportSectionTemplate:
    """Tests for the ReportSectionTemplate data class."""

    def test_defaults(self) -> None:
        template = ReportSectionTemplate(
            section_number=1,
            title="Test",
            retrieval_queries=(RetrievalQuery("q"),),
            extraction_prompt="Extract stuff.",
        )
        assert template.top_k == 15
        assert template.max_generation_tokens == 1500
        assert template.include_preamble is False

    def test_custom_values(self) -> None:
        template = ReportSectionTemplate(
            section_number=6,
            title="Debt Capacity",
            retrieval_queries=(
                RetrievalQuery("q1"),
                RetrievalQuery("q2", section_filter="negative_covenants"),
            ),
            extraction_prompt="Extract debt.",
            top_k=20,
            max_generation_tokens=2500,
            include_preamble=True,
        )
        assert template.section_number == 6
        assert len(template.retrieval_queries) == 2
        assert template.retrieval_queries[1].section_filter == "negative_covenants"
        assert template.top_k == 20
        assert template.include_preamble is True


class TestAllReportSections:
    """Tests for the ALL_REPORT_SECTIONS tuple."""

    def test_all_have_queries(self) -> None:
        for section in ALL_REPORT_SECTIONS:
            assert len(section.retrieval_queries) >= 1, (
                f"Section {section.section_number} has no retrieval queries"
            )

    def test_all_have_prompts(self) -> None:
        for section in ALL_REPORT_SECTIONS:
            assert len(section.extraction_prompt) > 20, (
                f"Section {section.section_number} has a very short prompt"
            )

    def test_all_titles_nonempty(self) -> None:
        for section in ALL_REPORT_SECTIONS:
            assert section.title.strip(), (
                f"Section {section.section_number} has an empty title"
            )

class TestExtractionSystemPrompt:
    """Tests for the shared extraction system prompt."""

    def test_nonempty(self) -> None:
        prompt = get_extraction_system_prompt()
        assert len(prompt) > 100

    def test_has_confidence_instruction(self) -> None:
        prompt = get_extraction_system_prompt()
        assert "Confidence:" in prompt

    def test_has_citation_instruction(self) -> None:
        prompt = get_extraction_system_prompt()
        assert "source number" in prompt.lower() or "[Source" in prompt

    def test_no_markdown_instruction(self) -> None:
        prompt = get_extraction_system_prompt()
        assert "no markdown" in prompt.lower() or "no **" in prompt
