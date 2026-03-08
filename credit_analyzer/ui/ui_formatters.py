"""HTML/JS rendering helpers for the Streamlit demo app."""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING

from credit_analyzer.ui.theme_constants import (
    BULLET_RE,
    CHECK_ICON_SVG,
    CLIPBOARD_ICON_SVG,
    EMPTY_ICONS,
    FIELD_RE,
    HEADING_RE,
    INLINE_MARKER_RE,
    NUMBERED_RE,
    TABLE_ROW_RE,
    TABLE_SEP_RE,
    safe_html,
)

if TYPE_CHECKING:
    from credit_analyzer.generation.response_parser import InlineCitation, SourceCitation
    from credit_analyzer.processing.definitions import DefinitionsIndex


# ---------------------------------------------------------------------------
# HTML helper functions
# ---------------------------------------------------------------------------


def metric_card(label: str, value: str, caption: str, accent: str = "") -> str:
    """Render a compact metric card.

    Args:
        label: Metric name (uppercase label).
        value: Primary metric value.
        caption: Descriptive caption beneath the value.
        accent: Optional CSS color for the left border (default: RBC_BLUE).
    """
    style_attr = f' style="border-left-color: {accent};"' if accent else ""
    return (
        f'<section class="metric-card"{style_attr}>'
        f'<div class="metric-label">{safe_html(label)}</div>'
        f'<div class="metric-value">{safe_html(value)}</div>'
        f'<div class="metric-caption">{safe_html(caption)}</div>'
        "</section>"
    )


def panel_card(title: str, copy: str | None = None) -> str:
    """Render a lightweight informational panel."""
    return (
        '<section class="panel-card">'
        f'<h3 class="panel-title">{safe_html(title)}</h3>'
        f'<p class="panel-copy">{safe_html(copy or "")}</p>'
        "</section>"
    )


def rail_card(label: str, value: str, meta: str | None = None, tone: str = "ready") -> str:
    """Render a compact sidebar control-rail card."""
    safe_tone = "warning" if tone == "warning" else "ready"
    return (
        f'<section class="rail-card is-{safe_tone}">'
        f'<div class="rail-label">{safe_html(label)}</div>'
        f'<div class="rail-value">{safe_html(value)}</div>'
        f'<div class="rail-meta">{safe_html(meta or "")}</div>'
        "</section>"
    )


def confidence_pill(confidence: str) -> str:
    """Render a color-coded confidence pill."""
    lowered = confidence.lower()
    tone = "medium"
    if lowered == "high":
        tone = "high"
    elif lowered == "low":
        tone = "low"
    return f'<span class="pill pill-{tone}">{safe_html(confidence.upper())}</span>'


# ---------------------------------------------------------------------------
# NEW helper functions
# ---------------------------------------------------------------------------


def copy_button(target_id: str) -> str:
    """Return HTML for a copy button with inline SVG clipboard icon.

    Args:
        target_id: DOM id of the element whose text to copy.
    """
    return (
        f'<button class="copy-btn" data-copy-target="{safe_html(target_id)}" '
        f'title="Copy to clipboard">'
        f"{CLIPBOARD_ICON_SVG}"
        "</button>"
    )


def nav_item(section_number: int, title: str, anchor: str) -> str:
    """Quick-nav link for report TOC sidebar.

    Args:
        section_number: The section number (1-10).
        title: Section title text.
        anchor: The HTML anchor id to link to.
    """
    safe_anchor = safe_html(anchor)
    return (
        f'<a class="quick-nav-item" data-scroll-target="{safe_anchor}">'
        f'<span class="nav-num">{section_number}</span>'
        f"<span>{safe_html(title)}</span>"
        "</a>"
    )


def report_scroll_script() -> str:
    """Return an HTML/JS snippet that enables scroll-to-section nav links.

    Inject once per report dialog via ``st.components.v1.html(snippet, height=0)``.
    """
    return """
    <script>
    (function() {
        var root = parent.document;
        if (root._reportNavAttached) return;
        root._reportNavAttached = true;
        root.addEventListener('click', function(e) {
            var link = e.target.closest('[data-scroll-target]');
            if (!link) return;
            e.preventDefault();
            var targetId = link.getAttribute('data-scroll-target');
            var el = root.getElementById(targetId);
            if (el) {
                el.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
        });
    })();
    </script>
    """


def scroll_to_top_script(container_selector: str = 'section.main') -> str:
    """Return an HTML/JS snippet that adds a floating scroll-to-top button.

    The button appears when the user scrolls down past 400px and smoothly
    scrolls the given container back to the top when clicked.

    Args:
        container_selector: CSS selector for the scrollable container.
            Use ``'section.main'`` for the main chat area, or
            ``'[data-testid="stDialog"]'`` for ``@st.dialog`` windows.
    """
    sel_js = container_selector.replace("\\", "\\\\").replace("'", "\\'")
    return f"""<script>
(function() {{
  var root = parent.document;
  var sel = '{sel_js}';
  var existing = root.querySelector(".scroll-top-btn[data-sel='" + sel + "']");
  if (existing) return;
  var container = root.querySelector(sel);
  if (!container) return;
  var scrollEl = container;
  if (sel.indexOf("stDialog") !== -1) {{
    var inner = container.querySelector('[data-testid="stDialogBody"]');
    if (inner) scrollEl = inner;
  }}
  var btn = root.createElement("button");
  btn.className = "scroll-top-btn";
  btn.setAttribute("data-sel", sel);
  btn.setAttribute("title", "Scroll to top");
  btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none">'
    + '<path d="M18 15l-6-6-6 6" stroke="white" stroke-width="2.5" '
    + 'stroke-linecap="round" stroke-linejoin="round"/></svg>';
  container.appendChild(btn);
  btn.addEventListener("click", function() {{
    scrollEl.scrollTo({{top: 0, behavior: "smooth"}});
  }});
  function onScroll() {{
    if (scrollEl.scrollTop > 400) {{
      btn.classList.add("visible");
    }} else {{
      btn.classList.remove("visible");
    }}
  }}
  scrollEl.addEventListener("scroll", onScroll);
  onScroll();
}})();
</script>"""


def definition_card(term: str, definition_text: str) -> str:
    """Definition browser entry card.

    Args:
        term: The defined term.
        definition_text: The definition body text.
    """
    return (
        '<div class="def-card">'
        f'<div class="def-term">{safe_html(term)}</div>'
        f'<div class="def-text">{safe_html(definition_text)}</div>'
        "</div>"
    )


def empty_state(title: str, description: str, icon: str = "document") -> str:
    """Centered empty state placeholder with SVG icon.

    Args:
        title: Heading for the empty state.
        description: Explanatory text beneath the heading.
        icon: One of "document", "search", "report".
    """
    icon_svg = EMPTY_ICONS.get(icon, EMPTY_ICONS["document"])
    return (
        '<div class="empty-state">'
        f"{icon_svg}"
        f'<div class="empty-title">{safe_html(title)}</div>'
        f'<div class="empty-desc">{safe_html(description)}</div>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Chat, pipeline, and skeleton helpers
# ---------------------------------------------------------------------------


def chat_welcome(has_document: bool = False) -> str:
    """Render centered welcome state for empty chat."""
    if has_document:
        return (
            '<div class="chat-welcome">'
            '<div class="chat-welcome-title">Ask a question about this agreement</div>'
            '<div class="chat-welcome-desc">'
            'Type a question below or choose from the suggestions.'
            '</div>'
            '</div>'
        )
    return (
        '<div class="chat-welcome">'
        '<div class="chat-welcome-title">Upload a credit agreement to get started</div>'
        '<div class="chat-welcome-desc">'
        'Use the sidebar to upload and index a PDF, then ask questions here.'
        '</div>'
        '</div>'
    )


def guide_step_card(number: str, title: str, description: str) -> str:
    """Render a numbered quick-start card for the welcome area."""
    return (
        '<div class="quick-start-card">'
        f'<div class="quick-start-number">{safe_html(number)}</div>'
        f'<div class="quick-start-title">{safe_html(title)}</div>'
        f'<div class="quick-start-desc">{description}</div>'
        '</div>'
    )


def guide_section_block(title: str, body_html: str) -> str:
    """Render a section block for the full guide dialog."""
    return (
        '<div class="guide-section">'
        f'<div class="guide-section-title">{safe_html(title)}</div>'
        f'<div class="guide-section-body">{body_html}</div>'
        '</div>'
    )


def context_strip(
    confidence: str,
    chunk_count: int,
    sections_used: str,
    duration_seconds: float,
    *,
    retrieval_rounds: int = 1,
) -> str:
    """Render the compact context indicator below an assistant message."""
    rounds_html = (
        f'<span>{retrieval_rounds} retrieval rounds</span>'
        f'<span>&middot;</span>'
        if retrieval_rounds > 1 else ""
    )
    return (
        '<div class="context-strip">'
        f'{rounds_html}'
        f'<span>{chunk_count} chunks</span>'
        f'<span>&middot;</span>'
        f'<span>{safe_html(sections_used)}</span>'
        f'<span>&middot;</span>'
        f'<span>{duration_seconds:.1f}s</span>'
        '</div>'
    )


def stream_status(label: str) -> str:
    """Render the animated streaming status line."""
    return (
        '<div class="stream-status">'
        '<span class="pulse-dot"></span>'
        f'<span>{safe_html(label)}</span>'
        '</div>'
    )


def message_timestamp(time_str: str) -> str:
    """Render a subtle timestamp below a chat message."""
    return f'<div class="msg-timestamp">{safe_html(time_str)}</div>'


def indexing_step(label: str, status: str, count: str = "") -> str:
    """Render one step in the indexing pipeline.

    Args:
        label: Step description (e.g. "Extracting text").
        status: One of "complete", "active", "pending".
        count: Optional result count (e.g. "42 pages").
    """
    if status == "complete":
        icon_html = f'<span class="step-icon">{CHECK_ICON_SVG}</span>'
        cls = "step-complete"
    elif status == "active":
        icon_html = '<span class="step-icon"><span class="pulse-dot"></span></span>'
        cls = "step-active"
    else:
        icon_html = '<span class="step-icon" style="color:var(--muted);">&#9675;</span>'
        cls = "step-pending"

    count_html = f'<span class="step-count">{safe_html(count)}</span>' if count else ""
    return (
        f'<div class="step-item {cls}">'
        f'{icon_html}'
        f'<span class="step-label">{safe_html(label)}</span>'
        f'{count_html}'
        '</div>'
    )


def compact_stats_grid(
    pages: int, sections: int, chunks: int, definitions: int
) -> str:
    """Render a 2x2 compact stats grid for the sidebar."""
    def _stat(value: int, label: str) -> str:
        return (
            '<div class="stat-item-compact">'
            f'<div class="stat-value">{value}</div>'
            f'<div class="stat-label">{label}</div>'
            '</div>'
        )
    return (
        '<div class="stats-grid-compact">'
        f'{_stat(pages, "Pages")}'
        f'{_stat(sections, "Sections")}'
        f'{_stat(chunks, "Chunks")}'
        f'{_stat(definitions, "Definitions")}'
        '</div>'
    )


def document_card(
    filename: str,
    pages: int,
    sections: int,
    chunks: int,
    definitions: int,
    source_path: str,
) -> str:
    """Render a compact document summary card for the sidebar."""
    stats_line = (
        f"{pages} pages &middot; {sections} sections &middot; "
        f"{chunks} chunks &middot; {definitions} definitions"
    )
    return (
        '<div class="doc-card">'
        f'<div class="doc-card-name">{safe_html(filename)}</div>'
        f'<div class="doc-card-stats">{stats_line}</div>'
        f'<div class="doc-card-source">{safe_html(source_path)}</div>'
        '</div>'
    )


def document_card_compact(
    filename: str,
    pages: int,
    chunks: int,
    is_active: bool = False,
    doc_id: str = "",
) -> str:
    """Render a compact document card for the multi-document sidebar list."""
    border_color = "var(--rbc-gold)" if is_active else "var(--border)"
    bg = "var(--surface)" if is_active else "var(--surface-alt)"
    weight = "600" if is_active else "400"
    truncated = (filename[:28] + "...") if len(filename) > 31 else filename
    return (
        f'<div class="doc-card-compact" style="'
        f'border:1.5px solid {border_color};background:{bg};'
        f'border-radius:6px;padding:0.35rem 0.5rem;margin-bottom:0.3rem;'
        f'cursor:pointer;" data-doc-id="{safe_html(doc_id)}">'
        f'<div style="font-size:0.78rem;font-weight:{weight};'
        f'color:var(--ink);white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis;">{safe_html(truncated)}</div>'
        f'<div style="font-size:0.65rem;color:var(--muted);">'
        f'{pages} pp &middot; {chunks} chunks</div>'
        f'</div>'
    )


def skeleton_lines(count: int = 4) -> str:
    """Render placeholder skeleton lines for loading states."""
    lines = ''.join('<div class="skeleton-line"></div>' for _ in range(count))
    return f'<div class="section-skeleton">{lines}</div>'


def report_nav_dot(status: str) -> str:
    """Small status dot for report quick-nav items.

    Args:
        status: One of "complete", "generating", "pending".
    """
    cls = (
        f"report-nav-dot-{status}"
        if status in ("complete", "generating", "pending")
        else "report-nav-dot-pending"
    )
    return f'<span class="report-nav-dot {cls}"></span>'


# ---------------------------------------------------------------------------
# Citation / source rendering (logic preserved exactly)
# ---------------------------------------------------------------------------


def render_citation_markers(body: str, citations: list[InlineCitation]) -> str:
    """Replace [N] markers with styled superscripts only (no footnotes).

    Use this inside ``format_report_body`` where footnotes are rendered
    separately at the section level.
    """
    if not citations:
        return safe_html(body)

    parts: list[str] = []
    last_end = 0
    for m in INLINE_MARKER_RE.finditer(body):
        parts.append(safe_html(body[last_end:m.start()]))
        num = int(m.group(1))
        parts.append(f'<span class="cite-marker">[{num}]</span>')
        last_end = m.end()
    parts.append(safe_html(body[last_end:]))
    return "".join(parts)


def render_citation_footnotes(citations: list[InlineCitation]) -> str:
    """Render footnotes block from a list of InlineCitation objects."""
    if not citations:
        return ""

    parts = ['<div class="cite-footnotes">']
    parts.append('<div class="cite-footnotes-title">Sources</div>')
    for cite in sorted(citations, key=lambda c: c.marker_number):
        title = safe_html(f"Section {cite.section_id}")
        if cite.section_title:
            title = safe_html(f"Section {cite.section_id} | {cite.section_title}")
        pages_str = (
            ", ".join(str(p) for p in cite.page_numbers)
            if cite.page_numbers
            else ""
        )
        pages_html = (
            f' <span class="cite-fn-pages">pp. {safe_html(pages_str)}</span>'
            if pages_str
            else ""
        )
        snippet_html = ""
        if cite.snippet:
            snippet_html = (
                f'<div class="cite-fn-snippet">{safe_html(cite.snippet)}</div>'
            )
        parts.append(
            f'<div class="cite-fn">'
            f'<span class="cite-fn-num">[{cite.marker_number}]</span>'
            f'<div class="cite-fn-body">'
            f'<span class="cite-fn-header">{title}</span>'
            f"{pages_html}"
            f"{snippet_html}"
            f"</div></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def render_inline_citations(body: str, citations: list[InlineCitation]) -> str:
    """Replace [N] markers with styled superscripts and append a footnotes block.

    Args:
        body: The answer text containing [1], [2] markers.
        citations: List of InlineCitation objects (must have marker_number,
            section_id, section_title, page_numbers, snippet attributes).

    Returns:
        HTML string with superscript markers and a footnotes section.
        If citations is empty, returns the body HTML-escaped with
        markers left as plain text.
    """
    if not citations:
        return format_chat_answer(body)

    body_html = _render_body_with_tables_and_citations(body, citations)
    footnotes_html = render_citation_footnotes(citations)
    return body_html + footnotes_html


def _render_body_with_tables_and_citations(
    body: str, citations: list[InlineCitation]
) -> str:
    """Render body text with both table detection and citation markers."""
    from credit_analyzer.utils.text_cleaning import normalize_tables

    body = normalize_tables(body)
    lines = body.split("\n")
    table_buffer: list[str] = []
    bullet_buffer: list[str] = []
    numbered_buffer: list[str] = []
    parts: list[str] = []

    def flush_table() -> None:
        if not table_buffer:
            return
        rows: list[list[str]] = []
        for row_line in table_buffer:
            if TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buffer.clear()
            return
        parts.append('<table class="rb-table">')
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{safe_html(cell)}</th>")
        parts.append("</tr></thead>")
        if len(rows) > 1:
            parts.append("<tbody>")
            for row in rows[1:]:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{safe_html(cell)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        table_buffer.clear()

    def flush_bullets() -> None:
        if not bullet_buffer:
            return
        parts.append('<ul class="rb-list">')
        for text in bullet_buffer:
            parts.append(f"<li>{render_citation_markers(text, citations)}</li>")
        parts.append("</ul>")
        bullet_buffer.clear()

    def flush_numbered() -> None:
        if not numbered_buffer:
            return
        parts.append('<ol class="rb-list">')
        for text in numbered_buffer:
            parts.append(f"<li>{render_citation_markers(text, citations)}</li>")
        parts.append("</ol>")
        numbered_buffer.clear()

    for line in lines:
        stripped = line.strip()
        if TABLE_ROW_RE.match(stripped) or TABLE_SEP_RE.match(stripped):
            flush_bullets()
            flush_numbered()
            table_buffer.append(stripped)
            continue
        if table_buffer:
            flush_table()
        if not stripped:
            flush_bullets()
            flush_numbered()
            parts.append("<br/>")
            continue

        # Bullet item
        bullet_match = BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append(bullet_match.group(1))
            continue

        # Numbered item
        num_match = NUMBERED_RE.match(stripped)
        if num_match and not HEADING_RE.match(stripped):
            flush_bullets()
            numbered_buffer.append(num_match.group(2))
            continue

        flush_bullets()
        flush_numbered()

        if HEADING_RE.match(stripped) and len(stripped) > 3:
            parts.append(f'<div class="rb-heading">{safe_html(stripped)}</div>')
        else:
            parts.append(render_citation_markers(stripped, citations))

    flush_bullets()
    flush_numbered()
    flush_table()
    return "\n".join(parts)


def render_source_footnotes(sources: list[SourceCitation]) -> str:
    """Render a list of SourceCitation objects as a footnotes HTML block.

    Used as a fallback when inline citations are not available but
    SourceCitation objects exist (e.g. from the Sources: line).
    """
    if not sources:
        return ""

    parts = ['<div class="cite-footnotes">']
    parts.append('<div class="cite-footnotes-title">Sources</div>')
    for i, src in enumerate(sources, 1):
        title = safe_html(f"Section {src.section_id}")
        if src.section_title:
            title = safe_html(f"Section {src.section_id} | {src.section_title}")
        pages_str = (
            ", ".join(str(p) for p in src.page_numbers)
            if src.page_numbers
            else ""
        )
        pages_html = (
            f' <span class="cite-fn-pages">pp. {safe_html(pages_str)}</span>'
            if pages_str
            else ""
        )
        snippet_html = ""
        if src.relevant_text_snippet:
            snippet_html = (
                f'<div class="cite-fn-snippet">'
                f"{safe_html(src.relevant_text_snippet)}</div>"
            )
        parts.append(
            f'<div class="cite-fn">'
            f'<span class="cite-fn-num">[{i}]</span>'
            f'<div class="cite-fn-body">'
            f'<span class="cite-fn-header">{title}</span>'
            f"{pages_html}"
            f"{snippet_html}"
            f"</div></div>"
        )
    parts.append("</div>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Report body text formatter
# ---------------------------------------------------------------------------


def format_report_body(body: str, inline_citations: list[InlineCitation] | None = None) -> str:
    """Convert plain-text report section body to styled HTML.

    Recognises headings (standalone ALL-CAPS lines), field labels
    (LABEL: value), bullet lists, numbered lists, and plain paragraphs.
    Wraps NOT FOUND values in a muted style.

    Args:
        body: Raw section body text from the LLM.

    Returns:
        HTML string to render inside a report-body div.
    """
    from credit_analyzer.utils.text_cleaning import normalize_tables

    # Strip markdown backticks the LLM sometimes emits despite instructions.
    # Remove fenced code blocks (```...```) first, then inline backticks.
    body = re.sub(r"```[^\n]*\n?", "", body)
    body = body.replace("`", "")
    body = normalize_tables(body)

    lines = body.split("\n")
    # Each item in bullet_buffer is (html_text, list[sub_bullet_html])
    bullet_buffer: list[tuple[str, list[str]]] = []
    numbered_buffer: list[str] = []
    table_buffer: list[str] = []
    parts: list[str] = []

    def flush_table() -> None:
        if not table_buffer:
            return
        # Parse table rows, skip separator rows
        rows: list[list[str]] = []
        for row_line in table_buffer:
            if TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buffer.clear()
            return
        parts.append('<table class="rb-table">')
        # First row is header
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{style_value(cell)}</th>")
        parts.append("</tr></thead>")
        if len(rows) > 1:
            parts.append("<tbody>")
            for row in rows[1:]:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{style_value(cell)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        table_buffer.clear()

    def flush_bullets() -> None:
        if bullet_buffer:
            parts.append('<ul class="rb-list">')
            for text, subs in bullet_buffer:
                if subs:
                    parts.append(f"<li>{text}")
                    parts.append('<ul class="rb-sub-list">')
                    for sub in subs:
                        parts.append(f"<li>{sub}</li>")
                    parts.append("</ul>")
                    parts.append("</li>")
                else:
                    parts.append(f"<li>{text}</li>")
            parts.append("</ul>")
            bullet_buffer.clear()

    def flush_numbered() -> None:
        if numbered_buffer:
            parts.append('<ol class="rb-list">')
            for text in numbered_buffer:
                parts.append(f"<li>{text}</li>")
            parts.append("</ol>")
            numbered_buffer.clear()

    def style_value(val: str) -> str:
        """Wrap NOT FOUND in muted style."""
        stripped_val = val.strip()
        if stripped_val.upper() == "NOT FOUND" or stripped_val.upper().startswith("NOT FOUND"):
            return f'<span class="rb-not-found">{safe_html(stripped_val)}</span>'
        if inline_citations:
            return render_citation_markers(stripped_val, inline_citations)
        return safe_html(stripped_val)

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flush_numbered()
            flush_table()
            continue

        # Table row detection
        if TABLE_ROW_RE.match(stripped) or TABLE_SEP_RE.match(stripped):
            flush_bullets()
            flush_numbered()
            table_buffer.append(stripped)
            continue

        # If we had table rows buffered but this line isn't a table row, flush
        if table_buffer:
            flush_table()

        # Check for sub-bullets (indented bullets under a main bullet)
        is_indented = line.startswith("    ") or line.startswith("\t")
        if is_indented:
            sub_match = BULLET_RE.match(stripped)
            if sub_match and bullet_buffer:
                # Attach to the last main bullet
                bullet_buffer[-1][1].append(style_value(sub_match.group(1)))
                continue

        # Top-level bullet item
        bullet_match = BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append((style_value(bullet_match.group(1)), []))
            continue

        # Numbered item
        num_match = NUMBERED_RE.match(stripped)
        if num_match:
            flush_bullets()
            numbered_buffer.append(style_value(num_match.group(2)))
            continue

        # Flush any pending lists before handling headings/fields/paragraphs
        flush_bullets()
        flush_numbered()

        # Standalone heading (all-caps, no colon, no value)
        heading_match = HEADING_RE.match(stripped)
        if heading_match and len(stripped) > 3:
            parts.append(
                f'<div class="rb-heading">{safe_html(stripped)}</div>'
            )
            continue

        # Field label: value
        field_match = FIELD_RE.match(stripped)
        if field_match:
            label = field_match.group(1)
            value = field_match.group(2)
            if value:
                parts.append(
                    f'<div class="rb-field">'
                    f'<span class="rb-field-label">{safe_html(label)}</span> '
                    f'<span class="rb-field-value">{style_value(value)}</span>'
                    f"</div>"
                )
            else:
                # Label only, value on next lines (e.g. "MANDATORY PREPAYMENT:")
                parts.append(
                    f'<div class="rb-field">'
                    f'<span class="rb-field-label">{safe_html(label)}</span>'
                    f"</div>"
                )
            continue

        # Regular paragraph text
        parts.append(f'<div class="rb-para">{style_value(stripped)}</div>')

    # Final flush
    flush_bullets()
    flush_numbered()
    flush_table()

    return "\n".join(parts)


def format_chat_answer(body: str) -> str:
    """Format a Q&A answer body with tables, bullets, numbered lists, and headings.

    Detects pipe-delimited markdown tables and renders them as HTML.
    Bullet lines (- item) become ``<ul>`` lists. Numbered lines (1. item)
    become ``<ol>`` lists. ALL-CAPS lines become styled headings.
    Other lines are wrapped in ``<div>`` for proper paragraph spacing.
    """
    from credit_analyzer.utils.text_cleaning import normalize_tables

    # Strip markdown backticks the LLM sometimes emits despite instructions.
    body = re.sub(r"```[^\n]*\n?", "", body)
    body = body.replace("`", "")
    body = normalize_tables(body)

    lines = body.split("\n")
    table_buffer: list[str] = []
    bullet_buffer: list[str] = []
    numbered_buffer: list[str] = []
    parts: list[str] = []

    def flush_table() -> None:
        if not table_buffer:
            return
        rows: list[list[str]] = []
        for row_line in table_buffer:
            if TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buffer.clear()
            return
        parts.append('<table class="rb-table">')
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{safe_html(cell)}</th>")
        parts.append("</tr></thead>")
        if len(rows) > 1:
            parts.append("<tbody>")
            for row in rows[1:]:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{safe_html(cell)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        table_buffer.clear()

    def flush_bullets() -> None:
        if bullet_buffer:
            parts.append('<ul class="rb-list">')
            for text in bullet_buffer:
                parts.append(f"<li>{safe_html(text)}</li>")
            parts.append("</ul>")
            bullet_buffer.clear()

    def flush_numbered() -> None:
        if numbered_buffer:
            parts.append('<ol class="rb-list">')
            for text in numbered_buffer:
                parts.append(f"<li>{safe_html(text)}</li>")
            parts.append("</ol>")
            numbered_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flush_numbered()
            flush_table()
            continue

        if TABLE_ROW_RE.match(stripped) or TABLE_SEP_RE.match(stripped):
            flush_bullets()
            flush_numbered()
            table_buffer.append(stripped)
            continue
        if table_buffer:
            flush_table()

        # Bullet item
        bullet_match = BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append(bullet_match.group(1))
            continue

        # Numbered item — but NOT all-caps numbered headings like "1. OVERVIEW"
        num_match = NUMBERED_RE.match(stripped)
        if num_match and not HEADING_RE.match(stripped):
            flush_bullets()
            numbered_buffer.append(num_match.group(2))
            continue

        flush_bullets()
        flush_numbered()

        if HEADING_RE.match(stripped) and len(stripped) > 3:
            parts.append(f'<div class="rb-heading">{safe_html(stripped)}</div>')
        else:
            parts.append(f'<div class="rb-para">{safe_html(stripped)}</div>')

    flush_bullets()
    flush_numbered()
    flush_table()
    return "\n".join(parts)


def highlight_defined_terms(
    html: str,
    defs_index: DefinitionsIndex,
) -> str:
    """Wrap defined terms in HTML with tooltip popups.

    Scans text content (outside HTML tags) for defined terms and wraps
    them with tooltip spans showing the term name, page, and scrollable
    definition preview.

    Args:
        html: HTML string to process.
        defs_index: The definitions index with terms and entries.

    Returns:
        HTML with defined terms wrapped in tooltip spans.
    """
    if not defs_index.definitions:
        return html

    # Find terms present in the plain text (strip tags for search)
    plain_text = re.sub(r"<[^>]+>", " ", html)
    terms = defs_index.find_terms_in_text(plain_text)
    if not terms:
        return html

    # Process longest terms first (already sorted by find_terms_in_text)
    for term in terms:
        entry = defs_index.definitions.get(term)
        if entry is None:
            continue

        page_str = f"Page {entry.page_number}" if entry.page_number else "Page n/a"

        # Build tooltip HTML — plain text only, no links to other definitions
        # to prevent cascading popup windows.
        # Strip HTML tags and collapse newlines so markdown-it doesn't create
        # paragraph breaks inside the <span>, which would break DOM nesting
        # and cause subsequent response content to be swallowed by the tooltip.
        plain_def_text = re.sub(r"<[^>]+>", "", safe_html(entry.text))
        plain_def_text = re.sub(r"\s*\n\s*", " ", plain_def_text)
        tip_html = (
            f'<span class="def-tip">'
            f'<span class="def-tip-close" tabindex="0">&times;</span>'
            f'<span class="def-tip-term">{escape(term)}</span>'
            f'<span class="def-tip-meta">{escape(page_str)}</span>'
            f'<span class="def-tip-text">{plain_def_text}</span>'
            f"</span>"
        )

        # Replace term in text content only (not inside HTML tags)
        # Split HTML into tags and text segments, only replace in text segments
        escaped_term = re.escape(term)
        term_pattern = re.compile(r"\b" + escaped_term + r"\b")

        # Build a context-aware pattern that rejects matches inside longer
        # capitalized phrases (e.g. "Communications" inside "Ribbon Communications Operating")
        term_words = term.split()
        is_single_common_word = len(term_words) == 1 and term[0].isupper()

        segments = re.split(r"(<[^>]*>)", html)
        new_segments: list[str] = []
        replaced = False
        # Track nesting: when inside a def-hl span, count span depth so
        # we know when we've exited the def-hl wrapper completely.
        in_def_hl = False
        def_hl_span_depth = 0
        for segment in segments:
            if segment.startswith("<"):
                if 'class="def-hl"' in segment:
                    in_def_hl = True
                    def_hl_span_depth = 1
                elif in_def_hl:
                    if segment.startswith("<span"):
                        def_hl_span_depth += 1
                    elif segment == "</span>":
                        def_hl_span_depth -= 1
                        if def_hl_span_depth == 0:
                            in_def_hl = False
                new_segments.append(segment)
            else:
                # Text segment -- only replace if outside def-hl spans
                if not replaced and not in_def_hl:
                    match = term_pattern.search(segment)
                    if match and is_single_common_word:
                        start, end = match.start(), match.end()
                        before = segment[:start].rstrip()
                        after = segment[end:].lstrip()
                        prev_cap = bool(re.search(r"[A-Z][a-z]+\s*$", before))
                        next_cap = bool(re.match(r"\s*[A-Z][a-z]", after))
                        if prev_cap and next_cap:
                            new_segments.append(segment)
                            continue

                    if match:
                        pos = match.start()
                        replacement = (
                            f'<span class="def-hl" tabindex="0">'
                            f"{escape(match.group(0))}{tip_html}</span>"
                        )
                        segment = segment[:pos] + replacement + segment[match.end():]
                        replaced = True
                new_segments.append(segment)

        html = "".join(new_segments)

    return html


def def_tooltip_click_script() -> str:
    """Return a JS snippet that pins definition tooltips on click.

    Uses the ``def-hl-active`` CSS class instead of ``:focus`` so that
    browser auto-focus (e.g. when a Streamlit dialog opens) does not
    accidentally show a tooltip.
    """
    return """<script>
(function() {
    var doc = parent.document;
    if (doc._defTipClickAttached) return;
    doc._defTipClickAttached = true;
    doc.addEventListener('click', function(e) {
        var hl = e.target.closest('.def-hl');
        var closeBtn = e.target.closest('.def-tip-close');
        if (closeBtn) {
            var parentHl = closeBtn.closest('.def-hl');
            if (parentHl) parentHl.classList.remove('def-hl-active');
            e.stopPropagation();
            return;
        }
        // Remove active from all other tooltips
        doc.querySelectorAll('.def-hl-active').forEach(function(el) {
            if (el !== hl) el.classList.remove('def-hl-active');
        });
        if (hl) {
            hl.classList.toggle('def-hl-active');
        }
    });
})();
</script>"""


__all__ = [
    "metric_card",
    "panel_card",
    "rail_card",
    "confidence_pill",
    "copy_button",
    "nav_item",
    "report_scroll_script",
    "scroll_to_top_script",
    "definition_card",
    "empty_state",
    "chat_welcome",
    "guide_step_card",
    "guide_section_block",
    "context_strip",
    "stream_status",
    "message_timestamp",
    "indexing_step",
    "compact_stats_grid",
    "document_card",
    "document_card_compact",
    "skeleton_lines",
    "report_nav_dot",
    "render_citation_markers",
    "render_citation_footnotes",
    "render_inline_citations",
    "render_source_footnotes",
    "format_report_body",
    "format_chat_answer",
    "highlight_defined_terms",
    "def_tooltip_click_script",
]
