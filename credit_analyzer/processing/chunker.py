"""Section-aware chunking for credit agreement text."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import tiktoken

from credit_analyzer.config import (
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TARGET_TOKENS,
    MIN_DEFINITION_CHUNK_TOKENS,
    TIKTOKEN_ENCODING,
)
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.processing.section_detector import DocumentSection


def _normalize_for_search(text: str) -> str:
    """Normalize text for substring matching.

    Collapses whitespace and replaces Unicode smart quotes with ASCII
    equivalents so that chunk text can be reliably located within the
    parent section text even when PDF extraction introduces
    inconsistencies.

    Args:
        text: Raw text to normalize.

    Returns:
        Normalized text suitable for ``str.find()`` matching.
    """
    out = text.replace("\u201c", '"').replace("\u201d", '"')
    out = out.replace("\u2018", "'").replace("\u2019", "'")
    out = re.sub(r"\s+", " ", out)
    return out


def _estimate_chunk_pages(
    chunk_text: str,
    section_text: str,
    page_start: int,
    page_end: int,
) -> list[int]:
    """Estimate which pages a chunk spans based on its position in the section.

    Uses the chunk's character offset within the section text to interpolate
    which pages it covers.  Falls back to the full section range when the
    section fits on a single page or the chunk text is not found.

    Both texts are normalized (smart quotes collapsed, whitespace
    unified) before matching to handle PDF extraction inconsistencies.

    Args:
        chunk_text: The text of the chunk.
        section_text: The full text of the parent section.
        page_start: 1-indexed start page of the section.
        page_end: 1-indexed end page of the section.

    Returns:
        Sorted list of estimated page numbers for this chunk.
    """
    total_pages = page_end - page_start + 1
    if total_pages <= 1 or not section_text:
        return list(range(page_start, page_end + 1))

    norm_section = _normalize_for_search(section_text)
    norm_prefix = _normalize_for_search(chunk_text[:200])
    idx = norm_section.find(norm_prefix)
    if idx < 0:
        return list(range(page_start, page_end + 1))

    section_len = len(norm_section)
    # Estimate chunk length in normalized space proportionally
    chunk_len_est = int(len(chunk_text) * len(norm_section) / max(len(section_text), 1))
    chunk_start_frac = idx / section_len
    chunk_end_frac = min((idx + chunk_len_est) / section_len, 1.0)

    est_page_start = page_start + int(chunk_start_frac * total_pages)
    est_page_end = page_start + int(chunk_end_frac * total_pages)

    # Clamp to section bounds
    est_page_start = max(est_page_start, page_start)
    est_page_end = min(est_page_end, page_end)

    return list(range(est_page_start, est_page_end + 1))


@dataclass
class Chunk:
    """A retrieval-ready chunk of credit agreement text with metadata."""

    chunk_id: str
    text: str
    section_id: str
    section_title: str
    article_number: int
    article_title: str
    section_type: str
    chunk_type: str  # "text" | "table" | "definition"
    page_numbers: list[int]
    defined_terms_present: list[str]
    chunk_index: int  # position within the section
    token_count: int


def build_search_text(chunk: Chunk) -> str:
    """Build context-enriched text for embedding and keyword indexing.

    Prepends structural context (article, section, type) to the raw chunk
    text so that embedding models and BM25 can disambiguate structurally
    similar clauses. For example, a debt basket in Section 7.03 gets tagged
    with its article context ("Negative Covenants") and section type
    ("negative_covenants"), helping distinguish it from similar language
    in definitions or facility terms.

    Args:
        chunk: The chunk to enrich.

    Returns:
        Text suitable for embedding or BM25 indexing.
    """
    parts: list[str] = []
    # Article context helps group related sections
    if chunk.article_title:
        parts.append(f"[Article {chunk.article_number}: {chunk.article_title}]")
    parts.append(f"[Section {chunk.section_id}: {chunk.section_title}]")
    # Section type tag aids BM25 keyword matching on filtered queries
    if chunk.section_type:
        type_label = chunk.section_type.replace("_", " ")
        parts.append(f"[Type: {type_label}]")
    parts.append(chunk.text)
    return "\n".join(parts)


# Paragraph split patterns, tried in order of preference.
# Primary: double newline or subsection markers like (a), (b)
_PARAGRAPH_SPLIT_DOUBLE = re.compile(r"\n\s*\n|\n\s*(?=\([a-z]\)|\([ivx]+\))")
# Fallback: single newline (some PDFs have no double newlines)
_PARAGRAPH_SPLIT_SINGLE = re.compile(r"\n")


def _count_tokens(text: str, encoding: tiktoken.Encoding, _cache: dict[str, int] = {}) -> int:  # noqa: B006
    """Count tokens in text using the given tiktoken encoding.

    Results are cached in a mutable default dict so that repeated calls on
    overlapping text (common during paragraph splitting with overlap) avoid
    redundant tokenization.

    Args:
        text: The text to tokenize.
        encoding: The tiktoken encoding instance.

    Returns:
        Number of tokens.
    """
    cached = _cache.get(text)
    if cached is not None:
        return cached
    count = len(encoding.encode(text))
    _cache[text] = count
    return count


def _generate_chunk_id() -> str:
    """Generate a unique chunk ID.

    Returns:
        A short UUID-based string.
    """
    return uuid.uuid4().hex[:12]


class Chunker:
    """Converts document sections into retrieval-ready chunks.

    Handles definitions, tables, and regular text differently:
    - Each defined term becomes its own chunk (small ones are grouped).
    - Each table becomes its own chunk with surrounding context.
    - Regular text is split at paragraph boundaries with overlap.
    """

    def __init__(self) -> None:
        self._encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)

    def chunk_document(
        self,
        sections: list[DocumentSection],
        definitions_index: DefinitionsIndex,
    ) -> list[Chunk]:
        """Chunk all sections of a document.

        Args:
            sections: The detected document sections.
            definitions_index: The parsed definitions for term detection.

        Returns:
            List of Chunk objects ready for embedding and retrieval.
        """
        all_chunks: list[Chunk] = []

        definitions_chunked = False

        for section in sections:
            if section.section_type == "definitions" and not definitions_chunked:
                # Only chunk the first definitions section (e.g. 1.1 "Defined Terms")
                # as definition entries.  Remaining Article I sub-sections
                # (Rounding, Currency, etc.) are interpretive provisions and
                # should be chunked as regular text.
                chunks = self._chunk_definitions(section, definitions_index)
                definitions_chunked = True
            else:
                chunks = self._chunk_section(section, definitions_index)
            all_chunks.extend(chunks)

        return all_chunks

    def _chunk_definitions(
        self,
        section: DocumentSection,
        definitions_index: DefinitionsIndex,
    ) -> list[Chunk]:
        """Chunk a definitions section: one chunk per term, small ones grouped.

        Args:
            section: The definitions section.
            definitions_index: Parsed definitions.

        Returns:
            List of definition chunks.
        """
        chunks: list[Chunk] = []
        chunk_index = 0

        # Group small definitions together
        small_buffer: list[str] = []
        small_terms: list[str] = []
        small_tokens = 0

        for term, entry in definitions_index.definitions.items():
            definition = entry.text
            token_count = _count_tokens(definition, self._encoding)

            if token_count >= MIN_DEFINITION_CHUNK_TOKENS:
                # Flush any accumulated small definitions first
                if small_buffer:
                    chunks.append(
                        self._make_definition_chunk(
                            section,
                            "\n\n".join(small_buffer),
                            small_terms,
                            chunk_index,
                        )
                    )
                    chunk_index += 1
                    small_buffer = []
                    small_terms = []
                    small_tokens = 0

                # This definition is big enough for its own chunk
                chunks.append(
                    self._make_definition_chunk(
                        section, definition, [term], chunk_index
                    )
                )
                chunk_index += 1
            else:
                # Accumulate small definitions
                # Flush if adding this one would exceed target
                if small_tokens + token_count > CHUNK_TARGET_TOKENS and small_buffer:
                    chunks.append(
                        self._make_definition_chunk(
                            section,
                            "\n\n".join(small_buffer),
                            small_terms,
                            chunk_index,
                        )
                    )
                    chunk_index += 1
                    small_buffer = []
                    small_terms = []
                    small_tokens = 0

                small_buffer.append(definition)
                small_terms.append(term)
                small_tokens += token_count

        # Flush remaining small definitions
        if small_buffer:
            chunks.append(
                self._make_definition_chunk(
                    section,
                    "\n\n".join(small_buffer),
                    small_terms,
                    chunk_index,
                )
            )

        return chunks

    def _make_definition_chunk(
        self,
        section: DocumentSection,
        text: str,
        terms: list[str],
        chunk_index: int,
    ) -> Chunk:
        """Build a Chunk for one or more definitions.

        Args:
            section: The parent definitions section.
            text: The chunk text content.
            terms: Defined terms included in this chunk.
            chunk_index: Position index within the section.

        Returns:
            A definition-type Chunk.
        """
        pages = _estimate_chunk_pages(
            text, section.text, section.page_start, section.page_end,
        )
        return Chunk(
            chunk_id=_generate_chunk_id(),
            text=text,
            section_id=section.section_id,
            section_title=section.section_title,
            article_number=section.article_number,
            article_title=section.article_title,
            section_type=section.section_type,
            chunk_type="definition",
            page_numbers=pages,
            defined_terms_present=terms,
            chunk_index=chunk_index,
            token_count=_count_tokens(text, self._encoding),
        )

    def _chunk_section(
        self,
        section: DocumentSection,
        definitions_index: DefinitionsIndex,
    ) -> list[Chunk]:
        """Chunk a non-definitions section: tables split out, text split at paragraphs.

        Args:
            section: The document section.
            definitions_index: For detecting defined terms in chunks.

        Returns:
            List of chunks for this section.
        """
        chunks: list[Chunk] = []
        chunk_index = 0

        section_text = section.text.strip()

        # Handle tables as separate chunks
        for table_md in section.tables:
            terms = definitions_index.find_terms_in_text(table_md)
            pages = _estimate_chunk_pages(
                table_md, section_text, section.page_start, section.page_end,
            )
            chunks.append(
                Chunk(
                    chunk_id=_generate_chunk_id(),
                    text=table_md,
                    section_id=section.section_id,
                    section_title=section.section_title,
                    article_number=section.article_number,
                    article_title=section.article_title,
                    section_type=section.section_type,
                    chunk_type="table",
                    page_numbers=pages,
                    defined_terms_present=terms,
                    chunk_index=chunk_index,
                    token_count=_count_tokens(table_md, self._encoding),
                )
            )
            chunk_index += 1

        # Chunk the main text
        if not section_text:
            return chunks

        text_tokens = _count_tokens(section_text, self._encoding)

        if text_tokens <= CHUNK_TARGET_TOKENS:
            # Fits in one chunk — use full section page range
            terms = definitions_index.find_terms_in_text(section_text)
            chunks.append(
                Chunk(
                    chunk_id=_generate_chunk_id(),
                    text=section_text,
                    section_id=section.section_id,
                    section_title=section.section_title,
                    article_number=section.article_number,
                    article_title=section.article_title,
                    section_type=section.section_type,
                    chunk_type="text",
                    page_numbers=list(
                        range(section.page_start, section.page_end + 1)
                    ),
                    defined_terms_present=terms,
                    chunk_index=chunk_index,
                    token_count=text_tokens,
                )
            )
        else:
            # Split at paragraph boundaries
            text_chunks = self._split_text(section_text)
            for split_text in text_chunks:
                terms = definitions_index.find_terms_in_text(split_text)
                pages = _estimate_chunk_pages(
                    split_text, section_text,
                    section.page_start, section.page_end,
                )
                chunks.append(
                    Chunk(
                        chunk_id=_generate_chunk_id(),
                        text=split_text,
                        section_id=section.section_id,
                        section_title=section.section_title,
                        article_number=section.article_number,
                        article_title=section.article_title,
                        section_type=section.section_type,
                        chunk_type="text",
                        page_numbers=pages,
                        defined_terms_present=terms,
                        chunk_index=chunk_index,
                        token_count=_count_tokens(split_text, self._encoding),
                    )
                )
                chunk_index += 1

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text at paragraph boundaries with overlap.

        Splits at double newlines or subsection markers, then merges
        paragraphs into chunks that stay under the target token limit.
        Applies overlap from the end of the previous chunk.

        Args:
            text: The text to split.

        Returns:
            List of chunk text strings.
        """
        # Try splitting on double newlines first; if that produces only 1 part,
        # fall back to single newlines (common in PDFs with no blank lines).
        parts = [p.strip() for p in _PARAGRAPH_SPLIT_DOUBLE.split(text) if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in _PARAGRAPH_SPLIT_SINGLE.split(text) if p.strip()]
        paragraphs = parts

        if not paragraphs:
            return [text] if text.strip() else []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = _count_tokens(para, self._encoding)

            # If a single paragraph exceeds max, split at clause/sentence boundaries
            if para_tokens > CHUNK_MAX_TOKENS and not current_parts:
                sub_chunks = self._split_oversized_paragraph(para)
                chunks.extend(sub_chunks)
                continue

            if current_tokens + para_tokens > CHUNK_TARGET_TOKENS and current_parts:
                # Flush current chunk
                chunk_text = "\n\n".join(current_parts)
                chunks.append(chunk_text)

                # Build overlap: take paragraphs from the end of the current chunk.
                # If the last paragraph exceeds the overlap budget, take its
                # trailing sentences to ensure nonzero overlap.
                overlap_parts: list[str] = []
                overlap_tokens = 0
                for prev_para in reversed(current_parts):
                    prev_tokens = _count_tokens(prev_para, self._encoding)
                    if overlap_tokens + prev_tokens > CHUNK_OVERLAP_TOKENS:
                        # If we have nothing yet, take trailing sentences from this paragraph
                        if not overlap_parts:
                            sentences = re.split(r"(?<=\.)\s+", prev_para)
                            tail: list[str] = []
                            tail_tokens = 0
                            for sent in reversed(sentences):
                                sent_tokens = _count_tokens(sent, self._encoding)
                                if tail_tokens + sent_tokens > CHUNK_OVERLAP_TOKENS:
                                    break
                                tail.insert(0, sent)
                                tail_tokens += sent_tokens
                            if tail:
                                overlap_parts = [" ".join(tail)]
                                overlap_tokens = tail_tokens
                        break
                    overlap_parts.insert(0, prev_para)
                    overlap_tokens += prev_tokens

                current_parts = overlap_parts + [para]
                current_tokens = overlap_tokens + para_tokens
            else:
                current_parts.append(para)
                current_tokens += para_tokens

        # Flush remaining
        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks

    def _split_oversized_paragraph(self, para: str) -> list[str]:
        """Split an oversized paragraph at clause or sentence boundaries.

        Tries clause markers like (a), (b), (i), (ii) first, then
        semicolons, then sentence-ending periods. Falls back to the
        full paragraph if no split points are found.
        """
        # Try splitting at legal clause markers: (a), (b), (i), (ii), etc.
        clause_parts = re.split(r"(?=\([a-z]\)|\([ivx]+\))", para)
        if len(clause_parts) > 1:
            return self._merge_splits_to_target(clause_parts)

        # Try splitting at semicolons (common in legal enumeration)
        semi_parts = para.split(";")
        if len(semi_parts) > 1:
            # Re-attach the semicolons
            semi_parts = [p.strip() + ";" for p in semi_parts[:-1]] + [semi_parts[-1].strip()]
            return self._merge_splits_to_target(semi_parts)

        # Try splitting at sentence boundaries
        sentence_parts = re.split(r"(?<=\.)\s+(?=[A-Z])", para)
        if len(sentence_parts) > 1:
            return self._merge_splits_to_target(sentence_parts)

        # No good split point found — return as-is
        return [para]

    def _merge_splits_to_target(self, parts: list[str]) -> list[str]:
        """Merge small split parts back together to approach CHUNK_TARGET_TOKENS."""
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_tokens = _count_tokens(part, self._encoding)
            if current_tokens + part_tokens > CHUNK_TARGET_TOKENS and current:
                chunks.append("\n".join(current))
                current = [part]
                current_tokens = part_tokens
            else:
                current.append(part)
                current_tokens += part_tokens

        if current:
            chunks.append("\n".join(current))
        return chunks if chunks else parts
