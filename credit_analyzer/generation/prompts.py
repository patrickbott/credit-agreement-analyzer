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
agreement. Your role is to answer questions accurately based ONLY on the \
provided context excerpts from the agreement.

STRICT RULES:
1. Answer based ONLY on the provided context. Never supplement with general \
knowledge about credit agreements, market conventions, or typical terms.
2. Cite the specific Article/Section number (e.g., "per Section 7.06(a)") \
for every factual claim in your answer.
3. If the provided context does not contain enough information to answer the \
question, clearly state: "I could not find this information in the sections \
I was able to retrieve from the agreement. You may want to check [suggest \
likely section] manually."
4. For numerical values (dollar amounts, ratios, percentages), quote the \
exact language from the document rather than paraphrasing.
5. When a defined term is relevant, note its definition if provided in the \
context.
6. Do not make assumptions about provisions that are not explicitly stated \
in the context.

At the end of your answer, provide:

Confidence: HIGH | MEDIUM | LOW
- HIGH: The answer is directly and explicitly stated in the provided context.
- MEDIUM: The answer requires some interpretation or the context is partially \
relevant.
- LOW: The context is limited and the answer may be incomplete. Manual \
verification recommended.

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
) -> str:
    """Assemble the user prompt from retrieved context, definitions, history.

    Follows the Q&A Context Template from ``docs/PROMPTS.md``.

    Args:
        chunks: Ranked retrieved chunks to include as context.
        definitions: Injected definitions (term -> text).
        history: Recent conversation turns to include.
        question: The current user question.

    Returns:
        The assembled user prompt string.
    """
    parts: list[str] = ["=== CONTEXT FROM CREDIT AGREEMENT ===\n"]

    for hc in chunks:
        c = hc.chunk
        pages = ", ".join(str(p) for p in c.page_numbers)
        text = c.text
        if len(text) > QA_CHUNK_TEXT_MAX_CHARS:
            text = text[:QA_CHUNK_TEXT_MAX_CHARS].rstrip() + "..."
        parts.append(
            f"--- Source: {c.section_title} "
            f"(Section {c.section_id}, Pages {pages}) ---\n"
            f"{text}\n"
        )

    if definitions:
        parts.append("\n=== RELEVANT DEFINITIONS ===")
        for term, defn in definitions.items():
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
