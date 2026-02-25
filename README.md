# Credit Agreement Analyzer

A local-first tool for leveraged finance analysts to extract key terms, covenants, and provisions from credit agreement PDFs.

## Features

- **Automated Report Generation**: Upload a credit agreement PDF and generate a structured ~10-page summary covering pricing, covenants, baskets, bank group, and more
- **Targeted Q&A**: Ask specific questions about the agreement with cited sources and confidence ratings
- **Fully Local**: Runs entirely on your machine using Ollama — no external API calls
- **Swappable LLM**: Abstracted provider interface allows future migration to internal enterprise LLMs

## Quick Start

### Prerequisites

1. Python 3.10+
2. Ollama installed with Llama 3 8B:
   ```bash
   ollama pull llama3:8b
   ```
3. (Optional) Tesseract OCR for scanned PDFs

### Installation

```bash
cd credit_analyzer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Usage

```bash
streamlit run app.py
```

## Documentation

- [Project Plan](docs/PROJECT_PLAN.md) — Architecture, design decisions, and scope
- [Module Specs](docs/MODULE_SPECS.md) — Detailed specification for each component
- [Report Template](docs/REPORT_TEMPLATE.md) — Report structure and extraction prompts
- [Prompts](docs/PROMPTS.md) — All LLM prompts and engineering notes
- [Config Reference](docs/CONFIG_REFERENCE.md) — All tunable parameters
- [Build Order](docs/BUILD_ORDER.md) — Step-by-step implementation guide with test checkpoints

## Architecture

```
PDF Upload → Extract → Section Detect → Chunk → Embed → Store (ChromaDB)
                                                              ↓
                                            Hybrid Retrieval (Vector + BM25)
                                                    ↓              ↓
                                            Report Generator    Q&A Chat
                                                    ↓              ↓
                                              LLM Provider (Ollama / Internal)
```

## Tech Stack

| Component | Tool |
|---|---|
| PDF Parsing | PyMuPDF + pdfplumber |
| OCR | Tesseract (fallback) |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Vector DB | ChromaDB |
| Keyword Search | rank-bm25 |
| LLM | Ollama (Llama 3 8B) |
| UI | Streamlit |
