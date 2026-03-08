# pyright: reportUnsupportedDunderAll=false
"""LLM provider abstraction layer."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ClaudeProvider",
    "LLMProvider",
    "LLMResponse",
    "OllamaProvider",
    "InternalLLMProvider",
    "ProviderName",
    "get_provider",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "ClaudeProvider": ("credit_analyzer.llm.claude_provider", "ClaudeProvider"),
    "LLMProvider": ("credit_analyzer.llm.base", "LLMProvider"),
    "LLMResponse": ("credit_analyzer.llm.base", "LLMResponse"),
    "OllamaProvider": ("credit_analyzer.llm.ollama_provider", "OllamaProvider"),
    "InternalLLMProvider": ("credit_analyzer.llm.internal_provider", "InternalLLMProvider"),
    "ProviderName": ("credit_analyzer.llm.factory", "ProviderName"),
    "get_provider": ("credit_analyzer.llm.factory", "get_provider"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals().keys(), *__all__])
