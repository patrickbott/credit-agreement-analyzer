# Credit Agreement Analyzer

Local-first Streamlit app for leveraged finance teams to analyze credit agreement PDFs with retrieval-augmented Q&A and structured report generation.

## Features

- Upload and index a credit agreement PDF (text + tables + OCR fallback)
- Ask targeted questions with confidence signal and section/page citations
- Generate a 10-section analyst report and export it as PDF
- Switch LLM backends via config: `claude`, `ollama`, or `internal`
- Domain-aware knowledge layer for leveraged finance jargon (J.Crew, Serta, freebie baskets, etc.)
- Docker Compose deployment with Nginx reverse proxy and basic auth

## Quick Start

### Option A: Docker (recommended for sharing with your team)

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY or LLM_PROVIDER

docker compose up -d --build
```

Open `http://localhost` in a browser. See [Deployment Guide](docs/DEPLOYMENT.md) for full setup including basic auth and offline transfer.

### Option B: Local development

#### Prerequisites

- Python 3.11+
- Anthropic API key (if using `LLM_PROVIDER=claude`)

#### Install

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux
```

Set `ANTHROPIC_API_KEY` in `.env` when using Claude.

#### Run

```bash
streamlit run app.py
```

## Architecture

```
PDF Upload
  |
  v
[Processing Pipeline]
  pdf_extractor -> section_detector -> chunker -> definitions
  |
  v
[Indexing]
  VectorStore (ChromaDB) + BM25Store
  |
  v
[Query Processing]
  Knowledge Layer (concept matching + synonym expansion)
  -> HybridRetriever (vector + BM25 + RRF + reranking)
  -> Quality Gate (score + term overlap check)
  -> Conditional LLM Decomposition (complex queries only)
  |
  v
[Generation]
  QAEngine (streaming Q&A) or ReportGenerator (10-section report)
  |
  v
[UI]
  Chat-centric Streamlit app with citations, definitions, and report export
```

## Documentation

| Document | Description |
|---|---|
| [Deployment Guide](docs/DEPLOYMENT.md) | Docker Compose setup, offline transfer, user management |
| [Workstation Setup](docs/WORKSTATION_SETUP.md) | Step-by-step guide for deploying on a work computer |
| [Configuration Reference](docs/CONFIG_REFERENCE.md) | All environment variables and tuning knobs |
| [Retrieval Architecture](docs/RETRIEVAL_ARCHITECTURE.md) | Retrieval pipeline stages and knowledge layer |

## Development

```bash
.venv\Scripts\python -m pytest tests/
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m pyright
```

## Repository Notes

- `demo_uploads/` and `chroma_data/` are local runtime data folders.
- The `components/` directory contains custom Streamlit components (chat input bar).
- Knowledge layer data lives in `credit_analyzer/knowledge/` (YAML files for concepts and synonyms).
