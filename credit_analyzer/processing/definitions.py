"""Parse defined terms from the definitions section of a credit agreement."""

from __future__ import annotations

import bisect
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from credit_analyzer.processing.section_detector import DocumentSection

# Pattern to match defined terms in two styles:
#   Style 1 (colon): "Term": ... or \u201cTerm\u201d: ...
#   Style 2 (verb):  "Term" means ... or \u201cTerm\u201d means ...
# Group 1 = smart-quote colon, Group 2 = straight-quote colon,
# Group 3 = smart-quote verb, Group 4 = straight-quote verb.
_DEFINED_TERM_PATTERN = re.compile(
    # Style 1: quoted term followed by colon (no verb required)
    r'\u201c([A-Za-z][A-Za-z0-9\s\-/,()&]+?)\u201d\s*:'
    r"|"
    r'"([A-Za-z][A-Za-z0-9\s\-/,()&]+?)"\s*:'
    r"|"
    # Style 2: quoted term followed by definition verb
    r'\u201c([A-Za-z][A-Za-z0-9\s\-/,()&]+?)\u201d'
    r"|"
    r'"([A-Za-z][A-Za-z0-9\s\-/,()&]+?)"',
)

# Verbs that follow a defined term (used only for Style 2 matches).
_DEFINITION_VERBS = re.compile(
    r"\s*(?:means?|shall\s+mean|has\s+the\s+meaning|is\s+defined\s+as|refers?\s+to)",
    re.IGNORECASE,
)

# PDF source noise: BamSEC headers/footers, SEC filing lines, bare page numbers.
# These appear mid-definition when a definition spans a page break.
_PDF_NOISE_RE = re.compile(
    r"(?m)^\s*(?:"
    r"Powered by BamSEC\.com"
    r"|PDF page \d+"
    r"|[A-Z][A-Za-z\s,.]+ / \d+-[A-Z]+ / EX-[\d.]+ / [A-Za-z]+ \d+, \d{4}"
    r"|\d{1,3}$"
    r")\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class DefinitionEntry:
    """A single parsed definition with metadata."""

    text: str
    page_number: int | None = None


@dataclass(frozen=True)
class DefinitionsIndex:
    """Lookup index for defined terms extracted from a credit agreement.

    Attributes:
        definitions: Mapping of term name to its ``DefinitionEntry``.
    """

    definitions: dict[str, DefinitionEntry]
    _terms_pattern: re.Pattern[str] | None = field(default=None, init=False, repr=False, compare=False)
    _sub_terms: dict[str, list[str]] = field(
        default_factory=lambda: dict[str, list[str]](),
        init=False, repr=False, compare=False,
    )

    def __post_init__(self) -> None:
        if self.definitions:
            # Sort longest-first so the alternation matches the longest term
            sorted_terms = sorted(self.definitions.keys(), key=len, reverse=True)
            pattern = r"\b(?:" + "|".join(re.escape(t) for t in sorted_terms) + r")\b"
            # frozen=True requires object.__setattr__ for post_init
            object.__setattr__(self, "_terms_pattern", re.compile(pattern))

            # Pre-compute sub-term relationships: for each term, find all
            # shorter defined terms that are substrings of it.  This avoids
            # the O(n*m) loop in find_terms_in_text at query time.
            sub_terms: dict[str, list[str]] = {}
            for term in sorted_terms:
                subs = [
                    other
                    for other in sorted_terms
                    if other != term and other in term
                ]
                if subs:
                    sub_terms[term] = subs
            object.__setattr__(self, "_sub_terms", sub_terms)

    def lookup(self, term: str) -> str | None:
        """Look up a defined term by exact name.

        Args:
            term: The defined term to look up.

        Returns:
            The definition text, or None if not found.
        """
        entry = self.definitions.get(term)
        return entry.text if entry is not None else None

    def lookup_entry(self, term: str) -> DefinitionEntry | None:
        """Look up a defined term entry by exact name.

        Args:
            term: The defined term to look up.

        Returns:
            The ``DefinitionEntry``, or None if not found.
        """
        return self.definitions.get(term)

    def find_terms_in_text(self, text: str) -> list[str]:
        """Find all defined terms that appear in the given text.

        Uses a single pre-compiled alternation regex instead of O(n) per-term
        compilations. Also detects sub-terms contained within longer matches
        (e.g. "Net Income" inside "Consolidated Net Income").

        Args:
            text: The text to scan for defined terms.

        Returns:
            List of matching defined term names, longest first.
        """
        if self._terms_pattern is None:
            return []
        direct_matches = set(self._terms_pattern.findall(text))
        # Also find sub-terms that are wholly contained within longer matches
        # (regex alternation consumes the longest match, hiding sub-terms).
        # Uses pre-computed _sub_terms mapping instead of O(n*m) scan.
        found: set[str] = set()
        for m in direct_matches:
            if m in self.definitions:
                found.add(m)
            # Add pre-computed sub-terms for this match
            for sub in self._sub_terms.get(m, ()):
                found.add(sub)
        result = list(found)
        result.sort(key=len, reverse=True)
        return result

    def get_definitions_for_terms(self, terms: Sequence[str]) -> dict[str, str]:
        """Retrieve definition texts for a list of terms.

        Args:
            terms: Term names to look up.

        Returns:
            Dict mapping each found term to its definition text. Terms not
            in the index are silently skipped.
        """
        result: dict[str, str] = {}
        for term in terms:
            entry = self.definitions.get(term)
            if entry is not None:
                result[term] = entry.text
        return result

    def get_entries_for_terms(self, terms: Sequence[str]) -> dict[str, DefinitionEntry]:
        """Retrieve definition entries (with metadata) for a list of terms.

        Args:
            terms: Term names to look up.

        Returns:
            Dict mapping each found term to its ``DefinitionEntry``. Terms
            not in the index are silently skipped.
        """
        result: dict[str, DefinitionEntry] = {}
        for term in terms:
            entry = self.definitions.get(term)
            if entry is not None:
                result[term] = entry
        return result


class DefinitionsParser:
    """Parses defined terms from a credit agreement's definitions section."""

    def parse(
        self,
        definitions_section: DocumentSection,
        page_texts: list[tuple[int, str]] | None = None,
    ) -> DefinitionsIndex:
        """Extract all defined terms and their definitions from a section.

        Scans for quoted terms followed by definition verbs (means, shall mean,
        etc.), then captures everything up to the next defined term as the
        definition body.

        Args:
            definitions_section: The DocumentSection containing definitions
                (typically Article I).
            page_texts: Optional list of ``(page_number, page_text)`` tuples
                for the pages spanned by the definitions section.  When
                provided, each term is assigned the page number where it
                appears based on cumulative character offsets.

        Returns:
            A DefinitionsIndex with all parsed terms.
        """
        text = definitions_section.text
        term_positions = self._find_term_positions(text)

        if not term_positions:
            return DefinitionsIndex(definitions={})

        # Build page-offset mapping when page texts are available.
        page_boundaries: list[int] | None = None
        page_numbers: list[int] | None = None
        if page_texts:
            page_boundaries = []
            page_numbers = []
            cumulative = 0
            for page_num, page_text in page_texts:
                page_boundaries.append(cumulative)
                page_numbers.append(page_num)
                cumulative += len(page_text)

        definitions: dict[str, DefinitionEntry] = {}
        for i, (term, start) in enumerate(term_positions):
            # Definition text runs from the start of this term's line
            # to the start of the next term
            end = term_positions[i + 1][1] if i + 1 < len(term_positions) else len(text)

            raw_definition = text[start:end].strip()
            cleaned = self._clean_definition(raw_definition)

            # Determine page number via binary search on cumulative offsets.
            page_number: int | None = None
            if page_boundaries is not None and page_numbers is not None:
                idx = bisect.bisect_right(page_boundaries, start) - 1
                idx = max(0, min(idx, len(page_numbers) - 1))
                page_number = page_numbers[idx]

            definitions[term] = DefinitionEntry(text=cleaned, page_number=page_number)

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
            # Groups 1-2 = colon style (smart/straight), no verb needed
            # Groups 3-4 = verb style (smart/straight), verb required
            term = match.group(1) or match.group(2)
            needs_verb = False
            if term is None:
                term = match.group(3) or match.group(4)
                needs_verb = True
            if term is None:
                continue

            term = term.strip()
            if not term:
                continue

            # Verb-style matches must have a definition verb after the quote
            if needs_verb:
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

        Strips excess whitespace, normalizes line breaks, and removes
        PDF source noise (e.g. BamSEC page headers/footers).

        Args:
            raw: The raw definition text.

        Returns:
            Cleaned definition string.
        """
        # Remove BamSEC / SEC filing noise lines
        cleaned = _PDF_NOISE_RE.sub("", raw)
        # Collapse multiple newlines into single newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Collapse multiple spaces into single spaces within lines
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()
