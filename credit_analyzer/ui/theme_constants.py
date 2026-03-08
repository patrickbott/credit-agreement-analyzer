"""Theme constants — colors, icons, design tokens, and regex patterns."""

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

# Chat chip icons (14px)
_CIC = (
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' "
    "viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'%3E"
)
# Extended Thinking — clock/stopwatch icon
_CHIP_ICON_THINKING = (
    f"data:image/svg+xml,{_CIC}"
    "%3Ccircle cx='12' cy='12' r='10'/%3E"
    "%3Cpolyline points='12 6 12 12 16 14'/%3E"
    "%3C/svg%3E"
)
# X icon for dismissing active chip
_CHIP_ICON_DISMISS = (
    f"data:image/svg+xml,{_CIC}"
    "%3Cline x1='18' y1='6' x2='6' y2='18'/%3E"
    "%3Cline x1='6' y1='6' x2='18' y2='18'/%3E"
    "%3C/svg%3E"
)
# Cite Sources — bookmark icon
_CHIP_ICON_CITE = (
    f"data:image/svg+xml,{_CIC}"
    "%3Cpath d='M6 2h12a2 2 0 0 1 2 2v16l-8-4-8 4V4a2 2 0 0 1 2-2z'/%3E"
    "%3C/svg%3E"
)
# Commentary — lightbulb icon
_CHIP_ICON_COMMENTARY = (
    f"data:image/svg+xml,{_CIC}"
    "%3Cpath d='M9 18h6'/%3E"
    "%3Cpath d='M10 22h4'/%3E"
    "%3Cpath d='M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z'/%3E"
    "%3C/svg%3E"
)

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
# Regex patterns used by formatters
# ---------------------------------------------------------------------------

# Matches [1], [2], etc. in body text
_INLINE_MARKER_RE = re.compile(r"\[(\d+)\]")

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


__all__ = [
    # Helper
    "_safe",
    # Colors
    "NAVY_DEEP",
    "RBC_BLUE",
    "RBC_BLUE_DEEP",
    "RBC_BLUE_LIGHT",
    "RBC_GOLD",
    "GOLD_BRIGHT",
    "INK",
    "MUTED",
    "SURFACE",
    "SURFACE_ALT",
    "BG",
    "BORDER",
    "CHAT_BG",
    # Data-URI icons (sidebar buttons)
    "_IC",
    "_ICON_NEW_CHAT",
    "_ICON_DEFS",
    "_ICON_REPORT",
    "_ICON_GUIDE",
    "_ICON_REMOVE",
    "_ICON_VIEW_REPORT",
    "_ICON_NEW_REPORT",
    "_ICON_DISCARD",
    # Data-URI icons (chat chips)
    "_CIC",
    "_CHIP_ICON_THINKING",
    "_CHIP_ICON_DISMISS",
    "_CHIP_ICON_CITE",
    "_CHIP_ICON_COMMENTARY",
    # Inline SVG icons
    "_SEARCH_ICON_SVG",
    "_CHECK_ICON_SVG",
    "_CLIPBOARD_ICON_SVG",
    "_EMPTY_ICONS",
    # Regex patterns
    "_INLINE_MARKER_RE",
    "_HEADING_RE",
    "_FIELD_RE",
    "_NUMBERED_RE",
    "_BULLET_RE",
    "_TABLE_ROW_RE",
    "_TABLE_SEP_RE",
]
