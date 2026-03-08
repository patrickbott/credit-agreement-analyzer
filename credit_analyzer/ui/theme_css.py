"""APP_CSS — full design-system stylesheet for the Streamlit app."""

from __future__ import annotations

from credit_analyzer.ui.theme_constants import (
    BG,
    BORDER,
    CHAT_BG,
    CHIP_ICON_CITE,
    CHIP_ICON_COMMENTARY,
    CHIP_ICON_DISMISS,
    CHIP_ICON_THINKING,
    GOLD_BRIGHT,
    ICON_DEFS,
    ICON_DISCARD,
    ICON_GUIDE,
    ICON_NEW_CHAT,
    ICON_NEW_REPORT,
    ICON_REMOVE,
    ICON_REPORT,
    ICON_VIEW_REPORT,
    INK,
    MUTED,
    NAVY_DEEP,
    RBC_BLUE,
    RBC_BLUE_DEEP,
    RBC_BLUE_LIGHT,
    RBC_GOLD,
    SURFACE,
    SURFACE_ALT,
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
  display: flex !important;
  flex-direction: column !important;
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

/* ---- Stop-generating button — rendered inside streaming chat message ---- */

.st-key-stop-chat-generation {{
  text-align: center;
  margin-top: 0.5rem;
}}

.st-key-stop-chat-generation button {{
  background: {RBC_GOLD} !important;
  color: {INK} !important;
  border: none !important;
  border-radius: 20px !important;
  padding: 0.3rem 1rem !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  min-height: unset !important;
  height: auto !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12) !important;
  transition: background 0.15s ease !important;
  cursor: pointer !important;
}}

.st-key-stop-chat-generation button:hover {{
  background: #E6BC00 !important;
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
  background-image: url("{ICON_NEW_CHAT}");
}}

/* Definitions — book-open icon */
.st-key-open-defs button p::before {{
  background-image: url("{ICON_DEFS}");
}}

/* Generate Report — file-text icon */
.st-key-gen-report button p::before {{
  background-image: url("{ICON_REPORT}");
}}

/* View Report — eye icon */
.st-key-view-report button p::before {{
  background-image: url("{ICON_VIEW_REPORT}");
}}

/* New Report — file-plus icon */
.st-key-new-report button p::before {{
  background-image: url("{ICON_NEW_REPORT}");
}}

/* Guide — compass icon */
.st-key-open-guide button p::before {{
  background-image: url("{ICON_GUIDE}");
}}

/* Remove Document — trash icon */
.st-key-remove-doc button p::before {{
  background-image: url("{ICON_REMOVE}");
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
  background-image: url("{ICON_DISCARD}");
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 0.5;
}}

.st-key-discard-report button:hover::after {{
  opacity: 0.85;
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

/* ---- Chat option chips (near chat input bar) ---- */
/* JS moves .st-key-chips-on before the chat input and .st-key-chips-off
   after it inside [data-testid="stBottom"] > div.  Centering, sidebar
   offset, and max-width are inherited from stBottom automatically.
   All inner divs are flattened with display:contents so buttons become
   direct flex items of their container. */

/* Hide leftover containers from previous code versions */
.st-key-chips-bar,
.st-key-chip-on, .st-key-chip-off,
.st-key-chat-chips-on, .st-key-chat-chips-off,
.st-key-chips-active, .st-key-chips-inactive,
.st-key-chips-above, .st-key-chips-below,
.st-key-chips-on, .st-key-chips-off {{
  display: none !important;
}}

/* Hidden until JS moves it into stBottom */
.st-key-chat-chips {{
  display: none !important;
}}

/* Shown once inside stBottom — centered row of chips */
[data-testid="stBottom"] .st-key-chat-chips {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
  padding: 0.0rem 0 3.6rem 0;
}}

/* Flatten ALL inner wrapper divs so buttons become flex items */
.st-key-chat-chips div {{
  display: contents !important;
}}

/* ---- Chip button shared base ---- */
.st-key-chat-chips button {{
  display: inline-flex !important;
  align-items: center;
  border-radius: 999px !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  padding: 0.25rem 0.75rem !important;
  min-height: unset !important;
  line-height: 1.4 !important;
  box-shadow: none !important;
  cursor: pointer !important;
  transition: all 0.15s ease;
  width: auto !important;
}}

.st-key-chat-chips button p {{
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  margin: 0 !important;
}}

/* OFF state — outlined */
.st-key-chat-chips [class*="st-key-chip-"][class*="-off"] button {{
  background: {SURFACE} !important;
  border: 1px solid {BORDER} !important;
  color: {MUTED} !important;
}}

.st-key-chat-chips [class*="st-key-chip-"][class*="-off"] button:hover {{
  border-color: {NAVY_DEEP} !important;
  color: {NAVY_DEEP} !important;
  background: rgba(0, 61, 165, 0.04) !important;
}}

.st-key-chat-chips [class*="st-key-chip-"][class*="-off"] button p {{
  color: {MUTED} !important;
}}

.st-key-chat-chips [class*="st-key-chip-"][class*="-off"] button:hover p {{
  color: {NAVY_DEEP} !important;
}}

/* ON state — solid blue */
.st-key-chat-chips [class*="st-key-chip-"][class*="-on"] button {{
  background: {NAVY_DEEP} !important;
  border: 1px solid {NAVY_DEEP} !important;
  color: white !important;
}}

.st-key-chat-chips [class*="st-key-chip-"][class*="-on"] button:hover {{
  background: #002D7A !important;
  border-color: #002D7A !important;
}}

.st-key-chat-chips [class*="st-key-chip-"][class*="-on"] button p {{
  color: white !important;
}}

/* ---- Chip icons via CSS ::before ---- */

.st-key-chat-chips button p::before {{
  content: "";
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 5px;
  vertical-align: -2px;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
}}

/* Extended Thinking — OFF */
.st-key-chip-thinking-off button p::before {{
  background-image: url("{CHIP_ICON_THINKING}");
  opacity: 0.5;
}}

.st-key-chip-thinking-off button:hover p::before {{
  opacity: 0.8;
}}

/* Extended Thinking — ON */
.st-key-chip-thinking-on button p::before {{
  background-image: url("{CHIP_ICON_DISMISS}");
  opacity: 1;
  filter: brightness(0) invert(1);
}}

/* Cite Sources — OFF */
.st-key-chip-cite-off button p::before {{
  background-image: url("{CHIP_ICON_CITE}");
  opacity: 0.5;
}}

.st-key-chip-cite-off button:hover p::before {{
  opacity: 0.8;
}}

/* Cite Sources — ON */
.st-key-chip-cite-on button p::before {{
  background-image: url("{CHIP_ICON_DISMISS}");
  opacity: 1;
  filter: brightness(0) invert(1);
}}

/* Commentary — OFF */
.st-key-chip-commentary-off button p::before {{
  background-image: url("{CHIP_ICON_COMMENTARY}");
  opacity: 0.5;
}}

.st-key-chip-commentary-off button:hover p::before {{
  opacity: 0.8;
}}

/* Commentary — ON */
.st-key-chip-commentary-on button p::before {{
  background-image: url("{CHIP_ICON_DISMISS}");
  opacity: 1;
  filter: brightness(0) invert(1);
}}

</style>
"""

__all__ = ["APP_CSS"]
