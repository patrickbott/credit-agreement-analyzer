"""Sentence-transformer embedding wrapper for credit agreement chunks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.config import EMBEDDING_MODEL


class Embedder:
    """Thin wrapper around a SentenceTransformer model.

    Produces float32 embeddings for document chunks and queries.
    Uses the model configured in ``credit_analyzer.config.EMBEDDING_MODEL``.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self._model: SentenceTransformer = SentenceTransformer(model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: The texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
            Each vector is a plain list of floats.
        """
        if not texts:
            return []

        raw: NDArray[np.float32] = cast(
            NDArray[np.float32],
            self._model.encode(  # pyright: ignore[reportUnknownMemberType]
                list(texts),
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
        )
        return [row.tolist() for row in raw]

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string.

        Args:
            query: The search query.

        Returns:
            The embedding vector as a list of floats.
        """
        raw: NDArray[np.float32] = cast(
            NDArray[np.float32],
            self._model.encode(  # pyright: ignore[reportUnknownMemberType]
                query,
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
