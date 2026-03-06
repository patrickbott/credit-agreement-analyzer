"""Report generator: orchestrates multi-section credit agreement reports.

For each report section, runs targeted retrieval queries, merges and
deduplicates context chunks, assembles the extraction prompt, calls the
LLM, and parses the response.  Produces a final markdown document with
title, date, disclaimer, and all sections.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from credit_analyzer.config import QA_DEFINITION_MAX_CHARS, REPORT_MAX_WORKERS
from credit_analyzer.generation.report_template import (
    ALL_REPORT_SECTIONS,
    ReportSectionTemplate,
    RetrievalQuery,
    SectionStatus,
    get_extraction_system_prompt,
)
from credit_analyzer.generation.response_parser import (
    ConfidenceLevel,
    SourceCitation,
    build_citations_from_chunks,
    citations_from_chunks,
    extract_answer_body,
    parse_confidence,
)
from credit_analyzer.llm.base import LLMProvider, LLMResponse
from credit_analyzer.processing.chunker import Chunk
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridChunk,
    HybridRetriever,
    RetrievalResult,
    merge_multi_query_results,
)
from credit_analyzer.utils.text_cleaning import strip_markdown as _strip_markdown

logger = logging.getLogger(__name__)

ReportProgressCallback = Callable[[str, float], None]


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------


@dataclass
class GeneratedSection:
    """One completed section of the report.

    Attributes:
        section_number: Display order.
        title: Section heading.
        body: The extracted content (plain text, no markdown formatting).
        confidence: LLM-assessed confidence level.
        sources: Parsed source citations.
        status: Whether the section completed successfully.
        error_message: Error detail if status is "error".
        duration_seconds: LLM call duration.
        chunk_count: Number of context chunks used.
    """

    section_number: int
    title: str
    body: str
    confidence: ConfidenceLevel
    sources: list[SourceCitation]
    status: SectionStatus
    error_message: str = ""
    duration_seconds: float = 0.0
    chunk_count: int = 0
    inline_citations: list = field(default_factory=list)


@dataclass
class GeneratedReport:
    """A complete generated report.

    Attributes:
        borrower_name: Extracted borrower name (for the title).
        generated_at: Timestamp of generation.
        sections: All generated sections in order.
        total_duration_seconds: Sum of all LLM call durations.
    """

    borrower_name: str
    generated_at: datetime
    sections: list[GeneratedSection] = field(default_factory=lambda: list[GeneratedSection]())
    total_duration_seconds: float = 0.0

    def to_markdown(self) -> str:
        """Assemble the full report as a plain-text markdown document."""
        lines: list[str] = []
        lines.append(f"# Credit Agreement Analysis: {self.borrower_name}")
        lines.append(f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append(
            "DISCLAIMER: This report is auto-generated and should be "
            "verified against the source document. Extraction may be "
            "incomplete for non-standard agreement formats."
        )

        for section in self.sections:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(
                f"## Section {section.section_number}: {section.title}"
            )
            lines.append("")

            if section.status == "error":
                lines.append(
                    f"GENERATION ERROR: {section.error_message}"
                )
                continue

            if section.status == "pending":
                lines.append("(Not yet generated)")
                continue

            lines.append(section.body)
            lines.append("")

            # Confidence
            lines.append(f"Confidence: {section.confidence}")

            # Sources
            if section.sources:
                source_strs: list[str] = []
                for src in section.sources:
                    pages = ", ".join(str(p) for p in src.page_numbers)
                    if pages:
                        source_strs.append(
                            f"Section {src.section_id} (pp. {pages})"
                        )
                    else:
                        source_strs.append(f"Section {src.section_id}")
                lines.append(f"Sources: {', '.join(source_strs)}")

        lines.append("")
        lines.append("---")
        lines.append(
            f"Total generation time: "
            f"{self.total_duration_seconds:.1f}s"
        )
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context assembly for report sections
# ---------------------------------------------------------------------------


def _format_page_numbers(pages: Sequence[int]) -> str:
    """Compact page range string (e.g. [62,63,64] -> '62-64')."""
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


def _build_extraction_context(
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


def _retrieve_for_section(
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




# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Orchestrates multi-section credit agreement report generation.

    For each section template, runs targeted retrieval, assembles context,
    calls the LLM with the extraction prompt, and parses the response.
    Supports a progress callback for UI integration.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        llm: LLMProvider,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._preamble_text: str | None = None
        self._preamble_page_numbers: list[int] | None = None

    def set_preamble(
        self,
        text: str,
        page_numbers: Sequence[int] | None = None,
    ) -> None:
        """Set preamble text to inject in sections that request it.

        Args:
            text: The preamble/recitals text from the document.
            page_numbers: Optional page numbers spanned by the preamble.
        """
        self._preamble_text = text.strip() if text.strip() else None
        self._preamble_page_numbers = list(page_numbers) if page_numbers else None

    def generate(
        self,
        document_id: str,
        *,
        sections: Sequence[ReportSectionTemplate] = ALL_REPORT_SECTIONS,
        progress_callback: ReportProgressCallback | None = None,
    ) -> GeneratedReport:
        """Generate a full report for a processed document.

        Args:
            document_id: The document collection to query.
            sections: Section templates to generate (defaults to all 10).
            progress_callback: Called with (label, progress_fraction) as
                each section completes.

        Returns:
            A GeneratedReport with all sections.
        """
        report = GeneratedReport(
            borrower_name="(Unknown Borrower)",
            generated_at=datetime.now(),
        )

        total = len(sections)
        system_prompt = get_extraction_system_prompt()
        wall_clock_start = time.monotonic()

        # --- Phase 1: Generate Section 1 first (extracts borrower name) ---
        first_section = sections[0] if sections else None
        remaining_sections = list(sections[1:]) if len(sections) > 1 else []

        if first_section is not None:
            _notify(
                progress_callback,
                f"Generating: {first_section.title}...",
                0.0,
            )
            try:
                generated = self._generate_section(
                    first_section, document_id, system_prompt
                )
            except Exception as exc:
                logger.exception(
                    "Failed to generate section %d: %s",
                    first_section.section_number,
                    first_section.title,
                )
                generated = GeneratedSection(
                    section_number=first_section.section_number,
                    title=first_section.title,
                    body="",
                    confidence="LOW",
                    sources=[],
                    status="error",
                    error_message=str(exc),
                )

            report.sections.append(generated)

            if first_section.section_number == 1 and generated.status == "complete":
                borrower = _extract_borrower_name(generated.body)
                if borrower:
                    report.borrower_name = borrower

        # --- Phase 2: Generate remaining sections in parallel ---
        if remaining_sections:
            completed_count = 1  # Section 1 already done

            def _generate_with_error_handling(
                template: ReportSectionTemplate,
            ) -> GeneratedSection:
                try:
                    return self._generate_section(
                        template, document_id, system_prompt
                    )
                except Exception as exc:
                    logger.exception(
                        "Failed to generate section %d: %s",
                        template.section_number,
                        template.title,
                    )
                    return GeneratedSection(
                        section_number=template.section_number,
                        title=template.title,
                        body="",
                        confidence="LOW",
                        sources=[],
                        status="error",
                        error_message=str(exc),
                    )

            with ThreadPoolExecutor(max_workers=REPORT_MAX_WORKERS) as pool:
                future_to_template = {
                    pool.submit(_generate_with_error_handling, t): t
                    for t in remaining_sections
                }

                results_map: dict[int, GeneratedSection] = {}
                for future in as_completed(future_to_template):
                    section_result = future.result()
                    results_map[section_result.section_number] = section_result
                    completed_count += 1
                    _notify(
                        progress_callback,
                        f"Completed: {section_result.title}",
                        completed_count / max(total, 1),
                    )

            # Append in original section order
            for t in remaining_sections:
                report.sections.append(results_map[t.section_number])

        # Track wall-clock time instead of sum of section times
        report.total_duration_seconds = time.monotonic() - wall_clock_start

        _notify(progress_callback, "Report complete.", 1.0)
        return report

    def _generate_section(
        self,
        template: ReportSectionTemplate,
        document_id: str,
        system_prompt: str,
    ) -> GeneratedSection:
        """Generate a single report section.

        Args:
            template: The section template.
            document_id: Document collection ID.
            system_prompt: Shared extraction system prompt.

        Returns:
            A completed GeneratedSection.
        """
        # Retrieve context via multi-query
        result = _retrieve_for_section(
            self._retriever,
            document_id,
            template.retrieval_queries,
            template.top_k,
        )

        preamble = self._preamble_text if template.include_preamble else None

        # Assemble context + extraction prompt
        user_prompt, numbered_chunks = _build_extraction_context(
            chunks=result.chunks,
            definitions=result.injected_definitions,
            extraction_prompt=template.extraction_prompt,
            preamble_text=preamble,
            preamble_page_numbers=self._preamble_page_numbers,
        )

        # Call LLM
        llm_response: LLMResponse = self._llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=template.max_generation_tokens,
        )

        raw_text = llm_response.text
        body = _strip_markdown(extract_answer_body(raw_text))
        confidence = parse_confidence(raw_text)
        sources = citations_from_chunks(result.chunks)
        inline_cites, body = build_citations_from_chunks(body, numbered_chunks)

        return GeneratedSection(
            section_number=template.section_number,
            title=template.title,
            body=body,
            confidence=confidence,
            sources=sources,
            status="complete",
            duration_seconds=llm_response.duration_seconds,
            chunk_count=len(result.chunks),
            inline_citations=inline_cites,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_borrower_name(section_body: str) -> str | None:
    """Try to pull the borrower name from the Transaction Overview output.

    Looks for patterns like ``BORROWER: Some Corp LLC`` in the LLM output.

    Args:
        section_body: The body text from section 1.

    Returns:
        The borrower name if found, otherwise None.
    """
    # Try "BORROWER: Name" on one line first.
    match = re.search(
        r"(?i)BORROWER\s*:\s*(.+?)(?:\n|$)", section_body
    )
    if not match:
        # Try "BORROWER\n Name" where name is on the next non-empty line.
        match = re.search(
            r"(?i)BORROWER\s*\n+\s*(.+?)(?:\n|$)", section_body
        )
    if match:
        name = match.group(1).strip().rstrip(".")
        # Strip trailing citation like "(Preamble, p. 9)"
        name = re.sub(r"\s*\(.*$", "", name).strip().rstrip(",.")
        if name and name.upper() not in ("NOT FOUND", "NOT IDENTIFIED IN THE PROVIDED CONTEXT"):
            return name
    return None


def _notify(
    callback: ReportProgressCallback | None,
    label: str,
    progress: float,
) -> None:
    """Fire progress callback if provided."""
    if callback is not None:
        callback(label, progress)
