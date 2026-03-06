"""Tests for definitions browser UI helpers."""
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.ui.definitions_browser import (
    filter_definitions,
    paginate_definitions,
)


def _sample_index() -> DefinitionsIndex:
    return DefinitionsIndex(definitions={
        "Consolidated EBITDA": "means, for any period, Consolidated Net Income plus...",
        "Borrower": "means Holdings LLC, a Delaware limited liability company.",
        "Applicable Rate": "means the applicable percentage per annum set forth below...",
        "Net Income": "means the net income of the Borrower and its Subsidiaries...",
    })


def test_filter_definitions_no_query():
    idx = _sample_index()
    result = filter_definitions(idx, "")
    assert len(result) == 4


def test_filter_definitions_with_query():
    idx = _sample_index()
    result = filter_definitions(idx, "ebitda")
    assert len(result) == 1
    assert result[0][0] == "Consolidated EBITDA"


def test_filter_definitions_case_insensitive():
    idx = _sample_index()
    result = filter_definitions(idx, "BORROWER")
    # "Borrower" matches in term name, and "Borrower" also appears in the
    # Net Income definition text ("...of the Borrower and its Subsidiaries"),
    # so we expect 2 results.
    assert len(result) == 2


def test_filter_definitions_partial_match():
    idx = _sample_index()
    result = filter_definitions(idx, "net")
    # "Net Income" matches term name; "Consolidated EBITDA" definition
    # contains "Net Income", so 2 matches
    assert len(result) == 2


def test_filter_returns_sorted():
    idx = _sample_index()
    result = filter_definitions(idx, "")
    terms = [r[0] for r in result]
    assert terms == sorted(terms)


def test_paginate_definitions():
    items = [(f"Term {i}", f"Def {i}") for i in range(25)]
    page = paginate_definitions(items, page=0, per_page=10)
    assert len(page) == 10
    assert page[0] == ("Term 0", "Def 0")


def test_paginate_definitions_last_page():
    items = [(f"Term {i}", f"Def {i}") for i in range(25)]
    page = paginate_definitions(items, page=2, per_page=10)
    assert len(page) == 5
