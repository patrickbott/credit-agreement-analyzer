"""Streamlit app for the credit agreement analyzer -- chat-centric layout."""

from __future__ import annotations

import contextlib
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st
import streamlit.components.v1 as components

from credit_analyzer.config import CLAUDE_MODEL, LLM_PROVIDER, OLLAMA_MODEL, validate_config
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse
from credit_analyzer.generation.report_generator import ReportGenerator
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.llm.factory import get_provider
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.reranker import Reranker
from credit_analyzer.retrieval.vector_store import VectorStore
from credit_analyzer.ui.clipboard import clipboard_js_snippet, definition_tooltip_js_snippet
from credit_analyzer.ui.definitions_dialog import show_definitions_dialog
from credit_analyzer.ui.demo_report import SUGGESTED_QUESTIONS
from credit_analyzer.ui.report_dialog import show_report_dialog
from credit_analyzer.ui.theme import (
    APP_CSS,
    chat_welcome,
    compact_stats_grid,
    context_strip,
    copy_button,
    format_chat_answer,
    highlight_defined_terms,
    indexing_step,
    message_timestamp,
    rail_card,
    render_inline_citations,
    render_source_footnotes,
    stream_status,
)
from credit_analyzer.ui.workflows import (
    ProcessedDocument,
    build_processed_document,
    save_uploaded_pdf,
)

st.set_page_config(
    page_title="Credit Agreement Analyzer | RBC",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Application entry point."""
    config_errors = validate_config()
    if config_errors:
        for error in config_errors:
            st.error(error)
        st.stop()

    _initialize_state()

    # Warm up models on startup to avoid cold-start latency on first query
    load_embedder()
    load_reranker()

    st.markdown(APP_CSS, unsafe_allow_html=True)
    components.html(clipboard_js_snippet(), height=0)
    components.html(definition_tooltip_js_snippet(), height=0)

    provider, provider_status = _load_provider_state()
    documents: dict[str, ProcessedDocument] = st.session_state.documents
    active_document = documents.get(st.session_state.active_document_id)

    _render_sidebar(active_document, provider, provider_status)
    _render_main(active_document, provider, provider_status)


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
    # Clear the file uploader so user doesn't have to hit X separately
    for key in list(st.session_state.keys()):
        if "file_uploader" in str(key).lower() or "FormSubmitter" in str(key):
            st.session_state.pop(key, None)
    with contextlib.suppress(Exception):
        load_vector_store().delete_collection(document_id)
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


def _configured_model_name() -> str:
    if LLM_PROVIDER == "claude":
        return CLAUDE_MODEL
    if LLM_PROVIDER == "ollama":
        return OLLAMA_MODEL
    return LLM_PROVIDER


# ---------------------------------------------------------------------------
# Sidebar (actions + document management)
# ---------------------------------------------------------------------------


def _render_sidebar(
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
        report_clicked = st.button(
            "Generate Report",
            key="gen-report",
            disabled=active_document is None or not provider_status["ready"],
            use_container_width=True,
        )

        if new_chat_clicked and active_document:
            _clear_chat(active_document.document_id)
            st.rerun()
        if defs_clicked and active_document:
            show_definitions_dialog(active_document.definitions_index)
        if report_clicked and active_document and provider:
            generator = ReportGenerator(active_document.retriever, provider)
            if active_document.preamble_text is not None:
                generator.set_preamble(
                    active_document.preamble_text,
                    page_numbers=active_document.preamble_page_numbers,
                )
            show_report_dialog(active_document, provider, generator)

        st.markdown("---")

        # -- Document --
        st.caption("DOCUMENT")
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
            pdf_path = save_uploaded_pdf(uploaded_file.name, uploaded_file.getvalue())
            _process_document(pdf_path)

        if active_document is not None:
            st.markdown(
                compact_stats_grid(
                    pages=active_document.stats.total_pages,
                    sections=active_document.stats.section_count,
                    chunks=active_document.stats.chunk_count,
                    definitions=active_document.stats.definition_count,
                ),
                unsafe_allow_html=True,
            )
            st.caption(f"Source: {active_document.source_path}")
            if st.button("Remove Document", key="remove-doc"):
                _remove_document(active_document.document_id)
                st.rerun()

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


def _determine_active_step(label: str) -> int:
    """Return the 0-based index of the currently active pipeline step."""
    label_lower = label.lower()
    for i, triggers in enumerate(_STEP_TRIGGERS):
        for trigger in triggers:
            if trigger.lower() in label_lower:
                return i
    return 0


def _render_step_pipeline(active_step: int, counts: dict[int, str]) -> str:
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


def _process_document(pdf_path: Path) -> None:
    pipeline_placeholder = st.sidebar.empty()
    step_counts: dict[int, str] = {}

    def on_progress(label: str, progress: float) -> None:
        active = _determine_active_step(label)
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
            _render_step_pipeline(active, step_counts),
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


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------


def _render_main(
    active_document: ProcessedDocument | None,
    provider: LLMProvider | None,
    provider_status: dict[str, Any],
) -> None:
    if active_document is None:
        st.markdown(chat_welcome(has_document=False), unsafe_allow_html=True)
        st.chat_input("Ask about pricing, covenants, structure...", disabled=True)
        return

    if provider is None or not provider_status["ready"]:
        st.warning("The document is indexed, but the model backend is not ready.")
        return

    doc_id = active_document.document_id
    messages = st.session_state.chat_messages[doc_id]

    # If no messages and no pending question, show suggestions
    if not messages and doc_id not in st.session_state.pending_chat_questions:
        _render_suggestions(active_document)

    # Render existing messages
    defs_index = active_document.definitions_index if active_document else None
    for message in messages:
        _render_chat_message(message, defs_index=defs_index)

    # Handle pending question
    pending = st.session_state.pending_chat_questions.get(doc_id)
    if pending is not None:
        _run_pending_chat_question(active_document, provider, pending)
        st.rerun()

    # Chat input (always at bottom)
    user_question = st.chat_input("Ask about pricing, covenants, structure...")
    if user_question is not None:
        _queue_chat_question(active_document, user_question)
        st.rerun()


def _render_suggestions(active_document: ProcessedDocument) -> None:
    st.markdown(chat_welcome(has_document=True), unsafe_allow_html=True)
    with st.container(key="suggested-actions"):
        for row_start in range(0, len(SUGGESTED_QUESTIONS), 3):
            row_items = SUGGESTED_QUESTIONS[row_start : row_start + 3]
            cols = st.columns(len(row_items))
            for i, suggestion in enumerate(row_items):
                with cols[i]:
                    if suggestion.prompt is not None and st.button(
                        suggestion.label,
                        key=f"suggested-{row_start + i}",
                        use_container_width=True,
                    ):
                        _queue_chat_question(active_document, suggestion.prompt)
                        st.rerun()


# ---------------------------------------------------------------------------
# Chat Q&A
# ---------------------------------------------------------------------------


def _queue_chat_question(document: ProcessedDocument, question: str) -> None:
    st.session_state.chat_messages[document.document_id].append(
        {
            "role": "user",
            "question": question,
            "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
        }
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


def _clear_chat(document_id: str) -> None:
    st.session_state.chat_messages[document_id] = []
    st.session_state.pending_chat_questions.pop(document_id, None)
    # Drop the cached engine so history resets with the conversation.
    st.session_state.pop(f"qa_engine_{document_id}", None)


def _run_pending_chat_question(
    document: ProcessedDocument,
    provider: LLMProvider,
    question: str,
) -> None:
    st.session_state.pending_chat_questions.pop(document.document_id, None)
    qa_engine = _get_or_create_qa_engine(document, provider)

    try:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            response_placeholder = st.empty()
            streamed_text = ""
            final_response = None
            first_token = True

            status_placeholder.markdown(
                stream_status("Searching relevant sections..."),
                unsafe_allow_html=True,
            )
            t0 = time.monotonic()

            for item in qa_engine.ask_stream(question, document.document_id):
                if isinstance(item, QAResponse):
                    final_response = item
                else:
                    if first_token:
                        status_placeholder.markdown(
                            stream_status("Composing answer..."),
                            unsafe_allow_html=True,
                        )
                        first_token = False
                    streamed_text += item
                    response_placeholder.markdown(streamed_text + "\u258c")

            elapsed = time.monotonic() - t0
            status_placeholder.empty()

            if final_response is not None:
                # Replace streaming preview with final parsed answer
                response_placeholder.empty()
                answer_id = f"answer-{hash(final_response.answer) & 0xFFFFFFFF:08x}"
                defs_idx = document.definitions_index
                if final_response.inline_citations:
                    cited_html = render_inline_citations(
                        final_response.answer, final_response.inline_citations
                    )
                    if defs_idx and defs_idx.definitions:
                        # Highlight only the body, not citation footnotes
                        footnote_marker = '<div class="cite-footnotes">'
                        fn_pos = cited_html.find(footnote_marker)
                        if fn_pos >= 0:
                            body_part = highlight_defined_terms(cited_html[:fn_pos], defs_idx)
                            cited_html = body_part + cited_html[fn_pos:]
                        else:
                            cited_html = highlight_defined_terms(cited_html, defs_idx)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}" class="section-answer">{cited_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                elif final_response.sources:
                    answer_html = format_chat_answer(final_response.answer)
                    if defs_idx and defs_idx.definitions:
                        answer_html = highlight_defined_terms(answer_html, defs_idx)
                    footnotes_html = render_source_footnotes(final_response.sources)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}" class="section-answer">{answer_html}{footnotes_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    answer_html = format_chat_answer(final_response.answer)
                    if defs_idx and defs_idx.definitions:
                        answer_html = highlight_defined_terms(answer_html, defs_idx)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}">{answer_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Context strip
                sections_used = _extract_sections_used(final_response)
                chunk_count = len(final_response.retrieved_chunks) if final_response.retrieved_chunks else 0
                duration = final_response.llm_response.duration_seconds if final_response.llm_response else elapsed
                st.markdown(
                    context_strip(
                        final_response.confidence,
                        chunk_count,
                        sections_used,
                        duration,
                    ),
                    unsafe_allow_html=True,
                )

                # Expandable retrieved context
                if final_response.retrieved_chunks:
                    n_chunks = len(final_response.retrieved_chunks)
                    with st.expander(f"Retrieved context ({n_chunks} chunks)", expanded=False):
                        sorted_chunks = sorted(
                            final_response.retrieved_chunks,
                            key=lambda c: c.score,
                            reverse=True,
                        )
                        retrieved_df = pd.DataFrame(
                            [
                                {
                                    "section": chunk.chunk.section_id,
                                    "title": chunk.chunk.section_title,
                                    "relevance": round(chunk.score, 3),
                                    "pages": ", ".join(
                                        str(p) for p in chunk.chunk.page_numbers
                                    ),
                                }
                                for chunk in sorted_chunks
                            ]
                        )
                        _show_dataframe(retrieved_df, width="stretch", hide_index=True)

                # Timestamp
                ts = datetime.now().strftime("%I:%M %p").lstrip("0")
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)

        if final_response is not None:
            st.session_state.chat_messages[document.document_id].append(
                {
                    "role": "assistant",
                    "response": final_response,
                    "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
                }
            )
    except Exception as exc:
        st.error(f"Could not generate an answer: {exc}")


def _extract_sections_used(response: QAResponse) -> str:
    """Build a short summary string of which sections were retrieved."""
    if not response.retrieved_chunks:
        return ""
    section_ids: list[str] = []
    seen: set[str] = set()
    for chunk in response.retrieved_chunks:
        sid = chunk.chunk.section_id
        if sid and sid not in seen:
            seen.add(sid)
            section_ids.append(sid)
    if not section_ids:
        return ""
    if len(section_ids) <= 3:
        return ", ".join(section_ids)
    return ", ".join(section_ids[:3]) + f" +{len(section_ids) - 3}"


def _render_chat_message(
    message: dict[str, Any],
    defs_index: Any = None,
) -> None:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["question"])
            ts = message.get("timestamp")
            if ts:
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)
        return

    response: QAResponse = message["response"]
    answer_id = f"answer-{hash(response.answer) & 0xFFFFFFFF:08x}"
    with st.chat_message("assistant"):
        if response.inline_citations:
            cited_html = render_inline_citations(
                response.answer, response.inline_citations
            )
            if defs_index and defs_index.definitions:
                footnote_marker = '<div class="cite-footnotes">'
                fn_pos = cited_html.find(footnote_marker)
                if fn_pos >= 0:
                    body_part = highlight_defined_terms(cited_html[:fn_pos], defs_index)
                    cited_html = body_part + cited_html[fn_pos:]
                else:
                    cited_html = highlight_defined_terms(cited_html, defs_index)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}" class="section-answer">{cited_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif response.sources:
            answer_html = format_chat_answer(response.answer)
            if defs_index and defs_index.definitions:
                answer_html = highlight_defined_terms(answer_html, defs_index)
            footnotes_html = render_source_footnotes(response.sources)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}" class="section-answer">{answer_html}{footnotes_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            answer_html = format_chat_answer(response.answer)
            if defs_index and defs_index.definitions:
                answer_html = highlight_defined_terms(answer_html, defs_index)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}">{answer_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Context strip
        sections_used = _extract_sections_used(response)
        chunk_count = len(response.retrieved_chunks) if response.retrieved_chunks else 0
        duration = response.llm_response.duration_seconds if response.llm_response else 0.0
        st.markdown(
            context_strip(response.confidence, chunk_count, sections_used, duration),
            unsafe_allow_html=True,
        )

        # Expandable retrieved context
        if response.retrieved_chunks:
            n_chunks = len(response.retrieved_chunks)
            with st.expander(f"Retrieved context ({n_chunks} chunks)", expanded=False):
                sorted_chunks = sorted(
                    response.retrieved_chunks, key=lambda c: c.score, reverse=True
                )
                retrieved_df = pd.DataFrame(
                    [
                        {
                            "section": chunk.chunk.section_id,
                            "title": chunk.chunk.section_title,
                            "relevance": round(chunk.score, 3),
                            "pages": ", ".join(str(p) for p in chunk.chunk.page_numbers),
                        }
                        for chunk in sorted_chunks
                    ]
                )
                _show_dataframe(retrieved_df, width="stretch", hide_index=True)

        # Timestamp
        ts = message.get("timestamp")
        if ts:
            st.markdown(message_timestamp(ts), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
