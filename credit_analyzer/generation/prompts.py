"""Prompt templates and context assembly for credit agreement Q&A.

Contains the system prompts and functions for building the user-facing
context prompt that combines retrieved chunks, definitions, conversation
history, and the current question.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from credit_analyzer.config import QA_CHUNK_TEXT_MAX_CHARS, QA_DEFINITION_MAX_CHARS
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk

# ---------------------------------------------------------------------------
# System prompts (mirrors docs/PROMPTS.md)
# ---------------------------------------------------------------------------

QA_SYSTEM_PROMPT: str = """\
You are a leveraged finance analyst assistant analyzing a specific credit \
agreement. Answer questions accurately based ONLY on the provided context \
excerpts.

RULES:
1. Base answers ONLY on the provided context. Do not supplement with general \
knowledge about credit agreements or market conventions.
2. Cite the Section number (e.g., "Section 7.06(a)") for factual claims.
3. If the context does not contain the answer, say so clearly and suggest \
where the user might look (e.g., "check the definitions section" or \
"see Schedule 1.1A").
4. State dollar amounts, ratios, and percentages exactly as they appear in \
the document.
5. Do not assume provisions exist if they are not in the context.

RESPONSE STYLE:
- Write like a senior investment banking analyst briefing a colleague, not \
like a lawyer.
- Summarize provisions in plain business language. Do not quote lengthy \
legal text verbatim. Instead, state what the provision means in practical \
terms and cite the section/page so the reader can verify.
- Keep answers concise and structured. Lead with the direct answer, then \
provide supporting detail.
- Use numbered lists for multi-part answers (e.g., baskets, step-downs, \
conditions).
- FORMATTING: Use plain text only. Do NOT use markdown syntax such as \
** for bold, ## for headers, or - for bullet points. Use numbered lists \
(1., 2., 3.) and indentation for structure. Write section titles in plain \
text on their own line, not as markdown headers.

At the end of your answer, provide:

Confidence: HIGH | MEDIUM | LOW
- HIGH: Answer is directly stated in the provided context.
- MEDIUM: Requires some interpretation or context is partial.
- LOW: Context is limited; manual verification recommended.

Sources: Section X.XX (pp. XX-XX), Section Y.YY (pp. YY-YY)
"""

REFORMULATION_SYSTEM_PROMPT: str = """\
Given the conversation history below, reformulate the latest question into a \
standalone search query that captures the full intent. Respond with ONLY the \
search query, nothing else."""


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


@dataclass
class ConversationTurn:
    """A single Q&A exchange in conversation history."""

    question: str
    answer: str


# ---------------------------------------------------------------------------
# Page number formatting
# ---------------------------------------------------------------------------


def _format_page_numbers(pages: Sequence[int]) -> str:
    """Format a list of page numbers into a compact range string.

    Collapses consecutive pages into ranges (e.g. ``[62, 63, 64]`` becomes
    ``"62-64"``).  Single pages are kept as-is.  Multiple ranges are
    comma-separated.

    Args:
        pages: Sorted page numbers.

    Returns:
        Compact string representation.
    """
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges: list[str] = []
    start = sorted_pages[0]
    end = start
    for p in sorted_pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(f"{start}-{end}" if end > start else str(start))
            start = end = p
    ranges.append(f"{start}-{end}" if end > start else str(start))
    return ", ".join(ranges)


# ---------------------------------------------------------------------------
# Definition truncation
# ---------------------------------------------------------------------------


def truncate_definition(definition: str, max_chars: int = QA_DEFINITION_MAX_CHARS) -> str:
    """Truncate a long definition to ``max_chars`` characters.

    Truncation happens at a sentence boundary when possible, falling back
    to a hard cut with an ellipsis marker.

    Args:
        definition: The full definition text.
        max_chars: Maximum allowed characters.

    Returns:
        The (possibly truncated) definition.
    """
    if len(definition) <= max_chars:
        return definition
    truncated = definition[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars // 2:
        return truncated[: last_period + 1]
    return truncated.rstrip() + "..."


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def build_context_prompt(
    chunks: Sequence[HybridChunk],
    definitions: dict[str, str],
    history: Sequence[ConversationTurn],
    question: str,
    preamble_text: str | None = None,
) -> str:
    """Assemble the user prompt from retrieved context, definitions, history.

    Follows the Q&A Context Template from ``docs/PROMPTS.md``.

    When ``preamble_text`` is provided, it is always injected first as
    it contains headline terms (borrower, facility sizes, date) that
    are relevant to most queries.

    Definitions that already appear verbatim in a retrieved chunk are
    automatically skipped to avoid wasting context tokens on duplicates.

    Args:
        chunks: Ranked retrieved chunks to include as context.
        definitions: Injected definitions (term -> text).
        history: Recent conversation turns to include.
        question: The current user question.
        preamble_text: Optional preamble/recitals text to always inject.

    Returns:
        The assembled user prompt string.
    """
    parts: list[str] = ["=== CONTEXT FROM CREDIT AGREEMENT ===\n"]

    if preamble_text:
        parts.append(
            "--- Source: Preamble and Recitals (Pages 1-2) ---\n"
            f"{preamble_text}\n"
        )

    for hc in chunks:
        c = hc.chunk
        pages = _format_page_numbers(c.page_numbers)
        text = c.text
        if len(text) > QA_CHUNK_TEXT_MAX_CHARS:
            text = text[:QA_CHUNK_TEXT_MAX_CHARS].rstrip() + "..."
        parts.append(
            f"--- Source: {c.section_title} "
            f"(Section {c.section_id}, Pages {pages}) ---\n"
            f"{text}\n"
        )

    if definitions:
        # Skip definitions whose text already appears in a retrieved chunk
        chunk_texts = " ".join(hc.chunk.text for hc in chunks)
        filtered_defs = {
            term: defn
            for term, defn in definitions.items()
            if defn[:80] not in chunk_texts
        }
        if filtered_defs:
            parts.append("\n=== RELEVANT DEFINITIONS ===")
            for term, defn in filtered_defs.items():
                truncated = truncate_definition(defn)
                parts.append(f'"{term}" means {truncated}')

    if history:
        parts.append("\n=== PREVIOUS Q&A IN THIS SESSION ===")
        for turn in history:
            parts.append(f"User: {turn.question}")
            parts.append(f"Assistant: {turn.answer}")

    parts.append(f"\n=== CURRENT QUESTION ===\n{question}")

    return "\n".join(parts)


def build_reformulation_prompt(
    history: Sequence[ConversationTurn],
    question: str,
) -> str:
    """Build the user prompt for follow-up question reformulation.

    Args:
        history: Recent conversation turns.
        question: The current (possibly context-dependent) question.

    Returns:
        The user prompt for the reformulation LLM call.
    """
    parts: list[str] = ["Conversation:"]
    for turn in history:
        parts.append(f"User: {turn.question}")
        parts.append(f"Assistant: {turn.answer}")
    parts.append(f"\nLatest question: {question}")
    parts.append("\nReformulated search query:")
    return "\n".join(parts)
