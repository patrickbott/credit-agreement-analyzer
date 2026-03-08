"""Config-driven LLM provider factory."""

from __future__ import annotations

from typing import Literal

from credit_analyzer.config import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from credit_analyzer.llm.base import LLMProvider

ProviderName = Literal["ollama", "claude", "internal"]

_VALID_PROVIDERS: frozenset[str] = frozenset({"ollama", "claude", "internal"})


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Return a configured LLM provider instance.

    Args:
        provider_name: Override provider selection; defaults to LLM_PROVIDER in config.

    Raises:
        ValueError: If the provider name is unrecognized.
    """
    name = provider_name if provider_name is not None else LLM_PROVIDER

    if name == "ollama":
        from credit_analyzer.llm.ollama_provider import OllamaProvider

        return OllamaProvider(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

    if name == "claude":
        from credit_analyzer.llm.claude_provider import ClaudeProvider

        return ClaudeProvider(model=CLAUDE_MODEL, api_key=CLAUDE_API_KEY)

    if name == "internal":
        from credit_analyzer.llm.internal_provider import InternalLLMProvider

        return InternalLLMProvider()

    msg = f"Unknown LLM provider: {name!r}. Valid options: {sorted(_VALID_PROVIDERS)}"
    raise ValueError(msg)
