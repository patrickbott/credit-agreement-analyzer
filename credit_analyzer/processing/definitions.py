"""Parse defined terms from the definitions section of a credit agreement."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from credit_analyzer.processing.section_detector import DocumentSection

# Pattern to match defined terms: "Term" means / "Term" shall mean / "Term" has the meaning
# Captures the quoted term name.
_DEFINED_TERM_PATTERN = re.compile(
    r'\u201c([A-Za-z][A-Za-z0-9\s\-/,()&]+?)\u201d'  # smart quotes
    r"|"
    r'"([A-Za-z][A-Za-z0-9\s\-/,()&]+?)"',  # straight quotes
)

# Verbs that follow a defined term to confirm it's actually a definition
_DEFINITION_VERBS = re.compile(
    r"\s+(?:means?|shall\s+mean|has\s+the\s+meaning|is\s+defined\s+as|refers?\s+to)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DefinitionsIndex:
    """Lookup index for defined terms extracted from a credit agreement.

    Attributes:
        definitions: Mapping of term name to its full definition text.
    """

    definitions: dict[str, str]

    def lookup(self, term: str) -> str | None:
        """Look up a defined term by exact name.

        Args:
            term: The defined term to look up.

        Returns:
            The definition text, or None if not found.
        """
        return self.definitions.get(term)

    def find_terms_in_text(self, text: str) -> list[str]:
        """Find all defined terms that appear in the given text.

        Searches for each known defined term as a whole word in the text.
        Returns terms sorted longest-first to support greedy matching
        by downstream consumers.

        Args:
            text: The text to scan for defined terms.

        Returns:
            List of matching defined term names, longest first.
        """
        found: list[str] = []
        for term in self.definitions:
            # Whole-word match to avoid partial hits (e.g. "Loan" inside "Loans")
            # Use word boundary but allow for possessives and plurals at the end
            if re.search(r"\b" + re.escape(term) + r"\b", text):
                found.append(term)
        # Sort longest first so callers doing greedy replacement get the right match
        found.sort(key=len, reverse=True)
        return found

    def get_definitions_for_terms(self, terms: Sequence[str]) -> dict[str, str]:
        """Retrieve definitions for a list of terms.

        Args:
            terms: Term names to look up.

        Returns:
            Dict mapping each found term to its definition. Terms not in
            the index are silently skipped.
        """
        result: dict[str, str] = {}
        for term in terms:
            defn = self.definitions.get(term)
            if defn is not None:
                result[term] = defn
        return result


class DefinitionsParser:
    """Parses defined terms from a credit agreement's definitions section."""

    def parse(self, definitions_section: DocumentSection) -> DefinitionsIndex:
        """Extract all defined terms and their definitions from a section.

        Scans for quoted terms followed by definition verbs (means, shall mean,
        etc.), then captures everything up to the next defined term as the
        definition body.

        Args:
            definitions_section: The DocumentSection containing definitions
                (typically Article I).

        Returns:
            A DefinitionsIndex with all parsed terms.
        """
        text = definitions_section.text
        term_positions = self._find_term_positions(text)

        if not term_positions:
            return DefinitionsIndex(definitions={})

        definitions: dict[str, str] = {}
        for i, (term, start) in enumerate(term_positions):
            # Definition text runs from the start of this term's line
            # to the start of the next term
            if i + 1 < len(term_positions):
                end = term_positions[i + 1][1]
            else:
                end = len(text)

            raw_definition = text[start:end].strip()
            # Clean up: remove trailing whitespace and incomplete sentences
            definitions[term] = self._clean_definition(raw_definition)

        return DefinitionsIndex(definitions=definitions)

    def _find_term_positions(self, text: str) -> list[tuple[str, int]]:
        """Find all defined term positions in the text.

        A "defined term" is a quoted term followed by a definition verb
        (means, shall mean, etc.).

        Args:
            text: The definitions section text.

        Returns:
            List of (term_name, start_offset) tuples, sorted by position.
        """
        positions: list[tuple[str, int]] = []
        seen_terms: set[str] = set()

        for match in _DEFINED_TERM_PATTERN.finditer(text):
            # Group 1 = smart quotes, Group 2 = straight quotes
            term = match.group(1) or match.group(2)
            if term is None:
                continue

            term = term.strip()
            if not term:
                continue

            # Check that a definition verb follows the closing quote
            after_quote = text[match.end() : match.end() + 50]
            if not _DEFINITION_VERBS.match(after_quote):
                continue

            # Skip duplicates (keep first occurrence)
            if term in seen_terms:
                continue
            seen_terms.add(term)

            # Find the start of the line containing this term
            line_start = text.rfind("\n", 0, match.start())
            line_start = line_start + 1 if line_start != -1 else 0

            positions.append((term, line_start))

        return positions

    def _clean_definition(self, raw: str) -> str:
        """Clean up a raw definition text block.

        Strips excess whitespace and normalizes line breaks.

        Args:
            raw: The raw definition text.

        Returns:
            Cleaned definition string.
        """
        # Collapse multiple newlines into single newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", raw)
        # Collapse multiple spaces into single spaces within lines
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()
