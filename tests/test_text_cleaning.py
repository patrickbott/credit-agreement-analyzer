"""Tests for utils.text_cleaning."""

from __future__ import annotations

from credit_analyzer.utils.text_cleaning import (
    fix_encoding,
    normalize_whitespace,
    remove_page_artifacts,
    strip_markdown,
)

# ---------------------------------------------------------------------------
# strip_markdown
# ---------------------------------------------------------------------------


def test_strip_markdown_bold() -> None:
    assert strip_markdown("**bold text**") == "bold text"


def test_strip_markdown_header() -> None:
    assert strip_markdown("## Section Title") == "Section Title"


def test_strip_markdown_inline_code() -> None:
    assert strip_markdown("`some code`") == "some code"


def test_strip_markdown_preserves_plain_text() -> None:
    assert strip_markdown("plain text") == "plain text"


def test_strip_markdown_mixed() -> None:
    result = strip_markdown("**bold** and `code` under ## Header")
    assert "**" not in result
    assert "`" not in result
    assert "bold" in result
    assert "code" in result


# ---------------------------------------------------------------------------
# normalize_whitespace
# ---------------------------------------------------------------------------


def test_normalize_whitespace_collapses_spaces() -> None:
    assert normalize_whitespace("a  b") == "a b"


def test_normalize_whitespace_collapses_tabs() -> None:
    assert normalize_whitespace("a\t\tb") == "a b"


def test_normalize_whitespace_collapses_excess_newlines() -> None:
    assert normalize_whitespace("a\n\n\n\nb") == "a\n\nb"


def test_normalize_whitespace_strips_edges() -> None:
    assert normalize_whitespace("  text  ") == "text"


def test_normalize_whitespace_preserves_double_newlines() -> None:
    result = normalize_whitespace("para one\n\npara two")
    assert result == "para one\n\npara two"


# ---------------------------------------------------------------------------
# fix_encoding
# ---------------------------------------------------------------------------


def test_fix_encoding_smart_quotes() -> None:
    assert fix_encoding("\u201chello\u201d") == '"hello"'


def test_fix_encoding_apostrophe() -> None:
    assert fix_encoding("don\u2019t") == "don't"


def test_fix_encoding_em_dash() -> None:
    assert fix_encoding("a\u2014b") == "a--b"


def test_fix_encoding_en_dash() -> None:
    assert fix_encoding("a\u2013b") == "a-b"


def test_fix_encoding_fi_ligature() -> None:
    assert fix_encoding("\ufb01rst") == "first"


def test_fix_encoding_fl_ligature() -> None:
    assert fix_encoding("\ufb02oor") == "floor"


# ---------------------------------------------------------------------------
# remove_page_artifacts
# ---------------------------------------------------------------------------


def test_remove_page_artifacts_standalone_page_number() -> None:
    text = "Some text\n\n47\n\nMore text"
    result = remove_page_artifacts(text)
    assert "47" not in result
    assert "Some text" in result
    assert "More text" in result


def test_remove_page_artifacts_dashed_page_number() -> None:
    text = "Before\n\n- 47 -\n\nAfter"
    result = remove_page_artifacts(text)
    assert "47" not in result
    assert "Before" in result
    assert "After" in result


def test_remove_page_artifacts_three_digit_page() -> None:
    text = "Content\n\n123\n\nMore content"
    result = remove_page_artifacts(text)
    assert "123" not in result


def test_remove_page_artifacts_unsafe_for_legal_text() -> None:
    """remove_page_artifacts() strips all-caps lines 5-40 chars long.

    Credit agreements use ALL CAPS for article headers, section titles, and
    defined term labels (e.g. "ARTICLE I", "DEFINITIONS", "APPLICABLE MARGIN").
    These are structurally critical: the section detector and definitions parser
    rely on them.

    This test documents the unsafe behavior so that callers understand why this
    function must NOT be applied to raw PDF page text in pdf_extractor.py.
    """
    critical_legal_markers = [
        "ARTICLE I",
        "DEFINITIONS",
        "APPLICABLE MARGIN",
        "NEGATIVE COVENANTS",
        "EVENTS OF DEFAULT",
        "REPRESENTATIONS",
    ]
    for marker in critical_legal_markers:
        # The all-caps regex strips these markers — this is the known unsafe behavior.
        result = remove_page_artifacts(marker + "\n")
        assert marker not in result, (
            f"Expected remove_page_artifacts() to strip '{marker}' "
            "(documenting known unsafe behavior for legal text)"
        )
