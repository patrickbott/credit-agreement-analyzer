# credit_analyzer/generation/query_decomposer.py
"""LLM-based query decomposition for complex leveraged finance questions.

When the retrieval quality gate detects insufficient results, this module
asks the LLM to decompose the original query into targeted sub-queries
that can each be run through the retrieval pipeline independently.
"""

from __future__ import annotations

import logging
import re

from credit_analyzer.llm.base import LLMProvider

logger = logging.getLogger(__name__)

DECOMPOSITION_SYSTEM_PROMPT: str = """\
You are a leveraged finance expert helping to search a credit agreement. \
A user has asked a question, but the initial search did not find relevant \
passages. Your job is to decompose the question into 2-5 specific, \
targeted search queries that will find the relevant provisions in the \
document.

RULES:
1. Each query should target a DIFFERENT aspect or section of the credit \
agreement.
2. Use the specific legal/financial terminology that would appear in the \
document text (not colloquial names).
3. If domain concept context is provided, use the suggested search terms.
4. Output ONLY the search queries, one per line, numbered 1-5.
5. Keep each query under 15 words.
6. Do NOT include explanations or commentary."""

_MAX_SUB_QUERIES = 5


def decompose_query(
    llm: LLMProvider,
    question: str,
    *,
    concept_context: str = "",
) -> list[str]:
    """Decompose a complex query into targeted sub-queries using the LLM.

    Args:
        llm: The LLM provider to use for decomposition.
        question: The original user question.
        concept_context: Optional domain concept context from the registry.

    Returns:
        A list of 2-5 sub-queries for retrieval. Falls back to the
        original question on error.
    """
    user_parts: list[str] = []
    if concept_context:
        user_parts.append(concept_context)
        user_parts.append("")
    user_parts.append(f"USER QUESTION: {question}")
    user_parts.append("")
    user_parts.append("Generate 2-5 targeted search queries:")
    user_prompt = "\n".join(user_parts)

    try:
        response = llm.complete(
            system_prompt=DECOMPOSITION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=200,
        )
        queries = parse_sub_queries(response.text)
        if queries:
            logger.info(
                "Decomposed query into %d sub-queries: %r",
                len(queries), queries,
            )
            return queries
    except Exception:
        logger.warning("Query decomposition failed, using original", exc_info=True)

    return [question]


def parse_sub_queries(text: str) -> list[str]:
    """Parse numbered/bulleted sub-queries from LLM output.

    Handles formats:
    - "1. query text"
    - "- query text"
    - plain lines

    Returns up to _MAX_SUB_QUERIES queries. Empty lines are skipped.
    """
    lines = text.strip().splitlines()
    queries: list[str] = []
    for line in lines:
        # Strip numbering and bullet markers
        cleaned = re.sub(r"^\s*(?:\d+[.)]\s*|-\s*|\*\s*)", "", line).strip()
        if cleaned and len(cleaned) > 5:
            queries.append(cleaned)
        if len(queries) >= _MAX_SUB_QUERIES:
            break
    return queries
