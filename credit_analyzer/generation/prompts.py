"""Prompt templates and context assembly for credit agreement Q&A.

Contains the system prompts and functions for building the user-facing
context prompt that combines retrieved chunks, definitions, conversation
history, and the current question.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from credit_analyzer.config import QA_DEFINITION_MAX_CHARS
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import HybridChunk

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

QA_SYSTEM_PROMPT: str = """\
FORMATTING RULES (STRICT):
- Do NOT use markdown bold (**), headers (##), or backticks (`).
- Use numbered lists (1., 2., 3.) or bullet lists (- item) for structure.
- Write section labels in ALL CAPS on their own line.
- USE TABLES when data has a natural tabular structure (pricing grids, \
step-downs, comparisons). Format tables with pipes: "| Col A | Col B |" \
on each row, "| --- | --- |" separator after the header row, and a blank \
line before and after the table.

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

INLINE CITATIONS:
Each context excerpt is labeled [Source 1], [Source 2], etc. When you make \
a specific factual claim (dollar amounts, ratios, percentages, dates, \
covenant tests), place the corresponding source number in brackets \
immediately after the claim, e.g. [1], [2]. Reuse the same number when \
the same source supports multiple claims. Do NOT let citations make your \
response longer -- keep the same concise style.

RESPONSE STYLE:
1. Write like a senior investment banking analyst briefing a colleague, not \
like a lawyer.
2. Summarize provisions in plain business language. Do not quote lengthy \
legal text verbatim. Instead, state what the provision means in practical \
terms and cite the section/page so the reader can verify.
3. Keep answers concise and structured. Lead with the direct answer, then \
provide supporting detail if needed.
4. Use numbered lists for multi-part answers (e.g., baskets, step-downs, \
conditions).
5. When the answer has a natural tabular structure (pricing grids, \
step-downs, basket comparisons), present it as a table (see formatting \
rules above).
"""

REFORMULATION_SYSTEM_PROMPT: str = """\
Given the conversation history below, reformulate the latest question into a \
standalone search query that captures the full intent. Respond with ONLY the \
search query, nothing else."""

DEEP_ANALYSIS_ADDENDUM: str = """

ADDITIONAL CONTEXT RETRIEVAL:
If the provided context is insufficient to fully and accurately answer the \
question, output <needs_context>your follow-up search query</needs_context> \
at the END of your response. The system will retrieve additional context and \
ask you again with the expanded context. Only request additional context if \
you genuinely need it — do not request context speculatively."""


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
    preamble_page_numbers: Sequence[int] | None = None,
) -> tuple[str, list[HybridChunk]]:
    """Assemble the user prompt from retrieved context, definitions, history.

    Follows the in-code Q&A context template shape.

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
        preamble_page_numbers: Optional page numbers for the preamble text.

    Returns:
        A tuple of (prompt_string, numbered_chunks) where numbered_chunks
        is the list of chunks in the order they were numbered [Source 1],
        [Source 2], etc. in the prompt.
    """
    parts: list[str] = ["=== CONTEXT FROM CREDIT AGREEMENT ===\n"]

    # Build the numbered source list. Preamble gets [Source 1] when present.
    numbered: list[HybridChunk] = []
    source_num = 1

    if preamble_text:
        preamble_page_list = list(preamble_page_numbers or [])
        preamble_pages = _format_page_numbers(preamble_page_list)
        page_label = preamble_pages if preamble_pages else "n/a"
        parts.append(
            f"[Source {source_num}] Preamble and Recitals "
            f"(pp. {page_label})\n"
            f"{preamble_text}\n"
        )
        numbered.append(HybridChunk(
            chunk=Chunk(
                chunk_id="__preamble__",
                text=preamble_text,
                section_id="Preamble",
                section_title="Preamble and Recitals",
                article_number=0,
                article_title="",
                section_type="preamble",
                chunk_type="text",
                page_numbers=preamble_page_list,
                defined_terms_present=[],
                chunk_index=0,
                token_count=0,
            ),
            score=1.0,
            source="preamble",
        ))
        source_num += 1

    # Sort chunks by document position so cross-references flow naturally.
    # Score information is preserved on each HybridChunk for debugging/UI.
    sorted_chunks = sorted(
        chunks,
        key=lambda hc: (hc.chunk.article_number, hc.chunk.section_id, hc.chunk.chunk_index),
    )

    for hc in sorted_chunks:
        c = hc.chunk
        pages = _format_page_numbers(c.page_numbers)
        parts.append(
            f"[Source {source_num}] {c.section_title} "
            f"(Section {c.section_id}, pp. {pages})\n"
            f"{c.text}\n"
        )
        numbered.append(hc)
        source_num += 1

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
            # Truncate long prior answers to save tokens (~200 tokens)
            answer = turn.answer[:800] + "..." if len(turn.answer) > 800 else turn.answer
            parts.append(f"Assistant: {answer}")

    parts.append(f"\n=== CURRENT QUESTION ===\n{question}")

    return "\n".join(parts), numbered


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
