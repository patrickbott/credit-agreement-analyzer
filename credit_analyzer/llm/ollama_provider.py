"""Ollama-backed LLM provider."""

from __future__ import annotations

import logging
from typing import Any, cast

import ollama

from credit_analyzer.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """LLM provider that delegates to a local Ollama instance."""

    def __init__(self, model: str, base_url: str) -> None:
        self._model = model
        self._base_url = base_url
        self._client = ollama.Client(host=base_url)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a chat completion to Ollama and return the parsed response."""
        response: Any = self._client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature, "num_predict": max_tokens},
        )

        text = cast(str, response["message"]["content"])
        tokens_used = cast(int, response.get("eval_count", 0))
        # total_duration is in nanoseconds
        total_duration_ns = cast(int, response.get("total_duration", 0))
        duration_seconds = total_duration_ns / 1_000_000_000

        return LLMResponse(
            text=text,
            tokens_used=tokens_used,
            model=self._model,
            duration_seconds=duration_seconds,
        )

    def is_available(self) -> bool:
        """Check whether the Ollama server is reachable and the model is loaded."""
        try:
            models_response: Any = self._client.list()
            model_names: list[str] = [
                cast(str, m.get("name", "") if isinstance(m, dict) else getattr(m, "model", ""))
                for m in cast(list[Any], models_response.get("models", []))
            ]
            # Ollama tags may include `:latest`; match on prefix
            base_model = self._model.split(":")[0]
            return any(name.startswith(base_model) for name in model_names)
        except Exception:
            logger.debug("Ollama not reachable at %s", self._base_url, exc_info=True)
            return False

    def model_name(self) -> str:
        """Return the Ollama model identifier."""
        return self._model
