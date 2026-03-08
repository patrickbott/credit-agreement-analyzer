# CLAUDE.md

Repository notes for coding agents working in this project.

## Core Commands

```bash
# Run app
streamlit run app.py

# Tests
.venv/Scripts/python -m pytest tests/

# Lint
.venv/Scripts/python -m ruff check .

# Types
.venv/Scripts/python -m pyright
```

## Architecture

### Processing

`pdf_extractor.py -> section_detector.py -> chunker.py -> definitions.py`

- PDF text/table extraction with OCR fallback
- Section detection (includes preamble capture)
- Token-aware chunking and definition chunking
- Definitions index for term lookup/injection

### Retrieval

- `VectorStore` (ChromaDB + embeddings)
- `BM25Store` (rank-bm25)
- `HybridRetriever`:
  - vector + BM25 retrieval
  - RRF fusion
  - optional cross-encoder reranking
  - sibling expansion
  - definition injection/promotion

### Generation

- `QAEngine` for conversational Q&A
- `ReportGenerator` for 10-section report generation
- `response_parser.py` for confidence/citations parsing

### LLM Providers

- `ClaudeProvider`
- `OllamaProvider`
- `InternalLLMProvider`
- Selected via `LLM_PROVIDER` and `get_provider()`

### UI

`app.py` is chat-centric:

- Sidebar handles upload, indexing, model status, and actions
- Definitions and report views are dialog-based (`@st.dialog`)
- Report supports section refresh and PDF export

## Configuration

See:

- [docs/CONFIG_REFERENCE.md](docs/CONFIG_REFERENCE.md)
- [docs/RETRIEVAL_ARCHITECTURE.md](docs/RETRIEVAL_ARCHITECTURE.md)

## Important Behavior

- Report extraction prompt uses strict omission for missing fields (no `"NOT FOUND"` fill-ins except fully empty section fallback).
- Import surfaces are lazy-loaded in package `__init__.py` to avoid heavy dependency failures during unrelated module imports/tests.
