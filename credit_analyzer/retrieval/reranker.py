"""Cross-encoder reranker for second-stage retrieval scoring.

After hybrid retrieval produces an over-fetched candidate set, the
cross-encoder processes each (query, chunk) pair through a full
transformer to produce a more accurate relevance score than the
independent bi-encoder / BM25 scores used in the first stage.
"""

from __future__ import annotations

import logging
import math
import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sentence_transformers import CrossEncoder  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.config import RERANKER_MODEL

if TYPE_CHECKING:
    from credit_analyzer.retrieval.hybrid_retriever import HybridChunk


def _load_cross_encoder(model_name: str) -> CrossEncoder:
    """Load CrossEncoder with noisy library warnings suppressed."""
    prev_hf = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS")
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    loggers_to_quiet = ["safetensors", "sentence_transformers", "huggingface_hub"]
    saved_levels = {name: logging.getLogger(name).level for name in loggers_to_quiet}
    for name in loggers_to_quiet:
        logging.getLogger(name).setLevel(logging.ERROR)
    try:
        return CrossEncoder(model_name)  # pyright: ignore[reportUnknownMemberType]
    finally:
        for name, level in saved_levels.items():
            logging.getLogger(name).setLevel(level)
        if prev_hf is None:
            os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
        else:
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = prev_hf


class Reranker:
    """Cross-encoder reranker using sentence-transformers.

    Scores (query, chunk_text) pairs jointly through a cross-encoder
    model and returns the chunks sorted by relevance score descending.
    """

    def __init__(self, model_name: str = RERANKER_MODEL) -> None:
        self._model: CrossEncoder = _load_cross_encoder(model_name)

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
            _HybridChunk(chunk=hc.chunk, score=1.0 / (1.0 + math.exp(-float(s))), source=hc.source)
            for hc, s in zip(chunks, scores, strict=True)
        ]
        scored.sort(key=lambda hc: hc.score, reverse=True)
        return scored[:top_k]
