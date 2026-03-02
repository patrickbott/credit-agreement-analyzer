"""Sentence-transformer embedding wrapper for credit agreement chunks."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.config import EMBEDDING_MODEL

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    """Thin wrapper around a SentenceTransformer model.

    Produces float32 embeddings for document chunks and queries.
    Uses the model configured in ``credit_analyzer.config.EMBEDDING_MODEL``.

    For BGE models, query embeddings are automatically prefixed with the
    instruction string the model was trained with, improving retrieval
    alignment between queries and documents.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self._model: SentenceTransformer = SentenceTransformer(model_name)
        self._model_name = model_name
        self._is_bge = "bge" in model_name.lower()

    def embed(
        self,
        texts: Sequence[str],
        batch_size: int = 64,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: The texts to embed.
            batch_size: Number of texts to encode per batch.
            progress_callback: Optional ``(completed, total)`` callback
                fired after each batch so callers can update a progress bar.

        Returns:
            A list of embedding vectors, one per input text.
            Each vector is a plain list of floats.
        """
        if not texts:
            return []

        text_list = list(texts)
        total = len(text_list)

        # Fast path: small input or no progress tracking needed.
        if progress_callback is None or total <= batch_size:
            raw: NDArray[np.float32] = cast(
                NDArray[np.float32],
                self._model.encode(  # pyright: ignore[reportUnknownMemberType]
                    text_list,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    batch_size=batch_size,
                ),
            )
            if progress_callback is not None:
                progress_callback(total, total)
            return [row.tolist() for row in raw]

        # Batch path: encode in slices and report progress.
        all_embeddings: list[list[float]] = []
        for start in range(0, total, batch_size):
            batch = text_list[start : start + batch_size]
            raw = cast(
                NDArray[np.float32],
                self._model.encode(  # pyright: ignore[reportUnknownMemberType]
                    batch,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ),
            )
            all_embeddings.extend(row.tolist() for row in raw)
            progress_callback(min(start + batch_size, total), total)

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string.

        For BGE models, prepends the instruction prefix the model was
        trained with to improve query-document alignment.

        Args:
            query: The search query.

        Returns:
            The embedding vector as a list of floats.
        """
        text = f"{_BGE_QUERY_PREFIX}{query}" if self._is_bge else query
        raw: NDArray[np.float32] = cast(
            NDArray[np.float32],
            self._model.encode(  # pyright: ignore[reportUnknownMemberType]
                text,
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
        )
        return cast(list[float], raw.tolist())

    @property
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        dim: int = cast(
            int,
            self._model.get_sentence_embedding_dimension(),  # pyright: ignore[reportUnknownMemberType]
        )
        return dim
