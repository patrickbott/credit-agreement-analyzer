"""UI-facing orchestration helpers for document processing."""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from credit_analyzer.config import PROJECT_ROOT
from credit_analyzer.processing.chunker import Chunk, Chunker, build_search_text
from credit_analyzer.processing.definitions import DefinitionsIndex, DefinitionsParser
from credit_analyzer.processing.pdf_extractor import ExtractedDocument, PDFExtractor
from credit_analyzer.processing.section_detector import DocumentSection, SectionDetector
from credit_analyzer.retrieval.bm25_store import BM25Store
from credit_analyzer.retrieval.embedder import Embedder
from credit_analyzer.retrieval.hybrid_retriever import HybridRetriever
from credit_analyzer.retrieval.vector_store import VectorStore

ProgressCallback = Callable[[str, float], None]

UPLOADS_DIR = PROJECT_ROOT / "demo_uploads"


@dataclass(frozen=True)
class DocumentStats:
    """Top-line stats for a processed document."""

    processed_at: datetime
    total_pages: int
    extraction_method: str
    section_count: int
    definition_count: int
    chunk_count: int
    table_count: int
    section_type_counts: dict[str, int]


@dataclass(frozen=True)
class ProcessedDocument:
    """A fully indexed document ready for Q&A and demo reporting."""

    document_id: str
    display_name: str
    source_path: Path
    extracted_document: ExtractedDocument
    sections: list[DocumentSection]
    definitions_index: DefinitionsIndex
    chunks: list[Chunk]
    retriever: HybridRetriever
    preamble_text: str | None
    stats: DocumentStats


def ensure_uploads_dir() -> Path:
    """Create the demo upload directory if needed."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def save_uploaded_pdf(file_name: str, file_bytes: bytes) -> Path:
    """Persist an uploaded PDF for processing."""
    safe_name = _sanitize_filename(file_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = ensure_uploads_dir() / f"{timestamp}-{safe_name}"
    output_path.write_bytes(file_bytes)
    return output_path


def build_processed_document(
    pdf_path: Path,
    *,
    embedder: Embedder,
    vector_store: VectorStore,
    progress_callback: ProgressCallback | None = None,
) -> ProcessedDocument:
    """Process a PDF into retrieval-ready state for the UI."""
    _progress(progress_callback, "Extracting text from PDF...", 0.12)
    extracted_document = PDFExtractor().extract(pdf_path)

    _progress(progress_callback, "Detecting document structure...", 0.28)
    sections = SectionDetector().detect_sections(extracted_document)

    _progress(progress_callback, "Parsing defined terms...", 0.42)
    definitions_section = next(
        (section for section in sections if section.section_type == "definitions"),
        None,
    )
    definitions_index = (
        DefinitionsParser().parse(definitions_section)
        if definitions_section is not None
        else DefinitionsIndex(definitions={})
    )

    _progress(progress_callback, "Chunking agreement text...", 0.58)
    chunks = Chunker().chunk_document(sections, definitions_index)

    _progress(progress_callback, "Building embeddings...", 0.76)
    embeddings = embedder.embed([build_search_text(chunk) for chunk in chunks])

    _progress(progress_callback, "Creating hybrid search index...", 0.9)
    # Each run creates a new timestamped collection. Old collections persist in
    # chroma_data/ until manually pruned; this is acceptable for demo use but
    # should be replaced with a reuse/cleanup strategy in production.
    document_id = _build_document_id(pdf_path)
    try:
        vector_store.delete_collection(document_id)
    except ValueError:
        # Collection does not yet exist — nothing to delete.
        pass
    except Exception:
        logger.warning("Could not delete existing collection %r; proceeding with create.", document_id)
    vector_store.create_collection(document_id)
    vector_store.add_chunks(document_id, chunks, embeddings)

    bm25_store = BM25Store()
    bm25_store.build_index(chunks)
    retriever = HybridRetriever(vector_store, bm25_store, embedder, definitions_index)

    preamble = next(
        (
            section.text.strip()
            for section in sections
            if section.section_type == "preamble" and section.text.strip()
        ),
        None,
    )

    stats = DocumentStats(
        processed_at=datetime.now(),
        total_pages=extracted_document.total_pages,
        extraction_method=extracted_document.extraction_method,
        section_count=len(sections),
        definition_count=len(definitions_index.definitions),
        chunk_count=len(chunks),
        table_count=sum(len(section.tables) for section in sections),
        section_type_counts=dict(
            sorted(Counter(section.section_type for section in sections).items())
        ),
    )

    _progress(progress_callback, "Ready for review.", 1.0)

    return ProcessedDocument(
        document_id=document_id,
        display_name=pdf_path.name,
        source_path=pdf_path,
        extracted_document=extracted_document,
        sections=sections,
        definitions_index=definitions_index,
        chunks=chunks,
        retriever=retriever,
        preamble_text=preamble,
        stats=stats,
    )


def _build_document_id(pdf_path: Path) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower()).strip("-")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{stem or 'agreement'}-{timestamp}"


def _sanitize_filename(file_name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(file_name).name).strip("-")
    return safe or "agreement.pdf"


def _progress(
    callback: ProgressCallback | None,
    label: str,
    progress: float,
) -> None:
    """Fire the progress callback if one was provided."""
    if callback is not None:
        callback(label, progress)
