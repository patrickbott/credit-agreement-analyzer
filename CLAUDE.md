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

### Knowledge Layer

- `credit_analyzer/knowledge/concepts.yaml` — 20+ leveraged finance concepts with aliases, search terms, descriptions
- `credit_analyzer/knowledge/synonyms.yaml` — synonym groups mapping jargon to canonical terms
- `credit_analyzer/knowledge/registry.py` — `DomainRegistry` with alias matching and synonym expansion
- `credit_analyzer/retrieval/quality_gate.py` — retrieval quality scoring (score thresholds + term overlap)
- `credit_analyzer/generation/query_decomposer.py` — LLM-powered query decomposition for complex questions
- `credit_analyzer/generation/query_expansion.py` — concept-aware query expansion

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

- `QAEngine` for conversational Q&A with concept matching, quality gate, and conditional decomposition
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

### Deployment

- `Dockerfile` — Python 3.11 image with pre-cached ML models for offline use
- `docker-compose.yml` — app + Nginx reverse proxy with basic auth
- `nginx/` — Nginx config and `.htpasswd` for user management

## Configuration

See:

- [docs/CONFIG_REFERENCE.md](docs/CONFIG_REFERENCE.md)
- [docs/RETRIEVAL_ARCHITECTURE.md](docs/RETRIEVAL_ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/WORKSTATION_SETUP.md](docs/WORKSTATION_SETUP.md)

## Important Behavior

- Report extraction prompt uses strict omission for missing fields (no `"NOT FOUND"` fill-ins except fully empty section fallback).
- Import surfaces are lazy-loaded in package `__init__.py` to avoid heavy dependency failures during unrelated module imports/tests.
