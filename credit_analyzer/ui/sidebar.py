"""Sidebar rendering and document management functions extracted from app.py."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import Any

import streamlit as st

from credit_analyzer.config import CLAUDE_MODEL, LLM_PROVIDER, OLLAMA_MODEL
from credit_analyzer.generation.report_template import ReportSectionTemplate
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.ui.chat import clear_chat, clear_prompt_edit
from credit_analyzer.ui.definitions_dialog import show_definitions_dialog
from credit_analyzer.ui.guide_dialog import show_guide_dialog
from credit_analyzer.ui.report_dialog import show_report_dialog
from credit_analyzer.ui.report_pipeline import (
    generate_report,
    poll_deferred_generation,
    show_section_picker,
)
from credit_analyzer.ui.theme import (
    document_card,
    indexing_step,
    rail_card,
)
from credit_analyzer.ui.workflows import (
    ProcessedDocument,
    build_processed_document,
    save_uploaded_pdf,
)


# ---------------------------------------------------------------------------
# Provider state helpers
# ---------------------------------------------------------------------------


def load_provider_state() -> tuple[LLMProvider | None, dict[str, Any]]:
    cached = st.session_state.provider_status
    if cached is not None:
        provider = cached.get("provider")
        status = {key: value for key, value in cached.items() if key != "provider"}
        return provider, status

    try:
        from app import load_provider

        provider = load_provider(LLM_PROVIDER)
        available = provider.is_available()
        status = {
            "ready": bool(available),
            "provider_name": LLM_PROVIDER,
            "model_name": provider.model_name(),
            "message": (
                "Backend reachable."
                if available
                else "Configured, but not responding."
            ),
        }
    except Exception as exc:
        provider = None
        status = {
            "ready": False,
            "provider_name": LLM_PROVIDER,
            "model_name": configured_model_name(),
            "message": f"Unavailable: {exc}",
        }

    st.session_state.provider_status = {"provider": provider, **status}
    return provider, status


def configured_model_name() -> str:
    if LLM_PROVIDER == "claude":
        return CLAUDE_MODEL
    if LLM_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return LLM_PROVIDER


# ---------------------------------------------------------------------------
# Document removal
# ---------------------------------------------------------------------------


def remove_document(document_id: str) -> None:
    """Remove a document from session state and clean up its ChromaDB collection."""
    from app import load_vector_store

    documents: dict[str, ProcessedDocument] = st.session_state.documents
    clear_prompt_edit(document_id)
    documents.pop(document_id, None)
    st.session_state.chat_messages.pop(document_id, None)
    st.session_state.pending_chat_questions.pop(document_id, None)
    st.session_state.generated_reports.pop(document_id, None)
    st.session_state.pop(f"qa_engine_{document_id}", None)
    # Clear the file uploader so user doesn't have to hit X separately
    for key in list(st.session_state.keys()):
        if "file_uploader" in str(key).lower() or "FormSubmitter" in str(key):
            st.session_state.pop(key, None)
    with contextlib.suppress(Exception):
        load_vector_store().delete_collection(document_id)
    # Switch active document to the next available, or None.
    remaining = list(documents.keys())
    st.session_state.active_document_id = remaining[0] if remaining else None


# ---------------------------------------------------------------------------
# Sidebar rendering
# ---------------------------------------------------------------------------


def render_sidebar(
    active_document: ProcessedDocument | None,
    provider: LLMProvider | None,
    provider_status: dict[str, Any],
) -> None:
    with st.sidebar:
        # -- App title --
        st.markdown(
            '<div style="font-family:DM Sans,system-ui,sans-serif;'
            'font-size:1.1rem;font-weight:700;color:#003DA5;'
            'padding:0.25rem 0 0.05rem 0;margin-bottom:0;'
            'letter-spacing:-0.01em;">'
            "Credit Agreement Analyzer</div>"
            '<div style="font-size:0.68rem;color:#6B7280;'
            'margin-bottom:0.25rem;letter-spacing:0.02em;">'
            "RBC Capital Markets</div>",
            unsafe_allow_html=True,
        )

        # -- Action buttons --
        reports_cache = st.session_state.get("generated_reports", {})
        has_report = bool(
            active_document and active_document.document_id in reports_cache
        )
        report_disabled = active_document is None or not provider_status["ready"]

        new_chat_clicked = st.button(
            "New Chat",
            key="new-chat",
            disabled=active_document is None,
            use_container_width=True,
        )
        defs_clicked = st.button(
            "Definitions",
            key="open-defs",
            disabled=active_document is None,
            use_container_width=True,
        )

        # -- Report feature group --
        if has_report:
            view_report_clicked = st.button(
                "View Report",
                key="view-report",
                disabled=active_document is None,
                use_container_width=True,
            )
            new_report_clicked = st.button(
                "New Report",
                key="new-report",
                disabled=report_disabled,
                use_container_width=True,
            )
            generate_clicked = False
        else:
            generate_clicked = st.button(
                "Generate Report",
                key="gen-report",
                disabled=report_disabled,
                use_container_width=True,
            )
            view_report_clicked = False
            new_report_clicked = False

        guide_clicked = st.button(
            "Guide",
            key="open-guide",
            use_container_width=True,
        )

        if new_chat_clicked and active_document:
            clear_chat(active_document.document_id)
            st.rerun()
        if defs_clicked and active_document:
            show_definitions_dialog(active_document.definitions_index)
        if view_report_clicked and active_document:
            show_report_dialog(active_document)
        if (generate_clicked or new_report_clicked) and active_document and provider:
            show_section_picker()
        if guide_clicked:
            show_guide_dialog()

        # Pick up sections from the dialog and defer generation so the
        # dialog closes (page renders) before the slow blocking call.
        pending_sections: list[ReportSectionTemplate] | None = (
            st.session_state.pop("_pending_report_sections", None)
        )
        if pending_sections and active_document and provider:
            st.session_state["_deferred_report_sections"] = pending_sections
            # Do NOT st.rerun() here — let the script complete so the
            # page renders without the dialog.  The poller fragment
            # below will trigger the actual generation on the next cycle.

        # Deferred-generation poller: a self-triggering fragment that
        # waits one tick (so the dialog-free page reaches the client),
        # then kicks off a full app rerun that starts generation.
        if (
            st.session_state.get("_deferred_report_sections")
            and active_document
            and provider
        ):
            poll_deferred_generation()

        # Start generation when the poller has promoted sections.
        ready_sections: list[ReportSectionTemplate] | None = (
            st.session_state.pop("_ready_report_sections", None)
        )
        if ready_sections and active_document and provider:
            generate_report(active_document, provider, sections=ready_sections)

        # Auto-open report dialog after generation completes
        show_doc_id = st.session_state.pop("_show_report_dialog", None)
        if show_doc_id and show_doc_id in st.session_state.get("generated_reports", {}):
            doc = st.session_state.documents.get(show_doc_id)
            if doc is not None:
                show_report_dialog(doc)

        st.markdown("---")

        # -- Document --
        st.caption("DOCUMENT")
        if active_document is not None:
            st.markdown(
                document_card(
                    filename=Path(active_document.source_path).name,
                    pages=active_document.stats.total_pages,
                    sections=active_document.stats.section_count,
                    chunks=active_document.stats.chunk_count,
                    definitions=active_document.stats.definition_count,
                    source_path=str(active_document.source_path),
                ),
                unsafe_allow_html=True,
            )
            if st.button("Remove Document", key="remove-doc"):
                remove_document(active_document.document_id)
                st.rerun()
        else:
            uploaded_file = st.file_uploader(
                "Agreement PDF",
                type=["pdf"],
                help="PDF files are saved locally in demo_uploads/.",
                label_visibility="collapsed",
            )
            if st.button(
                "Index PDF",
                type="primary",
                disabled=uploaded_file is None,
                use_container_width=True,
            ) and uploaded_file is not None:
                pdf_path = save_uploaded_pdf(
                    uploaded_file.name, uploaded_file.getvalue()
                )
                process_document(pdf_path)

        st.markdown("---")

        # -- Model status --
        model_meta = (
            f"{provider_status['provider_name'].upper()} | Ready"
            if provider_status["ready"]
            else f"{provider_status['provider_name'].upper()} | {provider_status['message']}"
        )
        st.markdown(
            rail_card(
                "Model",
                provider_status["model_name"],
                model_meta,
                tone="ready" if provider_status["ready"] else "warning",
            ),
            unsafe_allow_html=True,
        )
        if not provider_status["ready"] and st.button(
            "Retry Connection", key="retry-model", use_container_width=True
        ):
            st.session_state.provider_status = None
            st.rerun()

        st.markdown(
            '<div style="font-size:0.62rem;color:#9CA3AF;margin-top:0.25rem;">'
            "v1.0</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Document processing with step pipeline
# ---------------------------------------------------------------------------

# Step labels and the callback text patterns that trigger them.
_STEP_LABELS = [
    "Extracting text",
    "Detecting structure",
    "Parsing definitions",
    "Building embeddings",
    "Creating search index",
]

_STEP_TRIGGERS: list[list[str]] = [
    ["Extracting text"],
    ["Detecting"],
    ["Parsing defined", "Chunking"],
    ["Building embeddings", "Reusing cached"],
    ["Creating", "search index"],
]


def determine_active_step(label: str) -> int:
    """Return the 0-based index of the currently active pipeline step."""
    label_lower = label.lower()
    for i, triggers in enumerate(_STEP_TRIGGERS):
        for trigger in triggers:
            if trigger.lower() in label_lower:
                return i
    return 0


def render_step_pipeline(active_step: int, counts: dict[int, str]) -> str:
    """Build the full step pipeline HTML."""
    parts = ['<div class="step-pipeline">']
    for i, step_label in enumerate(_STEP_LABELS):
        if i < active_step:
            status = "complete"
        elif i == active_step:
            status = "active"
        else:
            status = "pending"
        count = counts.get(i, "")
        parts.append(indexing_step(step_label, status, count))
    parts.append("</div>")
    return "".join(parts)


def process_document(pdf_path: Path) -> None:
    from app import load_embedder, load_reranker, load_vector_store

    pipeline_placeholder = st.sidebar.empty()
    step_counts: dict[int, str] = {}

    def on_progress(label: str, progress: float) -> None:
        active = determine_active_step(label)
        # Extract count info from the label if available
        if "pages" in label.lower():
            m = re.search(r"(\d+)\s*pages", label, re.IGNORECASE)
            if m:
                step_counts[0] = f"{m.group(1)} pages"
        elif "sections" in label.lower() and active >= 1:
            m = re.search(r"(\d+)\s*sections", label, re.IGNORECASE)
            if m:
                step_counts[1] = f"{m.group(1)} sections"
        elif "terms" in label.lower():
            m = re.search(r"(\d+)\s*terms", label, re.IGNORECASE)
            if m:
                step_counts[2] = f"{m.group(1)} terms"
        elif "chunks" in label.lower():
            m = re.search(r"(\d+/\d+)\s*chunks", label, re.IGNORECASE)
            if m:
                step_counts[3] = f"{m.group(1)} chunks"
            else:
                m2 = re.search(r"(\d+)\s*chunks", label, re.IGNORECASE)
                if m2:
                    step_counts[3] = f"{m2.group(1)} chunks"

        pipeline_placeholder.markdown(
            render_step_pipeline(active, step_counts),
            unsafe_allow_html=True,
        )

    try:
        document = build_processed_document(
            pdf_path,
            embedder=load_embedder(),
            vector_store=load_vector_store(),
            reranker=load_reranker(),
            progress_callback=on_progress,
        )
    except Exception as exc:
        pipeline_placeholder.empty()
        st.error(f"Processing failed: {exc}")
        return

    st.session_state.documents[document.document_id] = document
    st.session_state.active_document_id = document.document_id
    st.session_state.chat_messages[document.document_id] = []
    st.session_state.generated_reports.pop(document.document_id, None)

    pipeline_placeholder.empty()
    st.rerun()
