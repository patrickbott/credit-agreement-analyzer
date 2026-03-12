"""Query expansion and multi-query retrieval helpers for the Q&A engine.

Provides rule-based query expansion and helpers for merging retrieval
results across multiple queries.  When the domain concept registry is
available, concept alias matching and synonym expansion are applied
before the existing keyword/alias heuristics.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    merge_multi_query_results,
)

if TYPE_CHECKING:
    from credit_analyzer.knowledge.registry import ConceptMatch, DomainRegistry

__all__ = [
    "expand_query",
    "expand_query_with_concepts",
    "extract_needs_context",
    "merge_retrieval_results",
    "retrieve_multi_query",
]

# ---------------------------------------------------------------------------
# Lazy domain-registry singleton
# ---------------------------------------------------------------------------
_registry: DomainRegistry | None = None


def _get_registry() -> DomainRegistry:
    """Return the module-level DomainRegistry, creating it on first use."""
    global _registry
    if _registry is None:
        from credit_analyzer.knowledge.registry import DomainRegistry as _Cls
        _registry = _Cls()
    return _registry

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


# Common credit agreement terms in lowercase mapped to their canonical
# defined-term form.  Module-level constant to avoid rebuilding on every call.
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


def _expand_baseline(question: str, max_queries: int = 3) -> list[str]:
    """Run the original alias/keyword expansion logic.

    This is the pre-registry expansion: defined-term detection, term-alias
    lookup, and financial-keyword broadening.  Extracted so that both
    ``expand_query`` and ``expand_query_with_concepts`` can reuse it.
    """
    queries: list[str] = [question]
    question_lower = question.lower()

    # Extract key noun phrases that might be defined terms
    # Look for capitalized multi-word phrases (common in credit agreements)
    defined_term_pattern = re.compile(
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    )
    terms = defined_term_pattern.findall(question)

    # Also catch fully capitalized terms like "SOFR" or "ABR"
    upper_terms = re.findall(r'\b([A-Z]{2,})\b', question)

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

    if matched_keywords and len(queries) < max_queries:
        # Add a query that targets the likely section type
        broad_query = question + " " + " ".join(matched_keywords[:3])
        if broad_query != question:
            queries.append(broad_query)

    return queries[:max_queries]


def expand_query_with_concepts(
    question: str,
) -> tuple[list[str], list[ConceptMatch]]:
    """Generate expanded retrieval queries using the domain concept registry.

    Works in three phases:

    1. **Concept matching** -- Checks the question against the domain concept
       registry.  When aliases match, builds additional queries from the
       concept's curated search terms (3-4 terms per query).
    2. **Synonym expansion** -- Adds canonical/alternative terms found via
       the synonym dictionary.
    3. **Baseline expansion** -- Runs the existing alias/keyword heuristics.

    Returns ``(queries, concept_matches)`` where *queries* always starts
    with the original question and *concept_matches* is the list of
    :class:`ConceptMatch` objects (empty when nothing matched).

    The query cap is **5** when concepts are matched, **3** otherwise.
    """
    from credit_analyzer.knowledge.registry import ConceptMatch as _CM  # noqa: F811

    registry = _get_registry()
    concept_matches: list[_CM] = registry.match_concepts(question)

    max_queries = 5 if concept_matches else 3

    queries: list[str] = [question]
    seen: set[str] = {question}

    # Phase 1: concept search-term queries
    for match in concept_matches:
        # Combine 3-4 search terms into a single query
        terms = match.search_terms
        for i in range(0, len(terms), 4):
            batch = terms[i : i + 4]
            concept_query = " ".join(batch)
            if concept_query not in seen:
                queries.append(concept_query)
                seen.add(concept_query)
            if len(queries) >= max_queries:
                break
        if len(queries) >= max_queries:
            break

    # Phase 2: synonym expansion
    if len(queries) < max_queries:
        synonym_terms = registry.expand_synonyms(question)
        if synonym_terms:
            syn_query = question + " " + " ".join(synonym_terms[:3])
            if syn_query not in seen:
                queries.append(syn_query)
                seen.add(syn_query)

    # Phase 3: baseline alias/keyword expansion
    baseline = _expand_baseline(question, max_queries=max_queries)
    for bq in baseline[1:]:  # skip the original (already first)
        if bq not in seen and len(queries) < max_queries:
            queries.append(bq)
            seen.add(bq)

    return queries[:max_queries], concept_matches


def expand_query(question: str) -> list[str]:
    """Generate additional retrieval queries from a question.

    Uses the domain concept registry (when aliases match) and rule-based
    expansion to create complementary queries that search different aspects
    of the same question.

    Returns 1-5 queries (always includes the original).  Backward compatible
    -- callers that only need the query list can continue using this function.
    """
    queries, _matches = expand_query_with_concepts(question)
    return queries


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
