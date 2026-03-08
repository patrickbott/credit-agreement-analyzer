"""Streamlit app for the credit agreement analyzer -- chat-centric layout."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st
import streamlit.components.v1 as components

from credit_analyzer.config import LLM_PROVIDER, validate_config
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.llm.factory import get_provider
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.reranker import Reranker
from credit_analyzer.retrieval.vector_store import VectorStore
from credit_analyzer.ui.chat import render_main
from credit_analyzer.ui.clipboard import clipboard_js_snippet
from credit_analyzer.ui.sidebar import load_provider_state, render_sidebar
from credit_analyzer.ui.theme import (
    APP_CSS,
    def_tooltip_click_script,
)
from credit_analyzer.ui.workflows import ProcessedDocument

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
    st.html(clipboard_js_snippet(), unsafe_allow_javascript=True)
    components.html(def_tooltip_click_script(), height=0)

    # DEBUG: outline sidebar children to find spacing culprit
    components.html("""<script>
    setTimeout(() => {
        const sb = parent.document.querySelector('[data-testid="stSidebarContent"]');
        if (!sb) return;
        const info = [];
        function walk(el, depth) {
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            if (r.height > 0 || parseFloat(cs.paddingTop) > 0 || parseFloat(cs.marginTop) > 0) {
                info.push(
                    '  '.repeat(depth) +
                    (el.dataset.testid || el.tagName + '.' + el.className.slice(0,30)) +
                    ' h=' + r.height.toFixed(0) +
                    ' top=' + r.top.toFixed(0) +
                    ' pt=' + cs.paddingTop +
                    ' mt=' + cs.marginTop +
                    ' mb=' + cs.marginBottom
                );
            }
            if (depth < 6) {
                for (const c of el.children) walk(c, depth + 1);
            }
        }
        walk(sb, 0);
        console.log('SIDEBAR DOM DEBUG:\\n' + info.join('\\n'));
    }, 2000);
    </script>""", height=0)

    provider, provider_status = load_provider_state()
    documents: dict[str, ProcessedDocument] = st.session_state.documents
    active_document = documents.get(st.session_state.active_document_id)

    render_sidebar(active_document, provider, provider_status)
    render_main(active_document, provider, provider_status)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _initialize_state() -> None:
    st.session_state.setdefault("documents", {})
    st.session_state.setdefault("active_document_id", None)
    st.session_state.setdefault("chat_messages", defaultdict(list))
    st.session_state.setdefault("pending_chat_questions", {})
    st.session_state.setdefault("prompt_edit_index", {})
    st.session_state.setdefault("prompt_edit_draft", {})
    st.session_state.setdefault("generated_reports", {})
    st.session_state.setdefault("provider_status", None)
    st.session_state.setdefault("deep_analysis_enabled", False)
    st.session_state.setdefault("compare_mode", False)
    st.session_state.setdefault("upload_counter", 0)


if __name__ == "__main__":
    main()
