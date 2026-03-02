"""ChromaDB vector store wrapper for credit agreement chunks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import chromadb  # pyright: ignore[reportMissingTypeStubs]

from credit_analyzer.config import CHROMA_DATA_DIR, EMBEDDING_MODEL
from credit_analyzer.processing.chunker import Chunk


@dataclass
class RetrievedChunk:
    """A chunk returned from a vector similarity search.

    Attributes:
        chunk: The original Chunk object, reconstructed from stored metadata.
        score: The similarity score (lower distance = more similar).
    """

    chunk: Chunk
    score: float


# Keys stored in ChromaDB metadata.  ChromaDB only supports primitive
# types (str | int | float | bool) so list fields are serialized as strings.
_META_SECTION_ID = "section_id"
_META_SECTION_TITLE = "section_title"
_META_ARTICLE_NUMBER = "article_number"
_META_ARTICLE_TITLE = "article_title"
_META_SECTION_TYPE = "section_type"
_META_CHUNK_TYPE = "chunk_type"
_META_CHUNK_INDEX = "chunk_index"
_META_TOKEN_COUNT = "token_count"
_META_PAGE_NUMBERS = "page_numbers"  # pipe-separated ints, e.g. "45|46"
_META_DEFINED_TERMS = "defined_terms"  # pipe-separated strings, e.g. "Available Amount|Borrower"

# Pipe is used as a list delimiter because defined term names never contain it,
# whereas commas can appear in parenthetical definitions ("means X, Y, or Z").
_LIST_SEPARATOR = "|"
_META_EMBEDDING_MODEL = "embedding_model"


def chunk_to_metadata(chunk: Chunk) -> dict[str, str | int | float | bool]:
    """Convert a Chunk's metadata fields to a ChromaDB-compatible dict."""
    return {
        _META_SECTION_ID: chunk.section_id,
        _META_SECTION_TITLE: chunk.section_title,
        _META_ARTICLE_NUMBER: chunk.article_number,
        _META_ARTICLE_TITLE: chunk.article_title,
        _META_SECTION_TYPE: chunk.section_type,
        _META_CHUNK_TYPE: chunk.chunk_type,
        _META_CHUNK_INDEX: chunk.chunk_index,
        _META_TOKEN_COUNT: chunk.token_count,
        _META_PAGE_NUMBERS: _LIST_SEPARATOR.join(str(p) for p in chunk.page_numbers),
        _META_DEFINED_TERMS: _LIST_SEPARATOR.join(chunk.defined_terms_present),
    }


def metadata_to_chunk(
    chunk_id: str,
    text: str,
    meta: Mapping[str, str | int | float | bool],
) -> Chunk:
    """Reconstruct a Chunk from ChromaDB metadata and document text."""
    page_str = str(meta.get(_META_PAGE_NUMBERS, ""))
    page_numbers = [int(p) for p in page_str.split(_LIST_SEPARATOR) if p.strip()]

    terms_str = str(meta.get(_META_DEFINED_TERMS, ""))
    defined_terms = [t for t in terms_str.split(_LIST_SEPARATOR) if t.strip()]

    return Chunk(
        chunk_id=chunk_id,
        text=text,
        section_id=str(meta.get(_META_SECTION_ID, "")),
        section_title=str(meta.get(_META_SECTION_TITLE, "")),
        article_number=int(meta.get(_META_ARTICLE_NUMBER, 0)),
        article_title=str(meta.get(_META_ARTICLE_TITLE, "")),
        section_type=str(meta.get(_META_SECTION_TYPE, "")),
        chunk_type=str(meta.get(_META_CHUNK_TYPE, "")),
        page_numbers=page_numbers,
        defined_terms_present=defined_terms,
        chunk_index=int(meta.get(_META_CHUNK_INDEX, 0)),
        token_count=int(meta.get(_META_TOKEN_COUNT, 0)),
    )


class VectorStore:
    """ChromaDB-backed vector store for credit agreement chunks.

    Each processed document gets its own ChromaDB collection.
    Supports filtered search by section type and other metadata.
    """

    def __init__(self, persist_directory: str | None = None) -> None:
        path = persist_directory if persist_directory is not None else str(CHROMA_DATA_DIR)
        self._client: Any = chromadb.PersistentClient(  # pyright: ignore[reportUnknownMemberType]
            path=path,
        )

    def create_collection(self, document_id: str, embedding_model: str = EMBEDDING_MODEL) -> None:
        """Create or replace a collection for a document.

        Stores the embedding model name in collection metadata so that
        mismatched embeddings can be detected at search time.

        Args:
            document_id: Unique identifier for the document.
            embedding_model: The embedding model used for this collection.
        """
        self._client.get_or_create_collection(  # pyright: ignore[reportUnknownMemberType]
            name=document_id,
            metadata={"hnsw:space": "cosine", _META_EMBEDDING_MODEL: embedding_model},
        )

    def add_chunks(
        self,
        document_id: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Add chunks with pre-computed embeddings to a collection.

        Args:
            document_id: The collection to add to.
            chunks: The chunks to store.
            embeddings: Corresponding embedding vectors (same length as chunks).

        Raises:
            ValueError: If chunks and embeddings have different lengths.
        """
        if len(chunks) != len(embeddings):
            msg = f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have the same length"
            raise ValueError(msg)

        if not chunks:
            return

        collection: Any = self._client.get_collection(  # pyright: ignore[reportUnknownMemberType]
            name=document_id,
        )

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [chunk_to_metadata(c) for c in chunks]
        embedding_lists = [list(e) for e in embeddings]

        collection.add(  # pyright: ignore[reportUnknownMemberType]
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embedding_lists,
        )

    def search(
        self,
        document_id: str,
        query_embedding: Sequence[float],
        top_k: int = 5,
        section_filter: str | None = None,
        section_types_exclude: Sequence[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Search for similar chunks by embedding.

        Args:
            document_id: The collection to search.
            query_embedding: The query embedding vector.
            top_k: Maximum number of results to return.
            section_filter: If provided, only search chunks with this section_type.
                Takes precedence over section_types_exclude.
            section_types_exclude: If provided and section_filter is None,
                exclude chunks whose section_type is in this list.

        Returns:
            List of RetrievedChunk objects sorted by similarity (best first).
        """
        collection: Any = self._client.get_collection(  # pyright: ignore[reportUnknownMemberType]
            name=document_id,
        )

        # Check for embedding model mismatch
        col_meta: dict[str, Any] = collection.metadata or {}  # pyright: ignore[reportUnknownMemberType]
        stored_model = col_meta.get(_META_EMBEDDING_MODEL)
        if stored_model and stored_model != EMBEDDING_MODEL:
            raise ValueError(
                f"Collection '{document_id}' was indexed with embedding model "
                f"'{stored_model}', but the current model is '{EMBEDDING_MODEL}'. "
                f"Please re-index the document to use the new embedding model."
            )

        where: dict[str, Any] | None = None
        if section_filter is not None:
            where = {_META_SECTION_TYPE: section_filter}
        elif section_types_exclude:
            where = {_META_SECTION_TYPE: {"$nin": list(section_types_exclude)}}

        raw_result: Any = collection.query(  # pyright: ignore[reportUnknownMemberType]
            query_embeddings=[list(query_embedding)],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB returns nested lists: ids[0], documents[0], etc.
        ids_list = cast(list[list[str]], raw_result["ids"])
        docs_list = cast(list[list[str]], raw_result["documents"])
        metas_list = cast(
            list[list[Mapping[str, str | int | float | bool]]],
            raw_result["metadatas"],
        )
        distances_list = cast(list[list[float]], raw_result["distances"])

        if not ids_list or not ids_list[0]:
            return []

        results: list[RetrievedChunk] = []
        for chunk_id, doc_text, meta, distance in zip(
            ids_list[0],
            docs_list[0],
            metas_list[0],
            distances_list[0],
            strict=True,
        ):
            # ChromaDB cosine distance is in [0, 2]. Convert to similarity in [0, 1].
            similarity = 1.0 - (distance / 2.0)
            chunk = metadata_to_chunk(chunk_id, doc_text, meta)
            results.append(RetrievedChunk(chunk=chunk, score=similarity))

        return results

    def delete_collection(self, document_id: str) -> None:
        """Delete a document's collection.

        Args:
            document_id: The collection to delete.
        """
        self._client.delete_collection(  # pyright: ignore[reportUnknownMemberType]
            name=document_id,
        )

    def list_documents(self) -> list[str]:
        """List all document IDs (collection names) in the store.

        Returns:
            List of document ID strings.
        """
        collections: Any = self._client.list_collections()  # pyright: ignore[reportUnknownMemberType]
        return [cast(str, getattr(c, "name", str(c))) for c in cast(Sequence[Any], collections)]
