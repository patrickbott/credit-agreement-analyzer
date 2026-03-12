"""Tests for the leveraged finance knowledge registry."""

from __future__ import annotations

from credit_analyzer.knowledge.registry import (
    ConceptMatch,
    DomainRegistry,
)


class TestDomainRegistry:
    """Tests for loading and querying the concept registry."""

    def setup_method(self) -> None:
        self.registry = DomainRegistry()

    def test_loads_concepts(self) -> None:
        """Registry loads concepts from YAML."""
        assert len(self.registry.concepts) > 10

    def test_loads_synonyms(self) -> None:
        """Registry loads synonym groups from YAML."""
        assert len(self.registry.synonym_groups) > 10

    def test_match_concept_exact_alias(self) -> None:
        """Exact alias match returns the concept."""
        matches = self.registry.match_concepts("Are there any J.Crew provisions?")
        assert len(matches) >= 1
        assert any(m.concept_id == "j_crew_provision" for m in matches)

    def test_match_concept_case_insensitive(self) -> None:
        """Alias matching is case-insensitive."""
        matches = self.registry.match_concepts("does this have SERTA protections")
        assert any(m.concept_id == "serta_provision" for m in matches)

    def test_match_concept_multiple(self) -> None:
        """Multiple concepts can match in a single query."""
        matches = self.registry.match_concepts(
            "What about J.Crew and Serta provisions?"
        )
        ids = {m.concept_id for m in matches}
        assert "j_crew_provision" in ids
        assert "serta_provision" in ids

    def test_no_match_simple_query(self) -> None:
        """Simple queries without concept aliases return no matches."""
        matches = self.registry.match_concepts("What is the SOFR spread?")
        # This should NOT match a named provision concept
        named_provisions = {
            m.concept_id for m in matches
            if m.concept_id in ("j_crew_provision", "serta_provision", "chewy_provision")
        }
        assert len(named_provisions) == 0

    def test_concept_has_search_terms(self) -> None:
        """Matched concepts provide search terms for retrieval."""
        matches = self.registry.match_concepts("any trap-door provisions?")
        assert len(matches) >= 1
        m = next(m for m in matches if m.concept_id == "j_crew_provision")
        assert len(m.search_terms) > 0
        assert "intellectual property" in m.search_terms

    def test_concept_has_description(self) -> None:
        """Matched concepts include a description for LLM context."""
        matches = self.registry.match_concepts("freebie basket")
        m = next(m for m in matches if m.concept_id == "freebie_basket")
        assert "free-and-clear" in m.description.lower() or "free and clear" in m.description.lower()

    def test_expand_synonyms(self) -> None:
        """Synonym expansion returns canonical + alternatives."""
        expanded = self.registry.expand_synonyms("what is the revolver commitment")
        # Should find revolving_facility synonym group
        assert "Revolving Credit Facility" in expanded or "revolving commitment" in expanded

    def test_expand_synonyms_no_match(self) -> None:
        """Queries with no synonym matches return empty."""
        expanded = self.registry.expand_synonyms("tell me about the weather")
        assert len(expanded) == 0

    def test_get_concept_context(self) -> None:
        """get_concept_context returns formatted string for LLM injection."""
        matches = self.registry.match_concepts("J.Crew provisions")
        context = self.registry.get_concept_context(matches)
        assert "J.Crew" in context or "j_crew" in context
        assert "intellectual property" in context.lower()
