"""BM25 keyword-based retrieval for credit agreement chunks."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import rank_bm25  # pyright: ignore[reportMissingTypeStubs]
from numpy.typing import NDArray

from credit_analyzer.config import BM25_B, BM25_K1
from credit_analyzer.processing.chunker import Chunk, build_search_text


@dataclass
class BM25Result:
    """A chunk returned from a BM25 keyword search.

    Attributes:
        chunk: The matched Chunk object.
        score: The raw BM25 relevance score (higher is better).
    """

    chunk: Chunk
    score: float


def tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer with lowercasing.

    Splits on whitespace, lowercases, and strips punctuation from
    token edges.  Good enough for BM25 on legal text where exact
    dollar amounts and ratios matter.

    Args:
        text: The text to tokenize.

    Returns:
        List of lowercase token strings.
    """
    tokens: list[str] = []
    for word in text.lower().split():
        stripped = word.strip(".,;:!?()[]{}\"'")
        if stripped:
            tokens.append(stripped)
    return tokens


class BM25Store:
    """BM25 keyword index over credit agreement chunks.

    Complements vector search by catching exact term matches
    (dollar amounts, ratios, specific legal terms) that embedding
    models often miss.

    The index is built in-memory and is fast to reconstruct whenever
    a new document is processed.
    """

    def __init__(self) -> None:
        self._index: Any | None = None
        self._chunks: list[Chunk] = []

    @property
    def chunks(self) -> Sequence[Chunk]:
        """Return the indexed chunks (read-only).

        Used by HybridRetriever to build a definition chunk lookup
        at initialization time.

        Returns:
            The sequence of chunks currently in the index.
        """
        return self._chunks

    def build_index(self, chunks: Sequence[Chunk]) -> None:
        """Build a BM25 index from the given chunks.

        Replaces any existing index.

        Args:
            chunks: The chunks to index.
        """
        self._chunks = list(chunks)
        if not self._chunks:
            self._index = None
            return

        corpus = [tokenize(build_search_text(c)) for c in self._chunks]
        self._index = rank_bm25.BM25Plus(corpus, k1=BM25_K1, b=BM25_B)  # pyright: ignore[reportUnknownMemberType]

    def search(
        self,
        query: str,
        top_k: int = 5,
        section_filter: str | None = None,
        section_types_exclude: Sequence[str] | None = None,
    ) -> list[BM25Result]:
        """Search the index for chunks matching the query keywords.

        Args:
            query: The search query string.
            top_k: Maximum number of results to return.
            section_filter: If provided, only return chunks with this section_type.
                Takes precedence over section_types_exclude.
            section_types_exclude: If provided and section_filter is None,
                exclude chunks whose section_type is in this list.

        Returns:
            List of BM25Result objects sorted by score (best first).
        """
        if self._index is None or not self._chunks:
            return []

        tokenized_query = tokenize(query)
        if not tokenized_query:
            return []

        if section_filter is not None:
            return self._search_filtered(tokenized_query, top_k, section_filter)

        if section_types_exclude:
            exclude_set = set(section_types_exclude)
            return self._search_excluding(tokenized_query, top_k, exclude_set)

        return self._search_all(tokenized_query, top_k)

    def _search_all(
        self,
        tokenized_query: list[str],
        top_k: int,
    ) -> list[BM25Result]:
        """Search across all chunks.

        Args:
            tokenized_query: Pre-tokenized query terms.
            top_k: Maximum results.

        Returns:
            Sorted list of BM25Result.
        """
        raw_scores: NDArray[np.float64] = cast(
            NDArray[np.float64],
            self._index.get_scores(tokenized_query),  # pyright: ignore[reportOptionalMemberAccess, reportUnknownMemberType]
        )

        # Get top-k indices by score (descending)
        top_indices: NDArray[np.intp] = np.argsort(raw_scores)[::-1][:top_k]

        results: list[BM25Result] = []
        for idx in top_indices:
            i = int(idx)
            score = float(raw_scores[i])
            if score <= 0.0:
                break
            results.append(BM25Result(chunk=self._chunks[i], score=score))

        return results

    def _search_filtered(
        self,
        tokenized_query: list[str],
        top_k: int,
        section_filter: str,
    ) -> list[BM25Result]:
        """Search only chunks matching a section type filter.

        Scores all chunks with the pre-built index and filters post-hoc,
        avoiding the cost of rebuilding a temporary index per query.
        """
        all_results = self._search_all(tokenized_query, top_k=len(self._chunks))
        return [r for r in all_results if r.chunk.section_type == section_filter][:top_k]

    def _search_excluding(
        self,
        tokenized_query: list[str],
        top_k: int,
        exclude_set: set[str],
    ) -> list[BM25Result]:
        """Search chunks excluding certain section types.

        Scores all chunks with the pre-built index and filters post-hoc.
        """
        all_results = self._search_all(tokenized_query, top_k=len(self._chunks))
        return [r for r in all_results if r.chunk.section_type not in exclude_set][:top_k]
