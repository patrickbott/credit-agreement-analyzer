# pyright: reportPrivateUsage=false
"""Tests for section_detector module."""

from __future__ import annotations

from credit_analyzer.processing.pdf_extractor import ExtractedDocument, ExtractedPage
from credit_analyzer.processing.section_detector import (
    SectionDetector,
    _classify_section_type,
    _offset_to_page,
    _parse_article_number,
    _roman_to_int,
)

# --- Roman numeral conversion ---


def test_roman_to_int_basic() -> None:
    assert _roman_to_int("I") == 1
    assert _roman_to_int("IV") == 4
    assert _roman_to_int("VII") == 7
    assert _roman_to_int("IX") == 9
    assert _roman_to_int("XIV") == 14


def test_roman_to_int_invalid() -> None:
    assert _roman_to_int("HELLO") == 0
    assert _roman_to_int("") == 0


def test_parse_article_number_digit() -> None:
    assert _parse_article_number("7") == 7
    assert _parse_article_number(" 12 ") == 12


def test_parse_article_number_roman() -> None:
    assert _parse_article_number("VII") == 7
    assert _parse_article_number("XII") == 12


# --- Section type classification ---


def test_classify_definitions() -> None:
    assert _classify_section_type("DEFINITIONS AND ACCOUNTING TERMS") == "definitions"
    assert _classify_section_type("Defined Terms") == "definitions"


def test_classify_covenants() -> None:
    assert _classify_section_type("NEGATIVE COVENANTS") == "negative_covenants"
    assert _classify_section_type("AFFIRMATIVE COVENANTS") == "affirmative_covenants"
    assert _classify_section_type("FINANCIAL COVENANTS") == "financial_covenants"


def test_classify_events_of_default() -> None:
    assert _classify_section_type("EVENTS OF DEFAULT") == "events_of_default"


def test_classify_facility_terms() -> None:
    assert _classify_section_type("THE CREDITS") == "facility_terms"
    assert _classify_section_type("THE LOANS AND COMMITMENTS") == "facility_terms"
    assert _classify_section_type("AMOUNT AND TERMS OF COMMITMENTS") == "facility_terms"


def test_classify_other() -> None:
    assert _classify_section_type("SOMETHING UNKNOWN") == "other"


# --- Offset to page ---


def test_offset_to_page_basic() -> None:
    offsets = (0, 100, 200)
    assert _offset_to_page(0, offsets) == 1
    assert _offset_to_page(50, offsets) == 1
    assert _offset_to_page(100, offsets) == 2
    assert _offset_to_page(150, offsets) == 2
    assert _offset_to_page(200, offsets) == 3
    assert _offset_to_page(999, offsets) == 3


# --- Helper to build a fake ExtractedDocument ---


def _make_document(page_texts: list[str]) -> ExtractedDocument:
    """Build an ExtractedDocument from a list of page text strings."""
    pages = [
        ExtractedPage(
            page_number=i + 1,
            text=text,
            tables=[],
            is_ocr=False,
        )
        for i, text in enumerate(page_texts)
    ]
    from pathlib import Path

    return ExtractedDocument(
        pages=pages,
        total_pages=len(pages),
        source_path=Path("test.pdf"),
        extraction_method="digital",
    )


# --- ARTICLE format detection ---


def test_detect_article_format_single_no_subsections() -> None:
    """An ARTICLE header with no numbered sub-sections is returned as one section."""
    text = (
        "\nARTICLE I\nDEFINITIONS\n\n"
        "This is the definitions article with lots of defined terms.\n"
        '"Available Amount" means something.\n'
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].section_id == "SECTION_1"
    assert sections[0].article_number == 1
    assert sections[0].section_type == "definitions"


def test_detect_article_format_with_subsections() -> None:
    """An ARTICLE header with numbered sub-sections is split correctly."""
    text = (
        "\nARTICLE VII\nNEGATIVE COVENANTS\n\n"
        "Section 7.01 Indebtedness\n"
        "The Borrower will not incur indebtedness.\n\n"
        "Section 7.02 Liens\n"
        "The Borrower will not create liens.\n\n"
        "Section 7.03 Investments\n"
        "The Borrower will not make investments.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 3
    assert sections[0].section_id == "7.01"
    assert sections[0].section_title == "Indebtedness"
    assert sections[0].article_title == "NEGATIVE COVENANTS"
    assert sections[0].section_type == "negative_covenants"
    assert sections[1].section_id == "7.02"
    assert sections[2].section_id == "7.03"


def test_detect_article_format_multiple() -> None:
    """Multiple ARTICLE headers are all detected and classified."""
    text = (
        "\nARTICLE I\nDEFINITIONS\n\nSome definitions here.\n\n"
        "\nARTICLE II\nTHE CREDITS\n\nSection 2.01 Commitments\nText.\n\n"
        "\nARTICLE VII\nNEGATIVE COVENANTS\n\nSection 7.01 Indebtedness\nText.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    types = [s.section_type for s in sections]
    assert "definitions" in types
    assert "facility_terms" in types
    assert "negative_covenants" in types


# --- SECTION N format detection ---


def test_detect_section_format_single() -> None:
    """SECTION N TITLE format is detected as a top-level header."""
    text = (
        "\nSECTION 1 DEFINITIONS\n\n"
        "Lots of defined terms here.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].article_number == 1
    assert sections[0].section_type == "definitions"


def test_detect_section_format_with_subsections() -> None:
    """SECTION N format with numbered sub-sections like 7.01, 7.02."""
    text = (
        "\nSECTION 7 NEGATIVE COVENANTS\n\n"
        "7.01 Indebtedness\n"
        "The Borrower will not incur indebtedness.\n\n"
        "7.02 Liens\n"
        "The Borrower will not create liens.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 2
    assert sections[0].section_id == "7.01"
    assert sections[0].section_title == "Indebtedness"
    assert sections[0].section_type == "negative_covenants"
    assert sections[1].section_id == "7.02"


def test_detect_section_format_multiple() -> None:
    """Multiple SECTION N headers are detected and classified."""
    text = (
        "\nSECTION 1 DEFINITIONS\n\nDefined terms.\n\n"
        "\nSECTION 2 AMOUNT AND TERMS OF COMMITMENTS\n\n2.1 Term Commitments\nText.\n\n"
        "\nSECTION 7 NEGATIVE COVENANTS\n\n7.1 Indebtedness\nText.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    types = [s.section_type for s in sections]
    assert "definitions" in types
    assert "facility_terms" in types
    assert "negative_covenants" in types


# --- Cross-page and edge cases ---


def test_detect_across_pages() -> None:
    """Sections spanning multiple pages get correct page_start and page_end."""
    page1 = (
        "\nSECTION 7 NEGATIVE COVENANTS\n\n"
        "7.01 Indebtedness\n"
        "The Borrower will not incur any debt that exceeds the limits.\n"
    )
    page2 = (
        "7.02 Liens\n"
        "The Borrower will not create any liens on its property.\n"
    )
    doc = _make_document([page1, page2])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 2
    assert sections[0].page_start == 1
    assert sections[1].page_start == 2


def test_fallback_no_headers() -> None:
    """If no headers are found, fall back to a single section."""
    text = "This is a weird document with no article headers at all.\nJust plain text."
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].section_id == "FULL_DOC"
    assert sections[0].section_type == "other"


def test_tables_collected_for_section() -> None:
    """Tables from pages within a section's range are included."""
    pages = [
        ExtractedPage(
            page_number=1,
            text="\nSECTION 8 EVENTS OF DEFAULT\n\n8.01 Payment Default\nSee table.\n",
            tables=["| Type | Cure Period |\n| --- | --- |\n| Payment | 5 days |"],
            is_ocr=False,
        ),
    ]
    from pathlib import Path

    doc = ExtractedDocument(
        pages=pages,
        total_pages=1,
        source_path=Path("test.pdf"),
        extraction_method="digital",
    )
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert len(sections[0].tables) == 1
    assert "Payment" in sections[0].tables[0]


def test_tables_retained_on_last_page_of_multi_page_section() -> None:
    """A section keeps tables on its final page when no later section shares it."""
    pages = [
        ExtractedPage(
            page_number=1,
            text="\nSECTION 7 NEGATIVE COVENANTS\n\n7.01 Indebtedness\nText continues.\n",
            tables=[],
            is_ocr=False,
        ),
        ExtractedPage(
            page_number=2,
            text="More section 7.01 text.\n",
            tables=["| Basket | Amount |\n| --- | --- |\n| General | $50M |"],
            is_ocr=False,
        ),
    ]
    from pathlib import Path

    doc = ExtractedDocument(
        pages=pages,
        total_pages=2,
        source_path=Path("test.pdf"),
        extraction_method="digital",
    )
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].page_start == 1
    assert sections[0].page_end == 2
    assert len(sections[0].tables) == 1
    assert "General" in sections[0].tables[0]


def test_duplicate_numbers_skipped() -> None:
    """TOC references that repeat header numbers are skipped."""
    text = (
        "SECTION 1 DEFINITIONS......1\n"
        "SECTION 2 THE CREDITS......5\n\n"
        "End of table of contents\n\n"
        "\nSECTION 1 DEFINITIONS\n\nActual content here.\n\n"
        "\nSECTION 2 THE CREDITS\n\nMore content.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    # Article 0 = preamble (TOC text before real headers), 1 and 2 = real
    article_numbers = {s.article_number for s in sections}
    assert article_numbers == {0, 1, 2}
    assert sections[0].section_type == "preamble"


def test_roman_numeral_article_detection() -> None:
    """Articles numbered with Roman numerals are parsed correctly."""
    text = (
        "\nARTICLE XIV\nMISCELLANEOUS\n\n"
        "Section 14.01 Notices\nAll notices shall be in writing.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].article_number == 14
    assert sections[0].section_id == "14.01"
    assert sections[0].section_type == "miscellaneous"


# --- Preamble detection ---


def test_preamble_captured_with_recitals() -> None:
    """Pre-article content (recitals, parties, facility sizes) is captured as preamble."""
    text = (
        "CREDIT AGREEMENT\n\n"
        "dated as of March 3, 2020\n\n"
        "among\n\n"
        "RIBBON COMMUNICATIONS INC., as Borrower\n"
        "CITIZENS BANK, N.A., as Administrative Agent\n\n"
        "$350,000,000 Term Loan Facility\n"
        "$35,000,000 Revolving Credit Facility\n\n"
        "RECITALS\n\n"
        "The Borrower has requested that the Lenders provide a $350,000,000 "
        "term loan facility and a $35,000,000 revolving credit facility.\n\n"
        "\nARTICLE I\nDEFINITIONS\n\n"
        "Defined terms here.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    preamble = sections[0]
    assert preamble.section_type == "preamble"
    assert preamble.section_id == "PREAMBLE"
    assert preamble.article_number == 0
    assert "$350,000,000" in preamble.text
    assert "RIBBON COMMUNICATIONS" in preamble.text
    assert preamble.page_start == 1

    # The definitions article should follow
    assert sections[1].section_type == "definitions"


def test_no_preamble_when_article_starts_immediately() -> None:
    """No preamble section is created when the first article starts at the top."""
    text = (
        "\nARTICLE I\nDEFINITIONS\n\n"
        "Some defined terms.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert sections[0].section_type == "definitions"
    assert all(s.section_type != "preamble" for s in sections)


def test_article_format_preferred_over_section_format() -> None:
    """If ARTICLE headers are found, SECTION N headers are not used as top-level."""
    text = (
        "\nARTICLE I\nDEFINITIONS\n\nTerms here.\n\n"
        "\nARTICLE II\nTHE CREDITS\n\nSection 2.01 Commitments\nText.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    # Should use ARTICLE format, not SECTION format
    types = [s.section_type for s in sections]
    assert "definitions" in types
    assert "facility_terms" in types
