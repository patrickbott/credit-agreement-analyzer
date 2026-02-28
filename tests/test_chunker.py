"""Tests for chunker module."""

from __future__ import annotations

from credit_analyzer.processing.chunker import Chunker, _count_tokens, _estimate_chunk_pages
from credit_analyzer.processing.definitions import DefinitionsIndex
from credit_analyzer.processing.section_detector import DocumentSection, SectionType


def _make_section(
    text: str,
    section_type: SectionType = "negative_covenants",
    tables: list[str] | None = None,
    section_id: str = "7.01",
    article_number: int = 7,
) -> DocumentSection:
    """Build a minimal DocumentSection for testing."""
    return DocumentSection(
        section_id=section_id,
        article_number=article_number,
        section_title="Test Section",
        article_title="TEST ARTICLE",
        text=text,
        page_start=1,
        page_end=1,
        tables=tables if tables is not None else [],
        section_type=section_type,
    )


def _empty_index() -> DefinitionsIndex:
    """An empty definitions index for tests that don't need term detection."""
    return DefinitionsIndex(definitions={})


def _small_index() -> DefinitionsIndex:
    """A small definitions index for testing term detection in chunks."""
    return DefinitionsIndex(
        definitions={
            "Borrower": "the entity",
            "Available Amount": "some amount",
            "EBITDA": "earnings before...",
        }
    )


# --- Token counting ---


def test_count_tokens_basic() -> None:
    """Token counting returns a positive integer for non-empty text."""
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    count = _count_tokens("Hello world", enc)
    assert count > 0
    assert isinstance(count, int)


def test_count_tokens_empty() -> None:
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    assert _count_tokens("", enc) == 0


# --- Single chunk (fits in target) ---


def test_short_section_single_chunk() -> None:
    """A short section produces exactly one text chunk."""
    section = _make_section("The Borrower will not incur any debt.")
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "text"
    assert chunks[0].section_id == "7.01"
    assert chunks[0].token_count > 0


# --- Text splitting ---


def test_long_section_splits() -> None:
    """A section exceeding the target token count is split into multiple chunks."""
    # Build text that's definitely longer than 600 tokens
    paragraphs = [f"Paragraph {i}. " + ("word " * 80) for i in range(10)]
    long_text = "\n\n".join(paragraphs)

    section = _make_section(long_text)
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.chunk_type == "text"
        assert chunk.section_id == "7.01"


def test_split_respects_max_tokens() -> None:
    """No chunk should exceed CHUNK_MAX_TOKENS (except oversized single paragraphs)."""
    paragraphs = [f"Paragraph {i}. " + ("word " * 60) for i in range(15)]
    long_text = "\n\n".join(paragraphs)

    section = _make_section(long_text)
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    from credit_analyzer.config import CHUNK_MAX_TOKENS

    for chunk in chunks:
        # Allow some tolerance since we don't split mid-paragraph
        assert chunk.token_count < CHUNK_MAX_TOKENS * 2


# --- Table chunks ---


def test_tables_become_separate_chunks() -> None:
    """Tables in a section become their own table-type chunks."""
    table_md = "| Col1 | Col2 |\n| --- | --- |\n| A | B |"
    section = _make_section("Some text.", tables=[table_md])
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    table_chunks = [c for c in chunks if c.chunk_type == "table"]
    text_chunks = [c for c in chunks if c.chunk_type == "text"]

    assert len(table_chunks) == 1
    assert len(text_chunks) == 1
    assert "Col1" in table_chunks[0].text


# --- Definition chunks ---


def test_definitions_chunked_per_term() -> None:
    """Each large-enough definition becomes its own chunk."""
    # Make definitions big enough to exceed MIN_DEFINITION_CHUNK_TOKENS
    big_def = "word " * 60  # ~60 tokens
    index = DefinitionsIndex(
        definitions={
            "Term A": f'"Term A" means {big_def}',
            "Term B": f'"Term B" means {big_def}',
        }
    )
    section = _make_section("ignored", section_type="definitions", section_id="ARTICLE_1", article_number=1)
    chunker = Chunker()
    chunks = chunker.chunk_document([section], index)

    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.chunk_type == "definition"
        assert chunk.section_type == "definitions"


def test_small_definitions_grouped() -> None:
    """Small definitions are grouped into fewer chunks."""
    index = DefinitionsIndex(
        definitions={
            "A": '"A" means a.',
            "B": '"B" means b.',
            "C": '"C" means c.',
            "D": '"D" means d.',
        }
    )
    section = _make_section("ignored", section_type="definitions", section_id="ARTICLE_1", article_number=1)
    chunker = Chunker()
    chunks = chunker.chunk_document([section], index)

    # 4 tiny definitions should fit in 1 chunk
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "definition"


# --- Defined terms detection in chunks ---


def test_defined_terms_detected_in_chunks() -> None:
    """Chunks have defined_terms_present populated from the index."""
    section = _make_section("The Borrower shall maintain the Available Amount.")
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _small_index())

    assert len(chunks) == 1
    terms = chunks[0].defined_terms_present
    assert "Borrower" in terms
    assert "Available Amount" in terms
    # EBITDA is not in the text
    assert "EBITDA" not in terms


# --- Metadata ---


def test_chunk_metadata_correct() -> None:
    """Chunk metadata matches the source section."""
    section = _make_section(
        "Some covenant text.",
        section_type="negative_covenants",
        section_id="7.06",
        article_number=7,
    )
    section.section_title = "Restricted Payments"
    section.article_title = "NEGATIVE COVENANTS"

    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.section_id == "7.06"
    assert chunk.section_title == "Restricted Payments"
    assert chunk.article_number == 7
    assert chunk.article_title == "NEGATIVE COVENANTS"
    assert chunk.section_type == "negative_covenants"
    assert chunk.chunk_index == 0
    assert chunk.page_numbers == [1]


def test_chunk_ids_unique() -> None:
    """Every chunk gets a unique ID."""
    paragraphs = [f"Paragraph {i}. " + ("word " * 80) for i in range(10)]
    section = _make_section("\n\n".join(paragraphs))
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_empty_section_no_chunks() -> None:
    """An empty text section with no tables produces no chunks."""
    section = _make_section("")
    chunker = Chunker()
    chunks = chunker.chunk_document([section], _empty_index())

    assert len(chunks) == 0


def test_multiple_sections_chunked() -> None:
    """Multiple sections are all chunked and returned together."""
    sections = [
        _make_section("Text for section one.", section_id="7.01"),
        _make_section("Text for section two.", section_id="7.02"),
    ]
    chunker = Chunker()
    chunks = chunker.chunk_document(sections, _empty_index())

    section_ids = {c.section_id for c in chunks}
    assert section_ids == {"7.01", "7.02"}


# --- Page number estimation ---


def test_estimate_chunk_pages_single_page_section() -> None:
    """Single-page sections always return that page."""
    result = _estimate_chunk_pages("some text", "some text here", 42, 42)
    assert result == [42]


def test_estimate_chunk_pages_start_of_section() -> None:
    """Chunk at the start of a multi-page section maps to early pages."""
    section_text = "A" * 1000 + "B" * 1000 + "C" * 1000
    chunk_text = "A" * 200  # near the start
    result = _estimate_chunk_pages(chunk_text, section_text, 10, 40)
    # Should be pages near the start (10-ish), not pages 30+
    assert result[0] == 10
    assert max(result) < 20


def test_estimate_chunk_pages_end_of_section() -> None:
    """Chunk at the end of a multi-page section maps to late pages."""
    section_text = "A" * 1000 + "B" * 1000 + "C" * 200
    chunk_text = "C" * 200  # near the end
    result = _estimate_chunk_pages(chunk_text, section_text, 10, 40)
    # Should be pages near the end (30+), not pages 10-15
    assert min(result) > 25


def test_estimate_chunk_pages_not_found_returns_full_range() -> None:
    """When chunk text is not found, returns full section page range."""
    result = _estimate_chunk_pages("not in here", "section text", 5, 10)
    assert result == [5, 6, 7, 8, 9, 10]


def test_estimate_chunk_pages_empty_section() -> None:
    """Empty section text returns full range."""
    result = _estimate_chunk_pages("chunk", "", 1, 5)
    assert result == [1, 2, 3, 4, 5]


def test_multi_page_section_narrows_pages() -> None:
    """Chunks from a multi-page section get narrowed page numbers."""
    # Build a section spanning pages 9-56 (like definitions).
    # Use distinct paragraphs so each chunk has a unique prefix
    # that _estimate_chunk_pages can locate.
    paragraphs = [f"Paragraph {i}. " + ("word " * 100) for i in range(50)]
    section = _make_section(
        "\n\n".join(paragraphs),
        section_id="1.1",
        section_type="definitions",
    )
    section.page_start = 9
    section.page_end = 56

    chunker = Chunker()
    chunks = chunker._chunk_section(section, _empty_index())

    # Should produce multiple chunks
    assert len(chunks) > 2
    # Later chunks should not all start at page 9
    last_chunk = chunks[-1]
    assert last_chunk.page_numbers[0] > 9, (
        f"Last chunk starts at page {last_chunk.page_numbers[0]}, "
        f"expected it to be past the beginning"
    )
