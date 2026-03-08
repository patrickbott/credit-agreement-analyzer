"""PDF text and table extraction with OCR fallback."""

from __future__ import annotations

import io
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import fitz  # pyright: ignore[reportMissingTypeStubs]
import pdfplumber
import pdfplumber.page
import pytesseract  # pyright: ignore[reportMissingTypeStubs]
from PIL import Image

from credit_analyzer.config import OCR_TEXT_LENGTH_THRESHOLD, TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


@dataclass
class ExtractedPage:
    """Text and tables extracted from a single PDF page."""

    page_number: int  # 1-indexed
    text: str
    tables: list[str]  # Each table as a markdown string
    is_ocr: bool


@dataclass
class ExtractedDocument:
    """Full extraction result for a PDF file."""

    pages: list[ExtractedPage]
    total_pages: int
    source_path: Path
    extraction_method: str  # "digital" | "ocr" | "mixed"


def _table_to_markdown(table: Sequence[Sequence[str | None]]) -> str:
    """Convert a pdfplumber table (sequence of rows) to a pipe-delimited markdown string."""
    if not table:
        return ""

    def clean_cell(cell: str | None) -> str:
        if cell is None:
            return ""
        return cell.replace("\n", " ").strip()

    rows = [[clean_cell(cell) for cell in row] for row in table]

    header = "| " + " | ".join(rows[0]) + " |"
    separator = "| " + " | ".join("---" for _ in rows[0]) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])

    parts = [header, separator]
    if body:
        parts.append(body)
    return "\n".join(parts)


def _ocr_page(fitz_page: Any) -> str:
    """Render a fitz page to an image and run Tesseract OCR on it.

    Args:
        fitz_page: A fitz.Page object (typed as Any due to missing stubs).

    Returns:
        OCR-extracted text string.
    """
    mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR accuracy
    pix = fitz_page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    result = cast(str, pytesseract.image_to_string(img))  # pyright: ignore[reportUnknownMemberType]
    return result


def _extract_tables_from_page(plumber_page: pdfplumber.page.Page) -> list[str]:
    """Extract all tables from a pdfplumber page as markdown strings."""
    raw = plumber_page.extract_tables()
    if not raw:
        return []
    # pdfplumber stubs cells as Any; cast to the shape we expect before passing onward
    tables = cast(list[Sequence[Sequence[str | None]]], raw)
    return [_table_to_markdown(t) for t in tables if t]


_PAGE_WORKERS = 4


def _process_page(
    page_idx: int, fitz_doc: Any, plumber_doc: Any
) -> ExtractedPage:
    """Extract text and tables from a single PDF page."""
    fitz_page: Any = fitz_doc[page_idx]
    plumber_page = plumber_doc.pages[page_idx]

    raw_text = cast(str, fitz_page.get_text())
    is_ocr = False

    if len(raw_text.strip()) < OCR_TEXT_LENGTH_THRESHOLD:
        raw_text = _ocr_page(fitz_page)
        is_ocr = True

    tables = _extract_tables_from_page(plumber_page)

    return ExtractedPage(
        page_number=page_idx + 1,
        text=raw_text,
        tables=tables,
        is_ocr=is_ocr,
    )


class PDFExtractor:
    """Extracts text and tables from credit agreement PDFs.

    Uses PyMuPDF for text extraction, pdfplumber for tables, and
    Tesseract OCR as a fallback for scanned pages.
    """

    def extract(self, pdf_path: Path) -> ExtractedDocument:
        """Extract all pages from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ExtractedDocument with per-page text and tables.

        Raises:
            FileNotFoundError: If the PDF does not exist.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        fitz_doc: Any = fitz.open(str(pdf_path))
        plumber_doc = pdfplumber.open(str(pdf_path))

        try:
            num_pages = len(fitz_doc)
            with ThreadPoolExecutor(max_workers=_PAGE_WORKERS) as pool:
                pages = list(
                    pool.map(
                        _process_page,
                        range(num_pages),
                        [fitz_doc] * num_pages,
                        [plumber_doc] * num_pages,
                    )
                )
        finally:
            fitz_doc.close()
            plumber_doc.close()

        ocr_count = sum(1 for p in pages if p.is_ocr)
        digital_count = len(pages) - ocr_count

        if ocr_count == 0:
            extraction_method = "digital"
        elif digital_count == 0:
            extraction_method = "ocr"
        else:
            extraction_method = "mixed"

        return ExtractedDocument(
            pages=pages,
            total_pages=len(pages),
            source_path=pdf_path,
            extraction_method=extraction_method,
        )
