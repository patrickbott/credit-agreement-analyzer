# tests/test_query_decomposer.py
"""Tests for the LLM query decomposer."""

from __future__ import annotations

from unittest.mock import MagicMock

from credit_analyzer.generation.query_decomposer import (
    DECOMPOSITION_SYSTEM_PROMPT,
    decompose_query,
    parse_sub_queries,
)
from credit_analyzer.llm.base import LLMResponse


class TestParseSubQueries:
    """Tests for parsing LLM decomposition output."""

    def test_parses_numbered_list(self) -> None:
        text = (
            "1. What provisions allow IP transfer to unrestricted subsidiaries?\n"
            "2. Are there restrictions on designating unrestricted subsidiaries?"
        )
        queries = parse_sub_queries(text)
        assert len(queries) == 2
        assert "IP transfer" in queries[0]
        assert "unrestricted subsidiaries" in queries[1]

    def test_parses_dashed_list(self) -> None:
        text = "- provisions for transferring intellectual property\n- unrestricted subsidiary designation conditions"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_parses_plain_lines(self) -> None:
        text = "intellectual property transfer provisions\nunrestricted subsidiary restrictions"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_filters_empty_lines(self) -> None:
        text = "1. query one\n\n2. query two\n\n"
        queries = parse_sub_queries(text)
        assert len(queries) == 2

    def test_caps_at_max(self) -> None:
        text = "\n".join(f"{i}. query {i}" for i in range(1, 15))
        queries = parse_sub_queries(text)
        assert len(queries) <= 5

    def test_returns_original_on_empty(self) -> None:
        """If parsing yields nothing, returns empty list."""
        queries = parse_sub_queries("")
        assert queries == []


class TestDecomposeQuery:
    """Tests for the full decomposition call."""

    def test_calls_llm_with_concept_context(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = LLMResponse(
            text="1. What are the IP transfer provisions?\n2. Can the borrower designate unrestricted subsidiaries?",
            tokens_used=30, model="test", duration_seconds=0.5,
        )
        concept_context = "CONCEPT: J.Crew Provision\nDESCRIPTION: IP transfer to unrestricted subs"
        queries = decompose_query(
            llm, "Are there J.Crew provisions?", concept_context=concept_context,
        )
        assert len(queries) >= 2
        # Verify concept context was passed to LLM
        call_kwargs = llm.complete.call_args.kwargs
        assert "J.Crew" in call_kwargs["user_prompt"] or "J.Crew" in call_kwargs.get("system_prompt", "")

    def test_returns_fallback_on_llm_error(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("LLM down")
        queries = decompose_query(llm, "Are there J.Crew provisions?")
        # Should return fallback (original query)
        assert len(queries) >= 1
        assert "J.Crew" in queries[0]


class TestDecompositionPrompt:
    """Tests for the decomposition system prompt."""

    def test_prompt_exists_and_mentions_credit(self) -> None:
        assert len(DECOMPOSITION_SYSTEM_PROMPT) > 100
        assert "credit" in DECOMPOSITION_SYSTEM_PROMPT.lower()
