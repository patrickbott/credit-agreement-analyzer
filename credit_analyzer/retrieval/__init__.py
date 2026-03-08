# pyright: reportUnsupportedDunderAll=false
"""Retrieval layer: embedding, vector search, BM25, and hybrid retrieval."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "BM25Result",
    "BM25Store",
    "Embedder",
    "HybridChunk",
    "HybridRetriever",
    "RetrievalResult",
    "RetrievedChunk",
    "VectorStore",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BM25Result": ("credit_analyzer.retrieval.bm25_store", "BM25Result"),
    "BM25Store": ("credit_analyzer.retrieval.bm25_store", "BM25Store"),
    "Embedder": ("credit_analyzer.retrieval.embedder", "Embedder"),
    "HybridChunk": ("credit_analyzer.retrieval.hybrid_retriever", "HybridChunk"),
    "HybridRetriever": ("credit_analyzer.retrieval.hybrid_retriever", "HybridRetriever"),
    "RetrievalResult": ("credit_analyzer.retrieval.hybrid_retriever", "RetrievalResult"),
    "RetrievedChunk": ("credit_analyzer.retrieval.vector_store", "RetrievedChunk"),
    "VectorStore": ("credit_analyzer.retrieval.vector_store", "VectorStore"),
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
