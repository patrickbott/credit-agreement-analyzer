"""Domain knowledge registry for leveraged finance concepts and synonyms.

Loads curated YAML data files and provides fast lookup for concept alias
matching and synonym expansion during query processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # pyright: ignore[reportMissingTypeStubs]

_KNOWLEDGE_DIR = Path(__file__).parent


@dataclass(frozen=True)
class ConceptMatch:
    """A matched domain concept with its retrieval metadata."""

    concept_id: str
    matched_alias: str
    search_terms: list[str]
    description: str
    sections: list[str]


@dataclass
class _ConceptEntry:
    """Internal representation of a concept from YAML."""

    concept_id: str
    aliases: list[str]
    search_terms: list[str]
    description: str
    sections: list[str]
    # Pre-compiled pattern for fast matching
    pattern: re.Pattern[str]


@dataclass
class _SynonymGroup:
    """A group of synonymous terms."""

    canonical: str
    alternatives: list[str]


class DomainRegistry:
    """Registry of leveraged finance concepts and synonyms.

    Loads from YAML on construction and provides fast alias matching
    and synonym expansion for query preprocessing.
    """

    def __init__(
        self,
        concepts_path: Path | None = None,
        synonyms_path: Path | None = None,
    ) -> None:
        self._concepts: list[_ConceptEntry] = []
        self._synonym_groups: list[_SynonymGroup] = []

        concepts_file = concepts_path or _KNOWLEDGE_DIR / "concepts.yaml"
        synonyms_file = synonyms_path or _KNOWLEDGE_DIR / "synonyms.yaml"

        if concepts_file.exists():
            self._load_concepts(concepts_file)
        if synonyms_file.exists():
            self._load_synonyms(synonyms_file)

    @property
    def concepts(self) -> list[_ConceptEntry]:
        return self._concepts

    @property
    def synonym_groups(self) -> list[_SynonymGroup]:
        return self._synonym_groups

    def _load_concepts(self, path: Path) -> None:
        """Load concept entries from YAML and pre-compile alias patterns."""
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        for concept_id, entry in (data.get("concepts") or {}).items():
            aliases: list[str] = entry.get("aliases", [])
            if not aliases:
                continue

            # Build regex: sort aliases longest-first to prefer longer matches
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            escaped = [re.escape(a) for a in sorted_aliases]
            pattern = re.compile(
                r"\b(?:" + "|".join(escaped) + r")\b",
                re.IGNORECASE,
            )

            self._concepts.append(_ConceptEntry(
                concept_id=concept_id,
                aliases=aliases,
                search_terms=entry.get("search_terms", []),
                description=entry.get("description", "").strip(),
                sections=entry.get("sections", []),
                pattern=pattern,
            ))

    def _load_synonyms(self, path: Path) -> None:
        """Load synonym groups from YAML."""
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        for _group_id, entry in (data.get("synonyms") or {}).items():
            canonical = entry.get("canonical", "")
            alternatives = entry.get("alternatives", [])
            if canonical and alternatives:
                self._synonym_groups.append(
                    _SynonymGroup(canonical=canonical, alternatives=alternatives)
                )

    def match_concepts(self, query: str) -> list[ConceptMatch]:
        """Find all domain concepts whose aliases appear in the query.

        Returns a list of ConceptMatch objects with retrieval metadata.
        Matching is case-insensitive and uses word boundaries.
        """
        matches: list[ConceptMatch] = []
        for concept in self._concepts:
            m = concept.pattern.search(query)
            if m:
                matches.append(ConceptMatch(
                    concept_id=concept.concept_id,
                    matched_alias=m.group(0),
                    search_terms=concept.search_terms,
                    description=concept.description,
                    sections=concept.sections,
                ))
        return matches

    def expand_synonyms(self, query: str) -> list[str]:
        """Find synonym expansions relevant to the query.

        Returns a list of canonical and alternative terms that could
        be used to broaden retrieval.
        """
        query_lower = query.lower()
        expansions: list[str] = []
        for group in self._synonym_groups:
            # Check if canonical or any alternative appears in the query
            all_terms = [group.canonical.lower()] + [
                a.lower() for a in group.alternatives
            ]
            for term in all_terms:
                if len(term) >= 3 and term in query_lower:
                    # Add all terms from the group that are NOT already in the query
                    for t in [group.canonical] + group.alternatives:
                        if t.lower() not in query_lower:
                            expansions.append(t)
                    break
        return expansions

    def get_concept_context(self, matches: list[ConceptMatch]) -> str:
        """Format matched concepts as context text for LLM injection.

        Returns a string to append to the system prompt or user prompt
        giving the LLM domain context about what the user is asking about.
        """
        if not matches:
            return ""
        parts: list[str] = ["=== DOMAIN CONCEPT CONTEXT ==="]
        for m in matches:
            parts.append(
                f'CONCEPT: {m.concept_id.replace("_", " ").title()}\n'
                f"DESCRIPTION: {m.description}\n"
                f'LOOK FOR: {", ".join(m.search_terms)}'
            )
        return "\n\n".join(parts)
