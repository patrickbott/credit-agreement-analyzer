"""Definitions search dialog using @st.dialog."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import streamlit as st

from credit_analyzer.ui.definitions_browser import filter_definitions
from credit_analyzer.ui.theme import format_chat_answer, highlight_defined_terms

if TYPE_CHECKING:
    from credit_analyzer.processing.definitions import DefinitionsIndex

_MAX_DISPLAY = 30
_PREVIEW_LENGTH = 300


def _definition_card_rich(
    term: str,
    body_html: str,
    page_number: int | None = None,
) -> str:
    """Build a rich definition card with formatted body and page metadata.

    Args:
        term: The defined term name.
        body_html: Pre-formatted HTML body (from format_chat_answer).
        page_number: Optional page number for the term.
    """
    page_badge = ""
    if page_number is not None:
        page_badge = f'<span class="def-page">p.&thinsp;{page_number}</span>'

    return (
        '<div class="def-card">'
        '<div class="def-header">'
        f'<div class="def-term">{escape(term)}</div>'
        f"{page_badge}"
        "</div>"
        f'<div class="def-text">{body_html}</div>'
        "</div>"
    )


@st.dialog("Search Defined Terms", width="medium")
def show_definitions_dialog(defs_index: DefinitionsIndex) -> None:
    """Render a searchable definitions modal."""
    total = len(defs_index.definitions)

    query = st.text_input(
        "Search",
        placeholder="e.g. EBITDA, Applicable Rate, Borrower...",
        key="def-dialog-search",
        label_visibility="collapsed",
    )

    filtered = filter_definitions(defs_index, query)

    if query:
        st.caption(f"{len(filtered)} of {total} terms match '{query}'")
    else:
        st.caption(f"{total} defined terms")

    if not filtered:
        st.info("No definitions match your search.")
        return

    display_items = filtered[:_MAX_DISPLAY]
    remaining = len(filtered) - _MAX_DISPLAY

    for term, definition_text in display_items:
        entry = defs_index.lookup_entry(term)
        page_number = entry.page_number if entry else None

        preview = definition_text[:_PREVIEW_LENGTH]
        is_truncated = len(definition_text) > _PREVIEW_LENGTH
        if is_truncated:
            preview += "\u2026"

        # Format preview with rich markdown rendering (lists, paragraphs, etc.)
        preview_html = format_chat_answer(preview)
        # Highlight cross-references to other defined terms with tooltips
        preview_html = highlight_defined_terms(preview_html, defs_index)

        st.markdown(
            _definition_card_rich(term, preview_html, page_number),
            unsafe_allow_html=True,
        )
        if is_truncated:
            with st.expander(f"Full definition of \u201c{term}\u201d"):
                full_html = format_chat_answer(definition_text)
                full_html = highlight_defined_terms(full_html, defs_index)
                st.markdown(
                    f'<div class="def-text">{full_html}</div>',
                    unsafe_allow_html=True,
                )

    if remaining > 0:
        st.caption(
            f"Showing {_MAX_DISPLAY} of {len(filtered)} results."
            " Refine your search to see more."
        )
