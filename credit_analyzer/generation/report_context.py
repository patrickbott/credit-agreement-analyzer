"""Report context assembly and section retrieval helpers.

Builds the extraction context prompt for report sections and runs
multi-query retrieval with deduplication.
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from credit_analyzer.config import QA_DEFINITION_MAX_CHARS
from credit_analyzer.generation.report_models import format_page_numbers
from credit_analyzer.generation.report_template import RetrievalQuery
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    merge_multi_query_results,
)

__all__ = [
    "build_extraction_context",
    "retrieve_for_section",
]


def build_extraction_context(
    chunks: Sequence[HybridChunk],
    definitions: dict[str, str],
    extraction_prompt: str,
    preamble_text: str | None = None,
    preamble_page_numbers: Sequence[int] | None = None,
) -> tuple[str, list[HybridChunk]]:
    """Assemble the user prompt for a report section extraction.

    Similar to the Q&A context builder but without conversation history
    and with the extraction prompt appended instead of a question.

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
        preamble_pages = format_page_numbers(preamble_page_list)
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
    sorted_chunks = sorted(
        chunks,
        key=lambda hc: (hc.chunk.article_number, hc.chunk.section_id, hc.chunk.chunk_index),
    )

    for hc in sorted_chunks:
        c = hc.chunk
        pages = format_page_numbers(c.page_numbers)
        parts.append(
            f"[Source {source_num}] {c.section_title} "
            f"(Section {c.section_id}, pp. {pages})\n"
            f"{c.text}\n"
        )
        numbered.append(hc)
        source_num += 1

    if definitions:
        # Skip definitions whose text already appears in a chunk.
        chunk_texts = " ".join(hc.chunk.text for hc in chunks)
        filtered = {
            term: defn
            for term, defn in definitions.items()
            if defn[:80] not in chunk_texts
        }
        if filtered:
            parts.append("\n=== RELEVANT DEFINITIONS ===")
            for term, defn in filtered.items():
                truncated = defn[:QA_DEFINITION_MAX_CHARS] if len(defn) > QA_DEFINITION_MAX_CHARS else defn
                parts.append(f'"{term}" means {truncated}')

    parts.append(f"\n=== EXTRACTION TASK ===\n{extraction_prompt}")

    return "\n".join(parts), numbered


# ---------------------------------------------------------------------------
# Multi-query retrieval with deduplication
# ---------------------------------------------------------------------------


def retrieve_for_section(
    retriever: HybridRetriever,
    document_id: str,
    queries: Sequence[RetrievalQuery],
    top_k: int,
) -> RetrievalResult:
    """Run multiple retrieval queries and merge results via round-robin.

    Each query's results are kept as a separate list and merged using
    round-robin interleaving so that every query contributes proportionally
    to the final result set.  This prevents dominant queries from crowding
    out niche but important results (e.g. fee-related chunks being dropped
    because facility-size chunks score higher).

    Unfiltered queries (no section_filter) automatically exclude the
    ``miscellaneous`` section type to reduce noise.

    Args:
        retriever: The hybrid retriever instance.
        document_id: Document collection ID.
        queries: Retrieval queries to execute.
        top_k: Maximum total chunks to return after merging.

    Returns:
        Merged RetrievalResult.
    """
    per_query_results: list[list[HybridChunk]] = []
    per_query_definitions: list[dict[str, str]] = []

    def _run_query(rq: RetrievalQuery) -> RetrievalResult:
        # Unfiltered queries exclude miscellaneous to reduce noise,
        # matching the behaviour of the Q&A retrieval path.
        exclude: tuple[str, ...] | None = None
        if rq.section_filter is None:
            exclude = ("miscellaneous",)

        return retriever.retrieve(
            query=rq.query,
            document_id=document_id,
            top_k=top_k,
            section_filter=rq.section_filter,
            section_types_exclude=exclude,
        )

    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        results = list(pool.map(_run_query, queries))

    for result in results:
        per_query_results.append(result.chunks)
        per_query_definitions.append(result.injected_definitions)

    return merge_multi_query_results(
        per_query_results, per_query_definitions, top_k,
    )
