"""Query expansion and multi-query retrieval helpers for the Q&A engine.

Provides rule-based query expansion and helpers for merging retrieval
results across multiple queries.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    merge_multi_query_results,
)

__all__ = [
    "expand_query",
    "extract_needs_context",
    "merge_retrieval_results",
    "retrieve_multi_query",
]

# ---------------------------------------------------------------------------
# Deep-analysis helpers
# ---------------------------------------------------------------------------

_NEEDS_CONTEXT_RE = re.compile(
    r"<needs_context>(.*?)</needs_context>", re.DOTALL,
)


def extract_needs_context(text: str) -> tuple[str, str | None]:
    """Strip any <needs_context> tag and return (cleaned_text, follow_up_query).

    Returns the text with the tag removed and the follow-up query if found,
    or None if no tag is present.
    """
    match = _NEEDS_CONTEXT_RE.search(text)
    if match is None:
        return text, None
    cleaned = text[:match.start()].rstrip() + text[match.end():]
    return cleaned.strip(), match.group(1).strip()


def merge_retrieval_results(
    existing: RetrievalResult,
    new: RetrievalResult,
    top_k: int,
) -> RetrievalResult:
    """Merge new retrieval results into existing, deduplicating by chunk ID."""
    seen_ids = {hc.chunk.chunk_id for hc in existing.chunks}
    merged_chunks = list(existing.chunks)
    for hc in new.chunks:
        if hc.chunk.chunk_id not in seen_ids and len(merged_chunks) < top_k:
            seen_ids.add(hc.chunk.chunk_id)
            merged_chunks.append(hc)
    merged_defs = {**existing.injected_definitions, **new.injected_definitions}
    return RetrievalResult(chunks=merged_chunks, injected_definitions=merged_defs)


# ---------------------------------------------------------------------------
# Multi-query retrieval helpers
# ---------------------------------------------------------------------------


def expand_query(question: str) -> list[str]:
    """Generate additional retrieval queries from a question.

    Uses rule-based expansion to create complementary queries that search
    different aspects of the same question. This is cheaper than LLM-based
    expansion and catches cases where key terms appear in definitions,
    schedules, or different section types.

    Returns 1-3 queries (always includes the original).
    """
    queries = [question]
    question_lower = question.lower()

    # Extract key noun phrases that might be defined terms
    # Look for capitalized multi-word phrases (common in credit agreements)
    defined_term_pattern = re.compile(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    )
    terms = defined_term_pattern.findall(question)

    # Also catch fully capitalized terms like "SOFR" or "ABR"
    upper_terms = re.findall(r'\b([A-Z]{2,})\b', question)

    # Also detect common credit agreement terms in lowercase questions.
    # Maps lowercase phrases to their canonical defined-term form.
    _TERM_ALIASES: dict[str, str] = {
        "applicable margin": "Applicable Margin",
        "applicable rate": "Applicable Rate",
        "sofr spread": "Applicable Margin SOFR spread",
        "interest rate": "Applicable Rate interest rate",
        "pricing grid": "Applicable Rate pricing grid",
        "base rate": "Alternate Base Rate",
        "abr": "Alternate Base Rate ABR",
        "commitment fee": "Commitment Fee",
        "lc fee": "Letter of Credit Fee",
        "leverage ratio": "Total Net Leverage Ratio",
        "coverage ratio": "Fixed Charge Coverage Ratio",
        "ebitda": "Consolidated EBITDA",
        "consolidated ebitda": "Consolidated EBITDA",
        "available amount": "Available Amount",
        "permitted investments": "Permitted Investments",
        "permitted liens": "Permitted Liens",
        "permitted indebtedness": "Permitted Indebtedness",
        "change of control": "Change of Control",
        "required lenders": "Required Lenders",
        "net income": "Consolidated Net Income",
        "excess cash flow": "Excess Cash Flow",
    }
    alias_terms: list[str] = []
    for alias, canonical in _TERM_ALIASES.items():
        if alias in question_lower:
            alias_terms.append(canonical)

    # Build a definitions-focused query if we found potential defined terms
    all_terms = terms + upper_terms + alias_terms
    if all_terms:
        def_query = "definition " + " ".join(all_terms[:3])
        queries.append(def_query)

    # Build a broader structural query using key financial terms
    financial_keywords = {
        "margin", "spread", "rate", "pricing", "interest", "sofr", "libor",
        "abr", "floor", "grid", "step-down", "step-up",
        "leverage", "ratio", "covenant", "test", "threshold",
        "basket", "cap", "amount", "limit",
        "maturity", "amortization", "prepayment", "sweep",
        "dividend", "distribution", "restricted payment",
        "lien", "collateral", "security",
        "incremental", "accordion", "facility",
    }
    matched_keywords = [kw for kw in financial_keywords if kw in question_lower]

    if matched_keywords and len(queries) < 3:
        # Add a query that targets the likely section type
        broad_query = question + " " + " ".join(matched_keywords[:3])
        if broad_query != question:
            queries.append(broad_query)

    return queries[:3]  # Cap at 3 queries


def retrieve_multi_query(
    retriever: HybridRetriever,
    queries: list[str],
    document_id: str,
    top_k: int,
    section_types_exclude: tuple[str, ...] | None = None,
) -> RetrievalResult:
    """Run multiple retrieval queries and merge results via round-robin.

    Uses round-robin interleaving so every query contributes proportionally,
    preventing dominant queries from crowding out niche results.
    """
    per_query_results: list[list[HybridChunk]] = []
    per_query_definitions: list[dict[str, str]] = []

    def _run(q: str) -> RetrievalResult:
        return retriever.retrieve(
            query=q,
            document_id=document_id,
            top_k=top_k,
            section_types_exclude=section_types_exclude,
        )

    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        results = list(pool.map(_run, queries))

    for result in results:
        per_query_results.append(result.chunks)
        per_query_definitions.append(result.injected_definitions)

    return merge_multi_query_results(
        per_query_results, per_query_definitions, top_k,
    )
