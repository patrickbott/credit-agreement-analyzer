"""Report display dialog using @st.dialog."""

from __future__ import annotations

from html import escape as _html_escape
from typing import TYPE_CHECKING

import streamlit as st
import streamlit.components.v1 as components

from credit_analyzer.generation.pdf_export import report_to_pdf_bytes
from credit_analyzer.ui.theme import (
    copy_button,
    format_report_body,
    highlight_defined_terms,
    nav_item,
    render_citation_footnotes,
    render_source_footnotes,
    report_nav_dot,
    report_scroll_script,
    scroll_to_top_script,
)

if TYPE_CHECKING:
    from credit_analyzer.generation.report_generator import (
        GeneratedReport,
        GeneratedSection,
        ReportGenerator,
    )
    from credit_analyzer.llm.base import LLMProvider
    from credit_analyzer.processing.definitions import DefinitionsIndex
    from credit_analyzer.ui.workflows import ProcessedDocument


def _safe(text: str) -> str:
    """HTML-escape text and neutralise dollar signs for Streamlit."""
    return _html_escape(text).replace("$", "&#36;")


# Circular-arrow refresh SVG icon (inline, 16x16)
_REFRESH_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<path d="M1 4v6h6" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" '
    'stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
)


@st.dialog("Credit Agreement Report", width="large")
def show_report_dialog(
    document: ProcessedDocument,
) -> None:
    """Render the report dialog for a previously generated report."""
    doc_id = document.document_id
    defs_index = document.definitions_index
    reports: dict[str, GeneratedReport] = st.session_state.get(
        "generated_reports", {}
    )
    report: GeneratedReport | None = reports.get(doc_id)

    if report is None:
        st.warning("No report found. Please generate a report first.")
        return

    # Handle single-section regeneration
    regen_key = f"_regen_section_{doc_id}"
    regen_section_num: int | None = st.session_state.pop(regen_key, None)
    if regen_section_num is not None:
        _regenerate_section(report, regen_section_num, document)

    _render_report(
        report,
        defs_index=defs_index,
        document=document,
    )


def _regenerate_section(
    report: GeneratedReport,
    section_number: int,
    document: ProcessedDocument,
) -> None:
    """Regenerate a single section in-place."""
    from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS
    from credit_analyzer.generation.report_template import get_extraction_system_prompt
    from credit_analyzer.llm.factory import get_provider
    from credit_analyzer.config import LLM_PROVIDER

    template = None
    for t in ALL_REPORT_SECTIONS:
        if t.section_number == section_number:
            template = t
            break
    if template is None:
        return

    try:
        provider = get_provider(LLM_PROVIDER)
        from credit_analyzer.generation.report_generator import ReportGenerator
        generator = ReportGenerator(document.retriever, provider)
        if document.preamble_text is not None:
            generator.set_preamble(
                document.preamble_text,
                page_numbers=document.preamble_page_numbers,
            )
        system_prompt: str = get_extraction_system_prompt()
        new_section = generator.generate_section(
            template, document.document_id, system_prompt
        )
    except Exception as exc:
        st.error(f"Failed to regenerate section {section_number}: {exc}")
        return

    # Replace in report
    for i, s in enumerate(report.sections):
        if s.section_number == section_number:
            report.sections[i] = new_section
            break


def _render_report(
    report: GeneratedReport,
    defs_index: DefinitionsIndex | None = None,
    document: ProcessedDocument | None = None,
) -> None:
    """Render a completed report inside the dialog."""
    complete_count = sum(1 for s in report.sections if s.status == "complete")
    # Header
    st.markdown(
        f'<div class="report-dialog-header">'
        f'<p class="report-dialog-borrower">{_safe(report.borrower_name)}</p>'
        f'<p class="report-dialog-meta">Credit Agreement Analysis  |  '
        f'{_safe(report.generated_at.strftime("%B %d, %Y  %H:%M"))}  |  '
        f"{complete_count}/{len(report.sections)} sections  |  "
        f"{report.total_duration_seconds:.0f}s</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # PDF download & new report
    pdf_bytes = report_to_pdf_bytes(report)
    dl_col, new_col = st.columns([1, 1])
    with dl_col:
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"credit_report_{report.generated_at.strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
        )
    with new_col:
        if document is not None and st.button(
            "New Report",
            key="new-report-dialog",
        ):
            st.session_state.get("generated_reports", {}).pop(
                document.document_id, None
            )
            st.session_state["_show_section_picker"] = True
            st.rerun()

    # Two-column layout: nav + content
    nav_col, content_col = st.columns([0.22, 0.78], gap="medium")

    with nav_col:
        nav_html = '<div class="quick-nav">'
        nav_html += '<div class="quick-nav-title">SECTIONS</div>'
        for section in report.sections:
            dot = report_nav_dot(
                "complete" if section.status == "complete" else "pending"
            )
            nav_html += dot + nav_item(
                section.section_number,
                section.title,
                f"report-section-{section.section_number}",
            )
        nav_html += "</div>"
        st.markdown(nav_html, unsafe_allow_html=True)
        components.html(report_scroll_script(), height=0)
        components.html(
            scroll_to_top_script('[data-testid="stDialog"]'), height=0
        )

    with content_col:
        for section in report.sections:
            _render_section(
                section,
                defs_index=defs_index,
                document=document,
            )


def _build_section_html(
    section: GeneratedSection,
    defs_index: DefinitionsIndex | None = None,
    show_refresh: bool = False,
) -> str:
    """Build the HTML string for a single report section."""
    num_html = f'<span class="report-section-num">{section.section_number}</span>'
    anchor_id = f"report-section-{section.section_number}"
    body_id = f"section-body-{section.section_number}"

    refresh_html = ""
    if show_refresh:
        refresh_html = (
            f'<span class="section-refresh-icon">'
            f'{_REFRESH_ICON_SVG}'
            f'</span>'
        )

    if section.status == "error":
        return (
            f'<div id="{anchor_id}" class="report-section">'
            '<div class="report-section-head">'
            f'<div style="display:flex;align-items:center;">'
            f'{refresh_html}{num_html}'
            f'<span class="report-section-title">{_safe(section.title)}</span></div>'
            f'<div class="report-section-badges"></div>'
            "</div>"
            f'<div class="report-error-body">Generation error: {_safe(section.error_message)}</div>'
            "</div>"
        )

    inline_cites = getattr(section, "inline_citations", None)
    if inline_cites:
        footnotes_html = render_citation_footnotes(inline_cites)
    elif section.sources:
        footnotes_html = render_source_footnotes(section.sources)
    else:
        footnotes_html = ""

    body_html = format_report_body(section.body, inline_citations=inline_cites)
    if defs_index and defs_index.definitions:
        body_html = highlight_defined_terms(body_html, defs_index)

    return (
        f'<div id="{anchor_id}" class="report-section">'
        '<div class="report-section-head">'
        f'<div style="display:flex;align-items:center;">'
        f'{refresh_html}{num_html}'
        f'<span class="report-section-title">{_safe(section.title)}</span></div>'
        '<div class="report-section-badges">'
        f'<span class="badge-chunks">{section.chunk_count} chunks | {section.duration_seconds:.1f}s</span>'
        "</div></div>"
        '<div class="report-section-body" style="position:relative;">'
        f'<div id="{body_id}" class="report-body">'
        f"{body_html}"
        f"</div>"
        f"{copy_button(body_id)}"
        "</div>"
        f"{footnotes_html}"
        "</div>"
    )


def _render_section(
    section: GeneratedSection,
    defs_index: DefinitionsIndex | None = None,
    document: ProcessedDocument | None = None,
) -> None:
    """Render a single report section card with optional refresh button."""
    # Streamlit button sits above the rendered HTML section.
    if document is not None:
        doc_id = document.document_id
        regen_key = f"_regen_section_{doc_id}"
        if st.button(
            "Refresh",
            key=f"refresh-section-{section.section_number}",
            help=f"Regenerate: {section.title}",
        ):
            st.session_state[regen_key] = section.section_number
            st.rerun(scope="fragment")

    st.markdown(
        _build_section_html(section, defs_index=defs_index),
        unsafe_allow_html=True,
    )
