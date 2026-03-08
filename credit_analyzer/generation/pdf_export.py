# pyright: reportArgumentType=false, reportCallIssue=false, reportMissingModuleSource=false
"""PDF export for generated credit agreement reports.

Uses fpdf2 (pure-Python, no system dependencies) to produce a clean,
professional PDF with RBC-style branding.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from fpdf import FPDF  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from credit_analyzer.generation.report_generator import GeneratedReport
    from credit_analyzer.generation.response_parser import InlineCitation

# ---------------------------------------------------------------------------
# Brand colours (RGB tuples)
# ---------------------------------------------------------------------------

_RBC_BLUE: tuple[int, int, int] = (0, 59, 122)
_RBC_GOLD: tuple[int, int, int] = (255, 204, 0)
_INK: tuple[int, int, int] = (18, 32, 51)
_MUTED: tuple[int, int, int] = (91, 107, 130)
_WHITE: tuple[int, int, int] = (255, 255, 255)
_SURFACE: tuple[int, int, int] = (244, 247, 251)
_BORDER: tuple[int, int, int] = (213, 223, 236)
_SUCCESS: tuple[int, int, int] = (23, 99, 60)
_WARNING: tuple[int, int, int] = (138, 90, 0)
_DANGER: tuple[int, int, int] = (143, 36, 48)

# Page geometry (Letter)
_PAGE_W = 215.9
_MARGIN_L = 18.0
_MARGIN_R = 18.0
_CONTENT_W = _PAGE_W - _MARGIN_L - _MARGIN_R

_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_FAMILY = "DejaVuSans"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Matches field labels at start of line: "BORROWER:", "FACILITY 1:",
# "OID / UPFRONT FEE:", "COMMITMENT / PRINCIPAL:", etc.
_FIELD_LABEL_RE = re.compile(r"^([A-Z][A-Z0-9 /\-&().,]+?:)", re.MULTILINE)

# Matches standalone section headings: all-caps lines with no colon
# e.g. "BORROWER INFORMATION", "PRICING TERMS", "INVESTMENTS"
_SECTION_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /&,\-()]{3,}$")

# Matches citation markers like [1], [2], [1, 3]
_CITE_MARKER_RE = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')

# Matches pipe-delimited table rows (with or without leading/trailing pipes)
# e.g. "| A | B |" or "A | B | C" or "Level | Ratio | Spread"
_TABLE_ROW_RE = re.compile(r'^\|.+\|$|^[^|]+\|.+$')

# Matches table separator rows like "---|---", "|---|---|", "--- | --- | ---"
_TABLE_SEP_RE = re.compile(r'^\|?[\s:]*-{2,}[\s:]*(\|[\s:]*-{2,}[\s:]*)+\|?\s*$')


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------


class _ReportPDF(FPDF):  # pyright: ignore[reportMissingTypeStubs]
    """Custom FPDF subclass with header/footer and helper methods."""

    def __init__(self, generated_label: str) -> None:
        super().__init__(orientation="P", unit="mm", format="Letter")  # pyright: ignore[reportUnknownMemberType]
        self._generated_label = generated_label
        self._register_fonts()
        self.set_auto_page_break(auto=True, margin=20)  # pyright: ignore[reportUnknownMemberType]
        self.set_left_margin(margin=_MARGIN_L)  # pyright: ignore[reportUnknownMemberType]
        self.set_right_margin(margin=_MARGIN_R)  # pyright: ignore[reportUnknownMemberType]

    def _register_fonts(self) -> None:
        """Register the bundled Unicode font family used throughout the PDF."""
        required_fonts = {
            "": _FONT_DIR / "DejaVuSans.ttf",
            "B": _FONT_DIR / "DejaVuSans-Bold.ttf",
            "I": _FONT_DIR / "DejaVuSans-Oblique.ttf",
            "BI": _FONT_DIR / "DejaVuSans-BoldOblique.ttf",
        }
        missing_fonts = [path.name for path in required_fonts.values() if not path.exists()]
        if missing_fonts:
            missing = ", ".join(sorted(missing_fonts))
            raise FileNotFoundError(
                f"Missing bundled PDF fonts in {_FONT_DIR}: {missing}"
            )

        for style, path in required_fonts.items():
            self.add_font(  # pyright: ignore[reportUnknownMemberType]
                _FONT_FAMILY,
                style,
                str(path),
            )

    # -- page chrome --------------------------------------------------------

    def header(self) -> None:  # pyright: ignore[reportUnknownParameterType]
        """Thin branded bar at top of every page."""
        # Gold accent line
        self.set_fill_color(*_RBC_GOLD)  # pyright: ignore[reportUnknownMemberType]
        self.rect(x=0, y=0, w=_PAGE_W, h=2.2, style="F")  # pyright: ignore[reportUnknownMemberType]

        # Header text
        self.set_y(6)  # pyright: ignore[reportUnknownMemberType]
        self.set_font(_FONT_FAMILY, "B", 7.5)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
        self.cell(w=_CONTENT_W * 0.5, h=4, text="CREDIT AGREEMENT ANALYSIS", align="L")  # pyright: ignore[reportUnknownMemberType]
        self.cell(w=_CONTENT_W * 0.5, h=4, text=self._generated_label, align="R")  # pyright: ignore[reportUnknownMemberType]
        self.ln(8)  # pyright: ignore[reportUnknownMemberType]

    def footer(self) -> None:  # pyright: ignore[reportUnknownParameterType]
        """Page number footer."""
        self.set_y(-14)  # pyright: ignore[reportUnknownMemberType]
        self.set_font(_FONT_FAMILY, "", 7.5)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_BORDER)  # pyright: ignore[reportUnknownMemberType]
        page_label = f"Page {self.page_no()}"
        self.cell(w=0, h=8, text=page_label, align="C")  # pyright: ignore[reportUnknownMemberType]

    # -- drawing helpers ----------------------------------------------------

    def draw_gold_rule(self) -> None:
        """Draw a thin gold horizontal rule."""
        y = float(self.get_y())  # pyright: ignore[reportUnknownMemberType]
        self.set_draw_color(*_RBC_GOLD)  # pyright: ignore[reportUnknownMemberType]
        self.set_line_width(0.5)  # pyright: ignore[reportUnknownMemberType]
        self.line(x1=_MARGIN_L, y1=y, x2=_PAGE_W - _MARGIN_R, y2=y)  # pyright: ignore[reportUnknownMemberType]
        self.ln(3)  # pyright: ignore[reportUnknownMemberType]

    def render_section_heading(self, number: int, title: str) -> None:
        """Render a section heading with number and title."""
        # Ensure enough space for heading + some body
        if float(self.get_y()) > 240:  # pyright: ignore[reportUnknownMemberType]
            self.add_page()  # pyright: ignore[reportUnknownMemberType]

        self.ln(3)  # pyright: ignore[reportUnknownMemberType]
        self.draw_gold_rule()

        # Section number + title
        self.set_font(_FONT_FAMILY, "B", 11)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_RBC_BLUE)  # pyright: ignore[reportUnknownMemberType]
        heading_text = f"Section {number}  |  {title}"
        self.cell(w=_CONTENT_W, h=7, text=heading_text, align="L")  # pyright: ignore[reportUnknownMemberType]
        self.ln(9)  # pyright: ignore[reportUnknownMemberType]

    def _reset_x(self) -> None:
        """Reset cursor x to left margin to prevent drift."""
        self.set_x(_MARGIN_L)  # pyright: ignore[reportUnknownMemberType]

    def _reset_body_font(self) -> None:
        """Reset font and text color to default body text state."""
        self.set_font(_FONT_FAMILY, "", 9)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]

    def _multi_cell_with_refs(self, w: float, h: float, text: str,
                              font_size: float = 9, font_style: str = "") -> None:
        """Like multi_cell but renders [N] citation markers as superscript.

        If no citation markers are found, falls back to plain multi_cell.
        Uses fpdf2's write_html() to handle <sup> tags for citations.
        """
        if not _CITE_MARKER_RE.search(text):
            self.multi_cell(w=w, h=h, text=text)  # pyright: ignore[reportUnknownMemberType]
            return

        # Build HTML string with superscript citations
        safe = html_escape(text)
        safe = safe.replace('\n', '<br/>')

        r, g, b = _MUTED
        sup_color = f"#{r:02x}{g:02x}{b:02x}"
        sup_pt = max(int(font_size * 0.65), 5)

        def _sup_repl(m: re.Match[str]) -> str:
            return f'<sup><font color="{sup_color}" size="{sup_pt}">{html_escape(m.group(0))}</font></sup>'

        safe = _CITE_MARKER_RE.sub(_sup_repl, safe)

        # Wrap in font tag to maintain current style
        r2, g2, b2 = _INK
        body_color = f"#{r2:02x}{g2:02x}{b2:02x}"
        html_str = f'<font color="{body_color}" size="{int(font_size)}" face="{_FONT_FAMILY}">{safe}</font>'

        self.write_html(html_str)  # pyright: ignore[reportUnknownMemberType]
        self.ln(h)  # pyright: ignore[reportUnknownMemberType]

    def render_table(self, table_lines: list[str]) -> None:
        """Render a pipe-delimited markdown table."""
        rows: list[list[str]] = []
        for row_line in table_lines:
            # Skip separator rows like |---|---| or --- | --- | ---
            if _TABLE_SEP_RE.match(row_line):
                continue
            cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
            rows.append(cells)
        if not rows:
            return
        num_cols = max(len(r) for r in rows)
        col_w = _CONTENT_W / num_cols if num_cols else _CONTENT_W
        self.ln(2)  # pyright: ignore[reportUnknownMemberType]
        # Header row
        self.set_font(_FONT_FAMILY, "B", 8)  # pyright: ignore[reportUnknownMemberType]
        self.set_fill_color(*_SURFACE)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_RBC_BLUE)  # pyright: ignore[reportUnknownMemberType]
        self._reset_x()
        for cell in rows[0]:
            self.cell(w=col_w, h=5.5, text=cell, border=1, fill=True)  # pyright: ignore[reportUnknownMemberType]
        self.ln()  # pyright: ignore[reportUnknownMemberType]
        # Data rows
        self.set_font(_FONT_FAMILY, "", 8)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
        for row in rows[1:]:
            self._reset_x()
            for i, cell in enumerate(row):
                self.cell(w=col_w, h=5, text=cell if i < num_cols else "", border=1)  # pyright: ignore[reportUnknownMemberType]
            self.ln()  # pyright: ignore[reportUnknownMemberType]
        self.ln(2)  # pyright: ignore[reportUnknownMemberType]
        # Reset font state after table rendering
        self._reset_body_font()

    def render_body_text(self, text: str) -> None:
        """Render section body with headings, field labels, and lists."""
        lines = text.split("\n")
        table_buf: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Detect table rows: lines with pipe delimiters or separator rows
            if _TABLE_ROW_RE.match(stripped) or _TABLE_SEP_RE.match(stripped):
                table_buf.append(stripped)
                i += 1
                continue
            if table_buf:
                self.render_table(table_buf)
                table_buf.clear()
                # Reset font state after table
                self._reset_body_font()
            self._render_body_line(line, stripped)
            i += 1
        if table_buf:
            self.render_table(table_buf)
            # Reset font state after table
            self._reset_body_font()

    def _render_body_line(self, line: str, stripped: str) -> None:
        """Render a single body line."""
        if not stripped:
            self.ln(2.5)  # pyright: ignore[reportUnknownMemberType]
            return

        self._reset_x()
        is_indented = line.startswith("    ") or line.startswith("\t")

        # Standalone section heading (all-caps, no colon)
        if _SECTION_HEADING_RE.match(stripped):
            self.ln(3)  # pyright: ignore[reportUnknownMemberType]
            self._reset_x()
            self.set_font(_FONT_FAMILY, "B", 8.5)  # pyright: ignore[reportUnknownMemberType]
            self.set_text_color(*_RBC_BLUE)  # pyright: ignore[reportUnknownMemberType]
            self.multi_cell(w=_CONTENT_W, h=5.5, text=stripped)  # pyright: ignore[reportUnknownMemberType]
            self._reset_x()
            y = float(self.get_y())  # pyright: ignore[reportUnknownMemberType]
            self.set_draw_color(*_BORDER)  # pyright: ignore[reportUnknownMemberType]
            self.set_line_width(0.2)  # pyright: ignore[reportUnknownMemberType]
            self.line(x1=_MARGIN_L, y1=y, x2=_MARGIN_L + _CONTENT_W * 0.5, y2=y)  # pyright: ignore[reportUnknownMemberType]
            self.ln(2)  # pyright: ignore[reportUnknownMemberType]
            return

        # Field label: value
        match = _FIELD_LABEL_RE.match(stripped)
        if match:
            label = match.group(1)
            rest = stripped[len(label):].strip()
            self.set_font(_FONT_FAMILY, "B", 9)  # pyright: ignore[reportUnknownMemberType]
            self.set_text_color(*_RBC_BLUE)  # pyright: ignore[reportUnknownMemberType]
            self.multi_cell(w=_CONTENT_W, h=5, text=label)  # pyright: ignore[reportUnknownMemberType]
            if rest:
                self._reset_x()
                self.set_font(_FONT_FAMILY, "", 9)  # pyright: ignore[reportUnknownMemberType]
                if rest.upper().startswith("NOT FOUND"):
                    self.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
                    self.set_font(_FONT_FAMILY, "I", 9)  # pyright: ignore[reportUnknownMemberType]
                else:
                    self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
                self._multi_cell_with_refs(w=_CONTENT_W, h=5, text=rest)
            return

        # Bullet point
        if stripped.startswith("- ") or stripped.startswith("* "):
            indent = 8.0 if is_indented else 4.0
            self.set_font(_FONT_FAMILY, "", 8.5)  # pyright: ignore[reportUnknownMemberType]
            self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
            self.set_x(_MARGIN_L + indent)  # pyright: ignore[reportUnknownMemberType]
            bullet_text = f"\u2022  {stripped[2:]}"
            self._multi_cell_with_refs(w=_CONTENT_W - indent, h=5, text=bullet_text,
                                       font_size=8.5)
            return

        # Numbered item
        if re.match(r"^\d+\.\s", stripped):
            self.set_font(_FONT_FAMILY, "", 8.5)  # pyright: ignore[reportUnknownMemberType]
            self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
            self.set_x(_MARGIN_L + 4.0)  # pyright: ignore[reportUnknownMemberType]
            self._multi_cell_with_refs(w=_CONTENT_W - 4.0, h=5, text=stripped,
                                       font_size=8.5)
            return

        # Regular paragraph
        self.set_font(_FONT_FAMILY, "", 9)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
        self._multi_cell_with_refs(w=_CONTENT_W, h=5, text=stripped)

    def render_inline_references(self, citations: list[InlineCitation]) -> None:
        """Render a numbered reference list below the section body."""
        if not citations:
            return
        self.ln(3)  # pyright: ignore[reportUnknownMemberType]
        self.set_font(_FONT_FAMILY, "B", 7.5)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
        self._reset_x()
        self.cell(w=_CONTENT_W, h=4, text="REFERENCES")  # pyright: ignore[reportUnknownMemberType]
        self.ln(4)  # pyright: ignore[reportUnknownMemberType]

        self.set_font(_FONT_FAMILY, "", 7.5)  # pyright: ignore[reportUnknownMemberType]
        for cite in citations:
            pages = ", ".join(str(p) for p in cite.page_numbers)
            ref_text = f"[{cite.marker_number}] Section {cite.section_id}"
            if cite.section_title:
                ref_text += f" | {cite.section_title}"
            if pages:
                ref_text += f" (pp. {pages})"
            self._reset_x()
            self.multi_cell(w=_CONTENT_W, h=4, text=ref_text)  # pyright: ignore[reportUnknownMemberType]

    def render_sources_line(self, sources_text: str) -> None:
        """Render a compact sources line below the body."""
        self.ln(2)  # pyright: ignore[reportUnknownMemberType]
        self.set_font(_FONT_FAMILY, "I", 7.5)  # pyright: ignore[reportUnknownMemberType]
        self.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
        self.multi_cell(w=_CONTENT_W, h=4, text=sources_text)  # pyright: ignore[reportUnknownMemberType]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def report_to_pdf_bytes(report: GeneratedReport) -> bytes:
    """Convert a GeneratedReport to a PDF byte string.

    Args:
        report: The completed report to export.

    Returns:
        Raw PDF bytes suitable for st.download_button.
    """
    gen_label = report.generated_at.strftime("%B %d, %Y  %H:%M")
    pdf = _ReportPDF(gen_label)
    pdf.add_page()  # pyright: ignore[reportUnknownMemberType]

    # ---- Cover / title block ----
    pdf.ln(8)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_font(_FONT_FAMILY, "B", 22)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_text_color(*_RBC_BLUE)  # pyright: ignore[reportUnknownMemberType]
    pdf.multi_cell(w=_CONTENT_W, h=10, text=report.borrower_name, align="L")  # pyright: ignore[reportUnknownMemberType]

    pdf.ln(2)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_font(_FONT_FAMILY, "", 10)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
    pdf.cell(w=_CONTENT_W, h=6, text="Credit Agreement Analysis", align="L")  # pyright: ignore[reportUnknownMemberType]
    pdf.ln(6)  # pyright: ignore[reportUnknownMemberType]
    pdf.cell(w=_CONTENT_W, h=6, text=f"Generated {gen_label}", align="L")  # pyright: ignore[reportUnknownMemberType]
    pdf.ln(10)  # pyright: ignore[reportUnknownMemberType]

    # Disclaimer
    pdf.set_fill_color(*_SURFACE)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_font(_FONT_FAMILY, "I", 7.5)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
    pdf.multi_cell(  # pyright: ignore[reportUnknownMemberType]
        w=_CONTENT_W, h=4, fill=True,
        text=(
            "DISCLAIMER: This report is auto-generated and should be verified "
            "against the source document. Extraction may be incomplete for "
            "non-standard agreement formats."
        ),
    )
    pdf.ln(4)  # pyright: ignore[reportUnknownMemberType]

    # ---- Table of contents (compact) ----
    pdf.draw_gold_rule()
    pdf.set_font(_FONT_FAMILY, "B", 9)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_text_color(*_INK)  # pyright: ignore[reportUnknownMemberType]
    pdf.cell(w=_CONTENT_W, h=6, text="CONTENTS")  # pyright: ignore[reportUnknownMemberType]
    pdf.ln(6)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_font(_FONT_FAMILY, "", 8.5)  # pyright: ignore[reportUnknownMemberType]
    for section in report.sections:
        status_label = "" if section.status == "complete" else "  [ERROR]"
        toc_line = f"  {section.section_number}.  {section.title}{status_label}"
        pdf.cell(w=_CONTENT_W, h=5, text=toc_line)  # pyright: ignore[reportUnknownMemberType]
        pdf.ln(5)  # pyright: ignore[reportUnknownMemberType]
    pdf.ln(4)  # pyright: ignore[reportUnknownMemberType]

    # ---- Sections ----
    for section in report.sections:
        pdf.render_section_heading(
            section.section_number,
            section.title,
        )

        if section.status == "error":
            pdf.set_font(_FONT_FAMILY, "I", 9)  # pyright: ignore[reportUnknownMemberType]
            pdf.set_text_color(*_DANGER)  # pyright: ignore[reportUnknownMemberType]
            pdf.multi_cell(w=_CONTENT_W, h=5, text=f"Generation error: {section.error_message}")  # pyright: ignore[reportUnknownMemberType]
            continue

        if section.status == "pending":
            pdf.set_font(_FONT_FAMILY, "I", 9)  # pyright: ignore[reportUnknownMemberType]
            pdf.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
            pdf.cell(w=_CONTENT_W, h=5, text="(Not yet generated)")  # pyright: ignore[reportUnknownMemberType]
            pdf.ln(5)  # pyright: ignore[reportUnknownMemberType]
            continue

        pdf.render_body_text(section.body)
        pdf.render_inline_references(section.inline_citations)

        # Sources
        if section.sources:
            source_strs: list[str] = []
            for src in section.sources:
                pages = ", ".join(str(p) for p in src.page_numbers)
                if pages:
                    source_strs.append(f"Section {src.section_id} (pp. {pages})")
                else:
                    source_strs.append(f"Section {src.section_id}")
            pdf.render_sources_line(f"Sources: {', '.join(source_strs)}")

    # ---- Final footer line ----
    pdf.ln(6)  # pyright: ignore[reportUnknownMemberType]
    pdf.draw_gold_rule()
    pdf.set_font(_FONT_FAMILY, "I", 7.5)  # pyright: ignore[reportUnknownMemberType]
    pdf.set_text_color(*_MUTED)  # pyright: ignore[reportUnknownMemberType]
    pdf.cell(  # pyright: ignore[reportUnknownMemberType]
        w=_CONTENT_W, h=5,
        text=f"Total generation time: {report.total_duration_seconds:.1f}s",
    )

    buf = BytesIO()
    pdf.output(buf)  # pyright: ignore[reportUnknownMemberType]
    return buf.getvalue()
