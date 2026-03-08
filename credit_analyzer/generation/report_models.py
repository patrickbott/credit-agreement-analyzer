"""Report data models and formatting helpers.

Contains the GeneratedSection and GeneratedReport dataclasses, plus
the _format_page_numbers helper used during context assembly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from credit_analyzer.generation.citation_models import (
    ConfidenceLevel,
    InlineCitation,
    SourceCitation,
)
from credit_analyzer.generation.report_template import SectionStatus

__all__ = [
    "GeneratedReport",
    "GeneratedSection",
    "format_page_numbers",
]


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
    inline_citations: list[InlineCitation] = field(default_factory=lambda: list[InlineCitation]())


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


def format_page_numbers(pages: Sequence[int]) -> str:
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
