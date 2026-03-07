"""Report generation and display dialog using @st.dialog."""

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
    skeleton_lines,
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
    provider: LLMProvider,
    generator: ReportGenerator,
) -> None:
    """Render the report dialog -- generates if needed, displays if cached."""
    doc_id = document.document_id
    defs_index = document.definitions_index
    reports: dict[str, GeneratedReport] = st.session_state.get(
        "generated_reports", {}
    )
    report: GeneratedReport | None = reports.get(doc_id)

    # Handle single-section regeneration
    regen_key = f"_regen_section_{doc_id}"
    regen_section_num: int | None = st.session_state.pop(regen_key, None)
    if regen_section_num is not None and report is not None:
        _regenerate_section(
            report, regen_section_num, document, provider, generator
        )

    if report is not None:
        _render_report(
            report,
            defs_index=defs_index,
            document=document,
            generator=generator,
        )
        return

    # Generate the report with progress
    _generate_and_render(document, provider, generator)


def _regenerate_section(
    report: GeneratedReport,
    section_number: int,
    document: ProcessedDocument,
    provider: LLMProvider,
    generator: ReportGenerator,
) -> None:
    """Regenerate a single section in-place."""
    from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS

    template = None
    for t in ALL_REPORT_SECTIONS:
        if t.section_number == section_number:
            template = t
            break
    if template is None:
        return

    from credit_analyzer.generation.report_template import get_extraction_system_prompt

    system_prompt: str = get_extraction_system_prompt()
    try:
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


def _generate_and_render(
    document: ProcessedDocument,
    provider: LLMProvider,
    generator: ReportGenerator,
) -> None:
    """Generate report with progressive section rendering inside the dialog."""
    from typing import Any

    from credit_analyzer.generation.report_template import ALL_REPORT_SECTIONS

    status_container = st.empty()
    progress_bar = st.progress(0)

    # Pre-create placeholder containers for each section
    section_placeholders: dict[int, Any] = {}
    for template in ALL_REPORT_SECTIONS:
        section_placeholders[template.section_number] = st.empty()
        # Show skeleton initially
        section_placeholders[template.section_number].markdown(
            skeleton_lines(3), unsafe_allow_html=True
        )

    def on_progress(label: str, progress: float) -> None:
        status_container.info(label)
        progress_bar.progress(min(max(progress, 0.0), 1.0))

    def on_section(section: GeneratedSection) -> None:
        """Render a section as soon as it completes — no .empty() to avoid layout jump."""
        placeholder = section_placeholders.get(section.section_number)
        if placeholder is not None:
            html = _build_section_html(section)
            placeholder.markdown(html, unsafe_allow_html=True)

    try:
        report = generator.generate(
            document.document_id,
            progress_callback=on_progress,
            section_callback=on_section,
        )
    except Exception as exc:
        status_container.empty()
        progress_bar.empty()
        st.error(f"Report generation failed: {exc}")
        return

    st.session_state.setdefault("generated_reports", {})[
        document.document_id
    ] = report
    status_container.empty()
    progress_bar.empty()

    # Show completion message instead of st.rerun() which closes the dialog
    st.success("Report complete! Close and reopen to see the full view with navigation and PDF download.")


def _render_report(
    report: GeneratedReport,
    defs_index: DefinitionsIndex | None = None,
    document: ProcessedDocument | None = None,
    generator: ReportGenerator | None = None,
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

    # PDF download
    pdf_bytes = report_to_pdf_bytes(report)
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"credit_report_{report.generated_at.strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
    )

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
    # Refresh button (Streamlit button above the HTML section)
    if document is not None:
        doc_id = document.document_id
        regen_key = f"_regen_section_{doc_id}"
        if st.button(
            "↻",
            key=f"refresh-section-{section.section_number}",
            help=f"Regenerate: {section.title}",
        ):
            st.session_state[regen_key] = section.section_number
            st.rerun()

    st.markdown(
        _build_section_html(section, defs_index=defs_index),
        unsafe_allow_html=True,
    )
