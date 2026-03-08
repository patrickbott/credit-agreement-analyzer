"""Report generation pipeline functions extracted from app.py."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import streamlit as st

from credit_analyzer.generation.report_generator import GeneratedSection, ReportGenerator
from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS, ReportSectionTemplate
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.ui.theme import indexing_step
from credit_analyzer.ui.workflows import ProcessedDocument


# ---------------------------------------------------------------------------
# Report section picker
# ---------------------------------------------------------------------------


@st.dialog("Select Report Sections", width="large")
def show_section_picker() -> None:
    """Dialog for choosing which sections to include in report generation."""
    key_prefix = "_section_picker_"

    # Initialize checkbox state on first render
    if f"{key_prefix}inited" not in st.session_state:
        for t in ALL_REPORT_SECTIONS:
            st.session_state[f"{key_prefix}{t.section_number}"] = True
        st.session_state[f"{key_prefix}inited"] = True

    st.caption("Choose which sections to generate. Deselecting sections saves API calls.")

    # Select All / Deselect All
    col_all, col_none, _ = st.columns([1, 1, 3])
    with col_all:
        if st.button("Select All", use_container_width=True):
            for t in ALL_REPORT_SECTIONS:
                st.session_state[f"{key_prefix}{t.section_number}"] = True
            st.rerun(scope="fragment")
    with col_none:
        if st.button("Deselect All", use_container_width=True):
            for t in ALL_REPORT_SECTIONS:
                st.session_state[f"{key_prefix}{t.section_number}"] = False
            st.rerun(scope="fragment")

    # Individual section checkboxes
    for t in ALL_REPORT_SECTIONS:
        st.checkbox(
            f"{t.section_number}. {t.title}",
            key=f"{key_prefix}{t.section_number}",
        )

    # Generate button
    selected = [
        t for t in ALL_REPORT_SECTIONS
        if st.session_state.get(f"{key_prefix}{t.section_number}", True)
    ]

    if st.button(
        f"Generate ({len(selected)} section{'s' if len(selected) != 1 else ''})",
        disabled=len(selected) == 0,
        type="primary",
        use_container_width=True,
    ):
        st.session_state["_pending_report_sections"] = selected
        # Clean up picker state
        for t in ALL_REPORT_SECTIONS:
            st.session_state.pop(f"{key_prefix}{t.section_number}", None)
        st.session_state.pop(f"{key_prefix}inited", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Deferred generation poller
# ---------------------------------------------------------------------------


@st.fragment(run_every=timedelta(milliseconds=300))
def poll_deferred_generation() -> None:
    """Wait one render cycle (dialog dismissed), then trigger generation.

    On the first invocation (inline with the main script) we skip so the
    script completes and the client renders the page *without* the dialog.
    On the next auto-rerun (~300 ms later) we promote the deferred
    sections and kick off a full-app rerun that starts the actual
    generation.
    """
    key = "_deferred_gen_tick"
    if not st.session_state.get(key):
        # First tick — let the page render (dialog closes).
        st.session_state[key] = True
        return
    # Second tick — dialog is gone; trigger generation.
    st.session_state.pop(key, None)
    sections = st.session_state.pop("_deferred_report_sections", None)
    if sections is not None:
        st.session_state["_ready_report_sections"] = sections
        st.rerun()  # full-app rerun (default scope="app")


# ---------------------------------------------------------------------------
# Report generation with step pipeline
# ---------------------------------------------------------------------------

_REPORT_SECTION_TITLES: list[str] = [
    "Transaction Overview",
    "Facility Summary and Pricing",
    "Bank Group",
    "Financial Covenants",
    "Debt Capacity",
    "Liens",
    "Restricted Payments",
    "Investments and Asset Sales",
    "Events of Default and Amendments",
    "Other Notable Provisions",
]


def render_report_pipeline(
    active_step: int,
    step_statuses: dict[int, str],
    section_titles: list[str] | None = None,
) -> str:
    """Build the report generation step pipeline HTML."""
    titles = section_titles if section_titles is not None else _REPORT_SECTION_TITLES
    parts = ['<div class="step-pipeline">']
    for i, label in enumerate(titles):
        status = step_statuses.get(i, "pending")
        if i < active_step and status != "error":
            status = "complete"
        elif i == active_step and status != "error":
            status = "active"
        parts.append(indexing_step(label, status))
    parts.append("</div>")
    return "".join(parts)


def generate_report(
    document: ProcessedDocument,
    provider: LLMProvider,
    *,
    sections: list[ReportSectionTemplate] | None = None,
) -> None:
    """Generate a report with a step pipeline in the sidebar, then show the dialog."""
    selected_sections = sections if sections is not None else list(ALL_REPORT_SECTIONS)
    section_titles = [t.title for t in selected_sections]

    generator = ReportGenerator(document.retriever, provider)
    if document.preamble_text is not None:
        generator.set_preamble(
            document.preamble_text,
            page_numbers=document.preamble_page_numbers,
        )

    pipeline_placeholder = st.sidebar.empty()
    step_statuses: dict[int, str] = {}
    current_step = 0

    def on_progress(label: str, progress: float) -> None:
        nonlocal current_step
        for i, title in enumerate(section_titles):
            if title.lower() in label.lower():
                current_step = i + 1
                break
        pipeline_placeholder.markdown(
            render_report_pipeline(current_step, step_statuses, section_titles),
            unsafe_allow_html=True,
        )

    def on_section(section: GeneratedSection) -> None:
        for i, t in enumerate(selected_sections):
            if t.section_number == section.section_number:
                step_statuses[i] = "complete" if section.status == "complete" else "error"
                break

    # Show initial pipeline state
    pipeline_placeholder.markdown(
        render_report_pipeline(0, step_statuses, section_titles),
        unsafe_allow_html=True,
    )

    try:
        report = generator.generate(
            document.document_id,
            sections=selected_sections,
            progress_callback=on_progress,
            section_callback=on_section,
        )
    except Exception as exc:
        pipeline_placeholder.empty()
        st.error(f"Report generation failed: {exc}")
        return

    st.session_state.setdefault("generated_reports", {})[
        document.document_id
    ] = report
    pipeline_placeholder.empty()
    st.session_state["_show_report_dialog"] = document.document_id
    st.rerun()
