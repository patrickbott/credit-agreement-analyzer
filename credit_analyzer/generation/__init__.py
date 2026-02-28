"""Generation layer: Q&A engine, prompts, and response parsing."""

from credit_analyzer.generation.prompts import (
    ConversationTurn,
    build_context_prompt,
    build_reformulation_prompt,
    truncate_definition,
)
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
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
    "ConfidenceLevel",
    "ConversationTurn",
    "QAEngine",
    "QAResponse",
    "SourceCitation",
    "build_context_prompt",
    "build_reformulation_prompt",
    "citations_from_chunks",
    "enrich_citations",
    "extract_answer_body",
    "parse_confidence",
    "parse_page_numbers",
    "parse_sources_from_llm",
    "truncate_definition",
]
