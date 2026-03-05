"""Text normalization utilities for extracted PDF content and LLM output."""

import re
import unicodedata

# ---------------------------------------------------------------------------
# LLM output cleaning
# ---------------------------------------------------------------------------

# The extraction system prompt tells the LLM not to use markdown, but Claude
# occasionally emits bold, header, or backtick formatting anyway. These
# patterns strip the formatting while preserving the underlying text.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_HEADER_RE = re.compile(r"(?m)^#{1,4}\s+(.+)$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")


def strip_markdown(text: str) -> str:
    """Remove common markdown formatting tokens from LLM-generated text.

    Handles bold (**text**), ATX headers (### text), and inline code (`text`).
    Preserves the underlying content in each case.
    """
    text = _BOLD_RE.sub(r"\1", text)
    text = _HEADER_RE.sub(r"\1", text)
    text = _BACKTICK_RE.sub(r"\1", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs to single space; normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fix_encoding(text: str) -> str:
    """Normalize unicode, replace common ligatures and smart quotes."""
    text = unicodedata.normalize("NFKD", text)
    replacements: dict[str, str] = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u2022": "*",
        "\ufb01": "fi",
        "\ufb02": "fl",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Drop remaining non-ASCII that sneak through
    text = text.encode("ascii", errors="ignore").decode("ascii")
    return text


def clean_extracted_text(text: str) -> str:
    """Full cleaning pipeline for raw PDF-extracted text."""
    text = fix_encoding(text)
    text = normalize_whitespace(text)
    return text


def remove_page_artifacts(text: str) -> str:
    """Strip common header/footer artifacts: standalone page numbers, running headers."""
    # Standalone page number lines like "- 47 -" or just "47"
    text = re.sub(r"(?m)^\s*-?\s*\d{1,3}\s*-?\s*$", "", text)
    # Lines that are all caps short phrases typical of running headers (heuristic)
    text = re.sub(r"(?m)^[A-Z\s,&]{5,40}$\n", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
