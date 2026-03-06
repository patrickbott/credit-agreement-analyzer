# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
streamlit run app.py

# Run all tests
.venv/Scripts/python -m pytest tests/

# Run a single test file
.venv/Scripts/python -m pytest tests/test_chunker.py

# Run a single test by name
.venv/Scripts/python -m pytest tests/test_chunker.py::test_function_name

# Lint
.venv/Scripts/python -m ruff check .

# Type check
.venv/Scripts/python -m pyright
```

Install with:
```bash
pip install -r requirements.txt
# or for editable install (required for imports to resolve):
pip install -e ".[dev]"
```

## Architecture

The pipeline flows in one direction through three stages:

**Ingestion** (`credit_analyzer/processing/`): `pdf_extractor.py` → `section_detector.py` → `chunker.py` → `definitions.py`. A credit agreement PDF is parsed (PyMuPDF + pdfplumber, with Tesseract OCR fallback), split into typed `DocumentSection` objects, then chunked into `Chunk` objects. The definitions section is parsed separately into a `DefinitionsIndex` for downstream injection.

**Indexing** (`credit_analyzer/retrieval/`): Chunks are stored in two indices: `VectorStore` (ChromaDB with BAAI/bge-small-en-v1.5 embeddings) and `BM25Store` (rank-bm25). Both are keyed by `document_id`. Changing `EMBEDDING_MODEL` requires re-indexing (ChromaDB dimensionality check enforced in `vector_store.py`).

**Query** (`credit_analyzer/retrieval/hybrid_retriever.py` + `credit_analyzer/generation/`): `HybridRetriever.retrieve()` runs vector + BM25 search, fuses via RRF, reranks with a cross-encoder, then applies sibling expansion and definition injection. `QAEngine` wraps this for conversational Q&A with history-aware query reformulation. `ReportGenerator` runs multi-query retrieval per section (parallelized via `ThreadPoolExecutor`) and calls the LLM for each of the 10 report sections.

**LLM** (`credit_analyzer/llm/`): `LLMProvider` ABC with three implementations: `ClaudeProvider`, `OllamaProvider`, `InternalLLMProvider`. Selected via `LLM_PROVIDER` env var. `get_provider()` factory in `factory.py`.

**UI** (`app.py`): Single Streamlit file with three tabs: Documents (upload + indexing), Ask Questions (Q&A with citations), Full Report (report generation + PDF export). All pipeline objects are constructed and cached in Streamlit session state.

## Key Files

| File | Purpose |
|------|---------|
| `credit_analyzer/config.py` | All tunable parameters, loaded from `.env` |
| `credit_analyzer/generation/report_template.py` | 10 report section templates with retrieval queries and extraction prompts |
| `credit_analyzer/generation/prompts.py` | System and user prompt builders for Q&A and reformulation |
| `credit_analyzer/generation/response_parser.py` | Parse confidence, sources, and answer body from LLM output |
| `credit_analyzer/retrieval/reranker.py` | Cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) |
| `docs/CONFIG_REFERENCE.md` | Full env var reference |
| `docs/RETRIEVAL_ARCHITECTURE.md` | Detailed explanation of RRF, definition injection, sibling expansion |

## Configuration

All knobs live in `config.py` and can be overridden via `.env`:

- `ANTHROPIC_API_KEY` — required when `LLM_PROVIDER=claude`
- `LLM_PROVIDER` — `claude` | `ollama` | `internal` (default: `claude`)
- `ANTHROPIC_MODEL` — Claude model (default: `claude-sonnet-4-6`)
- `REPORT_MAX_WORKERS=2` — parallel report sections; keep low to avoid Anthropic rate limits (30k input tokens/min)
- `MIN_RETRIEVAL_SCORE=0.15` — post-rerank score floor; always keeps at least 3 chunks
- `RERANK_CANDIDATES_MULTIPLIER=3` — over-fetch factor before reranking
- `EMBEDDING_MODEL` — embedding model name (default: `BAAI/bge-small-en-v1.5`)

## Report Generation Behavior

- Section 1 (Transaction Overview) runs first to extract the borrower name via regex
- Sections 2–10 run in parallel with `REPORT_MAX_WORKERS` workers
- Per-section retrieval queries also run in parallel inside `_retrieve_for_section`
- The system prompt instructs the LLM to silently omit fields not found in context — do **not** add "NOT FOUND" language to extraction prompts
- `ClaudeProvider` has `max_retries=5` for rate-limit backoff

## Adding a New LLM Provider

1. Create `credit_analyzer/llm/my_provider.py` implementing `LLMProvider` ABC (`complete`, `is_available`, `model_name`)
2. Register it in `factory.py` and add the name to `_VALID_PROVIDERS`

## Testing Notes

- Tests use real objects (no heavy mocking); most are unit tests over small text fixtures
- The embedder and ChromaDB tests require no API key but will download models on first run
- LLM tests mock the provider to avoid API calls

| Test file | Covers |
|---|---|
| `test_chunker.py` | Token-based chunking, overlap, definition detection |
| `test_pdf_extractor.py` | PDF text extraction and OCR fallback |
| `test_section_detector.py` | Section type classification |
| `test_definitions.py` | DefinitionsIndex term parsing and lookup |
| `test_embedder.py` | Embedding model (downloads model on first run) |
| `test_vector_store.py` | ChromaDB storage and search |
| `test_bm25_store.py` | BM25Plus index and search |
| `test_hybrid_retriever.py` | Full retrieval pipeline with mocks |
| `test_qa_engine.py` | Q&A with history-aware reformulation |
| `test_report_template.py` | Section template structure and prompts |
| `test_report_generator.py` | Report generation with mocked LLM |
| `test_inline_citations.py` | Citation parsing and enrichment |
| `test_text_cleaning.py` | Markdown stripping utilities |
| `test_llm.py` | LLM provider mocks |
