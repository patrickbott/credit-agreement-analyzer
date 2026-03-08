# Chat Input Chips: Cite Sources & Commentary — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Cite Sources and Commentary toggle chips alongside Extended Thinking in the chat input bar, with corresponding prompt addendums in the QA engine.

**Architecture:** Two new prompt addendum constants in `prompts.py`, two new keyword args on `QAEngine.ask()`/`ask_stream()`, two new `st.button` chips in `app.py`, and matching CSS rules in `theme.py`. Follows the exact same pattern already established by `deep_analysis` and `CONCISE_ADDENDUM`.

**Tech Stack:** Python, Streamlit, CSS, SVG icons

---

### Task 1: Add prompt addendums (`prompts.py`)

**Files:**
- Modify: `credit_analyzer/generation/prompts.py:83-89` (after `CONCISE_ADDENDUM`)
- Test: `tests/test_qa_engine.py`

**Step 1: Write failing tests**

Add to `tests/test_qa_engine.py`:

```python
from credit_analyzer.generation.prompts import (
    CITE_SOURCES_ADDENDUM,
    COMMENTARY_ADDENDUM,
)


class TestPromptAddendums:
    """Tests for Cite Sources and Commentary prompt addendums."""

    def test_cite_sources_addendum_exists(self) -> None:
        assert len(CITE_SOURCES_ADDENDUM) > 50
        assert "section" in CITE_SOURCES_ADDENDUM.lower()

    def test_commentary_addendum_exists(self) -> None:
        assert len(COMMENTARY_ADDENDUM) > 50
        assert "commentary" in COMMENTARY_ADDENDUM.lower()

    def test_commentary_addendum_is_optional(self) -> None:
        """Commentary should instruct the LLM that it's optional, not required."""
        lower = COMMENTARY_ADDENDUM.lower()
        assert "omit" in lower or "only when" in lower or "if relevant" in lower or "do not" in lower
```

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py::TestPromptAddendums -v`
Expected: FAIL — `CITE_SOURCES_ADDENDUM` not found in `prompts.py`

**Step 3: Write the addendums**

Add after `CONCISE_ADDENDUM` in `credit_analyzer/generation/prompts.py`:

```python
CITE_SOURCES_ADDENDUM: str = """

CITE SOURCES MODE:
For every factual claim, provision, or term you reference, include an explicit \
inline citation with the section number, subsection, and page number where it \
appears (e.g., "Section 7.06(a) (p. 42)"). Cite clause-level references, not \
just article-level. When referencing defined terms, note where they are defined \
(e.g., "as defined in Section 1.01, p. 12"). Every substantive statement \
should have a citation, not just numbers and ratios."""

COMMENTARY_ADDENDUM: str = """

COMMENTARY MODE:
Where relevant, append a brief COMMENTARY section at the end of your response \
with 3-5 bullet points covering any of the following that apply:
- Market context: how this compares to typical leveraged credit agreement terms
- Borrower/lender lean: which party benefits from this language and why
- Notable outliers: unusually large or small baskets, atypical carve-outs, \
missing protections, or other oddities worth flagging
- Key takeaways: what the deal team should be aware of

Omit the COMMENTARY section entirely if the question is a simple lookup, \
definitional, or procedural question that does not warrant market commentary. \
Do not force commentary where it adds no value."""
```

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py::TestPromptAddendums -v`
Expected: PASS

**Step 5: Commit**

```bash
git add credit_analyzer/generation/prompts.py tests/test_qa_engine.py
git commit -m "feat: add Cite Sources and Commentary prompt addendums"
```

---

### Task 2: Wire addendums into QAEngine (`qa_engine.py`)

**Files:**
- Modify: `credit_analyzer/generation/qa_engine.py` — `ask()` (~line 285) and `ask_stream()` (~line 415)
- Test: `tests/test_qa_engine.py`

**Step 1: Write failing tests**

Add to `tests/test_qa_engine.py` inside `TestQAEngine`:

```python
    def test_cite_sources_adds_addendum(self) -> None:
        """cite_sources=True appends the cite sources addendum to the system prompt."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1", cite_sources=True)

        system_prompt: str = llm.complete.call_args.kwargs["system_prompt"]
        assert "CITE SOURCES MODE" in system_prompt

    def test_commentary_adds_addendum(self) -> None:
        """commentary=True appends the commentary addendum to the system prompt."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1", commentary=True)

        system_prompt: str = llm.complete.call_args.kwargs["system_prompt"]
        assert "COMMENTARY MODE" in system_prompt

    def test_all_addendums_stack(self) -> None:
        """All addendums can be active simultaneously."""
        retriever = MagicMock(spec=HybridRetriever)
        retriever.retrieve.return_value = _make_retrieval_result()

        llm = MagicMock()
        llm.complete = MagicMock(return_value=_mock_llm_response())

        engine = QAEngine(retriever=retriever, llm=llm)
        engine.ask("Q?", "doc1", deep_analysis=True, cite_sources=True, commentary=True)

        system_prompt: str = llm.complete.call_args.kwargs["system_prompt"]
        assert "CITE SOURCES MODE" in system_prompt
        assert "COMMENTARY MODE" in system_prompt
        assert "ADDITIONAL CONTEXT RETRIEVAL" in system_prompt
```

**Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py::TestQAEngine::test_cite_sources_adds_addendum tests/test_qa_engine.py::TestQAEngine::test_commentary_adds_addendum tests/test_qa_engine.py::TestQAEngine::test_all_addendums_stack -v`
Expected: FAIL — `ask()` doesn't accept `cite_sources` or `commentary` kwargs

**Step 3: Implement changes in `qa_engine.py`**

In `ask()` (around line 285), add params and addendum logic:

```python
    def ask(
        self,
        question: str,
        document_id: str,
        *,
        deep_analysis: bool = False,
        concise: bool = False,
        cite_sources: bool = False,
        commentary: bool = False,
    ) -> QAResponse:
```

And after the existing addendum lines (~line 323):

```python
        if cite_sources:
            system_prompt += CITE_SOURCES_ADDENDUM
        if commentary:
            system_prompt += COMMENTARY_ADDENDUM
```

Do the same for `ask_stream()` (~line 415): add the two kwargs and the same addendum appending after line 447.

Also update the import at the top of `qa_engine.py` to include:

```python
from credit_analyzer.generation.prompts import (
    ...
    CITE_SOURCES_ADDENDUM,
    COMMENTARY_ADDENDUM,
)
```

**Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_qa_engine.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add credit_analyzer/generation/qa_engine.py tests/test_qa_engine.py
git commit -m "feat: wire cite_sources and commentary params into QAEngine"
```

---

### Task 3: Add chip icons and CSS (`theme.py`)

**Files:**
- Modify: `credit_analyzer/ui/theme.py:114-133` (icon constants) and CSS block (~line 2175+)

**Step 1: Add SVG icon constants**

After the existing `_CHIP_ICON_DISMISS` constant (~line 133), add:

```python
# Cite Sources — quote/bookmark icon
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
```

**Step 2: Add CSS rules for the two new chips**

In the CSS string (APP_CSS), after the existing `chip-extended-thinking` rules, add identical rule blocks for `chip-cite-sources` and `chip-commentary`. The CSS follows the same pattern — just replace `chip-extended-thinking` with the new key names and reference the appropriate icon constants.

For each new chip, duplicate the CSS blocks:
- `[data-testid="stBottom"] .st-key-chip-cite-sources button { ... }` (same styles as extended-thinking)
- `[data-testid="stBottom"] .st-key-chip-cite-sources button p::before { ... }` (with `_CHIP_ICON_CITE`)
- Same pattern for `chip-commentary` with `_CHIP_ICON_COMMENTARY`

Use `_CHIP_ICON_DISMISS` for the active (on) state icon, same as extended thinking.

**Step 3: Verify lint passes**

Run: `.venv/Scripts/python -m ruff check credit_analyzer/ui/theme.py`
Expected: PASS

**Step 4: Commit**

```bash
git add credit_analyzer/ui/theme.py
git commit -m "feat: add icons and CSS for Cite Sources and Commentary chips"
```

---

### Task 4: Add chip buttons and wire session state (`app.py`)

**Files:**
- Modify: `app.py:775-783` (chip rendering) and `app.py:879-893` (passing state to `ask_stream`)

**Step 1: Add chip buttons**

In the chip container section (~line 775), after the Extended Thinking button, add:

```python
    # Cite Sources chip
    cite = st.session_state.get("cite_sources_enabled", False)
    cite_container_key = "chip-on" if cite else "chip-off"
    with st.container(key=cite_container_key):
        if st.button("Cite Sources", key="chip-cite-sources"):
            st.session_state["cite_sources_enabled"] = not cite
            st.rerun()

    # Commentary chip
    commentary = st.session_state.get("commentary_enabled", False)
    commentary_container_key = "chip-on" if commentary else "chip-off"
    with st.container(key=commentary_container_key):
        if st.button("Commentary", key="chip-commentary"):
            st.session_state["commentary_enabled"] = not commentary
            st.rerun()
```

**IMPORTANT:** Each chip needs its own on/off container key, but Streamlit requires unique keys. The current pattern uses `"chip-on"` / `"chip-off"` for a single chip. With multiple chips, you'll need unique container keys like `"chip-thinking-on"` / `"chip-thinking-off"`, `"chip-cite-on"` / `"chip-cite-off"`, `"chip-commentary-on"` / `"chip-commentary-off"`. Update the CSS selectors in `theme.py` accordingly to match these new key names.

**Step 2: Pass state to `ask_stream`**

In `_run_pending_chat_question()` (~line 890), update the `ask_stream` call:

```python
            cite = st.session_state.get("cite_sources_enabled", False)
            commentary = st.session_state.get("commentary_enabled", False)

            for item in qa_engine.ask_stream(
                question, document.document_id,
                deep_analysis=deep,
                cite_sources=cite,
                commentary=commentary,
            ):
```

**Step 3: Verify app runs**

Run: `streamlit run app.py` — verify all three chips render, toggle correctly, and responses reflect enabled modes.

**Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add Cite Sources and Commentary chip buttons to chat input"
```

---

### Task 5: Final integration test and lint check

**Step 1: Run full test suite**

Run: `.venv/Scripts/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: Run linter**

Run: `.venv/Scripts/python -m ruff check .`
Expected: PASS

**Step 3: Run type checker**

Run: `.venv/Scripts/python -m pyright`
Expected: PASS (or no new errors)

**Step 4: Final commit if any fixups needed**

```bash
git add -A
git commit -m "fix: lint and type fixes for chat chips feature"
```
