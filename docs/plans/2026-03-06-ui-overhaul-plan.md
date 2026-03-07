# UI Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the credit analyzer UI from a basic Streamlit app into a polished, premium RBC-branded banking tool with three new features (definitions browser, copy-to-clipboard, report quick-nav).

**Architecture:** The UI is a single Streamlit app (`app.py`) with a theme module (`credit_analyzer/ui/theme.py`) that provides all CSS and HTML helper functions. The overhaul rewrites theme.py with a new design system, restructures app.py layout and tabs, and adds a definitions browser tab, copy-to-clipboard JS utility, and report quick-nav.

**Tech Stack:** Streamlit, custom CSS/HTML injected via `st.markdown(unsafe_allow_html=True)`, JavaScript via `st.components.v1.html()` for clipboard.

**Reference:** See `docs/plans/2026-03-06-ui-overhaul-design.md` for color palette, typography, and design decisions.

---

### Task 1: Design System Foundation — Rewrite theme.py CSS

**Files:**
- Rewrite: `credit_analyzer/ui/theme.py` (lines 1-678 — the APP_CSS string and color constants)

**Context:** theme.py contains all CSS as a Python f-string (`APP_CSS`) plus color constants and HTML helper functions. This task rewrites ONLY the constants and CSS portion (lines 1-678). Helper functions are updated in Task 2.

**Step 1: Read the current theme.py to confirm structure**

Read `credit_analyzer/ui/theme.py` in full.

**Step 2: Rewrite color constants and APP_CSS**

Replace lines 1-678 with the new design system. Keep all existing Python function signatures unchanged — only modify the CSS string and color constants.

New color constants:
```python
# -- RBC Brand Palette (Refined) --
NAVY_DEEP = "#001A3E"
RBC_BLUE = "#0051A5"
RBC_BLUE_LIGHT = "#E8F0FE"
RBC_GOLD = "#C8A000"
GOLD_BRIGHT = "#D4AF37"
INK = "#0F1A2E"
MUTED = "#64748B"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FAFC"
BG = "#F1F5F9"
BORDER = "#E2E8F0"
```

New APP_CSS must include:
- Google Fonts import for DM Sans (400;500;600;700) and Source Sans 3 (400;500;600;700)
- CSS custom properties (`:root`) for all tokens
- Global styles: font-family Source Sans 3 for body, DM Sans for headings
- `.stApp` background: `BG` color with subtle noise texture via CSS gradient
- Sidebar: `NAVY_DEEP` background with subtle gradient, gold left-accent on active items
- `.block-container` max-width 1320px with refined padding
- Buttons: refined border-radius (10px), gold border accent on primary, smooth hover with `translateY(-1px)` and shadow transition (0.2s ease)
- File uploader / text inputs: clean 10px radius, subtle border, focus ring in RBC blue
- Tab bar: clean design with gold animated underline on active tab, smooth transitions
- Hero card: gradient from NAVY_DEEP to RBC_BLUE, subtle gold border, refined typography
- Metric cards: white surface, subtle shadow (`0 1px 3px rgba(0,0,0,0.08)`), left-accent border (3px solid RBC_BLUE), hover lift
- Panel cards: white surface, clean border, refined padding
- Rail cards (sidebar): translucent white on navy, gold left-accent for active state
- Report header: navy gradient with gold accent border, refined stats row
- Report sections: white cards with left-accent border (3px solid, color varies: blue for complete, gold for generating), hover shadow transition, refined section number badges
- Report body: Source Sans 3, refined heading/field/list styles
- Confidence pills: refined with subtle backgrounds — HIGH green, MEDIUM amber, LOW red
- Citation markers and footnotes: refined typography, subtle dividers
- Scrollbar styling for webkit: thin, navy-tinted
- All transitions: `transition: all 0.2s ease` on interactive elements
- Chat messages: refined spacing, subtle left-border on assistant messages
- New classes: `.copy-btn` (positioned absolute top-right of parent, small icon button, appears on hover of parent), `.quick-nav` (sticky sidebar for report TOC), `.def-card` (definitions browser entry), `.def-search` (search input for definitions)

**Step 3: Run existing tests to verify nothing breaks**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All tests pass (CSS changes don't affect backend logic)

**Step 4: Commit**

```bash
git add credit_analyzer/ui/theme.py
git commit -m "feat(ui): rewrite design system with refined RBC palette and typography"
```

---

### Task 2: Update HTML Helper Functions in theme.py

**Files:**
- Modify: `credit_analyzer/ui/theme.py` (helper functions: hero_card, metric_card, panel_card, rail_card, confidence_pill — lines 681-737)

**Context:** The helper functions generate HTML snippets used by app.py. Update them to use the new design system classes and add new helpers needed by later tasks.

**Step 1: Update existing helper functions**

Update `hero_card()` to include an RBC shield SVG icon (simple geometric shield shape in gold) and refined layout:
```python
def hero_card(title: str, copy: str, eyebrow: str | None = None) -> str:
    # Add inline SVG shield icon, refined typography classes
    # Keep same function signature
```

Update `metric_card()` to include left-accent border color parameter:
```python
def metric_card(label: str, value: str, caption: str, accent: str = "") -> str:
    # Add optional accent color for left border
    # Default accent uses RBC_BLUE
```

Update `rail_card()` to support an icon parameter for sidebar cards.

**Step 2: Add new helper functions**

Add `copy_button(target_id: str) -> str` — returns HTML for a copy-to-clipboard button (uses the `.copy-btn` CSS class). The button is an inline SVG clipboard icon.

Add `nav_item(section_number: int, title: str, anchor: str) -> str` — returns HTML for a quick-nav link item.

Add `definition_card(term: str, definition_text: str) -> str` — returns HTML for a definitions browser entry card.

Add `empty_state(title: str, description: str, icon: str = "document") -> str` — returns HTML for styled empty states with SVG icons (document, search, report).

**Step 3: Run tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add credit_analyzer/ui/theme.py
git commit -m "feat(ui): update HTML helpers and add copy button, nav, definition card components"
```

---

### Task 3: Clipboard JavaScript Utility

**Files:**
- Create: `credit_analyzer/ui/clipboard.py`

**Context:** Streamlit doesn't have native clipboard support. We inject a small JS snippet via `st.components.v1.html()` that listens for click events on `.copy-btn` elements and copies the text content of the sibling `.copy-target` element.

**Step 1: Write test for clipboard module**

Create `tests/test_clipboard.py`:
```python
"""Tests for clipboard utility HTML generation."""
from credit_analyzer.ui.clipboard import clipboard_js_snippet

def test_clipboard_js_returns_html():
    html = clipboard_js_snippet()
    assert "<script>" in html
    assert "clipboard" in html.lower() or "navigator.clipboard" in html

def test_clipboard_js_is_nonempty_string():
    html = clipboard_js_snippet()
    assert isinstance(html, str)
    assert len(html) > 50
```

**Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_clipboard.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement clipboard.py**

Create `credit_analyzer/ui/clipboard.py`:
```python
"""Clipboard integration for Streamlit via injected JavaScript."""

from __future__ import annotations


def clipboard_js_snippet() -> str:
    """Return an HTML/JS snippet that enables copy-to-clipboard buttons.

    Inject once per page via ``st.components.v1.html(snippet, height=0)``.
    Any element with class ``copy-btn`` will copy the ``data-copy-target``
    element's ``innerText`` to the clipboard on click, then briefly show
    a "Copied" tooltip.
    """
    return """
    <script>
    // Clipboard handler — runs in Streamlit iframe
    (function() {
        const root = parent.document;
        root.addEventListener('click', function(e) {
            const btn = e.target.closest('.copy-btn');
            if (!btn) return;
            const targetId = btn.getAttribute('data-copy-target');
            const target = root.getElementById(targetId);
            if (!target) return;
            const text = target.innerText || target.textContent;
            navigator.clipboard.writeText(text).then(function() {
                btn.classList.add('copied');
                btn.setAttribute('title', 'Copied!');
                setTimeout(function() {
                    btn.classList.remove('copied');
                    btn.setAttribute('title', 'Copy');
                }, 1500);
            });
        });
    })();
    </script>
    """
```

**Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_clipboard.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add credit_analyzer/ui/clipboard.py tests/test_clipboard.py
git commit -m "feat(ui): add clipboard JS utility for copy-to-clipboard buttons"
```

---

### Task 4: Definitions Browser Module

**Files:**
- Create: `credit_analyzer/ui/definitions_browser.py`
- Test: `tests/test_definitions_browser.py`

**Context:** The `DefinitionsIndex` (from `credit_analyzer/processing/definitions.py`) stores `definitions: dict[str, str]` mapping term names to definition text. It has `lookup(term)` and `find_terms_in_text(text)` methods. This module provides helpers to prepare definitions data for the UI tab.

**Step 1: Write tests**

Create `tests/test_definitions_browser.py`:
```python
"""Tests for definitions browser UI helpers."""
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.ui.definitions_browser import (
    filter_definitions,
    paginate_definitions,
)

def _sample_index() -> DefinitionsIndex:
    return DefinitionsIndex(definitions={
        "Consolidated EBITDA": "means, for any period, Consolidated Net Income plus...",
        "Borrower": "means Holdings LLC, a Delaware limited liability company.",
        "Applicable Rate": "means the applicable percentage per annum set forth below...",
        "Net Income": "means the net income of the Borrower and its Subsidiaries...",
    })

def test_filter_definitions_no_query():
    idx = _sample_index()
    result = filter_definitions(idx, "")
    assert len(result) == 4

def test_filter_definitions_with_query():
    idx = _sample_index()
    result = filter_definitions(idx, "ebitda")
    assert len(result) == 1
    assert result[0][0] == "Consolidated EBITDA"

def test_filter_definitions_case_insensitive():
    idx = _sample_index()
    result = filter_definitions(idx, "BORROWER")
    assert len(result) == 1

def test_filter_definitions_partial_match():
    idx = _sample_index()
    result = filter_definitions(idx, "net")
    assert len(result) == 2  # "Consolidated EBITDA" won't match, but "Net Income" and definition text matches

def test_filter_returns_sorted():
    idx = _sample_index()
    result = filter_definitions(idx, "")
    terms = [r[0] for r in result]
    assert terms == sorted(terms)

def test_paginate_definitions():
    items = [(f"Term {i}", f"Def {i}") for i in range(25)]
    page = paginate_definitions(items, page=0, per_page=10)
    assert len(page) == 10
    assert page[0] == ("Term 0", "Def 0")

def test_paginate_definitions_last_page():
    items = [(f"Term {i}", f"Def {i}") for i in range(25)]
    page = paginate_definitions(items, page=2, per_page=10)
    assert len(page) == 5
```

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_definitions_browser.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement definitions_browser.py**

Create `credit_analyzer/ui/definitions_browser.py`:
```python
"""Helpers for the Definitions Browser tab."""

from __future__ import annotations

from credit_analyzer.processing.definitions import DefinitionsIndex


def filter_definitions(
    index: DefinitionsIndex,
    query: str,
) -> list[tuple[str, str]]:
    """Filter and sort definitions by search query.

    Searches both term names and definition text (case-insensitive).
    Returns list of (term, definition_text) tuples sorted alphabetically by term.
    """
    query_lower = query.strip().lower()
    results: list[tuple[str, str]] = []
    for term, definition in sorted(index.definitions.items()):
        if not query_lower:
            results.append((term, definition))
        elif query_lower in term.lower() or query_lower in definition.lower():
            results.append((term, definition))
    return results


def paginate_definitions(
    items: list[tuple[str, str]],
    page: int = 0,
    per_page: int = 20,
) -> list[tuple[str, str]]:
    """Return a single page of definitions."""
    start = page * per_page
    return items[start : start + per_page]
```

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_definitions_browser.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add credit_analyzer/ui/definitions_browser.py tests/test_definitions_browser.py
git commit -m "feat(ui): add definitions browser filter and pagination helpers"
```

---

### Task 5: Restructure app.py — Sidebar and Header

**Files:**
- Modify: `app.py` (lines 50-276 — page config, main function, sidebar)

**Context:** This task updates the page config, hero section, and sidebar layout. The sidebar gets better visual hierarchy with sections for Model Status, Active Document, and Document Management. Import the new clipboard module.

**Step 1: Read current app.py**

Read `app.py` in full to confirm current structure.

**Step 2: Update imports and page config**

Add imports:
```python
import streamlit.components.v1 as components
from credit_analyzer.ui.clipboard import clipboard_js_snippet
```

Update `st.set_page_config`:
```python
st.set_page_config(
    page_title="Credit Agreement Analyzer | RBC",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

After `st.markdown(APP_CSS, ...)`, inject clipboard JS:
```python
components.html(clipboard_js_snippet(), height=0)
```

**Step 3: Update hero card call**

Change the hero card in `main()` to use an eyebrow badge:
```python
st.markdown(
    hero_card(
        title="Credit Agreement Analyzer",
        copy="Extract key terms, explore definitions, and generate structured reports from credit agreements.",
        eyebrow="RBC Leveraged Finance",
    ),
    unsafe_allow_html=True,
)
```

**Step 4: Update tab list to include Definitions**

Change the tabs line to add the 4th tab:
```python
tab_documents, tab_chat, tab_definitions, tab_report = st.tabs(
    ["Documents", "Ask Questions", "Definitions", "Full Report"]
)
```

Add the definitions tab rendering (placeholder — filled in Task 7):
```python
with tab_definitions:
    _render_definitions_tab(active_document)
```

Add a stub function:
```python
def _render_definitions_tab(active_document: ProcessedDocument | None) -> None:
    if active_document is None:
        st.info("Index a document to browse its defined terms.")
        return
    st.caption(f"Definitions from {active_document.display_name}")
```

**Step 5: Refine the sidebar**

Update `_render_sidebar` to have clearer sections:
- Add `st.markdown("---")` dividers between sections
- Use `st.caption` for section labels ("MODEL STATUS", "ACTIVE DOCUMENT") in uppercase
- Keep the rail_card usage but the new CSS from Task 1 will style them

**Step 6: Run tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 7: Commit**

```bash
git add app.py
git commit -m "feat(ui): restructure app layout with 4 tabs, refined sidebar, clipboard injection"
```

---

### Task 6: Redesign Documents and Chat Tabs

**Files:**
- Modify: `app.py` (lines 283-616 — `_render_document_tab`, `_render_document_summary`, `_render_chat_tab`, `_render_chat_message`)

**Context:** The Documents tab gets improved stats dashboard and upload flow. The Chat tab gets refined message styling, better suggested questions layout, and copy buttons on assistant responses.

**Step 1: Update Documents tab**

In `_render_document_tab`:
- Use `empty_state()` helper for the "no document" view instead of plain panel_card
- Keep the upload flow but improve the column ratio to `[1.0, 1.2]`

In `_render_document_summary`:
- Keep the 4 metric cards but pass accent colors: Pages (blue), Sections (blue), Definitions (gold — to hint at the new Definitions tab), Chunks (blue)
- Add a `st.divider()` between metrics and detail section

**Step 2: Update Chat tab**

In `_render_chat_tab`:
- Wrap suggested questions in a container with `st.container()` and use key `suggested-actions` for CSS targeting
- Improve the header layout

In `_render_chat_message`:
- For assistant messages, wrap the answer in a div with a unique ID (`id="answer-{hash}"`) and add a copy button using `copy_button()` helper from theme.py
- Keep all existing citation rendering logic unchanged

In `_run_pending_chat_question`:
- Same update: wrap final rendered answer in a copy-target div with copy button

**Step 3: Run tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat(ui): redesign documents and chat tabs with copy buttons and refined layout"
```

---

### Task 7: Definitions Browser Tab

**Files:**
- Modify: `app.py` (replace the stub `_render_definitions_tab` from Task 5)

**Context:** This renders the Definitions tab using the helpers from Task 4. The `DefinitionsIndex` is available via `active_document.definitions_index`. Display a search box, result count, and paginated definition cards.

**Step 1: Implement `_render_definitions_tab`**

```python
def _render_definitions_tab(active_document: ProcessedDocument | None) -> None:
    if active_document is None:
        st.markdown(
            empty_state(
                "No Document Loaded",
                "Index a credit agreement to browse its defined terms.",
                icon="search",
            ),
            unsafe_allow_html=True,
        )
        return

    from credit_analyzer.ui.definitions_browser import filter_definitions

    defs_index = active_document.definitions_index
    total_terms = len(defs_index.definitions)

    header_col, search_col = st.columns([0.6, 0.4])
    with header_col:
        st.markdown(
            panel_card(
                "Defined Terms",
                f"{total_terms} terms parsed from the definitions section.",
            ),
            unsafe_allow_html=True,
        )
    with search_col:
        search_query = st.text_input(
            "Search definitions",
            placeholder="e.g. EBITDA, Applicable Rate, Borrower...",
            key="def-search",
        )

    filtered = filter_definitions(defs_index, search_query)

    if search_query:
        st.caption(f"{len(filtered)} of {total_terms} terms match '{search_query}'")

    if not filtered:
        st.info("No definitions match your search.")
        return

    # Render in 2-column grid
    ITEMS_PER_PAGE = 20
    page_count = (len(filtered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    # Simple pagination via session state
    page_key = "def_page"
    st.session_state.setdefault(page_key, 0)
    # Reset to page 0 when search changes
    if search_query != st.session_state.get("def_last_query", ""):
        st.session_state[page_key] = 0
        st.session_state["def_last_query"] = search_query

    current_page = st.session_state[page_key]
    start = current_page * ITEMS_PER_PAGE
    page_items = filtered[start : start + ITEMS_PER_PAGE]

    for term, definition_text in page_items:
        # Truncate long definitions for display, with expander for full text
        preview = definition_text[:300]
        is_truncated = len(definition_text) > 300

        st.markdown(
            definition_card(term, preview + ("..." if is_truncated else "")),
            unsafe_allow_html=True,
        )
        if is_truncated:
            with st.expander(f"Full definition of {term}"):
                st.write(definition_text)

    # Pagination controls
    if page_count > 1:
        nav_cols = st.columns([1, 2, 1])
        with nav_cols[0]:
            if current_page > 0 and st.button("Previous", key="def-prev"):
                st.session_state[page_key] = current_page - 1
                st.rerun()
        with nav_cols[1]:
            st.caption(f"Page {current_page + 1} of {page_count}")
        with nav_cols[2]:
            if current_page < page_count - 1 and st.button("Next", key="def-next"):
                st.session_state[page_key] = current_page + 1
                st.rerun()
```

**Step 2: Add `definition_card` import to app.py imports**

Update the import from `credit_analyzer.ui.theme` to include `definition_card` and `empty_state`.

**Step 3: Run tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat(ui): implement definitions browser tab with search and pagination"
```

---

### Task 8: Report Tab Redesign with Quick-Nav

**Files:**
- Modify: `app.py` (lines 623-803 — `_render_report_tab`, `_render_report`, `_render_report_section`)

**Context:** The report tab gets a sticky quick-navigation sidebar and copy buttons on each section. Report sections get anchor IDs for jump-links.

**Step 1: Update `_render_report` to include quick-nav**

Wrap the report rendering in a two-column layout:
```python
def _render_report(report: GeneratedReport) -> None:
    # ... existing report header and PDF download button ...

    # Quick-nav sidebar + report content
    nav_col, content_col = st.columns([0.22, 0.78], gap="medium")

    with nav_col:
        st.markdown('<div class="quick-nav">', unsafe_allow_html=True)
        st.markdown('<div class="quick-nav-title">SECTIONS</div>', unsafe_allow_html=True)
        for section in report.sections:
            tone = "complete" if section.status == "complete" else "error"
            st.markdown(
                nav_item(section.section_number, section.title, f"section-{section.section_number}"),
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with content_col:
        for section in report.sections:
            _render_report_section(section)
```

**Step 2: Update `_render_report_section` to include anchors and copy buttons**

Add an anchor div at the top of each section for jump-links:
```html
<div id="section-{section_number}"></div>
```

Wrap the section body in a `copy-target` div and add a copy button:
```python
body_id = f"section-body-{section.section_number}"
# In the section HTML, add:
# <div id="{body_id}" class="copy-target">...body...</div>
# <button class="copy-btn" data-copy-target="{body_id}" title="Copy">...svg...</button>
```

**Step 3: Add `nav_item` import to app.py imports**

Update the import from `credit_analyzer.ui.theme` to include `nav_item`.

**Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 5: Commit**

```bash
git add app.py
git commit -m "feat(ui): redesign report tab with quick-nav sidebar and copy buttons"
```

---

### Task 9: Visual Polish and Integration Testing

**Files:**
- Modify: `credit_analyzer/ui/theme.py` (minor CSS tweaks)
- Modify: `app.py` (minor layout adjustments)

**Context:** Final polish pass. Run the app, check visual consistency, fix any spacing/alignment issues, ensure all transitions are smooth.

**Step 1: Run all tests**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 2: Run linter**

Run: `.venv/Scripts/python -m ruff check .`
Fix any issues.

**Step 3: Run type checker**

Run: `.venv/Scripts/python -m pyright`
Fix any type errors in modified files.

**Step 4: Visual review checklist**

Verify in the running app (`streamlit run app.py`):
- [ ] Hero card renders with new typography and gold eyebrow badge
- [ ] Sidebar has deep navy background with gold accent lines
- [ ] Model status card shows correctly
- [ ] Tabs have gold underline on active tab
- [ ] Documents tab: upload flow works, metric cards show accent borders
- [ ] Chat tab: suggested questions render in grid, copy buttons appear on answers
- [ ] Definitions tab: search works, cards render, pagination works
- [ ] Report tab: quick-nav sidebar shows section links, copy buttons work on sections
- [ ] Confidence pills show correct colors (green/amber/red)
- [ ] All transitions are smooth (hover, focus, active states)
- [ ] No visual regressions on existing functionality

**Step 5: Fix any issues found**

Address spacing, alignment, color, or transition issues discovered during visual review.

**Step 6: Run full test suite one final time**

Run: `.venv/Scripts/python -m pytest tests/ -x -q`
Expected: All pass

**Step 7: Final commit**

```bash
git add -A
git commit -m "feat(ui): final polish pass for UI overhaul"
```

---

## Task Dependency Graph

```
Task 1 (CSS) ──────┐
                    ├──> Task 5 (App Structure) ──> Task 6 (Docs/Chat) ──> Task 8 (Report) ──> Task 9 (Polish)
Task 2 (Helpers) ──┘                                      │
                                                           │
Task 3 (Clipboard) ───────────────────────────────────────┘
                                                           │
Task 4 (Definitions) ──────────────────────> Task 7 (Def Tab) ──────────────────────> Task 9
```

**Parallelizable:** Tasks 1+2 (same file but different sections), Tasks 3+4 (independent modules)
**Sequential:** Tasks 5-9 must run in order as they build on each other in app.py
