"""Config-driven LLM provider factory."""

from __future__ import annotations

from typing import Literal

from credit_analyzer.config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
from credit_analyzer.llm.base import LLMProvider
from credit_analyzer.llm.internal_provider import InternalLLMProvider
from credit_analyzer.llm.ollama_provider import OllamaProvider

ProviderName = Literal["ollama", "internal"]

_VALID_PROVIDERS: frozenset[str] = frozenset({"ollama", "internal"})


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Return an :class:`LLMProvider` instance based on config or an explicit name.

    Parameters
    ----------
    provider_name:
        Override the provider selection.  When ``None`` (the default),
        :data:`credit_analyzer.config.LLM_PROVIDER` is used.

    Raises
    ------
    ValueError
        If the provider name is not recognised.
    """
    name = provider_name if provider_name is not None else LLM_PROVIDER

    if name == "ollama":
        return OllamaProvider(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

    if name == "internal":
        return InternalLLMProvider()

    msg = f"Unknown LLM provider: {name!r}. Valid options: {sorted(_VALID_PROVIDERS)}"
    raise ValueError(msg)
