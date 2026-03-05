"""Abstract LLM provider interface and shared response type."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM completion call."""

    text: str
    tokens_used: int
    model: str
    duration_seconds: float


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Subclasses must implement ``complete``, ``is_available``, and ``model_name``.
    """

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a completion request and return the response."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` if the provider backend is reachable."""

    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the model in use."""

    def stream_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> Generator[str, None, None]:
        """Stream completion tokens as they are generated.

        Default implementation falls back to non-streaming complete().
        Subclasses may override for true streaming.
        """
        response = self.complete(system_prompt, user_prompt, temperature, max_tokens)
        yield response.text
