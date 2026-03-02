"""Streamlit app for the credit agreement analyzer."""

from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any, cast

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st

from credit_analyzer.config import CLAUDE_MODEL, LLM_PROVIDER, OLLAMA_MODEL, validate_config
from credit_analyzer.generation.pdf_export import report_to_pdf_bytes
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.report_generator import (
    GeneratedReport,
    GeneratedSection,
    ReportGenerator,
)
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.llm.factory import get_provider
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.reranker import Reranker
from credit_analyzer.retrieval.vector_store import VectorStore
from credit_analyzer.ui.demo_report import SUGGESTED_QUESTIONS
from credit_analyzer.ui.theme import (
    APP_CSS,
    confidence_pill,
    format_report_body,
    hero_card,
    metric_card,
    panel_card,
    rail_card,
)
from credit_analyzer.ui.workflows import (
    ProcessedDocument,
    build_processed_document,
    save_uploaded_pdf,
)

st.set_page_config(
    page_title="RBC Credit Agreement Analyzer",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(APP_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def load_embedder() -> Embedder:
    """Load the shared embedding model."""
    return Embedder()


@st.cache_resource(show_spinner=False)
def load_vector_store() -> VectorStore:
    """Load the shared ChromaDB vector store."""
    return VectorStore()


@st.cache_resource(show_spinner=False)
def load_reranker() -> Reranker:
    """Load the shared cross-encoder reranker model."""
    return Reranker()


@st.cache_resource(show_spinner=False)
def load_provider(provider_name: str) -> LLMProvider:
    """Load the configured LLM provider."""
    return get_provider(provider_name)


def _show_dataframe(
    data: Any,
    *,
    width: str = "stretch",
    hide_index: bool = True,
) -> None:
    """Wrapper for st.dataframe that appeases strict type checkers."""
    cast(Any, st).dataframe(
        data,
        width=width,
        hide_index=hide_index,
    )


def main() -> None:
    """Application entry point."""
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            st.error(error)
        st.stop()

    _initialize_state()

    st.markdown(
        hero_card(
            title="Credit Agreement Analyzer",
            copy="Review agreements, ask cited questions, and generate a structured report.",
        ),
        unsafe_allow_html=True,
    )

    provider, provider_status = _load_provider_state()
    documents: dict[str, ProcessedDocument] = st.session_state.documents
    active_document = documents.get(st.session_state.active_document_id)

    _render_sidebar(documents, active_document, provider_status)

    tab_documents, tab_chat, tab_report = st.tabs(
        ["Documents", "Ask Questions", "Full Report"]
    )

    with tab_documents:
        _render_document_tab(active_document)

    with tab_chat:
        _render_chat_tab(active_document, provider, provider_status)

    with tab_report:
        _render_report_tab(active_document, provider, provider_status)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _initialize_state() -> None:
    st.session_state.setdefault("documents", {})
    st.session_state.setdefault("active_document_id", None)
    st.session_state.setdefault("chat_messages", defaultdict(list))
    st.session_state.setdefault("pending_chat_questions", {})
    st.session_state.setdefault("generated_reports", {})
    st.session_state.setdefault("provider_status", None)


def _remove_document(document_id: str) -> None:
    """Remove a document from session state and clean up its ChromaDB collection."""
    documents: dict[str, ProcessedDocument] = st.session_state.documents
    documents.pop(document_id, None)
    st.session_state.chat_messages.pop(document_id, None)
    st.session_state.generated_reports.pop(document_id, None)
    st.session_state.pop(f"qa_engine_{document_id}", None)
    try:
        load_vector_store().delete_collection(document_id)
    except Exception:
        pass  # Collection may not exist or already be deleted.
    # Switch active document to the next available, or None.
    remaining = list(documents.keys())
    st.session_state.active_document_id = remaining[0] if remaining else None


def _load_provider_state() -> tuple[LLMProvider | None, dict[str, Any]]:
    cached = st.session_state.provider_status
    if cached is not None:
        provider = cached.get("provider")
        status = {key: value for key, value in cached.items() if key != "provider"}
        return provider, status

    try:
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
            "model_name": _configured_model_name(),
            "message": f"Unavailable: {exc}",
        }

    st.session_state.provider_status = {"provider": provider, **status}
    return provider, status


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar(
    documents: dict[str, ProcessedDocument],
    active_document: ProcessedDocument | None,
    provider_status: dict[str, Any],
) -> None:
    with st.sidebar:
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
        if not provider_status["ready"]:
            if st.button("Retry Connection", key="retry-model", width="stretch"):
                st.session_state.provider_status = None
                st.rerun()

        st.markdown("### Documents")
        if documents:
            choices = list(documents.keys())
            labels = {doc_id: documents[doc_id].display_name for doc_id in choices}
            current = (
                choices.index(st.session_state.active_document_id)
                if st.session_state.active_document_id in choices
                else 0
            )
            selected = st.selectbox(
                "Active document",
                options=choices,
                format_func=lambda doc_id: labels[doc_id],
                index=current,
            )
            st.session_state.active_document_id = selected
            active_document = documents[selected]
            st.markdown(
                rail_card(
                    "Active document",
                    active_document.display_name,
                    (
                        f"{active_document.stats.total_pages} pages | "
                        f"{active_document.stats.section_count} sections | "
                        f"{active_document.stats.chunk_count} chunks"
                    ),
                ),
                unsafe_allow_html=True,
            )
            if st.button("Remove Document", key="remove-doc", width="stretch"):
                _remove_document(selected)
                st.rerun()
        else:
            st.markdown(
                rail_card(
                    "Active document",
                    "None loaded",
                    "Index a PDF to enable Q&A and reporting.",
                    tone="warning",
                ),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Documents tab
# ---------------------------------------------------------------------------


def _render_document_tab(active_document: ProcessedDocument | None) -> None:
    upload_col, summary_col = st.columns([1.0, 1.1], gap="large")

    with upload_col:
        st.markdown(
            panel_card(
                "Load Document",
                "Upload a PDF.",
            ),
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Agreement PDF",
            type=["pdf"],
            help="PDF files are saved locally in demo_uploads/.",
        )

        process_uploaded = st.button(
            "Index PDF",
            type="primary",
            width="stretch",
            disabled=uploaded_file is None,
        )

        if process_uploaded and uploaded_file is not None:
            pdf_path = save_uploaded_pdf(uploaded_file.name, uploaded_file.getvalue())
            _process_document(pdf_path)

    with summary_col:
        if active_document is None:
            st.markdown(
                panel_card(
                    "Ready to Review",
                    "Load an agreement to inspect structure, ask questions, and generate a report.",
                ),
                unsafe_allow_html=True,
            )
            empty_cols = st.columns(3)
            empty_cards = (
                ("Pages", "--", "Agreement length"),
                ("Definitions", "--", "Defined terms"),
                ("Chunks", "--", "Retrieval index"),
            )
            for col, card in zip(empty_cols, empty_cards, strict=True):
                with col:
                    st.markdown(metric_card(*card), unsafe_allow_html=True)
            return

        _render_document_summary(active_document)


def _process_document(pdf_path: Path) -> None:
    status_box = st.empty()
    progress_bar = st.progress(0)

    def on_progress(label: str, progress: float) -> None:
        status_box.info(label)
        progress_bar.progress(min(max(progress, 0.0), 1.0))

    try:
        document = build_processed_document(
            pdf_path,
            embedder=load_embedder(),
            vector_store=load_vector_store(),
            reranker=load_reranker(),
            progress_callback=on_progress,
        )
    except Exception as exc:
        status_box.empty()
        progress_bar.empty()
        st.error(f"Processing failed: {exc}")
        return

    st.session_state.documents[document.document_id] = document
    st.session_state.active_document_id = document.document_id
    st.session_state.chat_messages[document.document_id] = []
    st.session_state.generated_reports.pop(document.document_id, None)

    status_box.success(f"{document.display_name} indexed.")
    progress_bar.progress(1.0)
    st.rerun()


def _render_document_summary(document: ProcessedDocument) -> None:
    stats = document.stats

    metric_cols = st.columns(4)
    cards = (
        ("Pages", str(stats.total_pages), f"Method: {stats.extraction_method}"),
        ("Sections", str(stats.section_count), "Detected sections"),
        ("Definitions", str(stats.definition_count), "Parsed terms"),
        ("Chunks", str(stats.chunk_count), f"Tables: {stats.table_count}"),
    )
    for col, card in zip(metric_cols, cards, strict=True):
        with col:
            st.markdown(metric_card(*card), unsafe_allow_html=True)

    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.markdown(
            panel_card(
                "Document",
                "Indexed structure for the active agreement.",
            ),
            unsafe_allow_html=True,
        )
        st.caption(f"Source: {document.source_path}")
        st.caption(f"Indexed: {stats.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        sections_df = pd.DataFrame(
            [
                {
                    "section_id": section.section_id,
                    "title": section.section_title,
                    "type": section.section_type,
                    "pages": f"{section.page_start}-{section.page_end}",
                }
                for section in document.sections[:40]
            ]
        )
        _show_dataframe(sections_df, width="stretch", hide_index=True)
        if len(document.sections) > 40:
            st.caption("Showing the first 40 sections.")

    with right_col:
        section_mix = pd.DataFrame(
            [
                {"section_type": key, "count": value}
                for key, value in stats.section_type_counts.items()
            ]
        )
        st.markdown(
            panel_card(
                "Section Mix",
                "Counts by detected section type.",
            ),
            unsafe_allow_html=True,
        )
        _show_dataframe(section_mix, width="stretch", hide_index=True)

        if document.preamble_text:
            with st.expander("Preamble Preview", expanded=False):
                st.write(document.preamble_text[:1800])


# ---------------------------------------------------------------------------
# Chat tab
# ---------------------------------------------------------------------------


def _render_chat_tab(
    active_document: ProcessedDocument | None,
    provider: LLMProvider | None,
    provider_status: dict[str, Any],
) -> None:
    if active_document is None:
        st.info("Index a document first.")
        return

    if provider is None or not provider_status["ready"]:
        st.warning("The document is indexed, but the model backend is not ready.")
        return

    header_col, action_col = st.columns([1.0, 0.28], gap="large")
    with header_col:
        st.caption(f"Active document: {active_document.display_name}")
    with action_col:
        if st.button("New Chat", key="new-chat", width="stretch"):
            _clear_chat(active_document.document_id)
            st.rerun()

    st.caption("Suggested questions")

    suggested_cols = st.columns(3)
    next_question: str | None = None
    for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
        with suggested_cols[index % len(suggested_cols)]:
            if suggestion.prompt is not None and st.button(
                suggestion.label,
                key=f"suggested-{index}",
                width="stretch",
            ):
                next_question = suggestion.prompt

    for message in st.session_state.chat_messages[active_document.document_id]:
        _render_chat_message(message)

    pending_question = st.session_state.pending_chat_questions.get(
        active_document.document_id
    )
    if pending_question is not None:
        _run_pending_chat_question(active_document, provider, pending_question)
        st.rerun()

    user_question = st.chat_input(
        "Ask about pricing, covenants, baskets, or debt capacity"
    )
    question: str | None = next_question or user_question
    if question is not None:
        _queue_chat_question(active_document, question)
        st.rerun()


def _queue_chat_question(document: ProcessedDocument, question: str) -> None:
    st.session_state.chat_messages[document.document_id].append(
        {"role": "user", "question": question}
    )
    st.session_state.pending_chat_questions[document.document_id] = question


def _get_or_create_qa_engine(document: ProcessedDocument, provider: LLMProvider) -> QAEngine:
    """Return the persistent QAEngine for this document, creating it on first call.

    Storing the engine in session_state preserves conversation history across
    Streamlit reruns, which is required for multi-turn reformulation to work.
    """
    engine_key = f"qa_engine_{document.document_id}"
    if engine_key not in st.session_state:
        engine = QAEngine(document.retriever, provider)
        if document.preamble_text is not None:
            engine.set_preamble(
                document.preamble_text,
                page_numbers=document.preamble_page_numbers,
            )
        st.session_state[engine_key] = engine
    return cast(QAEngine, st.session_state[engine_key])


def _run_pending_chat_question(
    document: ProcessedDocument,
    provider: LLMProvider,
    question: str,
) -> None:
    st.session_state.pending_chat_questions.pop(document.document_id, None)
    qa_engine = _get_or_create_qa_engine(document, provider)

    try:
        with st.chat_message("assistant"), st.spinner("Generating answer..."):
            response = qa_engine.ask(question, document.document_id)
        st.session_state.chat_messages[document.document_id].append(
            {"role": "assistant", "response": response}
        )
    except Exception as exc:
        st.error(f"Could not generate an answer: {exc}")


def _clear_chat(document_id: str) -> None:
    st.session_state.chat_messages[document_id] = []
    st.session_state.pending_chat_questions.pop(document_id, None)
    # Drop the cached engine so history resets with the conversation.
    st.session_state.pop(f"qa_engine_{document_id}", None)


def _render_chat_message(message: dict[str, Any]) -> None:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["question"])
        return

    response: QAResponse = message["response"]
    with st.chat_message("assistant"):
        st.write(response.answer)
        st.markdown(confidence_pill(response.confidence), unsafe_allow_html=True)
        expander_label = (
            f"Sources ({len(response.sources)})"
            if response.sources
            else "Retrieved context"
        )
        with st.expander(expander_label, expanded=False):
            if response.sources:
                for source in response.sources:
                    _render_source_card(source)
            if response.retrieved_chunks:
                st.caption("Retrieved chunks")
                retrieved_df = pd.DataFrame(
                    [
                        {
                            "section_id": chunk.chunk.section_id,
                            "title": chunk.chunk.section_title,
                            "score": round(chunk.score, 3),
                            "source": chunk.source,
                            "pages": ", ".join(str(page) for page in chunk.chunk.page_numbers),
                        }
                        for chunk in response.retrieved_chunks
                    ]
                )
                _show_dataframe(retrieved_df, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Report tab
# ---------------------------------------------------------------------------


def _render_report_tab(
    active_document: ProcessedDocument | None,
    provider: LLMProvider | None,
    provider_status: dict[str, Any],
) -> None:
    if active_document is None:
        st.info("Index a document first.")
        return

    if provider is None or not provider_status["ready"]:
        st.warning("Report generation requires a reachable model backend.")
        return

    header_col, action_col = st.columns([1.0, 0.32], gap="large")
    with header_col:
        st.caption(
            f"{active_document.display_name} | "
            "9-section structured report"
        )
    with action_col:
        generate = st.button(
            "Generate Report", type="primary", width="stretch"
        )

    if generate:
        _run_report_generation(active_document, provider)

    report: GeneratedReport | None = st.session_state.generated_reports.get(
        active_document.document_id
    )

    if report is None:
        st.caption("No report generated yet. Click Generate Report to start.")
        return

    _render_report(report)


def _run_report_generation(
    document: ProcessedDocument,
    provider: LLMProvider,
) -> None:
    """Run the full report generation with progress tracking."""
    status_box = st.empty()
    progress_bar = st.progress(0)

    def on_progress(label: str, progress: float) -> None:
        status_box.info(label)
        progress_bar.progress(min(max(progress, 0.0), 1.0))

    generator = ReportGenerator(document.retriever, provider)
    if document.preamble_text is not None:
        generator.set_preamble(
            document.preamble_text,
            page_numbers=document.preamble_page_numbers,
        )

    try:
        report = generator.generate(
            document.document_id,
            progress_callback=on_progress,
        )
    except Exception as exc:
        status_box.empty()
        progress_bar.empty()
        st.error(f"Report generation failed: {exc}")
        return

    st.session_state.generated_reports[document.document_id] = report
    status_box.success(
        f"Report ready. {len(report.sections)} sections in "
        f"{report.total_duration_seconds:.1f}s."
    )
    progress_bar.progress(1.0)


def _render_report(report: GeneratedReport) -> None:
    """Render the generated report in the Streamlit UI."""
    complete_count = sum(1 for s in report.sections if s.status == "complete")
    error_count = sum(1 for s in report.sections if s.status == "error")
    high_count = sum(
        1 for s in report.sections
        if s.status == "complete" and s.confidence == "HIGH"
    )
    med_count = sum(
        1 for s in report.sections
        if s.status == "complete" and s.confidence == "MEDIUM"
    )

    # Report header card
    stats_html = (
        '<div class="report-stats-row">'
        f'<span class="report-stat">{complete_count}/{len(report.sections)} sections</span>'
        f'<span class="report-stat report-stat-gold">{high_count} HIGH confidence</span>'
    )
    if med_count:
        stats_html += f'<span class="report-stat">{med_count} MEDIUM</span>'
    if error_count:
        stats_html += f'<span class="report-stat">{error_count} errors</span>'
    stats_html += (
        f'<span class="report-stat">{report.total_duration_seconds:.0f}s total</span>'
        "</div>"
    )

    st.markdown(
        (
            '<div class="report-header">'
            f'<p class="report-header-borrower">{escape(report.borrower_name)}</p>'
            f'<p class="report-header-meta">Credit Agreement Analysis  |  '
            f'{escape(report.generated_at.strftime("%B %d, %Y  %H:%M"))}</p>'
            f"{stats_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # PDF export
    pdf_bytes = report_to_pdf_bytes(report)
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"credit_report_{report.generated_at.strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
    )

    # Render each section
    for section in report.sections:
        _render_report_section(section)


def _render_report_section(section: GeneratedSection) -> None:
    """Render a single report section with card layout."""
    conf_pill = confidence_pill(section.confidence)
    num_html = f'<span class="report-section-num">{section.section_number}</span>'

    if section.status == "error":
        st.markdown(
            (
                '<div class="report-section">'
                '<div class="report-section-head">'
                f'<div style="display:flex;align-items:center;">{num_html}'
                f'<span class="report-section-title">{escape(section.title)}</span></div>'
                f'<div class="report-section-badges">{confidence_pill("LOW")}</div>'
                "</div>"
                f'<div class="report-error-body">Generation error: {escape(section.error_message)}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    # Sources bar
    sources_html = ""
    if section.sources:
        chips = "".join(
            f'<span class="report-source-chip">Sec. {escape(src.section_id)}'
            f" pp. {escape(', '.join(str(p) for p in src.page_numbers) or 'n/a')}"
            "</span>"
            for src in section.sources
        )
        sources_html = f'<div class="report-sources">{chips}</div>'

    st.markdown(
        (
            '<div class="report-section">'
            '<div class="report-section-head">'
            f'<div style="display:flex;align-items:center;">{num_html}'
            f'<span class="report-section-title">{escape(section.title)}</span></div>'
            '<div class="report-section-badges">'
            f'<span class="badge-chunks">{section.chunk_count} chunks | {section.duration_seconds:.1f}s</span>'
            f"{conf_pill}"
            "</div></div>"
            '<div class="report-section-body">'
            f'<div class="report-body">{format_report_body(section.body)}</div>'
            "</div>"
            f"{sources_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _render_source_card(source: Any) -> None:
    page_text = ", ".join(str(page) for page in source.page_numbers) or "n/a"
    title = f"Section {source.section_id}"
    if source.section_title:
        title = f"{title} | {source.section_title}"

    st.markdown(
        (
            '<section class="source-card">'
            f'<p class="source-title">{escape(title)}</p>'
            f'<p class="source-meta">Pages: {escape(page_text)}</p>'
            f'<p class="source-snippet">'
            f'{escape(source.relevant_text_snippet or "No snippet available.")}</p>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def _configured_model_name() -> str:
    if LLM_PROVIDER == "claude":
        return CLAUDE_MODEL
    if LLM_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return LLM_PROVIDER


if __name__ == "__main__":
    main()
