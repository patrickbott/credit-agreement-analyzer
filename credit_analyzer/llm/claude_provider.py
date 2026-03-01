"""Anthropic Claude API-backed LLM provider."""

from __future__ import annotations

import logging
import time
from typing import Any, cast

import anthropic  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """LLM provider that delegates to the Anthropic Messages API.

    Requires the ``anthropic`` package (``pip install anthropic``).
    The API key is read from the ``ANTHROPIC_API_KEY`` environment
    variable by default, or can be passed explicitly.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        # max_retries=3 handles transient rate-limits and network blips automatically.
        # The SDK applies exponential backoff between attempts.
        self._client: Any = anthropic.Anthropic(api_key=api_key, max_retries=3)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a completion request to the Anthropic Messages API."""
        start = time.perf_counter()

        response: Any = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        duration = time.perf_counter() - start

        text_blocks: list[Any] = [
            b for b in cast(list[Any], response.content) if getattr(b, "type", None) == "text"
        ]

        if not text_blocks:
            # The API returned no text blocks, which should not happen under normal
            # operation but can occur if the response was filtered or truncated.
            logger.warning(
                "Claude returned no text blocks for model=%s stop_reason=%s",
                self._model,
                getattr(response, "stop_reason", "unknown"),
            )
            text = ""
        else:
            if len(text_blocks) > 1:
                logger.debug("Claude returned %d text blocks; using the first.", len(text_blocks))
            text = cast(str, text_blocks[0].text)

        usage: Any = response.usage
        tokens_used = cast(int, getattr(usage, "output_tokens", 0))

        return LLMResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model,
            duration_seconds=duration,
        )

    def is_available(self) -> bool:
        """Check whether the Anthropic API is reachable with the configured key."""
        try:
            self._client.models.list(limit=1)
            return True
        except Exception:
            logger.debug("Anthropic API not reachable", exc_info=True)
            return False

    def model_name(self) -> str:
        """Return the Claude model identifier."""
        return self._model
