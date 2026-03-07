# pyright: reportUnsupportedDunderAll=false
"""Generation layer: Q&A engine, report generator, prompts, and response parsing."""

from __future__ import annotations

from importlib import import_module
from typing import Any

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
    "build_citations_from_chunks",
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

_EXPORTS: dict[str, tuple[str, str]] = {
    "ALL_REPORT_SECTIONS": ("credit_analyzer.generation.report_template", "ALL_REPORT_SECTIONS"),
    "ConfidenceLevel": ("credit_analyzer.generation.response_parser", "ConfidenceLevel"),
    "ConversationTurn": ("credit_analyzer.generation.prompts", "ConversationTurn"),
    "GeneratedReport": ("credit_analyzer.generation.report_generator", "GeneratedReport"),
    "GeneratedSection": ("credit_analyzer.generation.report_generator", "GeneratedSection"),
    "QAEngine": ("credit_analyzer.generation.qa_engine", "QAEngine"),
    "QAResponse": ("credit_analyzer.generation.qa_engine", "QAResponse"),
    "ReportGenerator": ("credit_analyzer.generation.report_generator", "ReportGenerator"),
    "ReportSectionTemplate": ("credit_analyzer.generation.report_template", "ReportSectionTemplate"),
    "RetrievalQuery": ("credit_analyzer.generation.report_template", "RetrievalQuery"),
    "SectionStatus": ("credit_analyzer.generation.report_template", "SectionStatus"),
    "SourceCitation": ("credit_analyzer.generation.response_parser", "SourceCitation"),
    "build_citations_from_chunks": ("credit_analyzer.generation.response_parser", "build_citations_from_chunks"),
    "build_context_prompt": ("credit_analyzer.generation.prompts", "build_context_prompt"),
    "build_reformulation_prompt": ("credit_analyzer.generation.prompts", "build_reformulation_prompt"),
    "citations_from_chunks": ("credit_analyzer.generation.response_parser", "citations_from_chunks"),
    "enrich_citations": ("credit_analyzer.generation.response_parser", "enrich_citations"),
    "extract_answer_body": ("credit_analyzer.generation.response_parser", "extract_answer_body"),
    "get_extraction_system_prompt": ("credit_analyzer.generation.report_template", "get_extraction_system_prompt"),
    "parse_confidence": ("credit_analyzer.generation.response_parser", "parse_confidence"),
    "parse_page_numbers": ("credit_analyzer.generation.response_parser", "parse_page_numbers"),
    "parse_sources_from_llm": ("credit_analyzer.generation.response_parser", "parse_sources_from_llm"),
    "truncate_definition": ("credit_analyzer.generation.prompts", "truncate_definition"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])
