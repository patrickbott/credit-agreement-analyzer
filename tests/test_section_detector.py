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


def test_classify_other() -> None:
    assert _classify_section_type("SOMETHING UNKNOWN") == "other"


# --- Offset to page ---


def test_offset_to_page_basic() -> None:
    # Three pages starting at offsets 0, 100, 200
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


# --- Full detection tests ---


def test_detect_single_article_no_sections() -> None:
    """An article with no numbered sections is returned as one DocumentSection."""
    text = (
        "\nARTICLE I\nDEFINITIONS\n\n"
        "This is the definitions article with lots of defined terms.\n"
        '"Available Amount" means something.\n'
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 1
    assert sections[0].section_id == "ARTICLE_1"
    assert sections[0].article_number == 1
    assert sections[0].section_type == "definitions"
    assert sections[0].page_start == 1
    assert sections[0].page_end == 1


def test_detect_article_with_sections() -> None:
    """An article with numbered sub-sections is split correctly."""
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


def test_detect_multiple_articles() -> None:
    """Multiple articles are all detected and classified."""
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


def test_detect_across_pages() -> None:
    """Sections spanning multiple pages get correct page_start and page_end."""
    page1 = (
        "\nARTICLE VII\nNEGATIVE COVENANTS\n\n"
        "Section 7.01 Indebtedness\n"
        "The Borrower will not incur any debt that exceeds the limits.\n"
    )
    page2 = (
        "Section 7.02 Liens\n"
        "The Borrower will not create any liens on its property.\n"
    )
    doc = _make_document([page1, page2])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    assert len(sections) == 2
    assert sections[0].page_start == 1
    # Section 7.02 starts on page 2
    assert sections[1].page_start == 2


def test_fallback_no_articles() -> None:
    """If no ARTICLE headers are found, fall back to a single section."""
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
            text="\nARTICLE VIII\nFINANCIAL COVENANTS\n\nSection 8.01 Leverage Ratio\nSee table.\n",
            tables=["| Ratio | Limit |\n| --- | --- |\n| Leverage | 4.50x |"],
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
    assert "Leverage" in sections[0].tables[0]


def test_duplicate_article_numbers_skipped() -> None:
    """TOC references that repeat article numbers are skipped."""
    text = (
        "ARTICLE I - DEFINITIONS......1\n"
        "ARTICLE II - THE CREDITS......5\n\n"
        "End of table of contents\n\n"
        "\nARTICLE I\nDEFINITIONS\n\nActual content here.\n\n"
        "\nARTICLE II\nTHE CREDITS\n\nMore content.\n"
    )
    doc = _make_document([text])
    detector = SectionDetector()
    sections = detector.detect_sections(doc)

    # Should only have 2 articles, not 4
    article_numbers = {s.article_number for s in sections}
    assert article_numbers == {1, 2}


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
