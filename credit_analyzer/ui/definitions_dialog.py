"""Definitions search dialog using @st.dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from credit_analyzer.ui.definitions_browser import filter_definitions
from credit_analyzer.ui.theme import definition_card

if TYPE_CHECKING:
    from credit_analyzer.processing.definitions import DefinitionsIndex

_MAX_DISPLAY = 30
_PREVIEW_LENGTH = 300


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
        preview = definition_text[:_PREVIEW_LENGTH]
        is_truncated = len(definition_text) > _PREVIEW_LENGTH
        st.markdown(
            definition_card(term, preview + ("\u2026" if is_truncated else "")),
            unsafe_allow_html=True,
        )
        if is_truncated:
            with st.expander(f"Full definition of \u201c{term}\u201d"):
                st.write(definition_text)

    if remaining > 0:
        st.caption(
            f"Showing {_MAX_DISPLAY} of {len(filtered)} results."
            " Refine your search to see more."
        )
