"""Tests for the embedder module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from credit_analyzer.retrieval.embedder import Embedder

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_DIM = 384


def _fake_encode(
    sentences: str | list[str],
    *,
    show_progress_bar: bool = False,
    convert_to_numpy: bool = True,
    **kwargs: Any,
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Return a deterministic numpy array mimicking SentenceTransformer.encode."""
    if isinstance(sentences, str):
        return np.ones((_FAKE_DIM,), dtype=np.float32) * 0.5
    return np.ones((len(sentences), _FAKE_DIM), dtype=np.float32) * 0.5


# ---------------------------------------------------------------------------
# Unit tests (mocked model)
# ---------------------------------------------------------------------------


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_embed_returns_list_of_lists(mock_st_cls: MagicMock) -> None:
    """embed() returns one list[float] per input text."""
    mock_model = MagicMock()
    mock_model.encode = MagicMock(side_effect=_fake_encode)
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    result = embedder.embed(["hello", "world"])

    assert len(result) == 2
    assert len(result[0]) == _FAKE_DIM
    assert isinstance(result[0][0], float)


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_embed_empty_input(mock_st_cls: MagicMock) -> None:
    """embed() returns an empty list for empty input."""
    mock_model = MagicMock()
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    result = embedder.embed([])

    assert result == []
    mock_model.encode.assert_not_called()


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_embed_query_returns_flat_list(mock_st_cls: MagicMock) -> None:
    """embed_query() returns a single flat list[float]."""
    mock_model = MagicMock()
    mock_model.encode = MagicMock(side_effect=_fake_encode)
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    result = embedder.embed_query("What is the revolver size?")

    assert isinstance(result, list)
    assert len(result) == _FAKE_DIM
    assert isinstance(result[0], float)


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_dimension_property(mock_st_cls: MagicMock) -> None:
    """dimension property returns the model's embedding dimension."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension = MagicMock(return_value=_FAKE_DIM)
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    assert embedder.dimension == _FAKE_DIM


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_embed_accepts_sequence_types(mock_st_cls: MagicMock) -> None:
    """embed() accepts any Sequence[str], not just list."""
    mock_model = MagicMock()
    mock_model.encode = MagicMock(side_effect=_fake_encode)
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    result = embedder.embed(("hello", "world"))

    assert len(result) == 2


@patch("credit_analyzer.retrieval.embedder.SentenceTransformer")
def test_encode_called_with_correct_args(mock_st_cls: MagicMock) -> None:
    """Verify encode is called with show_progress_bar=False and convert_to_numpy=True."""
    mock_model = MagicMock()
    mock_model.encode = MagicMock(side_effect=_fake_encode)
    mock_st_cls.return_value = mock_model

    embedder = Embedder(model_name="fake-model")
    embedder.embed(["test"])

    mock_model.encode.assert_called_once_with(
        ["test"],
        show_progress_bar=False,
        convert_to_numpy=True,
        batch_size=64,
    )
