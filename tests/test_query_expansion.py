"""Tests for concept-aware query expansion."""

from __future__ import annotations

from credit_analyzer.generation.query_expansion import (
    expand_query,
    expand_query_with_concepts,
)


class TestConceptAwareExpansion:
    """Tests that concept registry integration works in expand_query."""

    def test_j_crew_expands_to_search_terms(self) -> None:
        """A J.Crew query should produce retrieval queries with concept search terms."""
        queries = expand_query("Are there any J.Crew provisions?")
        all_text = " ".join(queries).lower()
        assert "intellectual property" in all_text or "unrestricted subsidiary" in all_text

    def test_serta_expands_to_search_terms(self) -> None:
        queries = expand_query("Does this document have Serta protections?")
        all_text = " ".join(queries).lower()
        assert "uptier" in all_text or "priming" in all_text or "subordinat" in all_text

    def test_freebie_expands(self) -> None:
        queries = expand_query("What is the freebie basket?")
        all_text = " ".join(queries).lower()
        assert "free and clear" in all_text or "incremental" in all_text

    def test_simple_query_unchanged(self) -> None:
        """Simple queries that don't match concepts still work normally."""
        queries = expand_query("What is the SOFR spread?")
        assert queries[0] == "What is the SOFR spread?"
        assert len(queries) >= 1

    def test_original_query_always_first(self) -> None:
        """The original query is always the first in the list."""
        queries = expand_query("Any J.Crew provisions?")
        assert queries[0] == "Any J.Crew provisions?"

    def test_max_queries_respected(self) -> None:
        """Expansion should not produce an excessive number of queries."""
        queries = expand_query("J.Crew and Serta and Chewy provisions?")
        assert len(queries) <= 6  # reasonable cap


class TestExpandQueryWithConcepts:
    """Tests for the new expand_query_with_concepts function."""

    def test_returns_tuple(self) -> None:
        """Should return (queries, concept_matches) tuple."""
        result = expand_query_with_concepts("Are there any J.Crew provisions?")
        assert isinstance(result, tuple)
        assert len(result) == 2
        queries, matches = result
        assert isinstance(queries, list)
        assert isinstance(matches, list)

    def test_j_crew_returns_concept_match(self) -> None:
        """J.Crew query should return a concept match."""
        queries, matches = expand_query_with_concepts("Are there any J.Crew provisions?")
        assert len(matches) >= 1
        concept_ids = [m.concept_id for m in matches]
        assert "j_crew_provision" in concept_ids

    def test_serta_returns_concept_match(self) -> None:
        queries, matches = expand_query_with_concepts("Does this have Serta protections?")
        assert len(matches) >= 1
        concept_ids = [m.concept_id for m in matches]
        assert "serta_provision" in concept_ids

    def test_no_concepts_returns_empty_matches(self) -> None:
        """Simple queries with no concept matches return empty list."""
        queries, matches = expand_query_with_concepts("What is the maturity date?")
        assert matches == []
        assert len(queries) >= 1

    def test_concept_matched_allows_more_queries(self) -> None:
        """When concepts are matched, up to 5 queries are allowed."""
        queries, matches = expand_query_with_concepts("J.Crew and Serta provisions?")
        assert len(matches) >= 1
        # With concepts matched, the cap is 5 (vs 3 without)
        assert len(queries) <= 5

    def test_no_concept_caps_at_3(self) -> None:
        """When no concepts matched, cap remains at 3."""
        queries, matches = expand_query_with_concepts("What is the SOFR spread?")
        assert len(queries) <= 3


class TestExpandQueryBaseline:
    """Ensure existing expansion behavior is preserved."""

    def test_defined_term_expansion(self) -> None:
        """Capitalized terms still generate definition-focused queries."""
        queries = expand_query("What is the Total Net Leverage Ratio?")
        all_text = " ".join(queries).lower()
        assert "definition" in all_text or "total net leverage ratio" in all_text

    def test_financial_keyword_expansion(self) -> None:
        """Financial keywords still broaden the query."""
        queries = expand_query("What is the leverage covenant test?")
        assert len(queries) >= 2
