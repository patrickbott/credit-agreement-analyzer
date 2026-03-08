# Credit Agreement Analyzer

Local-first Streamlit app for leveraged finance teams to analyze credit agreement PDFs with retrieval-augmented Q&A and structured report generation.

## Features

- Upload and index a credit agreement PDF (text + tables + OCR fallback)
- Ask targeted questions with confidence signal and section/page citations
- Generate a 10-section analyst report and export it as PDF
- Switch LLM backends via config: `claude`, `ollama`, or `internal`

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (if using `LLM_PROVIDER=claude`)

### Install

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux
```

Set `ANTHROPIC_API_KEY` in `.env` when using Claude.

### Run

```bash
streamlit run app.py
```

## Configuration

All runtime knobs live in [credit_analyzer/config.py](credit_analyzer/config.py).  
Reference docs:

- [Configuration Reference](docs/CONFIG_REFERENCE.md)
- [Retrieval Architecture](docs/RETRIEVAL_ARCHITECTURE.md)

## Development

```bash
.venv\Scripts\python -m pytest tests/
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m pyright
```

## Repository Notes

- `demo_uploads/` and `chroma_data/` are local runtime data folders.
- The docs set was pruned to keep only current, implementation-backed references.
