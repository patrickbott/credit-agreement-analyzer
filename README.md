# Credit Agreement Analyzer

A local-first tool for leveraged finance analysts to extract key terms, covenants, and provisions from credit agreement PDFs.

## Features

- **Automated Report Generation**: Upload a credit agreement PDF and generate a structured analyst brief covering pricing, covenants, restricted payments, incremental debt, and more
- **Targeted Q&A**: Ask specific questions with cited sources, confidence ratings, and multi-turn conversation history
- **Full Report Export**: Export a structured 10-section analyst report as a PDF
- **Swappable LLM**: Abstracted provider interface supports Claude (default), Ollama, or any internal LLM

## Quick Start (Claude API)

### Prerequisites

- Python 3.11+
- An Anthropic API key

### Installation

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
# Open .env and set ANTHROPIC_API_KEY=your-key-here
```

### Running the App

```bash
streamlit run app.py
```

Open http://localhost:8501, upload a credit agreement PDF, and start asking questions.

---

## Alternative: Local Model via Ollama

If you prefer to run without an external API:

```bash
# Install Ollama from https://ollama.ai, then pull a model
ollama pull llama3.2:3b
```

Set in `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```

Note: Smaller local models produce lower-quality extractions than Claude. Expect shorter answers and less precise citations.

---

## Optional: Tesseract OCR

Required only for scanned PDFs (image-based, no embedded text). Digital credit agreements do not need Tesseract.

- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki; set `TESSERACT_CMD` in `.env`
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt install tesseract-ocr`

---

## Documentation

| Document | Description |
|---|---|
| [Config Reference](docs/CONFIG_REFERENCE.md) | All tunable parameters and environment variables |
| [Retrieval Architecture](docs/RETRIEVAL_ARCHITECTURE.md) | How hybrid retrieval, definition injection, and sibling expansion work |
| [Project Plan](docs/PROJECT_PLAN.md) | Architecture decisions and build phases |
| [Report Template](docs/REPORT_TEMPLATE.md) | Report section definitions and extraction prompts |

---

## Architecture

```
PDF Upload -> Extract -> Section Detect -> Chunk -> Embed -> ChromaDB
                                                          |
                                  Hybrid Retrieval (Vector + BM25)
                                    + Definition Injection
                                    + Sibling Expansion
                                              |
                                  Q&A Engine / Report Generator
                                              |
                                        LLM Provider
                                  (Claude / Ollama / Internal)
```

## Tech Stack

| Component | Tool |
|---|---|
| PDF Parsing | PyMuPDF + pdfplumber |
| OCR | Tesseract (optional fallback) |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Vector DB | ChromaDB |
| Keyword Search | rank-bm25 |
| LLM | Claude (Anthropic API) |
| PDF Export | fpdf2 |
| UI | Streamlit |
