"""Theme helpers for the Streamlit demo app."""

from __future__ import annotations

import re
from html import escape


def _safe(text: str) -> str:
    """HTML-escape text and neutralise ``$`` signs for Streamlit.

    Streamlit's ``st.markdown(…, unsafe_allow_html=True)`` still passes
    the string through its markdown/LaTeX renderer *before* injecting
    HTML.  Bare ``$`` signs therefore get interpreted as inline-math
    delimiters, which silently eats dollar amounts like ``$15,000,000``.
    Replacing ``$`` with the HTML entity ``&#36;`` prevents this.
    """
    return escape(text).replace("$", "&#36;")


RBC_BLUE = "#0051A5"
RBC_BLUE_DEEP = "#003B7A"
RBC_GOLD = "#FFCC00"
INK = "#122033"
MUTED = "#5B6B82"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F4F7FB"
BORDER = "#D5DFEC"

APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {{
  --rbc-blue: {RBC_BLUE};
  --rbc-blue-deep: {RBC_BLUE_DEEP};
  --rbc-gold: {RBC_GOLD};
  --ink: {INK};
  --muted: {MUTED};
  --surface: {SURFACE};
  --surface-alt: {SURFACE_ALT};
  --border: {BORDER};
  --gold-wash: rgba(255, 204, 0, 0.16);
  --success-bg: #E9F6EE;
  --success-fg: #17633C;
  --warning-bg: #FFF4D6;
  --warning-fg: #8A5A00;
  --danger-bg: #FDEBEC;
  --danger-fg: #8F2430;
}}

html, body, [class*="css"] {{
  font-family: 'IBM Plex Sans', sans-serif;
}}

.stApp {{
  background: #F7F9FC;
  color: var(--ink);
}}

[data-testid="stHeader"] {{
  background: transparent;
}}

[data-testid="stSidebar"] {{
  background: rgba(0, 59, 122, 0.98);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}}

[data-testid="stSidebar"] * {{
  color: #F8FAFD;
}}

.block-container {{
  max-width: 1280px;
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}}

[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}

h1, h2, h3 {{
  letter-spacing: -0.02em;
}}

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {{
  border-radius: 14px;
  border: 1px solid rgba(255, 204, 0, 0.6);
  background: var(--surface);
  color: var(--ink);
  font-weight: 600;
  min-height: 2.65rem;
  padding: 0.55rem 1rem;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}}

div[data-testid="stButton"] > button[kind="primary"] {{
  background: var(--rbc-blue);
  color: white;
  border-color: rgba(255, 204, 0, 0.72);
}}

div[data-testid="stButton"] > button:hover {{
  border-color: rgba(255, 204, 0, 0.9);
  transform: translateY(-1px);
}}

.st-key-suggested-actions div[data-testid="stButton"] > button {{
  min-height: 5.25rem;
  height: 100%;
  align-items: center;
  justify-content: center;
  text-align: center;
  white-space: normal;
}}

.st-key-suggested-actions div[data-testid="stButton"] > button p {{
  white-space: normal;
  line-height: 1.3;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button {{
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 204, 0, 0.72);
  color: #F8FAFD !important;
  box-shadow: none;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button:hover {{
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 204, 0, 0.96);
}}

[data-testid="stFileUploader"] section,
[data-testid="stTextInputRootElement"],
[data-testid="stChatInput"],
[data-baseweb="select"] > div {{
  border-radius: 16px;
  border-color: var(--border);
}}

[data-testid="stFileUploader"] section,
[data-testid="stTextInputRootElement"],
[data-testid="stChatInput"] {{
  background: rgba(255, 255, 255, 0.92);
}}

[data-testid="stSidebar"] [data-baseweb="select"] > div {{
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 204, 0, 0.72);
}}

[data-testid="stSidebar"] [data-baseweb="select"] * {{
  color: #F8FAFD !important;
  fill: #F8FAFD !important;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 0.45rem;
  margin-bottom: 1rem;
}}

.stTabs [data-baseweb="tab"] {{
  height: auto;
  padding: 0.5rem 0.95rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(0, 81, 165, 0.1);
}}

.stTabs [aria-selected="true"] {{
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(0, 81, 165, 0.22);
  color: var(--rbc-blue-deep);
  box-shadow: inset 0 -2px 0 var(--rbc-gold);
}}

.hero-card {{
  background: rgba(0, 81, 165, 0.98);
  color: white;
  border-radius: 22px;
  padding: 1.15rem 1.35rem;
  border: 1px solid rgba(255, 204, 0, 0.4);
  box-shadow: 0 18px 40px rgba(0, 46, 94, 0.14);
}}

.hero-eyebrow {{
  display: inline-block;
  padding: 0.26rem 0.62rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: #F7FBFF;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid rgba(255, 204, 0, 0.26);
}}

.hero-title {{
  margin: 0.8rem 0 0.28rem 0;
  font-size: 1.85rem;
  line-height: 1.08;
  font-weight: 700;
}}

.hero-copy {{
  margin: 0;
  max-width: 44rem;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.96rem;
  line-height: 1.45;
}}

.metric-card,
.panel-card,
.section-card {{
  background: rgba(255, 255, 255, 0.93);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.05);
}}

.metric-card {{
  padding: 0.95rem 1rem;
  min-height: 124px;
}}

.metric-label {{
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.metric-value {{
  color: var(--ink);
  font-size: 1.8rem;
  font-weight: 700;
  margin-top: 0.38rem;
}}

.metric-caption {{
  color: var(--muted);
  font-size: 0.9rem;
  margin-top: 0.45rem;
  line-height: 1.32;
}}

.panel-card {{
  padding: 1rem 1.1rem;
}}

.panel-title {{
  margin: 0 0 0.45rem 0;
  color: var(--ink);
  font-size: 1rem;
  font-weight: 700;
}}

.panel-copy {{
  color: var(--muted);
  margin: 0;
  line-height: 1.45;
}}

.panel-copy:empty {{
  display: none;
}}

.section-card {{
  padding: 1rem 1.1rem;
  margin-bottom: 0.9rem;
}}

.section-title {{
  margin: 0;
  color: var(--ink);
  font-size: 1rem;
  font-weight: 700;
}}

.section-helper {{
  color: var(--muted);
  margin: 0.28rem 0 0.72rem 0;
  font-size: 0.9rem;
}}

.section-answer {{
  color: var(--ink);
  line-height: 1.5;
}}

.pill {{
  display: inline-block;
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}}

.pill-high {{
  background: var(--success-bg);
  color: var(--success-fg);
}}

.pill-medium {{
  background: var(--warning-bg);
  color: var(--warning-fg);
}}

.pill-low {{
  background: var(--danger-bg);
  color: var(--danger-fg);
}}

.meta-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.72rem;
}}

.meta-chip {{
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.3rem 0.66rem;
  background: rgba(0, 81, 165, 0.07);
  color: var(--rbc-blue-deep);
  font-size: 0.77rem;
  font-weight: 600;
}}

.rail-card {{
  padding: 0.9rem 0.95rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 204, 0, 0.42);
  margin-bottom: 0.8rem;
}}

.rail-card.is-ready {{
  box-shadow: inset 3px 0 0 rgba(255, 204, 0, 0.9);
}}

.rail-card.is-warning {{
  box-shadow: inset 3px 0 0 rgba(255, 229, 153, 0.9);
}}

.rail-label {{
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.8;
}}

.rail-value {{
  margin-top: 0.3rem;
  font-size: 1rem;
  font-weight: 700;
}}

.rail-meta {{
  margin-top: 0.25rem;
  font-size: 0.86rem;
  line-height: 1.35;
  opacity: 0.92;
}}

/* source-card CSS removed – sources now rendered as footnotes */

.subtle-note {{
  color: var(--muted);
  font-size: 0.92rem;
  margin-top: 0.4rem;
}}

/* ---- Report tab ---- */

.report-header {{
  background: linear-gradient(135deg, rgba(0, 59, 122, 0.97), rgba(0, 81, 165, 0.94));
  color: white;
  border-radius: 18px;
  padding: 1.2rem 1.4rem;
  border: 1px solid rgba(255, 204, 0, 0.35);
  box-shadow: 0 14px 30px rgba(0, 46, 94, 0.12);
  margin-bottom: 1rem;
}}

.report-header-borrower {{
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.2rem 0;
  line-height: 1.15;
}}

.report-header-meta {{
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.88rem;
  margin: 0;
}}

.report-stats-row {{
  display: flex;
  gap: 0.7rem;
  margin-top: 0.9rem;
  flex-wrap: wrap;
}}

.report-stat {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  padding: 0.32rem 0.72rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 204, 0, 0.25);
}}

.report-stat-gold {{
  background: rgba(255, 204, 0, 0.18);
  border-color: rgba(255, 204, 0, 0.5);
  color: #FFFBE6;
}}

.report-section {{
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 0;
  margin-bottom: 0.75rem;
  overflow: hidden;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}}

.report-section-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.1rem;
  border-bottom: 1px solid rgba(213, 223, 236, 0.6);
  cursor: default;
}}

.report-section-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 8px;
  background: var(--rbc-blue);
  color: white;
  font-size: 0.78rem;
  font-weight: 700;
  flex-shrink: 0;
}}

.report-section-title {{
  margin: 0 0 0 0.65rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ink);
  flex-grow: 1;
}}

.report-section-badges {{
  display: flex;
  gap: 0.4rem;
  align-items: center;
  flex-shrink: 0;
}}

.badge-chunks {{
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 500;
}}

.report-section-body {{
  padding: 0.9rem 1.1rem 1rem 1.1rem;
}}

.report-section-body pre {{
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.9rem;
  line-height: 1.55;
  color: var(--ink);
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  background: none;
  border: none;
  padding: 0;
}}

.report-sources {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding: 0.6rem 1.1rem;
  border-top: 1px solid rgba(213, 223, 236, 0.5);
  background: rgba(244, 247, 251, 0.5);
}}

/* report-source-chip removed – sources now rendered as footnotes */

.report-error-body {{
  padding: 0.9rem 1.1rem;
  color: var(--danger-fg);
  font-size: 0.9rem;
  font-style: italic;
}}

/* ---- Formatted report body ---- */

.report-body {{
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--ink);
}}

.report-body .rb-heading {{
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--rbc-blue);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0.7rem 0 0.2rem 0;
  padding-bottom: 0.2rem;
  border-bottom: 1px solid rgba(0, 81, 165, 0.1);
}}

.report-body .rb-heading:first-child {{
  margin-top: 0;
}}

.report-body .rb-field {{
  margin: 0.18rem 0;
  line-height: 1.45;
}}

.report-body .rb-field-label {{
  font-weight: 700;
  color: var(--rbc-blue-deep);
}}

.report-body .rb-field-value {{
  color: var(--ink);
}}

.report-body .rb-not-found {{
  color: var(--muted);
  font-style: italic;
}}

.report-body .rb-para {{
  margin: 0.15rem 0;
  line-height: 1.45;
}}

.report-body ul.rb-list {{
  margin: 0.15rem 0 0.15rem 1.1rem;
  padding: 0;
  list-style: disc;
}}

.report-body ul.rb-list li {{
  margin: 0.1rem 0;
  line-height: 1.4;
}}

.report-body ol.rb-list {{
  margin: 0.15rem 0 0.15rem 1.1rem;
  padding: 0;
}}

.report-body ol.rb-list li {{
  margin: 0.1rem 0;
  line-height: 1.4;
}}

.report-body .rb-sub-list {{
  margin: 0.15rem 0 0.15rem 1.1rem;
  padding: 0;
  list-style: circle;
}}

.report-body .rb-sub-list li {{
  margin: 0.1rem 0;
  line-height: 1.45;
  font-size: 0.87rem;
}}

/* Ensure tooltips are not clipped by Streamlit overflow */
.report-section,
/* overflow overrides removed – no longer needed without hover tooltips */

/* Inline citation markers (superscript) */
.cite-marker {{
  display: inline;
  color: var(--rbc-blue);
  font-size: 0.75em;
  font-weight: 700;
  vertical-align: super;
  line-height: 0;
  padding: 0 1px;
}}

/* Footnotes block */
.cite-footnotes {{
  margin-top: 0.5rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--border);
}}

.cite-footnotes-title {{
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.4rem;
}}

.cite-fn {{
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.85rem;
  line-height: 1.45;
}}

.cite-fn + .cite-fn {{
  border-top: 1px solid rgba(213, 223, 236, 0.4);
}}

.cite-fn-num {{
  flex-shrink: 0;
  color: var(--rbc-blue);
  font-weight: 700;
  min-width: 1.4em;
}}

.cite-fn-body {{
  flex: 1;
  min-width: 0;
}}

.cite-fn-header {{
  font-weight: 600;
  color: var(--ink);
}}

.cite-fn-pages {{
  color: var(--muted);
  font-size: 0.8rem;
  margin-left: 0.3rem;
}}

.cite-fn-snippet {{
  color: var(--muted);
  font-size: 0.82rem;
  margin-top: 0.15rem;
  line-height: 1.4;
}}

</style>
"""


def hero_card(title: str, copy: str, eyebrow: str | None = None) -> str:
    """Render the app hero block."""
    eyebrow_markup = (
        f'<div class="hero-eyebrow">{_safe(eyebrow)}</div>' if eyebrow else ""
    )
    return (
        '<section class="hero-card">'
        f"{eyebrow_markup}"
        f'<h1 class="hero-title">{_safe(title)}</h1>'
        f'<p class="hero-copy">{_safe(copy)}</p>'
        "</section>"
    )


def metric_card(label: str, value: str, caption: str) -> str:
    """Render a compact metric card."""
    return (
        '<section class="metric-card">'
        f'<div class="metric-label">{_safe(label)}</div>'
        f'<div class="metric-value">{_safe(value)}</div>'
        f'<div class="metric-caption">{_safe(caption)}</div>'
        "</section>"
    )


def panel_card(title: str, copy: str | None = None) -> str:
    """Render a lightweight informational panel."""
    return (
        '<section class="panel-card">'
        f'<h3 class="panel-title">{_safe(title)}</h3>'
        f'<p class="panel-copy">{_safe(copy or "")}</p>'
        "</section>"
    )


def rail_card(label: str, value: str, meta: str | None = None, tone: str = "ready") -> str:
    """Render a compact sidebar control-rail card."""
    safe_tone = "warning" if tone == "warning" else "ready"
    return (
        f'<section class="rail-card is-{safe_tone}">'
        f'<div class="rail-label">{_safe(label)}</div>'
        f'<div class="rail-value">{_safe(value)}</div>'
        f'<div class="rail-meta">{_safe(meta or "")}</div>'
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
    return f'<span class="pill pill-{tone}">{_safe(confidence.upper())}</span>'


# Matches [1], [2], etc. in body text
_INLINE_MARKER_RE = re.compile(r"\[(\d+)\]")


def render_citation_markers(body: str, citations: list) -> str:
    """Replace [N] markers with styled superscripts only (no footnotes).

    Use this inside ``format_report_body`` where footnotes are rendered
    separately at the section level.
    """
    if not citations:
        return _safe(body)

    parts: list[str] = []
    last_end = 0
    for m in _INLINE_MARKER_RE.finditer(body):
        parts.append(_safe(body[last_end:m.start()]))
        num = int(m.group(1))
        parts.append(f'<span class="cite-marker">[{num}]</span>')
        last_end = m.end()
    parts.append(_safe(body[last_end:]))
    return "".join(parts)


def render_citation_footnotes(citations: list) -> str:
    """Render footnotes block from a list of InlineCitation objects."""
    if not citations:
        return ""

    parts = ['<div class="cite-footnotes">']
    parts.append('<div class="cite-footnotes-title">Sources</div>')
    for cite in sorted(citations, key=lambda c: c.marker_number):
        title = _safe(f"Section {cite.section_id}")
        if cite.section_title:
            title = _safe(f"Section {cite.section_id} | {cite.section_title}")
        pages_str = (
            ", ".join(str(p) for p in cite.page_numbers)
            if cite.page_numbers
            else ""
        )
        pages_html = (
            f' <span class="cite-fn-pages">pp. {_safe(pages_str)}</span>'
            if pages_str
            else ""
        )
        snippet_html = ""
        if cite.snippet:
            snippet_html = (
                f'<div class="cite-fn-snippet">{_safe(cite.snippet)}</div>'
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


def render_inline_citations(body: str, citations: list) -> str:
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
        return _safe(body)

    body_html = render_citation_markers(body, citations)
    footnotes_html = render_citation_footnotes(citations)
    return body_html + footnotes_html


def render_source_footnotes(sources: list) -> str:
    """Render a list of SourceCitation objects as a footnotes HTML block.

    Used as a fallback when inline citations are not available but
    SourceCitation objects exist (e.g. from the Sources: line).
    """
    if not sources:
        return ""

    parts = ['<div class="cite-footnotes">']
    parts.append('<div class="cite-footnotes-title">Sources</div>')
    for i, src in enumerate(sources, 1):
        title = _safe(f"Section {src.section_id}")
        if src.section_title:
            title = _safe(f"Section {src.section_id} | {src.section_title}")
        pages_str = (
            ", ".join(str(p) for p in src.page_numbers)
            if src.page_numbers
            else ""
        )
        pages_html = (
            f' <span class="cite-fn-pages">pp. {_safe(pages_str)}</span>'
            if pages_str
            else ""
        )
        snippet_html = ""
        if src.relevant_text_snippet:
            snippet_html = (
                f'<div class="cite-fn-snippet">'
                f"{_safe(src.relevant_text_snippet)}</div>"
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

# Matches standalone headings: all-caps words on their own line, no colon
# e.g. "BORROWER INFORMATION", "PRICING TERMS", "GENERAL PROHIBITION"
_HEADING_RE = re.compile(
    r"^([A-Z][A-Z0-9 /&,\-()]+)$"
)

# Matches field labels at line start: "LABEL:" or "LABEL: value"
# Covers patterns like "BORROWER:", "FACILITY 1:", "SOFR FLOOR:",
# "COMMITMENT / PRINCIPAL:", "OID / UPFRONT FEE:", "LC FEE:"
_FIELD_RE = re.compile(
    r"^([A-Z][A-Z0-9 /&,\-().:]+?:)\s*(.*)"
)

# Numbered list item: "1. text", "2. text"
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.+)")

# Bullet: "- text" or "* text"
_BULLET_RE = re.compile(r"^[-*]\s+(.+)")


def format_report_body(body: str, inline_citations: list | None = None) -> str:
    """Convert plain-text report section body to styled HTML.

    Recognises headings (standalone ALL-CAPS lines), field labels
    (LABEL: value), bullet lists, numbered lists, and plain paragraphs.
    Wraps NOT FOUND values in a muted style.

    Args:
        body: Raw section body text from the LLM.

    Returns:
        HTML string to render inside a report-body div.
    """
    lines = body.split("\n")
    # Each item in bullet_buffer is (html_text, list[sub_bullet_html])
    bullet_buffer: list[tuple[str, list[str]]] = []
    numbered_buffer: list[str] = []
    parts: list[str] = []

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
            return f'<span class="rb-not-found">{_safe(stripped_val)}</span>'
        if inline_citations:
            return render_citation_markers(stripped_val, inline_citations)
        return _safe(stripped_val)

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flush_numbered()
            continue

        # Check for sub-bullets (indented bullets under a main bullet)
        is_indented = line.startswith("    ") or line.startswith("\t")
        if is_indented:
            sub_match = _BULLET_RE.match(stripped)
            if sub_match and bullet_buffer:
                # Attach to the last main bullet
                bullet_buffer[-1][1].append(style_value(sub_match.group(1)))
                continue

        # Top-level bullet item
        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append((style_value(bullet_match.group(1)), []))
            continue

        # Numbered item
        num_match = _NUMBERED_RE.match(stripped)
        if num_match:
            flush_bullets()
            numbered_buffer.append(style_value(num_match.group(2)))
            continue

        # Flush any pending lists before handling headings/fields/paragraphs
        flush_bullets()
        flush_numbered()

        # Standalone heading (all-caps, no colon, no value)
        heading_match = _HEADING_RE.match(stripped)
        if heading_match and len(stripped) > 3:
            parts.append(
                f'<div class="rb-heading">{_safe(stripped)}</div>'
            )
            continue

        # Field label: value
        field_match = _FIELD_RE.match(stripped)
        if field_match:
            label = field_match.group(1)
            value = field_match.group(2)
            if value:
                parts.append(
                    f'<div class="rb-field">'
                    f'<span class="rb-field-label">{_safe(label)}</span> '
                    f'<span class="rb-field-value">{style_value(value)}</span>'
                    f"</div>"
                )
            else:
                # Label only, value on next lines (e.g. "MANDATORY PREPAYMENT:")
                parts.append(
                    f'<div class="rb-field">'
                    f'<span class="rb-field-label">{_safe(label)}</span>'
                    f"</div>"
                )
            continue

        # Regular paragraph text
        parts.append(f'<div class="rb-para">{style_value(stripped)}</div>')

    # Final flush
    flush_bullets()
    flush_numbered()

    return "\n".join(parts)
