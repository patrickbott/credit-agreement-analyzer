"""Getting Started guide dialog using @st.dialog."""

from __future__ import annotations

import streamlit as st

from credit_analyzer.ui.guide_content import GUIDE_SECTIONS
from credit_analyzer.ui.theme import guide_section_block

_GUIDE_INDEX_KEY = "_guide_active_section_index"


def _set_guide_index(index: int) -> None:
    max_index = max(len(GUIDE_SECTIONS) - 1, 0)
    st.session_state[_GUIDE_INDEX_KEY] = min(max(index, 0), max_index)


@st.dialog("Getting Started", width="large")
def show_guide_dialog() -> None:
    """Render the guide as a paged walkthrough with left-side navigation."""
    if not GUIDE_SECTIONS:
        st.info("Guide content is not available.")
        return

    current_index = int(st.session_state.get(_GUIDE_INDEX_KEY, 0))
    _set_guide_index(current_index)
    current_index = int(st.session_state[_GUIDE_INDEX_KEY])

    nav_col, content_col = st.columns([0.34, 0.66], gap="large")

    with nav_col:
        st.markdown("#### Sections")
        for idx, (title, _body_html) in enumerate(GUIDE_SECTIONS):
            prefix = ">>" if idx == current_index else ""
            if st.button(
                f"{prefix} {idx + 1}. {title}".strip(),
                key=f"guide-nav-{idx}",
                use_container_width=True,
                type="primary" if idx == current_index else "secondary",
            ):
                _set_guide_index(idx)
                st.rerun(scope="fragment")
        st.caption(f"Section {current_index + 1} of {len(GUIDE_SECTIONS)}")

    with content_col:
        prev_col, body_col, next_col = st.columns([1, 8, 1], gap="small")
        with prev_col:
            if st.button(
                "<-",
                key="guide-prev",
                use_container_width=True,
                disabled=current_index <= 0,
            ):
                _set_guide_index(current_index - 1)
                st.rerun(scope="fragment")

        with body_col:
            title, body_html = GUIDE_SECTIONS[current_index]
            st.markdown(guide_section_block(title, body_html), unsafe_allow_html=True)

        with next_col:
            if st.button(
                "->",
                key="guide-next",
                use_container_width=True,
                disabled=current_index >= len(GUIDE_SECTIONS) - 1,
            ):
                _set_guide_index(current_index + 1)
                st.rerun(scope="fragment")
