"""Theme helpers for the Streamlit demo app."""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from credit_analyzer.generation.response_parser import InlineCitation, SourceCitation
    from credit_analyzer.processing.definitions import DefinitionsIndex


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

NAVY_DEEP = "#003DA5"  # RBC Capital Markets blue
RBC_BLUE = "#003DA5"
RBC_BLUE_DEEP = "#003DA5"
RBC_BLUE_LIGHT = "#E8F0FE"
RBC_GOLD = "#FFD100"  # RBC yellow from logo
GOLD_BRIGHT = "#FFD100"
INK = "#0F1A2E"
MUTED = "#64748B"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFC"
BG = "#E8ECF1"
BORDER = "#E2E8F0"

# ---------------------------------------------------------------------------
# APP_CSS — full design system
# ---------------------------------------------------------------------------

CHAT_BG = "#F0F0F0"

# URL-encoded SVG data URIs for sidebar button icons (Feather-style, 16px).
_IC = (
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' "
    "viewBox='0 0 24 24' fill='none' stroke='%231A1A1A' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'%3E"
)
_ICON_NEW_CHAT = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpath d='M12 20h9'/%3E"
    "%3Cpath d='M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z'/%3E"
    "%3C/svg%3E"
)
_ICON_DEFS = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpath d='M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z'/%3E"
    "%3Cpath d='M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z'/%3E"
    "%3C/svg%3E"
)
_ICON_REPORT = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpath d='M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z'/%3E"
    "%3Cpolyline points='14 2 14 8 20 8'/%3E"
    "%3Cline x1='16' y1='13' x2='8' y2='13'/%3E"
    "%3Cline x1='16' y1='17' x2='8' y2='17'/%3E"
    "%3Cpolyline points='10 9 9 9 8 9'/%3E"
    "%3C/svg%3E"
)
_ICON_GUIDE = (
    f"data:image/svg+xml,{_IC}"
    "%3Ccircle cx='12' cy='12' r='10'/%3E"
    "%3Cpolygon points='16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76'/%3E"
    "%3C/svg%3E"
)
_ICON_REMOVE = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpolyline points='3 6 5 6 21 6'/%3E"
    "%3Cpath d='M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4"
    "a2 2 0 012-2h4a2 2 0 012 2v2'/%3E"
    "%3C/svg%3E"
)
# View Report — eye icon
_ICON_VIEW_REPORT = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpath d='M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z'/%3E"
    "%3Ccircle cx='12' cy='12' r='3'/%3E"
    "%3C/svg%3E"
)
# New Report — file-plus icon
_ICON_NEW_REPORT = (
    f"data:image/svg+xml,{_IC}"
    "%3Cpath d='M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z'/%3E"
    "%3Cpolyline points='14 2 14 8 20 8'/%3E"
    "%3Cline x1='12' y1='18' x2='12' y2='12'/%3E"
    "%3Cline x1='9' y1='15' x2='15' y2='15'/%3E"
    "%3C/svg%3E"
)
# Discard — X-circle icon
_ICON_DISCARD = (
    f"data:image/svg+xml,{_IC}"
    "%3Ccircle cx='12' cy='12' r='10'/%3E"
    "%3Cline x1='15' y1='9' x2='9' y2='15'/%3E"
    "%3Cline x1='9' y1='9' x2='15' y2='15'/%3E"
    "%3C/svg%3E"
)

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
  --chat-bg: {CHAT_BG};
  --header-height: 0rem;
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

/* ---- App shell — light gray main, dark sidebar ---- */

.stApp {{
  background: {CHAT_BG};
  color: var(--ink);
}}

[data-testid="stHeader"] {{
  background: {CHAT_BG};
  height: 0 !important;
  min-height: 0 !important;
  padding: 0 !important;
}}

/* Keep the sidebar reopen button visible even when header is collapsed */
[data-testid="stSidebarCollapsedControl"] {{
  display: flex !important;
  visibility: visible !important;
}}

/* ---- Sidebar (light gray) ---- */

[data-testid="stSidebar"] {{
  background: #E5E5E5;
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  top: 0 !important;
}}

[data-testid="stSidebar"] * {{
  color: #1A1A1A;
}}

[data-testid="stSidebar"] .block-container {{
  padding-top: 0.8rem !important;
  background: transparent;
}}

/* Tighten sidebar spacing to prevent scroll */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
  gap: 0.15rem !important;
}}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div > div {{
  margin-bottom: 0.08rem !important;
}}

[data-testid="stSidebar"] hr {{
  margin: 0.5rem 0 !important;
}}

[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaption"] {{
  margin-bottom: 0.25rem !important;
  font-size: 0.68rem !important;
}}

/* Minimal sidebar scroll — auto only if needed */
section[data-testid="stSidebar"] > div[data-testid="stSidebarContent"] {{
  overflow-x: hidden !important;
  padding: 0 !important;
  margin: 0 !important;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{
  min-height: 0 !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: 0 !important;
}}

/* Remove all top spacing from sidebar user content */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
  padding-top: 0.8rem !important;
  margin-top: 0 !important;
}}

/* Collapse empty nav element that reserves space at top of sidebar */
[data-testid="stSidebarNav"] {{
  display: none !important;
}}

/* Float the close button out of flow so it doesn't push content down */
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {{
  position: absolute !important;
  top: 0.5rem !important;
  right: 0.5rem !important;
  z-index: 100;
  height: auto !important;
}}

/* Sidebar text alignment */
[data-testid="stSidebar"] [data-testid="stMarkdown"],
[data-testid="stSidebar"] .stMarkdown {{
  text-align: left;
}}

/* ---- Layout ---- */

.block-container {{
  max-width: 820px;
  padding-top: 0;
  padding-bottom: 2.5rem;
  background: transparent;
}}

/* Main content — light gray, start at viewport top like sidebar */
[data-testid="stMain"] {{
  background: {CHAT_BG};
  top: 0 !important;
}}

[data-testid="stMain"] > .block-container {{
  background: transparent;
  padding-top: 1.5rem;
}}

/* Bottom bar / chat input area */
[data-testid="stBottom"] {{
  background: {CHAT_BG};
  border-top: none;
}}

[data-testid="stBottom"] > div {{
  max-width: 820px;
  margin: 0 auto;
  padding-bottom: 0.75rem;
  position: relative;
}}

/* Chat input bar — like ChatGPT / Claude */
[data-testid="stChatInput"] {{
  background: {SURFACE} !important;
  border: 1px solid {BORDER} !important;
  border-radius: 24px !important;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
}}

[data-testid="stChatInput"] textarea {{
  color: #1A1A1A !important;
}}

[data-testid="stChatInput"]:focus-within {{
  border-color: var(--border) !important;
  box-shadow: none !important;
  outline: none !important;
}}

/* Send button — navy box with white up-arrow */
[data-testid="stChatInput"] button[kind="primary"],
[data-testid="stChatInput"] button {{
  background: {NAVY_DEEP} !important;
  color: white !important;
  border-radius: 8px !important;
  border: none !important;
  position: relative !important;
  overflow: hidden !important;
}}

/* Hide the original SVG icon completely */
[data-testid="stChatInput"] button svg {{
  display: none !important;
}}

/* Render a CSS up-arrow instead */
[data-testid="stChatInput"] button::after {{
  content: '' !important;
  display: block !important;
  width: 8px !important;
  height: 8px !important;
  border-top: 2.5px solid white !important;
  border-right: 2.5px solid white !important;
  transform: rotate(-45deg) !important;
  margin-top: 3px !important;
}}

/* ---- Stop-generating button — styled as gold send-button replacement ---- */

/* Hide stop button in its original DOM position (JS moves it into the chat input) */
.st-key-stop-chat-generation {{
  display: none !important;
}}

/* When relocated inside the chat input container, show it */
[data-testid="stChatInput"] .st-key-stop-chat-generation {{
  display: block !important;
  position: absolute !important;
  right: 0.45rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  z-index: 10 !important;
  width: auto !important;
  margin: 0 !important;
  padding: 0 !important;
}}

[data-testid="stChatInput"] {{
  position: relative !important;
}}

.st-key-stop-chat-generation button {{
  background: {RBC_GOLD} !important;
  color: {INK} !important;
  border: none !important;
  border-radius: 8px !important;
  width: 36px !important;
  height: 36px !important;
  min-height: 36px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 14px !important;
  line-height: 1 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12) !important;
  transition: background 0.15s ease !important;
  cursor: pointer !important;
}}

.st-key-stop-chat-generation button:hover {{
  background: #E6BC00 !important;
  transform: none !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
}}

.st-key-stop-chat-generation button p {{
  font-size: 14px !important;
  line-height: 1 !important;
  margin: 0 !important;
  padding: 0 !important;
}}

/* Hide the chat input's own send button when input is disabled (stop button replaces it) */
[data-testid="stChatInput"]:has(textarea[disabled]) button[kind="primary"] {{
  visibility: hidden !important;
}}

/* ---- Edit-prompt button — subtle inline action ---- */

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [class*="st-key-edit-prompt"] {{
  opacity: 0;
  transition: opacity 0.2s ease;
}}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]):hover [class*="st-key-edit-prompt"] {{
  opacity: 1;
}}

[class*="st-key-edit-prompt"] button {{
  background: transparent !important;
  border: none !important;
  color: {MUTED} !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  padding: 0.15rem 0.5rem !important;
  min-height: unset !important;
  box-shadow: none !important;
  cursor: pointer !important;
}}

[class*="st-key-edit-prompt"] button:hover {{
  color: {NAVY_DEEP} !important;
  background: rgba(0, 61, 165, 0.06) !important;
  border-radius: 6px !important;
  transform: none !important;
  box-shadow: none !important;
}}

[class*="st-key-edit-prompt"] button p {{
  font-size: 0.78rem !important;
  color: inherit !important;
}}

/* ---- Prompt editor panel ---- */

[class*="st-key-save-edit"] button[kind="primary"] {{
  font-size: 0.82rem !important;
  min-height: 2.2rem !important;
  padding: 0.35rem 1rem !important;
}}

[class*="st-key-cancel-edit"] button {{
  font-size: 0.82rem !important;
  min-height: 2.2rem !important;
  padding: 0.35rem 1rem !important;
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
  border-color: var(--rbc-blue);
}}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {{
  border-color: var(--rbc-blue);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 61, 165, 0.12);
}}

/* Suggestion cards — centered grid */
.st-key-suggested-actions div[data-testid="stButton"] > button {{
  min-height: 4rem;
  height: 100%;
  align-items: center;
  justify-content: center;
  text-align: center;
  white-space: normal;
  border: 1px solid {BORDER};
  border-radius: 12px;
  background: {SURFACE};
}}

.st-key-suggested-actions div[data-testid="stButton"] > button p {{
  white-space: normal;
  line-height: 1.3;
  color: var(--ink);
}}

/* Sidebar buttons — text-only, hover shows rounded highlight */
[data-testid="stSidebar"] div[data-testid="stButton"] > button,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button {{
  background: transparent;
  border: none;
  color: #1A1A1A !important;
  box-shadow: none;
  text-align: left;
  justify-content: flex-start;
  font-weight: 500;
  padding: 0.35rem 0.75rem;
  border-radius: 8px;
  min-height: 2rem;
  transition: background 0.15s ease;
}}

/* Force left alignment on ALL inner elements of sidebar buttons */
[data-testid="stSidebar"] div[data-testid="stButton"] > button * {{
  text-align: left !important;
  justify-content: flex-start !important;
}}

[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button * {{
  text-align: left !important;
  justify-content: flex-start !important;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
[data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button:hover {{
  background: rgba(0, 0, 0, 0.08);
  border: none;
  transform: none;
  box-shadow: none;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button:active {{
  background: rgba(0, 0, 0, 0.12);
}}

/* Sidebar action button icons — inline SVG via CSS */
.st-key-new-chat button p::before,
.st-key-open-defs button p::before,
.st-key-gen-report button p::before,
.st-key-view-report button p::before,
.st-key-new-report button p::before,
.st-key-open-guide button p::before,
.st-key-remove-doc button p::before {{
  content: "";
  display: inline-block;
  width: 16px;
  height: 16px;
  margin-right: 6px;
  vertical-align: -2px;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 0.7;
}}

/* New Chat — pen-on-square icon */
.st-key-new-chat button p::before {{
  background-image: url("{_ICON_NEW_CHAT}");
}}

/* Definitions — book-open icon */
.st-key-open-defs button p::before {{
  background-image: url("{_ICON_DEFS}");
}}

/* Generate Report — file-text icon */
.st-key-gen-report button p::before {{
  background-image: url("{_ICON_REPORT}");
}}

/* View Report — eye icon */
.st-key-view-report button p::before {{
  background-image: url("{_ICON_VIEW_REPORT}");
}}

/* New Report — file-plus icon */
.st-key-new-report button p::before {{
  background-image: url("{_ICON_NEW_REPORT}");
}}

/* Guide — compass icon */
.st-key-open-guide button p::before {{
  background-image: url("{_ICON_GUIDE}");
}}

/* Remove Document — trash icon */
.st-key-remove-doc button p::before {{
  background-image: url("{_ICON_REMOVE}");
}}

/* Discard report — small icon-only button */
.st-key-discard-report button {{
  padding: 0.25rem 0.4rem !important;
  min-height: 2rem !important;
  min-width: 2rem !important;
  width: 2rem !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}}

.st-key-discard-report button p {{
  display: none !important;
}}

.st-key-discard-report button::after {{
  content: "";
  display: block;
  width: 16px;
  height: 16px;
  background-image: url("{_ICON_DISCARD}");
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 0.5;
}}

.st-key-discard-report button:hover::after {{
  opacity: 0.85;
}}

/* ---- Inline section picker (sidebar) ---- */

.section-picker-container {{
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  padding: 0.5rem 0.6rem 0.3rem;
  margin: 0.15rem 0;
}}

.section-picker-header {{
  font-size: 0.68rem;
  font-weight: 600;
  color: {MUTED};
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}}

/* Disabled sidebar buttons — fade icons too */
[data-testid="stSidebar"] div[data-testid="stButton"] > button:disabled p::before {{
  opacity: 0.35;
}}

/* Index PDF button — navy, white text, no outline */
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {{
  background: var(--navy-deep) !important;
  color: white !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  font-weight: 600;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] p {{
  text-align: center !important;
  color: white !important;
}}

[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {{
  background: #002952 !important;
  box-shadow: none !important;
}}

/* File uploader in sidebar — compact */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {{
  background: white !important;
  border-color: rgba(0, 0, 0, 0.12) !important;
  padding: 0.5rem !important;
}}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
  background: white;
  color: #1A1A1A !important;
  border: 1px solid rgba(0, 0, 0, 0.12);
  padding: 0.2rem 0.5rem !important;
  min-height: 1.8rem !important;
  font-size: 0.8rem !important;
}}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {{
  background: rgba(0, 0, 0, 0.04);
  border-color: var(--rbc-blue);
}}

[data-testid="stSidebar"] [data-testid="stFileUploader"] small {{
  color: #6B7280 !important;
  font-size: 0.68rem !important;
}}

/* ---- Inputs ---- */

[data-testid="stFileUploader"] section,
[data-testid="stTextInputRootElement"] {{
  border-radius: 10px;
  border-color: var(--border);
  background: {SURFACE};
  transition: all 0.2s ease;
}}

[data-testid="stFileUploader"] section:focus-within,
[data-testid="stTextInputRootElement"]:focus-within {{
  border-color: var(--rbc-blue);
  box-shadow: 0 0 0 3px rgba(0, 81, 165, 0.12);
}}

[data-testid="stChatInput"] textarea::placeholder {{
  color: #9CA3AF !important;
  opacity: 1 !important;
}}

[data-testid="stSidebar"] [data-baseweb="select"] > div {{
  background: white;
  border-color: rgba(0, 0, 0, 0.12);
}}

[data-testid="stSidebar"] [data-baseweb="select"] * {{
  color: #1A1A1A !important;
  fill: #1A1A1A !important;
}}

/* ---- Chat area ---- */

.chat-welcome {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 45vh;
  text-align: center;
  padding: 2rem;
}}

.chat-welcome-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: {INK};
  margin-bottom: 0.5rem;
}}

.chat-welcome-desc {{
  font-size: 0.95rem;
  color: {MUTED};
  max-width: 24rem;
  line-height: 1.5;
}}

.suggestions-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.65rem;
  max-width: 800px;
  margin: 0 auto 2rem auto;
  padding: 0 1rem;
}}

.suggestion-card {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 0.85rem 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  font-size: 0.88rem;
  font-weight: 500;
  color: {INK};
  line-height: 1.35;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}}

.suggestion-card:hover {{
  border-color: {RBC_BLUE};
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,81,165,0.1);
}}

/* Suggestion buttons on the light background */
.st-key-suggested-actions div[data-testid="stButton"] > button {{
  background: {SURFACE};
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}}

/* Context strip below assistant messages */
.context-strip {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  font-size: 0.78rem;
  color: {MUTED};
  cursor: pointer;
  transition: all 0.15s ease;
}}

.context-strip:hover {{
  color: {RBC_BLUE};
}}

.context-strip .ctx-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}}

.ctx-dot-high {{ background: #059669; }}
.ctx-dot-medium {{ background: #D97706; }}
.ctx-dot-low {{ background: #DC2626; }}

.msg-timestamp {{
  font-size: 0.72rem;
  color: {MUTED};
  opacity: 0.6;
  margin-top: 0.25rem;
}}

/* Streaming status line */
.stream-status {{
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0;
  font-size: 0.82rem;
  color: {RBC_BLUE};
  font-weight: 500;
}}

.stream-status .pulse-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {RBC_BLUE};
  animation: pulse 1.5s ease-in-out infinite;
}}

@keyframes pulse {{
  0%, 100% {{ opacity: 0.4; transform: scale(0.9); }}
  50% {{ opacity: 1; transform: scale(1.1); }}
}}

/* ---- Indexing step pipeline ---- */

.step-pipeline {{
  padding: 0.5rem 0;
}}

.step-item {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0;
  font-size: 0.82rem;
  line-height: 1.3;
}}

.step-item .step-icon {{
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 0.7rem;
}}

.step-complete .step-icon {{ color: #059669; }}
.step-active .step-icon {{ color: {RBC_BLUE}; }}
.step-active .step-icon .pulse-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: {RBC_BLUE};
  animation: pulse 1.5s ease-in-out infinite;
}}
.step-pending {{ opacity: 0.45; }}

.step-label {{ flex: 1; }}
.step-count {{
  color: {MUTED};
  font-size: 0.78rem;
  font-weight: 500;
}}

.stats-grid-compact {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.25rem;
  padding: 0.25rem 0;
}}

.stat-item-compact {{
  padding: 0.2rem 0.4rem;
  border-radius: 6px;
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.08);
}}

.stat-item-compact .stat-value {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
}}

.stat-item-compact .stat-label {{
  font-size: 0.62rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
}}

/* ---- Document card (sidebar, loaded state) ---- */

.doc-card {{
  background: white;
  border: 1px solid var(--border);
  border-left: 3px solid {RBC_GOLD};
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  margin-bottom: 0.25rem;
}}

.doc-card-name {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--ink);
  line-height: 1.3;
  word-break: break-word;
}}

.doc-card-stats {{
  font-size: 0.72rem;
  color: var(--muted);
  margin-top: 0.2rem;
  line-height: 1.4;
}}

.doc-card-source {{
  font-size: 0.65rem;
  color: #9CA3AF;
  margin-top: 0.3rem;
  word-break: break-all;
  line-height: 1.3;
}}

/* ---- Skeleton loaders ---- */

.skeleton-line {{
  height: 0.85rem;
  border-radius: 4px;
  background: linear-gradient(90deg, {BORDER} 25%, {SURFACE_ALT} 50%, {BORDER} 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  margin-bottom: 0.5rem;
}}

.skeleton-line:last-child {{ width: 60%; }}

@keyframes shimmer {{
  0% {{ background-position: 200% 0; }}
  100% {{ background-position: -200% 0; }}
}}

/* ---- Definitions modal ---- */

.def-modal-search {{
  margin-bottom: 0.75rem;
}}

.def-modal-count {{
  font-size: 0.8rem;
  color: {MUTED};
  padding: 0.25rem 0 0.5rem 0;
}}

.def-modal-list {{
  max-height: 55vh;
  overflow-y: auto;
}}

/* ---- Report dialog ---- */

.report-dialog-header {{
  padding-bottom: 0.75rem;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 0.75rem;
}}

.report-dialog-borrower {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 1.4rem;
  font-weight: 700;
  color: {INK};
  margin: 0;
}}

.report-dialog-meta {{
  font-size: 0.85rem;
  color: {MUTED};
  margin: 0.15rem 0 0 0;
}}

.report-nav-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.report-nav-dot-complete {{ background: #059669; }}
.report-nav-dot-generating {{ background: {RBC_BLUE}; animation: pulse 1.5s ease-in-out infinite; }}
.report-nav-dot-pending {{ background: {BORDER}; }}

.section-skeleton {{
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-left: 3px solid {BORDER};
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.75rem;
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
  padding: 0.45rem 0.65rem;
  border-radius: 8px;
  background: white;
  border: 1px solid rgba(0, 0, 0, 0.08);
  margin-bottom: 0.25rem;
  transition: all 0.2s ease;
}}

.rail-card.is-ready {{
  border-left: 3px solid {RBC_GOLD};
}}

.rail-card.is-warning {{
  border-left: 3px solid #D97706;
}}

.rail-label {{
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.75;
}}

.rail-value {{
  margin-top: 0.1rem;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 0.88rem;
  font-weight: 700;
}}

.rail-meta {{
  margin-top: 0.1rem;
  font-size: 0.75rem;
  line-height: 1.25;
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
  border: 1px solid rgba(255, 209, 0, 0.3);
  box-shadow: 0 8px 28px rgba(0, 61, 165, 0.15);
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
  border: 1px solid rgba(255, 209, 0, 0.2);
}}

.report-stat-gold {{
  background: rgba(255, 209, 0, 0.15);
  border-color: rgba(255, 209, 0, 0.45);
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
  overflow: visible;
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

/* Section refresh button — small circular arrow */
.section-refresh-icon {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 6px;
  cursor: pointer;
  color: var(--muted);
  margin-right: 0.3rem;
  flex-shrink: 0;
  transition: all 0.15s ease;
}}

.section-refresh-icon:hover {{
  color: var(--rbc-blue);
  background: var(--rbc-blue-light);
}}

.report-section-body {{
  padding: 0.9rem 1.1rem 1rem 1.1rem;
  position: relative;
  overflow: visible;
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

.rb-heading {{
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

.rb-heading:first-child {{
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

/* Tables */
.report-body table.rb-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.88rem;
}}

.report-body table.rb-table th {{
  background: var(--surface-alt);
  font-weight: 700;
  text-align: left;
  padding: 0.45rem 0.65rem;
  border: 1px solid var(--border);
  font-size: 0.82rem;
  color: var(--navy-deep);
}}

.report-body table.rb-table td {{
  padding: 0.4rem 0.65rem;
  border: 1px solid var(--border);
  line-height: 1.45;
  vertical-align: top;
}}

.report-body table.rb-table tr:nth-child(even) td {{
  background: rgba(248, 250, 252, 0.5);
}}

/* Tables in chat answers */
.section-answer table.rb-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.88rem;
}}

.section-answer table.rb-table th {{
  background: var(--surface-alt);
  font-weight: 700;
  text-align: left;
  padding: 0.45rem 0.65rem;
  border: 1px solid var(--border);
  font-size: 0.82rem;
  color: var(--navy-deep);
}}

.section-answer table.rb-table td {{
  padding: 0.4rem 0.65rem;
  border: 1px solid var(--border);
  line-height: 1.45;
  vertical-align: top;
}}

.section-answer table.rb-table tr:nth-child(even) td {{
  background: rgba(248, 250, 252, 0.5);
}}

/* Lists and paragraphs in chat answers */
.section-answer .rb-para {{
  margin: 0.35rem 0;
}}
.section-answer ul.rb-list {{
  margin: 0.3rem 0 0.3rem 1.2rem;
  padding: 0;
}}
.section-answer ul.rb-list li {{
  margin-bottom: 0.2rem;
}}
.section-answer ol.rb-list {{
  margin: 0.3rem 0 0.3rem 1.2rem;
  padding: 0;
}}
.section-answer ol.rb-list li {{
  margin-bottom: 0.2rem;
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
  padding: 0.55rem 1.1rem;
  border-top: 1px solid var(--border);
  background: var(--surface-alt);
  border-radius: 0 0 12px 12px;
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

/* ---- Chat messages (ChatGPT / Claude style) ---- */

[data-testid="stChatMessage"] {{
  background: transparent;
  border-radius: 0;
  padding: 1.25rem 0;
  margin-bottom: 0;
  box-shadow: none;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  max-width: 820px;
}}

/* User message — light yellow background box */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
  background: rgba(255, 209, 0, 0.08) !important;
  border-radius: 12px !important;
  padding: 1rem 1.25rem !important;
  margin-bottom: 0.5rem !important;
  border: 1px solid rgba(255, 209, 0, 0.18) !important;
  border-bottom: 1px solid rgba(255, 209, 0, 0.18) !important;
}}

/* Chat avatar colors — gold for user, navy for assistant */
[data-testid="stChatMessageAvatarUser"] {{
  background: {GOLD_BRIGHT} !important;
  border-radius: 50%;
}}

[data-testid="stChatMessageAvatarAssistant"] {{
  background: {NAVY_DEEP} !important;
  border-radius: 50%;
}}

/* White outline icons on avatars */
[data-testid="stChatMessageAvatarUser"] svg,
[data-testid="stChatMessageAvatarAssistant"] svg {{
  color: white !important;
  fill: white !important;
  stroke: white !important;
}}

[data-testid="stChatMessageAvatarUser"] svg path,
[data-testid="stChatMessageAvatarAssistant"] svg path {{
  fill: white !important;
  stroke: white !important;
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

.def-card .def-header {{
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}}

.def-card .def-term {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--rbc-blue);
  margin-bottom: 0;
}}

.def-card .def-page {{
  font-size: 0.72rem;
  color: var(--muted);
  background: var(--ghost);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  white-space: nowrap;
}}

.def-card .def-text {{
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--ink);
}}

.def-card .def-text .rb-para {{
  margin-bottom: 0.3rem;
}}

.def-card .def-text ul.rb-list,
.def-card .def-text ol.rb-list {{
  margin: 0.25rem 0 0.25rem 1.2rem;
  padding: 0;
}}

.def-card .def-text ul.rb-list li,
.def-card .def-text ol.rb-list li {{
  margin-bottom: 0.15rem;
}}

/* ---- Definition term highlights ---- */

.def-hl {{
  color: var(--rbc-blue);
  border-bottom: 1px dotted var(--rbc-blue);
  cursor: pointer;
  position: relative;
  display: inline;
}}

.def-hl:hover {{
  color: #0060C0;
  border-bottom-style: solid;
}}

/* Remove default focus outline */
.def-hl:focus {{
  outline: none;
}}

/* Show tooltip preview on hover (non-interactive) */
.def-hl:hover > .def-tip {{
  display: block;
  pointer-events: none;
}}

/* Pin tooltip on click via focus (interactive, scrollable) */
.def-hl:focus > .def-tip {{
  display: block !important;
  pointer-events: auto !important;
}}

/* Tooltip: hidden by default */
.def-hl .def-tip {{
  display: none;
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 300px;
  max-width: 80vw;
  padding: 0.6rem 0.8rem;
  background: #F0F0F0;
  color: #1A1A1A;
  border: 2px solid var(--rbc-blue);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  font-size: 0.82rem;
  line-height: 1.45;
  z-index: 9999;
  pointer-events: none;
  text-align: left;
  font-weight: normal;
}}

/* Pinned via click — stays open, interactive, scrollable */
.def-hl-active > .def-tip {{
  display: block !important;
  pointer-events: auto !important;
}}

.def-tip-term {{
  display: block;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--rbc-blue);
  margin-bottom: 0.2rem;
  padding-right: 1.2rem;
}}

.def-tip-meta {{
  display: block;
  font-size: 0.75rem;
  color: var(--muted);
  margin-bottom: 0.3rem;
}}

.def-tip-text {{
  display: block;
  color: #1A1A1A;
  font-size: 0.8rem;
  line-height: 1.4;
  max-height: 150px;
  overflow-y: auto;
  word-wrap: break-word;
  overflow-wrap: break-word;
  padding-right: 0.25rem;
}}

/* Scrollbar styling for tooltip */
.def-tip-text::-webkit-scrollbar {{
  width: 4px;
}}
.def-tip-text::-webkit-scrollbar-thumb {{
  background: rgba(0, 61, 165, 0.3);
  border-radius: 2px;
}}

/* Close button inside tooltip */
.def-tip-close {{
  position: absolute;
  top: 0.35rem;
  right: 0.35rem;
  width: 1.2rem;
  height: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1;
  background: transparent;
  border: none;
  transition: all 0.15s ease;
  z-index: 1;
}}

.def-tip-close:hover {{
  color: var(--ink);
  background: rgba(0, 0, 0, 0.08);
}}

/* Suppress any nested definition highlights inside tooltips */
.def-tip .def-hl {{
  color: inherit !important;
  border-bottom: none !important;
  cursor: default !important;
}}

.def-tip .def-hl .def-tip {{
  display: none !important;
}}

/* Arrow pointing down (tooltip above term) */
.def-tip::before {{
  content: '';
  position: absolute;
  top: 100%;
  left: 1rem;
  border: 6px solid transparent;
  border-top-color: {RBC_BLUE};
}}

/* Invisible bridge between term and tooltip to prevent hover gap */
.def-tip::after {{
  content: '';
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  height: 8px;
}}

/* Ensure tooltip containers don't clip */
.section-answer,
.report-section-body,
[data-testid="stChatMessage"] {{
  overflow: visible !important;
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

/* ---- Guide: quick-start cards + dialog sections ---- */

.quick-start-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1rem 1rem;
  text-align: center;
  height: 100%;
}}

.quick-start-number {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background: var(--rbc-blue);
  color: #fff;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}}

.quick-start-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--ink);
  margin-bottom: 0.3rem;
}}

.quick-start-desc {{
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.45;
}}

.guide-section {{
  margin-bottom: 1.25rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}}

.guide-section:last-child {{
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}}

.guide-section-title {{
  font-family: 'DM Sans', system-ui, sans-serif;
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--rbc-blue);
  margin-bottom: 0.5rem;
}}

.guide-section-body {{
  font-family: 'Source Sans 3', system-ui, sans-serif;
  font-size: 0.88rem;
  color: var(--ink);
  line-height: 1.55;
}}

.guide-section-body p {{
  margin: 0 0 0.5rem 0;
}}

.guide-section-body ul, .guide-section-body ol {{
  margin: 0.25rem 0 0.5rem 1.25rem;
  padding: 0;
}}

.guide-section-body li {{
  margin-bottom: 0.25rem;
}}

.guide-section-body table {{
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}}

.guide-section-body th {{
  font-weight: 600;
  border-bottom: 1px solid var(--border);
}}

/* Guide dialog navigation */
[class*="st-key-guide-nav-"] div[data-testid="stButton"] > button {{
  justify-content: flex-start;
  text-align: left;
  min-height: 2.05rem;
  padding: 0.35rem 0.55rem;
  border-radius: 8px;
  box-shadow: none;
}}

[class*="st-key-guide-nav-"] div[data-testid="stButton"] > button:hover {{
  transform: none;
  box-shadow: none;
}}

.st-key-guide-prev div[data-testid="stButton"] > button,
.st-key-guide-next div[data-testid="stButton"] > button {{
  min-height: 2.2rem;
  border-radius: 999px;
  padding: 0.2rem;
  font-weight: 700;
}}

/* ---- Scroll-to-top button ---- */

.scroll-top-btn {{
  position: fixed;
  bottom: 5.5rem;
  right: 1.5rem;
  z-index: 999;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: {RBC_BLUE};
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.18);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}}

.scroll-top-btn.visible {{
  opacity: 1;
  pointer-events: auto;
}}

.scroll-top-btn:hover {{
  background: {NAVY_DEEP};
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}}

</style>
"""

# ---------------------------------------------------------------------------
# SVG Icons (inline, no external assets)
# ---------------------------------------------------------------------------

_SEARCH_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>'
    '<line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2"/>'
    '</svg>'
)

_CHECK_ICON_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'xmlns="http://www.w3.org/2000/svg">'
    '<polyline points="20,6 9,17 4,12" stroke="currentColor" stroke-width="2.5" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '</svg>'
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
    return (
        f'<a class="quick-nav-item" data-scroll-target="{safe_anchor}">'
        f'<span class="nav-num">{section_number}</span>'
        f"<span>{_safe(title)}</span>"
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
        f'<div class="quick-start-number">{_safe(number)}</div>'
        f'<div class="quick-start-title">{_safe(title)}</div>'
        f'<div class="quick-start-desc">{description}</div>'
        '</div>'
    )


def guide_section_block(title: str, body_html: str) -> str:
    """Render a section block for the full guide dialog."""
    return (
        '<div class="guide-section">'
        f'<div class="guide-section-title">{_safe(title)}</div>'
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
        f'<span>{_safe(sections_used)}</span>'
        f'<span>&middot;</span>'
        f'<span>{duration_seconds:.1f}s</span>'
        '</div>'
    )


def stream_status(label: str) -> str:
    """Render the animated streaming status line."""
    return (
        '<div class="stream-status">'
        '<span class="pulse-dot"></span>'
        f'<span>{_safe(label)}</span>'
        '</div>'
    )


def message_timestamp(time_str: str) -> str:
    """Render a subtle timestamp below a chat message."""
    return f'<div class="msg-timestamp">{_safe(time_str)}</div>'


def indexing_step(label: str, status: str, count: str = "") -> str:
    """Render one step in the indexing pipeline.

    Args:
        label: Step description (e.g. "Extracting text").
        status: One of "complete", "active", "pending".
        count: Optional result count (e.g. "42 pages").
    """
    if status == "complete":
        icon_html = f'<span class="step-icon">{_CHECK_ICON_SVG}</span>'
        cls = "step-complete"
    elif status == "active":
        icon_html = '<span class="step-icon"><span class="pulse-dot"></span></span>'
        cls = "step-active"
    else:
        icon_html = '<span class="step-icon" style="color:var(--muted);">&#9675;</span>'
        cls = "step-pending"

    count_html = f'<span class="step-count">{_safe(count)}</span>' if count else ""
    return (
        f'<div class="step-item {cls}">'
        f'{icon_html}'
        f'<span class="step-label">{_safe(label)}</span>'
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
        f'<div class="doc-card-name">{_safe(filename)}</div>'
        f'<div class="doc-card-stats">{stats_line}</div>'
        f'<div class="doc-card-source">{_safe(source_path)}</div>'
        '</div>'
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
            if _TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buffer.clear()
            return
        parts.append('<table class="rb-table">')
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{_safe(cell)}</th>")
        parts.append("</tr></thead>")
        if len(rows) > 1:
            parts.append("<tbody>")
            for row in rows[1:]:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{_safe(cell)}</td>")
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
        if _TABLE_ROW_RE.match(stripped) or _TABLE_SEP_RE.match(stripped):
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
        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append(bullet_match.group(1))
            continue

        # Numbered item
        num_match = _NUMBERED_RE.match(stripped)
        if num_match and not _HEADING_RE.match(stripped):
            flush_bullets()
            numbered_buffer.append(num_match.group(2))
            continue

        flush_bullets()
        flush_numbered()

        if _HEADING_RE.match(stripped) and len(stripped) > 3:
            parts.append(f'<div class="rb-heading">{_safe(stripped)}</div>')
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
    r"^(?:\d+\.\s+)?([A-Z][A-Z0-9 /&,\-()]+?)(?:\s*\[[\d,\s]+\])?$"
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

# Table row: contains at least 2 pipe separators (at least 3 cells).
# Handles "| col1 | col2 |", "| col1 | col2", and "col1 | col2 | col3".
_TABLE_ROW_RE = re.compile(
    r"^\|[^|]+\|.+"           # starts with |  e.g. "| A | B |"
    r"|"
    r"^[^|\n]+\|[^|\n]+\|"   # no leading |, 2+ pipes  e.g. "A | B | C"
    r"|"
    r"^[^|\n]+\s\|\s[^|\n]+" # no leading |, 1 pipe with spaces  e.g. "A | B"
)

# Table separator row: "| --- | --- |" or "|---|---|" or "--- | --- | ---"
_TABLE_SEP_RE = re.compile(r"^\|?[\s:]*-{2,}[\s:]*(\|[\s:]*-{2,}[\s:]*)+\|?\s*$")


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
            if _TABLE_SEP_RE.match(row_line):
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
            return f'<span class="rb-not-found">{_safe(stripped_val)}</span>'
        if inline_citations:
            return render_citation_markers(stripped_val, inline_citations)
        return _safe(stripped_val)

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flush_numbered()
            flush_table()
            continue

        # Table row detection
        if _TABLE_ROW_RE.match(stripped) or _TABLE_SEP_RE.match(stripped):
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
            if _TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            table_buffer.clear()
            return
        parts.append('<table class="rb-table">')
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{_safe(cell)}</th>")
        parts.append("</tr></thead>")
        if len(rows) > 1:
            parts.append("<tbody>")
            for row in rows[1:]:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{_safe(cell)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        table_buffer.clear()

    def flush_bullets() -> None:
        if bullet_buffer:
            parts.append('<ul class="rb-list">')
            for text in bullet_buffer:
                parts.append(f"<li>{_safe(text)}</li>")
            parts.append("</ul>")
            bullet_buffer.clear()

    def flush_numbered() -> None:
        if numbered_buffer:
            parts.append('<ol class="rb-list">')
            for text in numbered_buffer:
                parts.append(f"<li>{_safe(text)}</li>")
            parts.append("</ol>")
            numbered_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flush_numbered()
            flush_table()
            continue

        if _TABLE_ROW_RE.match(stripped) or _TABLE_SEP_RE.match(stripped):
            flush_bullets()
            flush_numbered()
            table_buffer.append(stripped)
            continue
        if table_buffer:
            flush_table()

        # Bullet item
        bullet_match = _BULLET_RE.match(stripped)
        if bullet_match:
            flush_numbered()
            bullet_buffer.append(bullet_match.group(1))
            continue

        # Numbered item — but NOT all-caps numbered headings like "1. OVERVIEW"
        num_match = _NUMBERED_RE.match(stripped)
        if num_match and not _HEADING_RE.match(stripped):
            flush_bullets()
            numbered_buffer.append(num_match.group(2))
            continue

        flush_bullets()
        flush_numbered()

        if _HEADING_RE.match(stripped) and len(stripped) > 3:
            parts.append(f'<div class="rb-heading">{_safe(stripped)}</div>')
        else:
            parts.append(f'<div class="rb-para">{_safe(stripped)}</div>')

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
        plain_def_text = re.sub(r"<[^>]+>", "", _safe(entry.text))
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


def stop_button_relocate_script() -> str:
    """Return a JS snippet that moves the stop button inside the chat input container.

    Streamlit renders the stop button as a sibling below the chat input in a
    deeply nested DOM.  CSS alone can't reliably overlay it on the send button,
    so this script physically relocates the element into ``[data-testid="stChatInput"]``
    where CSS ``position: absolute`` works correctly.
    """
    return """<script>
(function() {
    var doc = parent.document;
    var stopBtn = doc.querySelector('.st-key-stop-chat-generation');
    var chatInput = doc.querySelector('[data-testid="stChatInput"]');
    if (stopBtn && chatInput && !chatInput.contains(stopBtn)) {
        chatInput.appendChild(stopBtn);
    }
})();
</script>"""
