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
from datetime import datetime

from credit_analyzer.config import REPORT_MAX_WORKERS
from credit_analyzer.generation.report_context import (
    build_extraction_context,
    retrieve_for_section,
)
from credit_analyzer.generation.report_models import (
    GeneratedReport,
    GeneratedSection,
    format_page_numbers,
)
from credit_analyzer.generation.report_template import (
    ALL_REPORT_SECTIONS,
    ReportSectionTemplate,
    get_extraction_system_prompt,
)
from credit_analyzer.generation.response_parser import (
    build_citations_from_chunks,
    citations_from_chunks,
    extract_answer_body,
    parse_confidence,
)
from credit_analyzer.llm.base import LLMProvider, LLMResponse
from credit_analyzer.retrieval.hybrid_retriever import (
    HybridRetriever,
)
from credit_analyzer.utils.text_cleaning import strip_markdown as _strip_markdown

logger = logging.getLogger(__name__)

ReportProgressCallback = Callable[[str, float], None]
SectionCallback = Callable[["GeneratedSection"], None]

# Re-export moved helpers under their original private names so that
# existing imports (including tests) continue to work.
_build_extraction_context = build_extraction_context
_retrieve_for_section = retrieve_for_section
_format_page_numbers = format_page_numbers


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
        section_callback: SectionCallback | None = None,
    ) -> GeneratedReport:
        """Generate a full report for a processed document.

        Args:
            document_id: The document collection to query.
            sections: Section templates to generate (defaults to all 10).
            progress_callback: Called with (label, progress_fraction) as
                each section completes.
            section_callback: Called with a completed ``GeneratedSection``
                as soon as it finishes, enabling progressive rendering.

        Returns:
            A GeneratedReport with all sections.
        """
        logger.info("Starting report generation: %d sections", len(sections))

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
                generated = self.generate_section(
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
            if section_callback is not None:
                section_callback(generated)

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
                    return self.generate_section(
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
                    if section_callback is not None:
                        section_callback(section_result)

            # Append in original section order
            for t in remaining_sections:
                report.sections.append(results_map[t.section_number])

        # Track wall-clock time instead of sum of section times
        report.total_duration_seconds = time.monotonic() - wall_clock_start

        logger.info(
            "Report generation complete: sections=%d, total_time=%.2fs",
            len(report.sections), report.total_duration_seconds or 0.0,
        )
        _notify(progress_callback, "Report complete.", 1.0)
        return report

    def generate_section(
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
        logger.info(
            "Generating section %d: %s",
            template.section_number, template.title,
        )
        section_start = time.monotonic()

        # Retrieve context via multi-query
        result = retrieve_for_section(
            self._retriever,
            document_id,
            template.retrieval_queries,
            template.top_k,
        )

        preamble = self._preamble_text if template.include_preamble else None

        # Assemble context + extraction prompt
        user_prompt, numbered_chunks = build_extraction_context(
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

        section_duration = time.monotonic() - section_start
        logger.info(
            "Section %d (%s) complete: confidence=%s, chunks=%d, time=%.2fs",
            template.section_number, template.title, confidence,
            len(result.chunks), section_duration,
        )

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
        # Strip trailing citation markers like [1] and (Preamble, p. 9)
        name = re.sub(r"\s*\[\d+\]", "", name)
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
