"""Chat UI and Q&A management functions extracted from app.py."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, cast

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st
import streamlit.components.v1 as components

from components.chat_bar import chat_bar
from credit_analyzer.generation.qa_engine import QAEngine, QAResponse, QAStatusEvent
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.ui.demo_report import SUGGESTED_QUESTIONS
from credit_analyzer.ui.guide_content import QUICK_START_STEPS
from credit_analyzer.ui.theme import (
    CHIP_ICON_CITE,
    CHIP_ICON_COMMENTARY,
    CHIP_ICON_DISMISS,
    CHIP_ICON_THINKING,
    chat_welcome,
    concept_status,
    context_strip,
    copy_button,
    decomposed_search_status,
    escalation_status,
    format_chat_answer,
    guide_step_card,
    highlight_defined_terms,
    message_timestamp,
    render_inline_citations,
    render_source_footnotes,
    scroll_to_top_script,
    stream_status,
)
from credit_analyzer.ui.workflows import ProcessedDocument


def _show_dataframe(
    data: Any,
    *,
    width: str = "stretch",
    hide_index: bool = True,
) -> None:
    """Wrapper for st.dataframe that appeases strict type checkers."""
    cast(Any, st).dataframe(
        data,
        width=width,
        hide_index=hide_index,
    )


def _build_chip_list() -> list[dict[str, object]]:
    """Build the chip descriptor list from session state."""
    return [
        {
            "id": "deep_analysis",
            "label": "Extended Thinking",
            "icon_off": CHIP_ICON_THINKING,
            "icon_on": CHIP_ICON_DISMISS,
            "active": st.session_state.get("deep_analysis_enabled", False),
        },
        {
            "id": "cite_sources",
            "label": "Show Sources",
            "icon_off": CHIP_ICON_CITE,
            "icon_on": CHIP_ICON_DISMISS,
            "active": st.session_state.get("cite_sources_enabled", False),
        },
        {
            "id": "commentary",
            "label": "Commentary",
            "icon_off": CHIP_ICON_COMMENTARY,
            "icon_on": CHIP_ICON_DISMISS,
            "active": st.session_state.get("commentary_enabled", False),
        },
    ]


def render_main(
    active_document: ProcessedDocument | None,
    provider: LLMProvider | None,
    provider_status: dict[str, Any],
) -> None:
    if active_document is None:
        st.markdown(chat_welcome(has_document=False), unsafe_allow_html=True)
        cols = st.columns(len(QUICK_START_STEPS))
        for i, (number, title, desc) in enumerate(QUICK_START_STEPS):
            with cols[i]:
                st.markdown(
                    guide_step_card(number, title, desc), unsafe_allow_html=True
                )
        chat_bar(chips=_build_chip_list(), disabled=True)
        return

    if provider is None or not provider_status["ready"]:
        st.warning("The document is indexed, but the model backend is not ready.")
        return

    doc_id = active_document.document_id
    messages = st.session_state.chat_messages[doc_id]

    # If no messages and no pending question, show suggestions
    if not messages and doc_id not in st.session_state.pending_chat_questions:
        render_suggestions(active_document)

    # Render existing messages
    defs_index = active_document.definitions_index if active_document else None
    for message_index, message in enumerate(messages):
        render_chat_message(
            message,
            defs_index=defs_index,
            document_id=doc_id,
            message_index=message_index,
        )

    # Recover partial output from a cancelled stream.
    # Gate on pending_chat_questions (popped BEFORE any yield points in the
    # streaming function) instead of streaming_active, because with Streamlit's
    # fastReruns the new ScriptRunner starts before the old one's finally block
    # has set streaming_active = False.
    partial = st.session_state.partial_response
    if partial is not None and doc_id not in st.session_state.pending_chat_questions:
        if partial.get("doc_id") == doc_id and partial.get("text", "").strip():
            st.session_state.chat_messages[doc_id].append({
                "role": "assistant_cancelled",
                "text": partial["text"],
                "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
            })
            # Add interrupted turn to QA history so follow-ups have context
            last_q = next(
                (m["question"] for m in reversed(messages) if m.get("role") == "user"),
                None,
            )
            if last_q:
                qa = get_or_create_qa_engine(active_document, provider)  # type: ignore[arg-type]
                qa.add_history_turn(str(last_q), partial["text"])
        st.session_state.partial_response = None
        st.session_state.pending_chat_questions.pop(doc_id, None)
        st.rerun()

    render_prompt_editor(active_document, provider)

    # Custom chat bar: chips + input + send/stop — rendered before the
    # pending-question handler so the stop button is visible during streaming.
    has_pending = doc_id in st.session_state.pending_chat_questions
    bar_result = chat_bar(
        chips=_build_chip_list(),
        is_streaming=has_pending,
    )

    # Process chat bar events (deduplicate via event id)
    if bar_result is not None:
        eid = bar_result.get("_id")
        if eid != st.session_state.get("_chat_bar_last_eid"):
            st.session_state["_chat_bar_last_eid"] = eid

            if bar_result["type"] == "submit":
                queue_chat_question(active_document, str(bar_result["text"]))
                st.rerun()
            elif bar_result["type"] == "toggle":
                chip_key = f"{bar_result['chip']}_enabled"
                st.session_state[chip_key] = bar_result["active"]
                st.rerun()

    # Handle pending question (synchronous streaming — blocks until done)
    pending = st.session_state.pending_chat_questions.get(doc_id)
    if pending is not None:
        run_pending_chat_question(active_document, provider, str(pending))
        st.rerun()

    # Scroll-to-top button
    components.html(scroll_to_top_script("section.main"), height=0)


def render_suggestions(active_document: ProcessedDocument) -> None:
    st.markdown(chat_welcome(has_document=True), unsafe_allow_html=True)
    with st.container(key="suggested-actions"):
        for row_start in range(0, len(SUGGESTED_QUESTIONS), 3):
            row_items = SUGGESTED_QUESTIONS[row_start : row_start + 3]
            cols = st.columns(len(row_items))
            for i, suggestion in enumerate(row_items):
                with cols[i]:
                    if suggestion.prompt is not None and st.button(
                        suggestion.label,
                        key=f"suggested-{row_start + i}",
                        use_container_width=True,
                    ):
                        queue_chat_question(active_document, suggestion.prompt)
                        st.rerun()


# ---------------------------------------------------------------------------
# Chat Q&A
# ---------------------------------------------------------------------------


def queue_chat_question(document: ProcessedDocument, question: str) -> None:
    clear_prompt_edit(document.document_id)
    st.session_state.chat_messages[document.document_id].append(
        {
            "role": "user",
            "question": question,
            "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
        }
    )
    st.session_state.pending_chat_questions[document.document_id] = question


def get_or_create_qa_engine(document: ProcessedDocument, provider: LLMProvider) -> QAEngine:
    """Return the persistent QAEngine for this document, creating it on first call.

    Storing the engine in session_state preserves conversation history across
    Streamlit reruns, which is required for multi-turn reformulation to work.
    """
    engine_key = f"qa_engine_{document.document_id}"
    if engine_key not in st.session_state:
        engine = QAEngine(document.retriever, provider)
        if document.preamble_text is not None:
            engine.set_preamble(
                document.preamble_text,
                page_numbers=document.preamble_page_numbers,
            )
        st.session_state[engine_key] = engine
    return cast(QAEngine, st.session_state[engine_key])


def clear_chat(document_id: str) -> None:
    clear_prompt_edit(document_id)
    st.session_state.chat_messages[document_id] = []
    st.session_state.pending_chat_questions.pop(document_id, None)
    # Drop the cached engine so history resets with the conversation.
    st.session_state.pop(f"qa_engine_{document_id}", None)


def run_pending_chat_question(
    document: ProcessedDocument,
    provider: LLMProvider,
    question: str,
) -> None:
    st.session_state.pending_chat_questions.pop(document.document_id, None)
    qa_engine = get_or_create_qa_engine(document, provider)

    try:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            response_placeholder = st.empty()
            streamed_text = ""
            st.session_state.streaming_active = True
            st.session_state.partial_response = {"doc_id": document.document_id, "text": ""}
            final_response = None
            first_token = True

            deep = st.session_state.get("deep_analysis_enabled", False)
            status_label = (
                "Extended thinking: searching relevant sections..."
                if deep else "Searching relevant sections..."
            )
            status_placeholder.markdown(
                stream_status(status_label),
                unsafe_allow_html=True,
            )
            t0 = time.monotonic()

            _STREAM_FLUSH_INTERVAL = 0.045  # seconds between UI updates
            _last_flush = time.monotonic()
            _pending = ""

            cite = st.session_state.get("cite_sources_enabled", False)
            commentary = st.session_state.get("commentary_enabled", False)

            for item in qa_engine.ask_stream(
                question, document.document_id,
                deep_analysis=deep,
                cite_sources=cite,
                commentary=commentary,
            ):
                if isinstance(item, QAResponse):
                    final_response = item
                elif isinstance(item, QAStatusEvent):
                    if item.stage == "concept_match":
                        status_placeholder.markdown(
                            concept_status([item.detail]),
                            unsafe_allow_html=True,
                        )
                    elif item.stage == "escalation":
                        status_placeholder.markdown(
                            escalation_status(),
                            unsafe_allow_html=True,
                        )
                    elif item.stage == "decomposed_search":
                        status_placeholder.markdown(
                            decomposed_search_status(item.detail),
                            unsafe_allow_html=True,
                        )
                else:
                    if first_token:
                        status_placeholder.markdown(
                            stream_status("Composing answer..."),
                            unsafe_allow_html=True,
                        )
                        first_token = False
                    _pending += item
                    now = time.monotonic()
                    if now - _last_flush >= _STREAM_FLUSH_INTERVAL:
                        streamed_text += _pending
                        _pending = ""
                        _last_flush = now
                        st.session_state.partial_response["text"] = streamed_text
                        response_placeholder.markdown(streamed_text + "\u258c")

            # Flush any remaining buffered tokens
            if _pending:
                streamed_text += _pending
                st.session_state.partial_response["text"] = streamed_text
                response_placeholder.markdown(streamed_text + "\u258c")

            elapsed = time.monotonic() - t0
            status_placeholder.empty()

            if final_response is not None:
                response_placeholder.empty()
                answer_id = f"answer-{hash(final_response.answer) & 0xFFFFFFFF:08x}"
                defs_idx = document.definitions_index
                if final_response.inline_citations:
                    cited_html = render_inline_citations(
                        final_response.answer, final_response.inline_citations
                    )
                    if defs_idx and defs_idx.definitions:
                        footnote_marker = '<div class="cite-footnotes">'
                        fn_pos = cited_html.find(footnote_marker)
                        if fn_pos >= 0:
                            body_part = highlight_defined_terms(cited_html[:fn_pos], defs_idx)
                            cited_html = body_part + cited_html[fn_pos:]
                        else:
                            cited_html = highlight_defined_terms(cited_html, defs_idx)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}" class="section-answer">{cited_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                elif final_response.sources:
                    answer_html = format_chat_answer(final_response.answer)
                    if defs_idx and defs_idx.definitions:
                        answer_html = highlight_defined_terms(answer_html, defs_idx)
                    footnotes_html = render_source_footnotes(final_response.sources)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}" class="section-answer">{answer_html}{footnotes_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    answer_html = format_chat_answer(final_response.answer)
                    if defs_idx and defs_idx.definitions:
                        answer_html = highlight_defined_terms(answer_html, defs_idx)
                    response_placeholder.markdown(
                        f'<div style="position:relative;">'
                        f'<div id="{answer_id}" class="section-answer">{answer_html}</div>'
                        f"{copy_button(answer_id)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Context strip
                sections_used = _extract_sections_used(final_response)
                chunk_count = len(final_response.retrieved_chunks) if final_response.retrieved_chunks else 0
                duration = final_response.llm_response.duration_seconds if final_response.llm_response else elapsed
                rounds = final_response.retrieval_rounds
                st.markdown(
                    context_strip(
                        final_response.confidence, chunk_count,
                        sections_used, duration,
                        retrieval_rounds=rounds,
                        concepts=final_response.concepts_matched if final_response.concepts_matched else None,
                        escalated=final_response.escalated,
                    ),
                    unsafe_allow_html=True,
                )

                # Expandable retrieved context
                if final_response.retrieved_chunks:
                    n_chunks = len(final_response.retrieved_chunks)
                    with st.expander(f"Retrieved context ({n_chunks} chunks)", expanded=False):
                        sorted_chunks = sorted(
                            final_response.retrieved_chunks,
                            key=lambda c: c.score,
                            reverse=True,
                        )
                        retrieved_df = pd.DataFrame(
                            [
                                {
                                    "section": chunk.chunk.section_id,
                                    "title": chunk.chunk.section_title,
                                    "relevance": round(chunk.score, 3),
                                    "pages": ", ".join(
                                        str(p) for p in chunk.chunk.page_numbers
                                    ),
                                }
                                for chunk in sorted_chunks
                            ]
                        )
                        _show_dataframe(retrieved_df, width="stretch", hide_index=True)

                # Timestamp
                ts = datetime.now().strftime("%I:%M %p").lstrip("0")
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)

        if final_response is not None:
            st.session_state.chat_messages[document.document_id].append(
                {
                    "role": "assistant",
                    "response": final_response,
                    "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
                }
            )
            st.session_state.partial_response = None
    except Exception as exc:
        st.error(f"Could not generate an answer: {exc}")
    finally:
        st.session_state.streaming_active = False


def render_prompt_editor(document: ProcessedDocument, provider: LLMProvider) -> None:
    doc_id = document.document_id
    edit_targets: dict[str, int] = st.session_state.prompt_edit_index
    if doc_id not in edit_targets:
        return

    message_index = edit_targets[doc_id]
    messages = st.session_state.chat_messages.get(doc_id, [])
    if (
        message_index < 0
        or message_index >= len(messages)
        or messages[message_index].get("role") != "user"
    ):
        clear_prompt_edit(doc_id)
        return

    draft_widget_key = f"prompt-edit-input-{doc_id}"
    if draft_widget_key not in st.session_state:
        st.session_state[draft_widget_key] = st.session_state.prompt_edit_draft.get(
            doc_id,
            "",
        )

    edited_prompt: str = st.text_area(
        "Edit prompt",
        key=draft_widget_key,
        height=100,
        label_visibility="collapsed",
    )

    save_col, cancel_col, _ = st.columns([1, 1, 4])
    with save_col:
        if st.button("\u2191 Resend", key=f"save-edit-{doc_id}", type="primary"):
            apply_prompt_edit(document, provider, message_index, edited_prompt)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key=f"cancel-edit-{doc_id}"):
            clear_prompt_edit(doc_id)
            st.rerun()


def apply_prompt_edit(
    document: ProcessedDocument,
    provider: LLMProvider,
    message_index: int,
    edited_prompt: str,
) -> None:
    doc_id = document.document_id
    new_question = edited_prompt.strip()
    if not new_question:
        st.warning("Prompt cannot be empty.")
        return

    messages = st.session_state.chat_messages[doc_id]
    if (
        message_index < 0
        or message_index >= len(messages)
        or messages[message_index].get("role") != "user"
    ):
        st.warning("Could not edit that prompt because the chat changed.")
        clear_prompt_edit(doc_id)
        return

    retained_messages = messages[:message_index]
    st.session_state.chat_messages[doc_id] = retained_messages
    st.session_state.pending_chat_questions.pop(doc_id, None)
    clear_prompt_edit(doc_id)
    rebuild_qa_history(document, provider, retained_messages)
    queue_chat_question(document, new_question)


def rebuild_qa_history(
    document: ProcessedDocument,
    provider: LLMProvider,
    messages: list[dict[str, Any]],
) -> None:
    st.session_state.pop(f"qa_engine_{document.document_id}", None)
    qa_engine = get_or_create_qa_engine(document, provider)
    for question, answer in _history_pairs_from_messages(messages):
        qa_engine.add_history_turn(question, answer)


def clear_prompt_edit(document_id: str) -> None:
    st.session_state.get("prompt_edit_index", {}).pop(document_id, None)
    st.session_state.get("prompt_edit_draft", {}).pop(document_id, None)
    st.session_state.pop(f"prompt-edit-input-{document_id}", None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _history_pairs_from_messages(
    messages: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    pending_question: str | None = None

    for message in messages:
        role = message.get("role")
        if role == "user":
            raw_question = cast(str | None, message.get("question"))
            question = (raw_question or "").strip()
            pending_question = question or None
            continue

        if role == "assistant" and pending_question is not None:
            response = message.get("response")
            if isinstance(response, QAResponse):
                pairs.append((pending_question, response.answer))
                pending_question = None
        elif role == "assistant_cancelled" and pending_question is not None:
            text = cast(str, message.get("text", ""))
            if text.strip():
                pairs.append((pending_question, text))
                pending_question = None

    return pairs


def _extract_sections_used(response: QAResponse) -> str:
    """Build a short summary string of which sections were retrieved."""
    if not response.retrieved_chunks:
        return ""
    section_ids: list[str] = []
    seen: set[str] = set()
    for chunk in response.retrieved_chunks:
        sid = chunk.chunk.section_id
        if sid and sid not in seen:
            seen.add(sid)
            section_ids.append(sid)
    if not section_ids:
        return ""
    if len(section_ids) <= 3:
        return ", ".join(section_ids)
    return ", ".join(section_ids[:3]) + f" +{len(section_ids) - 3}"


def render_chat_message(
    message: dict[str, Any],
    defs_index: Any = None,
    *,
    document_id: str | None = None,
    message_index: int | None = None,
) -> None:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["question"])
            ts = message.get("timestamp")
            if ts:
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)
            if document_id is not None and message_index is not None:
                edit_key = f"edit-prompt-{document_id}-{message_index}"
                if st.button("\u270E Edit", key=edit_key):
                    st.session_state.prompt_edit_index[document_id] = message_index
                    st.session_state.prompt_edit_draft[document_id] = cast(
                        str,
                        message.get("question", ""),
                    )
                    st.rerun()
        return

    if message["role"] == "assistant_notice":
        with st.chat_message("assistant"):
            notice_text = cast(str, message.get("text", ""))
            st.markdown(format_chat_answer(notice_text), unsafe_allow_html=True)
            ts = message.get("timestamp")
            if ts:
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)
        return

    if message["role"] == "assistant_cancelled":
        with st.chat_message("assistant"):
            answer_html = format_chat_answer(cast(str, message.get("text", "")))
            if defs_index and defs_index.definitions:
                answer_html = highlight_defined_terms(answer_html, defs_index)
            st.markdown(
                f'<div class="section-answer">{answer_html}'
                f'<span style="color:#999;font-size:0.8rem;font-style:italic;">'
                f' (generation stopped)</span></div>',
                unsafe_allow_html=True,
            )
            ts = message.get("timestamp")
            if ts:
                st.markdown(message_timestamp(ts), unsafe_allow_html=True)
        return

    response: QAResponse = message["response"]
    answer_id = f"answer-{hash(response.answer) & 0xFFFFFFFF:08x}"
    with st.chat_message("assistant"):
        if response.inline_citations:
            cited_html = render_inline_citations(
                response.answer, response.inline_citations
            )
            if defs_index and defs_index.definitions:
                footnote_marker = '<div class="cite-footnotes">'
                fn_pos = cited_html.find(footnote_marker)
                if fn_pos >= 0:
                    body_part = highlight_defined_terms(cited_html[:fn_pos], defs_index)
                    cited_html = body_part + cited_html[fn_pos:]
                else:
                    cited_html = highlight_defined_terms(cited_html, defs_index)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}" class="section-answer">{cited_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif response.sources:
            answer_html = format_chat_answer(response.answer)
            if defs_index and defs_index.definitions:
                answer_html = highlight_defined_terms(answer_html, defs_index)
            footnotes_html = render_source_footnotes(response.sources)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}" class="section-answer">{answer_html}{footnotes_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            answer_html = format_chat_answer(response.answer)
            if defs_index and defs_index.definitions:
                answer_html = highlight_defined_terms(answer_html, defs_index)
            st.markdown(
                f'<div style="position:relative;">'
                f'<div id="{answer_id}" class="section-answer">{answer_html}</div>'
                f"{copy_button(answer_id)}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Context strip
        sections_used = _extract_sections_used(response)
        chunk_count = len(response.retrieved_chunks) if response.retrieved_chunks else 0
        duration = response.llm_response.duration_seconds if response.llm_response else 0.0
        rounds = response.retrieval_rounds
        st.markdown(
            context_strip(
                response.confidence, chunk_count, sections_used, duration,
                retrieval_rounds=rounds,
                concepts=response.concepts_matched if response.concepts_matched else None,
                escalated=response.escalated,
            ),
            unsafe_allow_html=True,
        )

        # Expandable retrieved context
        if response.retrieved_chunks:
            n_chunks = len(response.retrieved_chunks)
            with st.expander(f"Retrieved context ({n_chunks} chunks)", expanded=False):
                sorted_chunks = sorted(
                    response.retrieved_chunks, key=lambda c: c.score, reverse=True
                )
                retrieved_df = pd.DataFrame(
                    [
                        {
                            "section": chunk.chunk.section_id,
                            "title": chunk.chunk.section_title,
                            "relevance": round(chunk.score, 3),
                            "pages": ", ".join(str(p) for p in chunk.chunk.page_numbers),
                        }
                        for chunk in sorted_chunks
                    ]
                )
                _show_dataframe(retrieved_df, width="stretch", hide_index=True)

        # Timestamp
        ts = message.get("timestamp")
        if ts:
            st.markdown(message_timestamp(ts), unsafe_allow_html=True)


