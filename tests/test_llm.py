"""Tests for the LLM provider layer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from credit_analyzer.llm.base import LLMProvider, LLMResponse
from credit_analyzer.llm.factory import get_provider
from credit_analyzer.llm.internal_provider import InternalLLMProvider
from credit_analyzer.llm.ollama_provider import OllamaProvider

# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


def test_llm_response_fields() -> None:
    """LLMResponse stores all fields correctly."""
    resp = LLMResponse(text="hello", tokens_used=10, model="test", duration_seconds=1.5)
    assert resp.text == "hello"
    assert resp.tokens_used == 10
    assert resp.model == "test"
    assert resp.duration_seconds == 1.5


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_get_provider_ollama() -> None:
    """Factory returns OllamaProvider when asked for 'ollama'."""
    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.model_name() == "llama3.2:3b"  # default from config


def test_get_provider_internal() -> None:
    """Factory returns InternalLLMProvider when asked for 'internal'."""
    provider = get_provider("internal")
    assert isinstance(provider, InternalLLMProvider)


def test_get_provider_default_uses_config() -> None:
    """Factory with no argument uses LLM_PROVIDER from config."""
    provider = get_provider()
    # Config default is "ollama"
    assert isinstance(provider, OllamaProvider)


def test_get_provider_unknown_raises() -> None:
    """Factory raises ValueError for an unrecognised provider name."""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider("nonexistent")


# ---------------------------------------------------------------------------
# OllamaProvider (mocked)
# ---------------------------------------------------------------------------


def _mock_chat_response() -> dict[str, Any]:
    """A minimal dict mimicking Ollama's chat() return shape."""
    return {
        "message": {"role": "assistant", "content": "Facility: Revolving; Amount: $50M"},
        "eval_count": 42,
        "total_duration": 2_500_000_000,  # 2.5 seconds in nanoseconds
    }


@patch("credit_analyzer.llm.ollama_provider.ollama.Client")
def test_ollama_complete(mock_client_cls: MagicMock) -> None:
    """OllamaProvider.complete() parses the Ollama response correctly."""
    mock_client = MagicMock()
    mock_client.chat.return_value = _mock_chat_response()
    mock_client_cls.return_value = mock_client

    provider = OllamaProvider(model="llama3:8b", base_url="http://localhost:11434")
    resp = provider.complete(
        system_prompt="Extract info.",
        user_prompt="What is the facility?",
        temperature=0.0,
        max_tokens=512,
    )

    assert resp.text == "Facility: Revolving; Amount: $50M"
    assert resp.tokens_used == 42
    assert resp.model == "llama3:8b"
    assert resp.duration_seconds == pytest.approx(2.5)

    # Verify the call shape
    mock_client.chat.assert_called_once()
    call_kwargs = mock_client.chat.call_args
    assert call_kwargs.kwargs["model"] == "llama3:8b"
    messages = call_kwargs.kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


@patch("credit_analyzer.llm.ollama_provider.ollama.Client")
def test_ollama_is_available_true(mock_client_cls: MagicMock) -> None:
    """is_available() returns True when the model is listed."""
    mock_client = MagicMock()
    mock_client.list.return_value = {
        "models": [{"name": "llama3:8b", "model": "llama3:8b"}],
    }
    mock_client_cls.return_value = mock_client

    provider = OllamaProvider(model="llama3:8b", base_url="http://localhost:11434")
    assert provider.is_available() is True


@patch("credit_analyzer.llm.ollama_provider.ollama.Client")
def test_ollama_is_available_false_no_model(mock_client_cls: MagicMock) -> None:
    """is_available() returns False when the model is not listed."""
    mock_client = MagicMock()
    mock_client.list.return_value = {"models": [{"name": "mistral:7b", "model": "mistral:7b"}]}
    mock_client_cls.return_value = mock_client

    provider = OllamaProvider(model="llama3:8b", base_url="http://localhost:11434")
    assert provider.is_available() is False


@patch("credit_analyzer.llm.ollama_provider.ollama.Client")
def test_ollama_is_available_false_connection_error(mock_client_cls: MagicMock) -> None:
    """is_available() returns False when Ollama is unreachable."""
    mock_client = MagicMock()
    mock_client.list.side_effect = ConnectionError("refused")
    mock_client_cls.return_value = mock_client

    provider = OllamaProvider(model="llama3:8b", base_url="http://localhost:11434")
    assert provider.is_available() is False


@patch("credit_analyzer.llm.ollama_provider.ollama.Client")
def test_ollama_complete_missing_optional_fields(mock_client_cls: MagicMock) -> None:
    """OllamaProvider handles missing eval_count / total_duration gracefully."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"role": "assistant", "content": "answer"},
    }
    mock_client_cls.return_value = mock_client

    provider = OllamaProvider(model="llama3:8b", base_url="http://localhost:11434")
    resp = provider.complete(system_prompt="s", user_prompt="q")

    assert resp.text == "answer"
    assert resp.tokens_used == 0
    assert resp.duration_seconds == 0.0


# ---------------------------------------------------------------------------
# InternalLLMProvider
# ---------------------------------------------------------------------------


def test_internal_provider_complete_raises() -> None:
    """InternalLLMProvider.complete() raises NotImplementedError."""
    provider = InternalLLMProvider()
    with pytest.raises(NotImplementedError, match="not configured"):
        provider.complete(system_prompt="s", user_prompt="q")


def test_internal_provider_not_available() -> None:
    """InternalLLMProvider.is_available() always returns False."""
    provider = InternalLLMProvider()
    assert provider.is_available() is False


def test_internal_provider_model_name() -> None:
    """InternalLLMProvider.model_name() returns a descriptive placeholder."""
    provider = InternalLLMProvider()
    assert "not configured" in provider.model_name()


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------


def test_cannot_instantiate_base() -> None:
    """LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]
