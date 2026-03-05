"""Generation layer: Q&A engine, report generator, prompts, and response parsing."""

from credit_analyzer.generation.prompts import (
    ConversationTurn,
    build_context_prompt,
    build_reformulation_prompt,
    truncate_definition,
)
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.report_generator import (
    GeneratedReport,
    GeneratedSection,
    ReportGenerator,
)
from credit_analyzer.generation.report_template import (
    ALL_REPORT_SECTIONS,
    ReportSectionTemplate,
    RetrievalQuery,
    SectionStatus,
    get_extraction_system_prompt,
)
from credit_analyzer.generation.response_parser import (
    ConfidenceLevel,
    SourceCitation,
    citations_from_chunks,
    enrich_citations,
    extract_answer_body,
    parse_confidence,
    parse_page_numbers,
    parse_sources_from_llm,
)

__all__ = [
    "ALL_REPORT_SECTIONS",
    "ConfidenceLevel",
    "ConversationTurn",
    "GeneratedReport",
    "GeneratedSection",
    "QAEngine",
    "QAResponse",
    "ReportGenerator",
    "ReportSectionTemplate",
    "RetrievalQuery",
    "SectionStatus",
    "SourceCitation",
    "build_context_prompt",
    "build_reformulation_prompt",
    "citations_from_chunks",
    "enrich_citations",
    "extract_answer_body",
    "get_extraction_system_prompt",
    "parse_confidence",
    "parse_page_numbers",
    "parse_sources_from_llm",
    "truncate_definition",
]
