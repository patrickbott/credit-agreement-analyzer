"""Tests for definitions parser module."""

from __future__ import annotations

from credit_analyzer.processing.definitions import DefinitionsIndex, DefinitionsParser
from credit_analyzer.processing.section_detector import DocumentSection


def _make_definitions_section(text: str) -> DocumentSection:
    """Build a minimal DocumentSection for testing the definitions parser."""
    return DocumentSection(
        section_id="ARTICLE_1",
        article_number=1,
        section_title="DEFINITIONS",
        article_title="DEFINITIONS",
        text=text,
        page_start=1,
        page_end=1,
        tables=[],
        section_type="definitions",
    )


# --- DefinitionsParser tests ---


def test_parse_basic_definitions_straight_quotes() -> None:
    """Parse terms defined with straight quotes and 'means'."""
    text = (
        '"Available Amount" means the sum of X and Y.\n\n'
        '"Borrower" means the entity identified on the signature page.\n'
    )
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Available Amount" in index.definitions
    assert "Borrower" in index.definitions
    assert "sum of X and Y" in index.definitions["Available Amount"]


def test_parse_smart_quotes() -> None:
    """Parse terms defined with smart (curly) quotes."""
    text = (
        "\u201cConsolidated Net Income\u201d means the net income of the Borrower.\n\n"
        "\u201cEBITDA\u201d means earnings before interest, taxes, depreciation.\n"
    )
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Consolidated Net Income" in index.definitions
    assert "EBITDA" in index.definitions


def test_parse_shall_mean_variant() -> None:
    """'shall mean' is recognized as a definition verb."""
    text = '"Permitted Acquisition" shall mean any acquisition by the Borrower.\n'
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Permitted Acquisition" in index.definitions


def test_parse_has_the_meaning_variant() -> None:
    """'has the meaning' is recognized as a definition verb."""
    text = '"Agent" has the meaning assigned to such term in Section 9.01.\n'
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Agent" in index.definitions


def test_parse_skips_non_definition_quotes() -> None:
    """Quoted terms not followed by definition verbs are skipped."""
    text = (
        'The "Borrower" means the company.\n\n'
        'References to "dollars" throughout this Agreement are to USD.\n'
    )
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Borrower" in index.definitions
    # "dollars" is not followed by means/shall mean/etc. directly
    assert "dollars" not in index.definitions


def test_parse_empty_section() -> None:
    """An empty section produces an empty index."""
    section = _make_definitions_section("")
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert len(index.definitions) == 0


def test_parse_definition_boundary() -> None:
    """Each definition's text ends where the next one starts."""
    text = (
        '"Term A" means the first thing. It has many details.\n\n'
        '"Term B" means the second thing.\n'
    )
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    # Term A's text should NOT contain Term B's definition
    assert "second thing" not in index.definitions["Term A"]
    assert "first thing" in index.definitions["Term A"]


# --- DefinitionsIndex tests ---


def test_lookup_found() -> None:
    index = DefinitionsIndex(definitions={"EBITDA": "earnings before..."})
    assert index.lookup("EBITDA") == "earnings before..."


def test_lookup_not_found() -> None:
    index = DefinitionsIndex(definitions={"EBITDA": "earnings before..."})
    assert index.lookup("Missing Term") is None


def test_find_terms_in_text() -> None:
    """find_terms_in_text returns matching terms sorted longest first."""
    index = DefinitionsIndex(
        definitions={
            "Consolidated Net Income": "...",
            "Net Income": "...",
            "Borrower": "...",
        }
    )
    text = "The Borrower shall calculate Consolidated Net Income as follows."
    found = index.find_terms_in_text(text)

    assert "Consolidated Net Income" in found
    assert "Net Income" in found  # substring also matches as whole word
    assert "Borrower" in found
    # Longest first
    assert found[0] == "Consolidated Net Income"


def test_find_terms_no_partial_match() -> None:
    """Whole-word matching: 'Loan' should not match inside 'Loans' boundary issues."""
    index = DefinitionsIndex(definitions={"Loan": "a single loan"})
    # "Loan" as a whole word should match
    assert index.find_terms_in_text("The Loan is due.") == ["Loan"]
    # "Loans" is a different word but \b still matches at the boundary
    # This is expected: "Loan" appears at a word boundary in "Loans" -> no match
    # Actually \bLoan\b does NOT match "Loans" because 's' is a word char
    assert index.find_terms_in_text("The Loans are due.") == []


def test_find_terms_empty_text() -> None:
    index = DefinitionsIndex(definitions={"Borrower": "..."})
    assert index.find_terms_in_text("") == []


def test_get_definitions_for_terms() -> None:
    index = DefinitionsIndex(
        definitions={
            "EBITDA": "earnings...",
            "Borrower": "the company",
            "Agent": "the administrative agent",
        }
    )
    result = index.get_definitions_for_terms(["EBITDA", "Agent", "Missing"])
    assert result == {"EBITDA": "earnings...", "Agent": "the administrative agent"}


def test_get_definitions_for_terms_empty() -> None:
    index = DefinitionsIndex(definitions={"EBITDA": "earnings..."})
    assert index.get_definitions_for_terms([]) == {}


def test_duplicate_terms_keeps_first() -> None:
    """If the same term appears twice, the first occurrence wins."""
    text = (
        '"Rate" means the initial rate.\n\n'
        'Some intervening text about the "Rate" means nothing here.\n\n'
        '"Other" means something else.\n'
    )
    section = _make_definitions_section(text)
    parser = DefinitionsParser()
    index = parser.parse(section)

    assert "Rate" in index.definitions
    assert "initial rate" in index.definitions["Rate"]
