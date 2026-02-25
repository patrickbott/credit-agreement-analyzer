"""Detect structural sections (articles, sections) in a credit agreement."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from credit_analyzer.processing.pdf_extractor import ExtractedDocument

# Page delimiter inserted between pages when building full text
_PAGE_DELIMITER = "\n\n"

# Known section type classifications based on article title keywords
SectionType = Literal[
    "definitions",
    "facility_terms",
    "conditions",
    "representations",
    "affirmative_covenants",
    "negative_covenants",
    "financial_covenants",
    "events_of_default",
    "agents",
    "miscellaneous",
    "guaranty",
    "collateral",
    "exhibits",
    "schedules",
    "other",
]

# Mapping of title keywords (lowercased) to section types.
# Order matters: first match wins, so more specific patterns come first.
_SECTION_TYPE_KEYWORDS: tuple[tuple[str, SectionType], ...] = (
    ("financial covenant", "financial_covenants"),
    ("negative covenant", "negative_covenants"),
    ("affirmative covenant", "affirmative_covenants"),
    ("event of default", "events_of_default"),
    ("events of default", "events_of_default"),
    ("definition", "definitions"),
    ("defined terms", "definitions"),
    ("condition", "conditions"),
    ("conditions precedent", "conditions"),
    ("representation", "representations"),
    ("warranties", "representations"),
    ("the credit", "facility_terms"),
    ("the loan", "facility_terms"),
    ("amounts and terms", "facility_terms"),
    ("commitments", "facility_terms"),
    ("agent", "agents"),
    ("administrative agent", "agents"),
    ("miscellaneous", "miscellaneous"),
    ("general provisions", "miscellaneous"),
    ("guaranty", "guaranty"),
    ("guarantee", "guaranty"),
    ("collateral", "collateral"),
    ("security", "collateral"),
    ("pledge", "collateral"),
    ("exhibit", "exhibits"),
    ("schedule", "schedules"),
)

# Regex for article headers.
# Matches patterns like:
#   ARTICLE VII - NEGATIVE COVENANTS
#   ARTICLE 7 -- Negative Covenants
#   Article VII
#   ARTICLE VII\nNEGATIVE COVENANTS
_ARTICLE_PATTERN = re.compile(
    r"(?:^|\n)\s*"
    r"ARTICLE\s+([IVXLCDM]+|\d+)"
    r"\s*[:\-\x97\u2014\u2013.]*\s*\n?\s*"
    # Keep titles on a single line; using explicit space avoids consuming the next header line.
    r"([A-Z][A-Za-z0-9 ,&()'/-]+)",
    re.MULTILINE,
)

# Regex for section headers within articles.
# Matches patterns like:
#   Section 7.06  Restricted Payments
#   SECTION 7.06. Restricted Payments
#   7.06 Restricted Payments
_SECTION_HEADER_PATTERN = re.compile(
    r"(?:^|\n)\s*"
    r"(?:SECTION|Section)?\s*"
    r"(\d+\.\d+)"
    r"\s*[.:]?\s+"
    r"([A-Za-z][^\n.;]{2,80})",
    re.MULTILINE,
)

# Roman numeral values for conversion
_ROMAN_VALUES: tuple[tuple[str, int], ...] = (
    ("M", 1000),
    ("CM", 900),
    ("D", 500),
    ("CD", 400),
    ("C", 100),
    ("XC", 90),
    ("L", 50),
    ("XL", 40),
    ("X", 10),
    ("IX", 9),
    ("V", 5),
    ("IV", 4),
    ("I", 1),
)


@dataclass
class DocumentSection:
    """A structural section detected in a credit agreement."""

    section_id: str  # e.g. "7.06" or "ARTICLE_7" for article-level
    article_number: int
    section_title: str
    article_title: str
    text: str
    page_start: int  # 1-indexed
    page_end: int  # 1-indexed
    tables: list[str]
    section_type: SectionType


def _roman_to_int(roman: str) -> int:
    """Convert a Roman numeral string to an integer.

    Args:
        roman: Uppercase Roman numeral string (e.g. "VII").

    Returns:
        Integer value. Returns 0 if the string is not a valid Roman numeral.
    """
    result = 0
    remaining = roman.upper()
    for numeral, value in _ROMAN_VALUES:
        while remaining.startswith(numeral):
            result += value
            remaining = remaining[len(numeral) :]
    if remaining:
        # Leftover characters means it wasn't a clean Roman numeral
        return 0
    return result


def _parse_article_number(raw: str) -> int:
    """Parse an article number from either a digit string or Roman numeral.

    Args:
        raw: The raw string from the regex match (e.g. "7" or "VII").

    Returns:
        Integer article number. Returns 0 if parsing fails.
    """
    stripped = raw.strip()
    if stripped.isdigit():
        return int(stripped)
    return _roman_to_int(stripped)


def _classify_section_type(article_title: str) -> SectionType:
    """Classify an article into a section type based on its title.

    Args:
        article_title: The article title text.

    Returns:
        The best-matching SectionType.
    """
    lower_title = article_title.lower()
    for keyword, section_type in _SECTION_TYPE_KEYWORDS:
        if keyword in lower_title:
            return section_type
    return "other"


def _offset_to_page(offset: int, page_offsets: tuple[int, ...]) -> int:
    """Convert a character offset in the full text to a 1-indexed page number.

    Args:
        offset: Character position in the concatenated full text.
        page_offsets: Tuple of starting character offsets for each page.

    Returns:
        1-indexed page number.
    """
    for i in range(len(page_offsets) - 1, -1, -1):
        if offset >= page_offsets[i]:
            return i + 1
    return 1


def _collect_tables_for_pages(
    document: ExtractedDocument, page_start: int, page_end: int
) -> list[str]:
    """Gather all table markdown strings from pages in the given range.

    Args:
        document: The source extracted document.
        page_start: 1-indexed start page (inclusive).
        page_end: 1-indexed end page (inclusive).

    Returns:
        List of markdown table strings.
    """
    tables: list[str] = []
    for page in document.pages:
        if page_start <= page.page_number <= page_end:
            tables.extend(page.tables)
    return tables


@dataclass
class _ArticleBoundary:
    """Internal representation of a detected article."""

    article_number: int
    article_title: str
    section_type: SectionType
    text_start: int  # character offset in full text
    text_end: int  # character offset in full text


class SectionDetector:
    """Detects article and section boundaries in a credit agreement.

    Uses regex patterns to identify ARTICLE and Section headers, then
    classifies each article by type. Falls back to treating the entire
    document as a single section if no articles are detected.
    """

    def detect_sections(self, document: ExtractedDocument) -> list[DocumentSection]:
        """Detect structural sections from an extracted document.

        Args:
            document: The extracted PDF document.

        Returns:
            List of DocumentSection objects, ordered by position in the document.
        """
        full_text, page_offsets = self._build_full_text(document)
        articles = self._detect_articles(full_text)

        if not articles:
            return self._fallback_single_section(document, full_text)

        # Set text_end boundaries: each article ends where the next one starts
        for i in range(len(articles) - 1):
            articles[i].text_end = articles[i + 1].text_start
        articles[-1].text_end = len(full_text)

        sections: list[DocumentSection] = []
        for article in articles:
            article_text = full_text[article.text_start : article.text_end]
            article_sections = self._detect_sections_in_article(
                article, article_text, full_text, page_offsets, document
            )
            if article_sections:
                sections.extend(article_sections)
            else:
                # No sub-sections found; treat entire article as one section
                page_start = _offset_to_page(article.text_start, page_offsets)
                page_end = _offset_to_page(
                    max(article.text_end - 1, article.text_start), page_offsets
                )
                sections.append(
                    DocumentSection(
                        section_id=f"ARTICLE_{article.article_number}",
                        article_number=article.article_number,
                        section_title=article.article_title.strip(),
                        article_title=article.article_title.strip(),
                        text=article_text,
                        page_start=page_start,
                        page_end=page_end,
                        tables=_collect_tables_for_pages(
                            document, page_start, page_end
                        ),
                        section_type=article.section_type,
                    )
                )

        return sections

    def _build_full_text(
        self, document: ExtractedDocument
    ) -> tuple[str, tuple[int, ...]]:
        """Concatenate all page texts and track page character offsets.

        Args:
            document: The extracted document.

        Returns:
            Tuple of (full_text, page_offsets) where page_offsets[i] is the
            character offset where page i+1 starts.
        """
        parts: list[str] = []
        offsets: list[int] = []
        current_offset = 0

        for page in document.pages:
            offsets.append(current_offset)
            parts.append(page.text)
            current_offset += len(page.text) + len(_PAGE_DELIMITER)

        full_text = _PAGE_DELIMITER.join(parts)
        return full_text, tuple(offsets)

    def _detect_articles(self, full_text: str) -> list[_ArticleBoundary]:
        """Find all article headers in the full text.

        Args:
            full_text: Concatenated document text.

        Returns:
            List of _ArticleBoundary objects sorted by position.
        """
        matches = list(_ARTICLE_PATTERN.finditer(full_text))
        if not matches:
            return []

        articles: list[_ArticleBoundary] = []
        seen_numbers: set[int] = set()

        for match in matches:
            article_num = _parse_article_number(match.group(1))
            if article_num == 0:
                continue

            # Skip duplicate article numbers (likely TOC references)
            if article_num in seen_numbers:
                continue
            seen_numbers.add(article_num)

            title = match.group(2).strip().rstrip(",").strip()
            articles.append(
                _ArticleBoundary(
                    article_number=article_num,
                    article_title=title,
                    section_type=_classify_section_type(title),
                    text_start=match.start(),
                    text_end=0,  # set later
                )
            )

        return articles

    def _detect_sections_in_article(
        self,
        article: _ArticleBoundary,
        article_text: str,
        full_text: str,
        page_offsets: tuple[int, ...],
        document: ExtractedDocument,
    ) -> list[DocumentSection]:
        """Find numbered sections within an article.

        Args:
            article: The parent article boundary.
            article_text: Text of just this article.
            full_text: Full concatenated document text.
            page_offsets: Page offset mapping.
            document: Source document for table collection.

        Returns:
            List of DocumentSection objects for sub-sections, or empty if none found.
        """
        matches = list(_SECTION_HEADER_PATTERN.finditer(article_text))

        # Filter to only sections belonging to this article
        article_prefix = f"{article.article_number}."
        matches = [m for m in matches if m.group(1).startswith(article_prefix)]

        if not matches:
            return []

        sections: list[DocumentSection] = []
        for i, match in enumerate(matches):
            section_id = match.group(1)
            section_title = match.group(2).strip().rstrip(".")

            # Section text runs from this match to the next match (or end of article)
            text_start_in_article = match.start()
            # Use the section number start for page attribution so leading newlines
            # (which may belong to the prior page) do not shift page_start backward.
            header_start_in_article = match.start(1)
            if i + 1 < len(matches):
                text_end_in_article = matches[i + 1].start()
            else:
                text_end_in_article = len(article_text)

            section_text = article_text[text_start_in_article:text_end_in_article]

            # Convert offsets back to full-text offsets for page lookup
            abs_start = article.text_start + header_start_in_article
            abs_end = article.text_start + text_end_in_article
            page_start = _offset_to_page(abs_start, page_offsets)
            page_end = _offset_to_page(max(abs_end - 1, abs_start), page_offsets)

            sections.append(
                DocumentSection(
                    section_id=section_id,
                    article_number=article.article_number,
                    section_title=section_title,
                    article_title=article.article_title.strip(),
                    text=section_text,
                    page_start=page_start,
                    page_end=page_end,
                    tables=_collect_tables_for_pages(document, page_start, page_end),
                    section_type=article.section_type,
                )
            )

        return sections

    def _fallback_single_section(
        self, document: ExtractedDocument, full_text: str
    ) -> list[DocumentSection]:
        """Fallback when no articles are detected: return the entire document as one section.

        Args:
            document: The source document.
            full_text: Concatenated full text.

        Returns:
            Single-element list with the whole document as one section.
        """
        all_tables: list[str] = []
        for page in document.pages:
            all_tables.extend(page.tables)

        return [
            DocumentSection(
                section_id="FULL_DOC",
                article_number=0,
                section_title="Full Document",
                article_title="Full Document",
                text=full_text,
                page_start=1,
                page_end=document.total_pages,
                tables=all_tables,
                section_type="other",
            )
        ]
