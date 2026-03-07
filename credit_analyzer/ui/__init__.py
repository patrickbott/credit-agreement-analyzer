# pyright: reportUnsupportedDunderAll=false
"""Streamlit UI helpers for the demo app."""

from __future__ import annotations

from importlib import import_module
from typing import Any

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

_EXPORTS: dict[str, tuple[str, str]] = {
    "APP_CSS": ("credit_analyzer.ui.theme", "APP_CSS"),
    "DEFAULT_BRIEF_PROMPTS": ("credit_analyzer.ui.demo_report", "DEFAULT_BRIEF_PROMPTS"),
    "SUGGESTED_QUESTIONS": ("credit_analyzer.ui.demo_report", "SUGGESTED_QUESTIONS"),
    "BriefPrompt": ("credit_analyzer.ui.demo_report", "BriefPrompt"),
    "BriefSection": ("credit_analyzer.ui.demo_report", "BriefSection"),
    "DocumentStats": ("credit_analyzer.ui.workflows", "DocumentStats"),
    "ProcessedDocument": ("credit_analyzer.ui.workflows", "ProcessedDocument"),
    "build_demo_brief": ("credit_analyzer.ui.demo_report", "build_demo_brief"),
    "build_processed_document": ("credit_analyzer.ui.workflows", "build_processed_document"),
    "save_uploaded_pdf": ("credit_analyzer.ui.workflows", "save_uploaded_pdf"),
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
