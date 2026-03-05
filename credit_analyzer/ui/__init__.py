"""Streamlit UI helpers for the demo app."""

from credit_analyzer.ui.demo_report import (
    DEFAULT_BRIEF_PROMPTS,
    SUGGESTED_QUESTIONS,
    BriefPrompt,
    BriefSection,
    build_demo_brief,
)
from credit_analyzer.ui.theme import APP_CSS
from credit_analyzer.ui.workflows import (
    DocumentStats,
    ProcessedDocument,
    build_processed_document,
    save_uploaded_pdf,
)

__all__ = [
    "APP_CSS",
    "DEFAULT_BRIEF_PROMPTS",
    "SUGGESTED_QUESTIONS",
    "BriefPrompt",
    "BriefSection",
    "DocumentStats",
    "ProcessedDocument",
    "build_demo_brief",
    "build_processed_document",
    "save_uploaded_pdf",
]
