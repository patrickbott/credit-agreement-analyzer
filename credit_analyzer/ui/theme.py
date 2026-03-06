"""Theme helpers for the Streamlit demo app."""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from credit_analyzer.generation.response_parser import InlineCitation, SourceCitation


def _safe(text: str) -> str:
    """HTML-escape text and neutralise ``$`` signs for Streamlit.

    Streamlit's ``st.markdown(…, unsafe_allow_html=True)`` still passes
    the string through its markdown/LaTeX renderer *before* injecting
    HTML.  Bare ``$`` signs therefore get interpreted as inline-math
    delimiters, which silently eats dollar amounts like ``$15,000,000``.
    Replacing ``$`` with the HTML entity ``&#36;`` prevents this.
    """
    return escape(text).replace("$", "&#36;")


# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

NAVY_DEEP = "#001A3E"
RBC_BLUE = "#0051A5"
RBC_BLUE_DEEP = "#001A3E"  # backward compat alias
RBC_BLUE_LIGHT = "#E8F0FE"
RBC_GOLD = "#C8A000"
GOLD_BRIGHT = "#D4AF37"
INK = "#0F1A2E"
MUTED = "#64748B"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFC"
BG = "#F1F5F9"
BORDER = "#E2E8F0"

# ---------------------------------------------------------------------------
# APP_CSS — full design system
# ---------------------------------------------------------------------------

APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {{
  --navy-deep: {NAVY_DEEP};
  --rbc-blue: {RBC_BLUE};
  --rbc-blue-deep: {RBC_BLUE_DEEP};
  --rbc-blue-light: {RBC_BLUE_LIGHT};
  --rbc-gold: {RBC_GOLD};
  --gold-bright: {GOLD_BRIGHT};
  --ink: {INK};
  --muted: {MUTED};
  --surface: {SURFACE};
  --surface-alt: {SURFACE_ALT};
  --bg: {BG};
  --border: {BORDER};
}}

/* ---- Base typography ---- */

html, body, [class*="css"] {{
  font-family: 'Source Sans 3', 'Source Sans Pro', system-ui, sans-serif;
  color: var(--ink);
}}

h1, h2, h3 {{
  font-family: 'DM Sans', 'Source Sans 3', system-ui, sans-serif;
  letter-spacing: -0.02em;
}}

/* ---- App shell ---- */

.stApp {{
  background: var(--bg);
  color: var(--ink);
}}

[data-testid="stHeader"] {{
  background: transparent;
}}

/* ---- Sidebar ---- */

[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, {NAVY_DEEP} 0%, #00254D 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}}

[data-testid="stSidebar"]::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0,26,62,0) 60%, rgba(0,81,165,0.08) 100%);
  pointer-events: none;
}}

[data-testid="stSidebar"] * {{
  color: #F0F4FA;
}}

[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}

/* ---- Layout ---- */

.block-container {{
  max-width: 1320px;
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}}

/* ---- Buttons ---- */

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {{
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink);
  font-family: 'Source Sans 3', system-ui, sans-serif;
  font-weight: 600;
  min-height: 2.65rem;
  padding: 0.55rem 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}}

div[data-testid="stButton"] > button[kind="primary"] {{
  background: var(--rbc-blue);
  color: white;
  border-color: {GOLD_BRIGHT};
}}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {{
  border-color: {GOLD_BRIGHT};
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 26, 62, 0.12);
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

/* Sidebar buttons */
[data-testid="stSidebar"] div[data-testid="stButton"] > button,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button {{
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(200, 160, 0, 0.5);
  color: #F0F4FA !important;
  box-shadow: none;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button:hover {{
  background: rgba(255, 255, 255, 0.13);
  border-color: {GOLD_BRIGHT};
}}

/* ---- Inputs ---- */

[data-testid="stFileUploader"] section,
[data-testid="stTextInputRootElement"],
[data-testid="stChatInput"],
[data-baseweb="select"] > div {{
  border-radius: 10px;
  border-color: var(--border);
  transition: all 0.2s ease;
}}

[data-testid="stFileUploader"] section:focus-within,
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stChatInput"]:focus-within {{
  border-color: var(--rbc-blue);
  box-shadow: 0 0 0 3px rgba(0, 81, 165, 0.12);
}}

[data-testid="stFileUploader"] section,
[data-testid="stTextInputRootElement"],
[data-testid="stChatInput"] {{
  background: rgba(255, 255, 255, 0.95);
}}

[data-testid="stSidebar"] [data-baseweb="select"] > div {{
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(200, 160, 0, 0.5);
}}

[data-testid="stSidebar"] [data-baseweb="select"] * {{
  color: #F0F4FA !important;
  fill: #F0F4FA !important;
}}

/* ---- Tabs ---- */

.stTabs [data-baseweb="tab-list"] {{
  gap: 0.25rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}}

.stTabs [data-baseweb="tab"] {{
  height: auto;
  padding: 0.6rem 1.1rem;
  border-radius: 0;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 500;
  color: var(--muted);
  transition: all 0.2s ease;
}}

.stTabs [data-baseweb="tab"]:hover {{
  color: var(--ink);
}}

.stTabs [aria-selected="true"] {{
  background: transparent;
  color: var(--ink);
  font-weight: 600;
  border-bottom: 2px solid {RBC_GOLD};
}}

/* ---- Hero card ---- */

.hero-card {{
  background: linear-gradient(135deg, {NAVY_DEEP} 0%, {RBC_BLUE} 100%);
  color: white;
  border-radius: 16px;
  padding: 1.25rem 1.5rem;
  border: 1px solid rgba(212, 175, 55, 0.3);
  box-shadow: 0 8px 32px rgba(0, 26, 62, 0.18);
  position: relative;
  overflow: hidden;
}}

.hero-card::after {{
  content: '';
  position: absolute;
  top: -40%;
  right: -10%;
  width: 280px;
  height: 280px;
  background: radial-gradient(circle, rgba(200, 160, 0, 0.06) 0%, transparent 70%);
  pointer-events: none;
}}

.hero-eyebrow {{
  display: inline-block;
  padding: 0.22rem 0.6rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  font-family: 'Source Sans 3', system-ui, sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border: 1px solid rgba(212, 175, 55, 0.25);
}}

.hero-icon {{
  display: inline-block;
  margin-right: 0.5rem;
  vertical-align: middle;
}}

.hero-title {{
  margin: 0.75rem 0 0.25rem 0;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
}}

.hero-copy {{
  margin: 0;
  max-width: 44rem;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.95rem;
  line-height: 1.5;
}}

/* ---- Metric cards ---- */

.metric-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--rbc-blue);
  border-radius: 12px;
  padding: 0.95rem 1.1rem;
  min-height: 120px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}}

.metric-card:hover {{
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}}

.metric-label {{
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.metric-value {{
  color: var(--ink);
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.75rem;
  font-weight: 700;
  margin-top: 0.35rem;
  letter-spacing: -0.01em;
}}

.metric-caption {{
  color: var(--muted);
  font-size: 0.88rem;
  margin-top: 0.4rem;
  line-height: 1.35;
}}

/* ---- Panel cards ---- */

.panel-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.15rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}}

.panel-title {{
  margin: 0 0 0.4rem 0;
  font-family: 'DM Sans', system-ui, sans-serif;
  color: var(--ink);
  font-size: 1rem;
  font-weight: 700;
}}

.panel-copy {{
  color: var(--muted);
  margin: 0;
  line-height: 1.5;
  font-size: 0.92rem;
}}

.panel-copy:empty {{
  display: none;
}}

/* ---- Section card (Q&A) ---- */

.section-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.15rem;
  margin-bottom: 0.9rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}}

.section-title {{
  margin: 0;
  font-family: 'DM Sans', system-ui, sans-serif;
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
  line-height: 1.55;
}}

/* ---- Confidence pills ---- */

.pill {{
  display: inline-block;
  border-radius: 999px;
  padding: 0.25rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}}

.pill-high {{
  background: #ECFDF5;
  color: #059669;
}}

.pill-medium {{
  background: #FFFBEB;
  color: #D97706;
}}

.pill-low {{
  background: #FEF2F2;
  color: #DC2626;
}}

/* ---- Meta row / chips ---- */

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
  padding: 0.28rem 0.62rem;
  background: var(--rbc-blue-light);
  color: var(--rbc-blue);
  font-size: 0.76rem;
  font-weight: 600;
}}

/* ---- Rail cards (sidebar) ---- */

.rail-card {{
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(200, 160, 0, 0.3);
  margin-bottom: 0.75rem;
  transition: all 0.2s ease;
}}

.rail-card.is-ready {{
  border-left: 3px solid {RBC_GOLD};
}}

.rail-card.is-warning {{
  border-left: 3px solid rgba(212, 175, 55, 0.5);
}}

.rail-label {{
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.75;
}}

.rail-value {{
  margin-top: 0.25rem;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1rem;
  font-weight: 700;
}}

.rail-meta {{
  margin-top: 0.2rem;
  font-size: 0.85rem;
  line-height: 1.35;
  opacity: 0.88;
}}

.subtle-note {{
  color: var(--muted);
  font-size: 0.92rem;
  margin-top: 0.4rem;
}}

/* ---- Report header ---- */

.report-header {{
  background: linear-gradient(135deg, {NAVY_DEEP} 0%, {RBC_BLUE} 100%);
  color: white;
  border-radius: 14px;
  padding: 1.25rem 1.4rem;
  border: 1px solid rgba(212, 175, 55, 0.3);
  box-shadow: 0 8px 28px rgba(0, 26, 62, 0.15);
  margin-bottom: 1rem;
}}

.report-header-borrower {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.45rem;
  font-weight: 700;
  margin: 0 0 0.2rem 0;
  line-height: 1.15;
  letter-spacing: -0.01em;
}}

.report-header-meta {{
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.87rem;
  margin: 0;
}}

.report-stats-row {{
  display: flex;
  gap: 0.65rem;
  margin-top: 0.85rem;
  flex-wrap: wrap;
}}

.report-stat {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(212, 175, 55, 0.2);
}}

.report-stat-gold {{
  background: rgba(200, 160, 0, 0.15);
  border-color: rgba(212, 175, 55, 0.45);
  color: #FFF8E0;
}}

/* ---- Report sections ---- */

.report-section {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--rbc-blue);
  border-radius: 12px;
  padding: 0;
  margin-bottom: 0.75rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
}}

.report-section:hover {{
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}}

.report-section-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1.1rem;
  border-bottom: 1px solid var(--border);
  cursor: default;
}}

.report-section-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.65rem;
  height: 1.65rem;
  border-radius: 8px;
  background: var(--rbc-blue);
  color: white;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.76rem;
  font-weight: 700;
  flex-shrink: 0;
}}

.report-section-title {{
  margin: 0 0 0 0.6rem;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.94rem;
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
  position: relative;
}}

.report-section-body pre {{
  font-family: 'Source Sans 3', system-ui, sans-serif;
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
  padding: 0.55rem 1.1rem;
  border-top: 1px solid var(--border);
  background: var(--surface-alt);
}}

.report-error-body {{
  padding: 0.9rem 1.1rem;
  color: #DC2626;
  font-size: 0.9rem;
  font-style: italic;
}}

/* ---- Formatted report body ---- */

.report-body {{
  font-family: 'Source Sans 3', system-ui, sans-serif;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--ink);
}}

.report-body .rb-heading {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--rbc-blue);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0.75rem 0 0.25rem 0;
  padding-bottom: 0.2rem;
  border-bottom: 1px solid rgba(0, 81, 165, 0.08);
}}

.report-body .rb-heading:first-child {{
  margin-top: 0;
}}

.report-body .rb-field {{
  margin: 0.2rem 0;
  line-height: 1.5;
}}

.report-body .rb-field-label {{
  font-weight: 700;
  color: var(--navy-deep);
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
  line-height: 1.5;
}}

.report-body ul.rb-list {{
  margin: 0.15rem 0 0.15rem 1.1rem;
  padding: 0;
  list-style: disc;
}}

.report-body ul.rb-list li {{
  margin: 0.1rem 0;
  line-height: 1.45;
}}

.report-body ol.rb-list {{
  margin: 0.15rem 0 0.15rem 1.1rem;
  padding: 0;
}}

.report-body ol.rb-list li {{
  margin: 0.1rem 0;
  line-height: 1.45;
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

/* ---- Inline citation markers ---- */

.cite-marker {{
  display: inline;
  color: var(--rbc-blue);
  font-size: 0.75em;
  font-weight: 700;
  vertical-align: super;
  line-height: 0;
  padding: 0 1px;
}}

/* ---- Footnotes block ---- */

.cite-footnotes {{
  margin-top: 0.5rem;
  padding-top: 0.4rem;
  border-top: 1px solid var(--border);
}}

.cite-footnotes-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.76rem;
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
  border-top: 1px solid rgba(226, 232, 240, 0.5);
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

/* ---- Chat assistant messages ---- */

[data-testid="stChatMessage"]:nth-child(even) {{
  border-left: 3px solid var(--rbc-blue);
  border-radius: 0;
  padding-left: 1rem;
}}

/* ---- Copy button ---- */

.copy-btn {{
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.3rem 0.4rem;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}}

*:hover > .copy-btn {{
  opacity: 0.7;
}}

.copy-btn:hover {{
  opacity: 1 !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}}

.copy-btn.copied {{
  opacity: 1 !important;
  border-color: #059669;
  color: #059669;
}}

/* ---- Quick nav (report TOC) ---- */

.quick-nav {{
  position: sticky;
  top: 3.5rem;
  max-height: calc(100vh - 5rem);
  overflow-y: auto;
  padding: 0.75rem 0;
}}

.quick-nav-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  padding: 0 0.6rem;
  margin-bottom: 0.5rem;
}}

.quick-nav-item {{
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.35rem 0.6rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--muted);
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
}}

.quick-nav-item:hover {{
  background: var(--rbc-blue-light);
  color: var(--rbc-blue);
}}

.quick-nav-item.active {{
  background: var(--rbc-blue-light);
  color: var(--rbc-blue);
  font-weight: 600;
}}

.quick-nav-item .nav-num {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 5px;
  background: var(--border);
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 700;
  flex-shrink: 0;
}}

.quick-nav-item:hover .nav-num,
.quick-nav-item.active .nav-num {{
  background: var(--rbc-blue);
  color: white;
}}

/* ---- Definition cards ---- */

.def-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}}

.def-card:hover {{
  border-color: var(--rbc-blue);
  box-shadow: 0 2px 8px rgba(0, 81, 165, 0.08);
}}

.def-card .def-term {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--rbc-blue);
  margin-bottom: 0.2rem;
}}

.def-card .def-text {{
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--ink);
}}

/* ---- Definition search ---- */

.def-search {{
  border-radius: 10px !important;
  border: 1px solid var(--border) !important;
  padding: 0.55rem 0.8rem;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}}

.def-search:focus {{
  border-color: var(--rbc-blue) !important;
  box-shadow: 0 0 0 3px rgba(0, 81, 165, 0.1);
}}

/* ---- Empty state ---- */

.empty-state {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
}}

.empty-state .empty-icon {{
  margin-bottom: 1rem;
  opacity: 0.4;
}}

.empty-state .empty-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 0.35rem;
}}

.empty-state .empty-desc {{
  font-size: 0.9rem;
  color: var(--muted);
  max-width: 28rem;
  line-height: 1.5;
}}

</style>
"""

# ---------------------------------------------------------------------------
# SVG Icons (inline, no external assets)
# ---------------------------------------------------------------------------

_SHIELD_ICON_SVG = (
    '<svg class="hero-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" '
    f'stroke="{GOLD_BRIGHT}" stroke-width="1.5" fill="none"/>'
    '<path d="M12 6l-4 2.5v3c0 3.33 2.3 6.44 4 7.2 1.7-.76 4-3.87 4-7.2v-3L12 6z" '
    f'fill="{GOLD_BRIGHT}" fill-opacity="0.2" stroke="{GOLD_BRIGHT}" stroke-width="1"/>'
    "</svg>"
)

_CLIPBOARD_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<rect x="9" y="2" width="6" height="4" rx="1" stroke="currentColor" stroke-width="2"/>'
    '<path d="M9 4H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V6a2 2 0 00-2-2h-2" '
    'stroke="currentColor" stroke-width="2"/>'
    "</svg>"
)

_EMPTY_ICONS = {
    "document": (
        '<svg class="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" '
        f'stroke="{MUTED}" stroke-width="1.5"/>'
        f'<polyline points="14,2 14,8 20,8" stroke="{MUTED}" stroke-width="1.5"/>'
        f'<line x1="8" y1="13" x2="16" y2="13" stroke="{MUTED}" stroke-width="1.5"/>'
        f'<line x1="8" y1="17" x2="13" y2="17" stroke="{MUTED}" stroke-width="1.5"/>'
        "</svg>"
    ),
    "search": (
        '<svg class="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="11" cy="11" r="7" stroke="{MUTED}" stroke-width="1.5"/>'
        f'<line x1="16.5" y1="16.5" x2="21" y2="21" stroke="{MUTED}" stroke-width="1.5"/>'
        "</svg>"
    ),
    "report": (
        '<svg class="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M4 4h16v16H4z" stroke="{MUTED}" stroke-width="1.5" rx="2"/>'
        f'<line x1="8" y1="8" x2="16" y2="8" stroke="{MUTED}" stroke-width="1.5"/>'
        f'<line x1="8" y1="12" x2="16" y2="12" stroke="{MUTED}" stroke-width="1.5"/>'
        f'<line x1="8" y1="16" x2="12" y2="16" stroke="{MUTED}" stroke-width="1.5"/>'
        "</svg>"
    ),
}

# ---------------------------------------------------------------------------
# HTML helper functions
# ---------------------------------------------------------------------------


def hero_card(title: str, copy: str, eyebrow: str | None = None) -> str:
    """Render the app hero block."""
    eyebrow_markup = (
        f'<div class="hero-eyebrow">{_safe(eyebrow)}</div>' if eyebrow else ""
    )
    return (
        '<section class="hero-card">'
        f"{eyebrow_markup}"
        f'<h1 class="hero-title">{_SHIELD_ICON_SVG}{_safe(title)}</h1>'
        f'<p class="hero-copy">{_safe(copy)}</p>'
        "</section>"
    )


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


# ---------------------------------------------------------------------------
# NEW helper functions
# ---------------------------------------------------------------------------


def copy_button(target_id: str) -> str:
    """Return HTML for a copy button with inline SVG clipboard icon.

    Args:
        target_id: DOM id of the element whose text to copy.
    """
    return (
        f'<button class="copy-btn" data-copy-target="{_safe(target_id)}" '
        f'title="Copy to clipboard">'
        f"{_CLIPBOARD_ICON_SVG}"
        "</button>"
    )


def nav_item(section_number: int, title: str, anchor: str) -> str:
    """Quick-nav link for report TOC sidebar.

    Args:
        section_number: The section number (1-10).
        title: Section title text.
        anchor: The HTML anchor id to link to.
    """
    safe_anchor = _safe(anchor)
    scroll_js = f"parent.document.getElementById('{safe_anchor}')"
    scroll_js += "?.scrollIntoView({behavior:'smooth',block:'start'})"
    return (
        f'<a class="quick-nav-item" href="javascript:void(0)"'
        f' onclick="{scroll_js}">'
        f'<span class="nav-num">{section_number}</span>'
        f"<span>{_safe(title)}</span>"
        "</a>"
    )


def definition_card(term: str, definition_text: str) -> str:
    """Definition browser entry card.

    Args:
        term: The defined term.
        definition_text: The definition body text.
    """
    return (
        '<div class="def-card">'
        f'<div class="def-term">{_safe(term)}</div>'
        f'<div class="def-text">{_safe(definition_text)}</div>'
        "</div>"
    )


def empty_state(title: str, description: str, icon: str = "document") -> str:
    """Centered empty state placeholder with SVG icon.

    Args:
        title: Heading for the empty state.
        description: Explanatory text beneath the heading.
        icon: One of "document", "search", "report".
    """
    icon_svg = _EMPTY_ICONS.get(icon, _EMPTY_ICONS["document"])
    return (
        '<div class="empty-state">'
        f"{icon_svg}"
        f'<div class="empty-title">{_safe(title)}</div>'
        f'<div class="empty-desc">{_safe(description)}</div>'
        "</div>"
    )


# ---------------------------------------------------------------------------
# Citation / source rendering (logic preserved exactly)
# ---------------------------------------------------------------------------

# Matches [1], [2], etc. in body text
_INLINE_MARKER_RE = re.compile(r"\[(\d+)\]")


def render_citation_markers(body: str, citations: list[InlineCitation]) -> str:
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


def render_citation_footnotes(citations: list[InlineCitation]) -> str:
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
        return _safe(body)

    body_html = render_citation_markers(body, citations)
    footnotes_html = render_citation_footnotes(citations)
    return body_html + footnotes_html


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
