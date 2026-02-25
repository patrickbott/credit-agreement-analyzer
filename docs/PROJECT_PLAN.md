# Credit Agreement Analyzer — Project Plan

## Project Overview

A local-first application that allows leveraged finance analysts to upload credit agreement PDFs and:
1. **Generate a structured report** (max ~10 pages) extracting all key terms, pricing, covenants, baskets, and provisions
2. **Ask targeted follow-up questions** via a chat interface with cited sources and confidence ratings

The system runs entirely locally (no external API calls) using Ollama + Llama 3 8B, with an abstracted LLM interface that allows future migration to an internal enterprise LLM.

---

## Hardware & Environment

- **RAM**: 32GB DDR4
- **GPU**: None / not relied upon (CPU inference via Ollama)
- **LLM**: Llama 3 8B via Ollama
- **Embedding Model**: BAAI/bge-small-en-v1.5 (runs on CPU, ~130MB)
- **OS**: Windows (assumed based on file paths)
- **Python**: 3.10+

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                     │
│         (Upload PDF, View Report, Chat)           │
└──────────────┬──────────────────┬────────────────┘
               │                  │
        ┌──────▼──────┐   ┌──────▼──────┐
        │   Report     │   │    Q&A      │
        │  Generator   │   │   Engine    │
        └──────┬──────┘   └──────┬──────┘
               │                  │
        ┌──────▼──────────────────▼──────┐
        │        Retrieval Layer          │
        │  (Vector Search + BM25 Hybrid)  │
        └──────────────┬─────────────────┘
               ┌───────┴────────┐
               │                │
        ┌──────▼──────┐  ┌─────▼───────┐
        │  ChromaDB    │  │  Definitions │
        │  (vectors)   │  │    Index     │
        └─────────────┘  └─────────────┘
               │
        ┌──────▼──────────────────────────┐
        │      Document Processor          │
        │  (PDF Parse → Section Detect →   │
        │   Chunk → Embed → Store)         │
        └─────────────────────────────────┘

        ┌─────────────────────────────────┐
        │         LLM Provider            │
        │        (Abstract Interface)      │
        │  ┌───────────┐ ┌─────────────┐  │
        │  │  Ollama    │ │  Internal   │  │
        │  │  Adapter   │ │  LLM Adapter│  │
        │  └───────────┘ └─────────────┘  │
        └─────────────────────────────────┘
```

### Key Design Principles

1. **LLM is decoupled**: All LLM calls go through an abstract `LLMProvider` interface. Swapping from Ollama to an internal LLM requires only writing a new adapter and changing one config value.
2. **Retrieval precision over recall**: Section-aware chunking + metadata filtering + hybrid search (vector + BM25) ensures the right context reaches the model.
3. **Extraction over generation**: Prompts are structured to extract specific data points from source text, not generate free-form summaries. This plays to small model strengths and reduces hallucination.
4. **Transparency**: Every output includes source citations (article/section numbers, page numbers) and confidence ratings.

---

## File Structure

```
credit_analyzer/
├── app.py                     # Streamlit entry point
├── config.py                  # All configuration in one place
├── requirements.txt
│
├── llm/
│   ├── __init__.py
│   ├── base.py                # LLMProvider abstract class
│   ├── ollama_provider.py     # Ollama adapter
│   └── internal_provider.py   # Future: internal LLM adapter (stub)
│
├── processing/
│   ├── __init__.py
│   ├── pdf_extractor.py       # PDF → raw text + tables
│   ├── section_detector.py    # Identify article/section structure
│   ├── chunker.py             # Section-aware chunking
│   └── definitions.py         # Parse and index defined terms
│
├── retrieval/
│   ├── __init__.py
│   ├── embedder.py            # Sentence transformer embedding
│   ├── vector_store.py        # ChromaDB wrapper
│   ├── bm25_store.py          # BM25 keyword index
│   └── hybrid_retriever.py    # Combined retrieval + definition injection
│
├── generation/
│   ├── __init__.py
│   ├── report_generator.py    # Orchestrates multi-section report
│   ├── report_template.py     # Report section definitions & prompts
│   ├── qa_engine.py           # Conversational Q&A
│   └── prompts.py             # All prompt templates
│
├── ui/
│   ├── __init__.py
│   ├── upload_page.py         # PDF upload + processing progress
│   ├── report_page.py         # Report display + export
│   └── chat_page.py           # Q&A chat interface
│
└── utils/
    ├── __init__.py
    ├── text_cleaning.py       # Normalize whitespace, fix encoding
    └── validation.py          # Verify extracted values against source text
```

---

## Performance Expectations

| Operation | Estimated Time |
|---|---|
| PDF ingestion (parse + chunk + embed, 300pg) | 1–3 minutes |
| Full report generation (~15-20 LLM calls) | 8–15 minutes |
| Single Q&A response | 15–30 seconds |

Report generation is the slowest step. Mitigations:
- Show sections as they complete (streaming UX)
- Potential future: parallelize independent sections
- Potential future: larger/faster model if hardware allows

---

## Build Phases

### Phase 1: Document Processing Pipeline
**Goal**: Upload a PDF → get structured, chunked, embedded content in ChromaDB.

1. PDF extractor (PyMuPDF primary, pdfplumber for tables, Tesseract OCR fallback)
2. Section detector (regex-based article/section identification)
3. Definitions parser (extract Article 1 defined terms into lookup dictionary)
4. Section-aware chunker (with metadata tagging)
5. Embedding + ChromaDB storage
6. BM25 index construction
7. **Test**: Process a real credit agreement, inspect chunks, verify section labels and definitions

### Phase 2: LLM Provider Layer
**Goal**: Abstract LLM interface with working Ollama adapter.

1. Abstract `LLMProvider` base class
2. `OllamaProvider` implementation
3. Stub `InternalLLMProvider` for future use
4. Config-driven provider selection
5. **Test**: Send extraction prompts through Ollama, verify structured output

### Phase 3: Retrieval Layer
**Goal**: Given a query, return the most relevant chunks with injected definitions.

1. Hybrid retriever (vector + BM25 score merging)
2. Metadata-filtered retrieval (search within specific sections)
3. Definition injection (scan retrieved chunks for defined terms, append definitions)
4. **Test**: Run sample queries against a processed document, verify retrieved chunks are relevant

### Phase 4: Q&A Engine
**Goal**: Working chat interface where analysts can ask questions and get cited answers.

1. Q&A engine with conversation history
2. Source citation formatting
3. Confidence rating
4. Streamlit chat UI
5. **Test**: Ask a variety of questions against a real credit agreement, verify accuracy

### Phase 5: Report Generator
**Goal**: Automated multi-section report generation.

1. Report template with section definitions and extraction prompts
2. Report orchestrator (iterates sections, runs retrieval + LLM for each)
3. Markdown assembly and rendering
4. PDF/export functionality
5. Streamlit report UI with progress indicator
6. **Test**: Generate full reports for multiple credit agreements, review for completeness and accuracy

### Phase 6: Polish & Hardening
**Goal**: Production-ready for other analysts.

1. Error handling throughout (bad PDFs, Ollama not running, etc.)
2. Validation layer (cross-check extracted numbers against source text)
3. UI polish (clear error messages, loading states, help text)
4. Documentation for end users (how to install Ollama, how to use the tool)
5. Handle edge cases (cov-lite deals, amendments, unusual formatting)

---

## Dependencies

```
# Core
streamlit
pymupdf (fitz)
pdfplumber
pytesseract          # OCR fallback for scanned PDFs
chromadb
sentence-transformers
rank-bm25
ollama               # Python client for Ollama

# Utilities
tiktoken             # Token counting for chunk sizing
jinja2               # Report template rendering
markdown
weasyprint           # Markdown → PDF export (or markdown-pdf)

# Development
pytest
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Llama 3 8B hallucinates numbers/terms | Medium | High | Structured extraction prompts, validation layer, confidence ratings, always cite sources |
| PDF parsing fails on unusual formatting | Medium | Medium | Multiple parser fallback chain (PyMuPDF → pdfplumber → OCR), manual section override option |
| Section detection misidentifies structure | Medium | Medium | Regex patterns covering common formats, fallback to sequential chunking, allow manual correction |
| Embedding model misses legal term similarity | Low-Medium | Medium | Hybrid retrieval (BM25 catches keyword matches that embeddings miss) |
| Report generation too slow on CPU | High | Low-Medium | Streaming UI (show sections as complete), potential parallelization, accept ~10 min as reasonable for a 10-page report |
| Definitions chain resolution too deep | Low | Low | Cap definition injection at 5 per query, handle most common first-level references |

---

## Future Scope (Not In V1)

- Multi-document comparison ("compare RP baskets across Deal A and Deal B")
- Batch processing (upload multiple agreements, generate reports for all)
- Fine-tuned embedding model on legal/financial corpus
- Integration with internal LLM when available
- Amendment tracking (detect changes between original and amended agreements)
- Export to Excel/PowerPoint for pitch book integration
