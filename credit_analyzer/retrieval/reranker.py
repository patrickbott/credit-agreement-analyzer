"""Cross-encoder reranker for second-stage retrieval scoring.

After hybrid retrieval produces an over-fetched candidate set, the
cross-encoder processes each (query, chunk) pair through a full
transformer to produce a more accurate relevance score than the
independent bi-encoder / BM25 scores used in the first stage.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sentence_transformers import CrossEncoder  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.config import RERANKER_MODEL

if TYPE_CHECKING:
    from credit_analyzer.retrieval.hybrid_retriever import HybridChunk


class Reranker:
    """Cross-encoder reranker using sentence-transformers.

    Scores (query, chunk_text) pairs jointly through a cross-encoder
    model and returns the chunks sorted by relevance score descending.
    """

    def __init__(self, model_name: str = RERANKER_MODEL) -> None:
        self._model: CrossEncoder = CrossEncoder(model_name)  # pyright: ignore[reportUnknownMemberType]

    def rerank(
        self,
        query: str,
        chunks: Sequence[HybridChunk],
        top_k: int,
    ) -> list[HybridChunk]:
        """Rerank candidate chunks by cross-encoder relevance score.

        Args:
            query: The search query.
            chunks: Candidate chunks from hybrid retrieval (over-fetched).
            top_k: Maximum number of chunks to return after reranking.

        Returns:
            Top-k chunks sorted by cross-encoder score descending, with
            scores replaced by the cross-encoder output.
        """
        from credit_analyzer.retrieval.hybrid_retriever import HybridChunk as _HybridChunk

        if not chunks:
            return []

        pairs: list[list[str]] = [[query, hc.chunk.text] for hc in chunks]
        scores: list[float] = self._model.predict(pairs).tolist()  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

        scored = [
            _HybridChunk(chunk=hc.chunk, score=float(s), source=hc.source)
            for hc, s in zip(chunks, scores, strict=True)
        ]
        scored.sort(key=lambda hc: hc.score, reverse=True)
        return scored[:top_k]
