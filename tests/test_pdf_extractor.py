"""Tests for processing.pdf_extractor."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from credit_analyzer.processing.pdf_extractor import (
    PDFExtractor,
    _table_to_markdown,  # type: ignore[reportPrivateUsage]
)

# ---------------------------------------------------------------------------
# Unit tests -- _table_to_markdown
# ---------------------------------------------------------------------------


def test_table_to_markdown_basic() -> None:
    table: Sequence[Sequence[str | None]] = [["Header A", "Header B"], ["cell 1", "cell 2"]]
    result = _table_to_markdown(table)
    assert "Header A" in result
    assert "Header B" in result
    assert "cell 1" in result
    assert "---" in result


def test_table_to_markdown_none_cells() -> None:
    table: Sequence[Sequence[str | None]] = [["Col A", None], [None, "val"]]
    result = _table_to_markdown(table)
    assert "Col A" in result
    assert "val" in result


def test_table_to_markdown_empty() -> None:
    assert _table_to_markdown([]) == ""


def test_table_to_markdown_newlines_in_cells() -> None:
    table: Sequence[Sequence[str | None]] = [["Multi\nline", "Normal"], ["a\nb", "c"]]
    result = _table_to_markdown(table)
    # Cell content should have newlines replaced with spaces
    assert "\n" not in result.split("|")[1].strip()


# ---------------------------------------------------------------------------
# Unit tests -- PDFExtractor (mocked fitz + pdfplumber)
# ---------------------------------------------------------------------------


@pytest.fixture()
def extractor() -> PDFExtractor:
    return PDFExtractor()


def _make_fitz_page(text: str) -> MagicMock:
    page = MagicMock()
    page.get_text.return_value = text
    return page


def _make_fitz_doc(pages: list[MagicMock]) -> MagicMock:
    doc = MagicMock()
    doc.__len__ = MagicMock(return_value=len(pages))
    doc.__getitem__ = MagicMock(side_effect=lambda i: pages[i])  # type: ignore[reportUnknownLambdaType]
    return doc


def _make_plumber_page(tables: list[list[list[str]]] | None = None) -> MagicMock:
    page = MagicMock()
    page.extract_tables.return_value = tables or []
    return page


def _make_plumber_doc(pages: list[MagicMock]) -> MagicMock:
    doc = MagicMock()
    doc.pages = pages
    return doc


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
def test_extract_digital_pdf(
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    """Digital PDF with text > threshold should not trigger OCR."""
    long_text = "A" * 200
    fitz_pages = [_make_fitz_page(long_text), _make_fitz_page(long_text)]
    fitz_doc = _make_fitz_doc(fitz_pages)
    fitz_doc.close = MagicMock()

    plumber_pages = [_make_plumber_page(), _make_plumber_page()]
    plumber_doc = _make_plumber_doc(plumber_pages)
    plumber_doc.close = MagicMock()

    mock_fitz_open.return_value = fitz_doc
    mock_plumber_open.return_value = plumber_doc

    pdf_file = tmp_path / "test.pdf"
    pdf_file.touch()

    doc = extractor.extract(pdf_file)

    assert doc.total_pages == 2
    assert doc.extraction_method == "digital"
    assert all(not p.is_ocr for p in doc.pages)
    assert doc.pages[0].page_number == 1
    assert doc.pages[1].page_number == 2
    assert doc.pages[0].text == long_text


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
@patch("credit_analyzer.processing.pdf_extractor._ocr_page")
def test_extract_ocr_fallback(
    mock_ocr: MagicMock,
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    """Short text on a page should trigger OCR fallback."""
    mock_ocr.return_value = "OCR extracted text from scanned page"

    fitz_pages = [_make_fitz_page("short")]  # < threshold
    fitz_doc = _make_fitz_doc(fitz_pages)
    fitz_doc.close = MagicMock()

    plumber_pages = [_make_plumber_page()]
    plumber_doc = _make_plumber_doc(plumber_pages)
    plumber_doc.close = MagicMock()

    mock_fitz_open.return_value = fitz_doc
    mock_plumber_open.return_value = plumber_doc

    pdf_file = tmp_path / "scanned.pdf"
    pdf_file.touch()

    doc = extractor.extract(pdf_file)

    assert doc.total_pages == 1
    assert doc.extraction_method == "ocr"
    assert doc.pages[0].is_ocr is True
    assert doc.pages[0].text == "OCR extracted text from scanned page"
    mock_ocr.assert_called_once()


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
def test_extract_with_tables(
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    """Tables on a page should be extracted as markdown strings."""
    fitz_pages = [_make_fitz_page("A" * 200)]
    fitz_doc = _make_fitz_doc(fitz_pages)
    fitz_doc.close = MagicMock()

    table_data: list[list[str]] = [["Col1", "Col2"], ["val1", "val2"]]
    plumber_pages = [_make_plumber_page(tables=[table_data])]
    plumber_doc = _make_plumber_doc(plumber_pages)
    plumber_doc.close = MagicMock()

    mock_fitz_open.return_value = fitz_doc
    mock_plumber_open.return_value = plumber_doc

    pdf_file = tmp_path / "tables.pdf"
    pdf_file.touch()

    doc = extractor.extract(pdf_file)

    assert len(doc.pages[0].tables) == 1
    assert "Col1" in doc.pages[0].tables[0]
    assert "val1" in doc.pages[0].tables[0]


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
def test_extract_mixed_method(
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    """Mix of digital and scanned pages should yield 'mixed' extraction_method."""
    with patch("credit_analyzer.processing.pdf_extractor._ocr_page", return_value="ocr text"):
        fitz_pages = [_make_fitz_page("A" * 200), _make_fitz_page("x")]
        fitz_doc = _make_fitz_doc(fitz_pages)
        fitz_doc.close = MagicMock()

        plumber_pages = [_make_plumber_page(), _make_plumber_page()]
        plumber_doc = _make_plumber_doc(plumber_pages)
        plumber_doc.close = MagicMock()

        mock_fitz_open.return_value = fitz_doc
        mock_plumber_open.return_value = plumber_doc

        pdf_file = tmp_path / "mixed.pdf"
        pdf_file.touch()

        doc = extractor.extract(pdf_file)

    assert doc.extraction_method == "mixed"
    assert doc.pages[0].is_ocr is False
    assert doc.pages[1].is_ocr is True


def test_extract_file_not_found(extractor: PDFExtractor) -> None:
    with pytest.raises(FileNotFoundError):
        extractor.extract(Path("/nonexistent/path.pdf"))


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
def test_extract_preserves_allcaps_legal_headers(
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    """Extraction must not strip all-caps section markers from page text.

    Credit agreements use ALL CAPS for article headers (ARTICLE I), section
    titles (DEFINITIONS, NEGATIVE COVENANTS), and defined-term labels
    (APPLICABLE MARGIN).  These are parsed by the section detector and
    definitions parser.  Applying remove_page_artifacts() to raw page text
    silently deletes them, producing 0 definitions and empty sections.

    If this test fails, check that remove_page_artifacts() is not being
    called anywhere in pdf_extractor.py.
    """
    legal_text = (
        "ARTICLE I\n"
        "DEFINITIONS\n"
        "\n"
        '"Applicable Margin" means the applicable rate per the pricing grid.\n'
        "\n"
        "NEGATIVE COVENANTS\n"
        "\n"
        "The Borrower shall not permit Consolidated Total Debt to exceed limits.\n"
    ) * 5  # repeat to stay well above OCR threshold

    fitz_pages = [_make_fitz_page(legal_text)]
    fitz_doc = _make_fitz_doc(fitz_pages)
    fitz_doc.close = MagicMock()

    plumber_pages = [_make_plumber_page()]
    plumber_doc = _make_plumber_doc(plumber_pages)
    plumber_doc.close = MagicMock()

    mock_fitz_open.return_value = fitz_doc
    mock_plumber_open.return_value = plumber_doc

    pdf_file = tmp_path / "agreement.pdf"
    pdf_file.touch()

    doc = extractor.extract(pdf_file)

    page_text = doc.pages[0].text
    assert "ARTICLE I" in page_text, "ARTICLE I stripped from page text"
    assert "DEFINITIONS" in page_text, "DEFINITIONS stripped from page text"
    assert "NEGATIVE COVENANTS" in page_text, "NEGATIVE COVENANTS stripped from page text"
    assert "Applicable Margin" in page_text, "Defined term label stripped from page text"


@patch("credit_analyzer.processing.pdf_extractor.pdfplumber.open")
@patch("credit_analyzer.processing.pdf_extractor.fitz.open")
def test_extract_source_path_preserved(
    mock_fitz_open: MagicMock,
    mock_plumber_open: MagicMock,
    extractor: PDFExtractor,
    tmp_path: Path,
) -> None:
    fitz_doc = _make_fitz_doc([_make_fitz_page("A" * 200)])
    fitz_doc.close = MagicMock()
    plumber_doc = _make_plumber_doc([_make_plumber_page()])
    plumber_doc.close = MagicMock()

    mock_fitz_open.return_value = fitz_doc
    mock_plumber_open.return_value = plumber_doc

    pdf_file = tmp_path / "agreement.pdf"
    pdf_file.touch()

    doc = extractor.extract(pdf_file)
    assert doc.source_path == pdf_file
