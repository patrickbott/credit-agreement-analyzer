"""Stub provider for a future internal / enterprise LLM endpoint."""

from __future__ import annotations

from credit_analyzer.llm.base import LLMProvider, LLMResponse


class InternalLLMProvider(LLMProvider):
    """Placeholder for an internal enterprise LLM integration.

    Implement :meth:`complete` to call your internal API when ready.
    """

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Not yet implemented."""
        raise NotImplementedError(
            "Internal LLM provider is not configured. "
            "Set LLM_PROVIDER = 'ollama' in config.py or implement this provider."
        )

    def is_available(self) -> bool:
        """Always returns ``False`` until implemented."""
        return False

    def model_name(self) -> str:
        """Return a placeholder name."""
        return "internal (not configured)"
