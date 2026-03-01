# Configuration Reference

All tunable parameters for the Credit Agreement Analyzer. Every constant lives in
`credit_analyzer/config.py`. Override runtime values via environment variable — the
app reads `.env` at startup (copy `.env.example` to `.env` to get started).

Call `validate_config()` before doing any pipeline work; it returns a list of
human-readable errors and is called automatically by `app.py` at startup.

---

## Environment Variables

These are the only values that **must** be set externally (in `.env` or your shell).
Everything else has a sensible default and is changed in `config.py`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (Claude) | — | API key for the Anthropic Claude API. |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model ID to use for generation. |
| `LLM_PROVIDER` | No | `claude` | Active provider: `claude`, `ollama`, or `internal`. |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | Ollama model name (only used when `LLM_PROVIDER=ollama`). |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL. |
| `TESSERACT_CMD` | No | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Full path to the Tesseract binary. Set this on macOS/Linux. |

---

## LLM Configuration

```python
LLM_PROVIDER = "claude"              # Active provider; override via LLM_PROVIDER env var
CLAUDE_MODEL  = "claude-sonnet-4-6"  # Override via ANTHROPIC_MODEL env var
CLAUDE_API_KEY = None                # Populated from ANTHROPIC_API_KEY env var

OLLAMA_MODEL    = "llama3.2:3b"
OLLAMA_BASE_URL = "http://localhost:11434"
```

The `claude` provider uses the Anthropic SDK with `max_retries=3`. The `ollama`
provider adds a single retry with a 1-second sleep on transient HTTP failures.

---

## Embedding Configuration

```python
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # HuggingFace sentence-transformers model
```

The model is downloaded from HuggingFace on first run and cached locally. `bge-small-en-v1.5`
is fast on CPU and produces 384-dimensional embeddings suitable for cosine similarity
search in ChromaDB.

---

## Chunking Configuration

```python
CHUNK_TARGET_TOKENS     = 600   # Target size per chunk (tiktoken cl100k_base)
CHUNK_MAX_TOKENS        = 800   # Hard ceiling; a chunk is always split below this
CHUNK_OVERLAP_TOKENS    = 100   # Token overlap between consecutive split chunks
MIN_DEFINITION_CHUNK_TOKENS = 50  # Minimum tokens before a definition chunk is
                                  # merged with the next rather than emitted alone
TIKTOKEN_ENCODING = "cl100k_base"
```

**Tuning guidance:**
- **Shorter chunks (400 tokens):** More precise retrieval; may drop cross-sentence context.
- **Longer chunks (800 tokens):** Richer per-chunk context; increases noise per retrieval hit.
- 600 tokens is a reasonable default for legal text with clearly delineated subsections.

---

## Retrieval Configuration

```python
VECTOR_WEIGHT  = 0.6   # Fraction of score from vector (semantic) similarity
BM25_WEIGHT    = 0.4   # Fraction of score from BM25 (keyword) matching
                        # Must sum to 1.0; validated at startup

MAX_DEFINITIONS_INJECTED   = 18   # Max definition chunks injected per query
                                   # (includes recursive expansion hits)
SIBLING_EXPANSION_MAX_TOKENS = 800 # Token budget for sibling-chunk context window
                                   # appended around each top-ranked chunk
DEFINITION_UBIQUITY_THRESHOLD = 0.25  # Terms present in > 25% of chunks are
                                       # treated as ubiquitous and skipped during
                                       # definition injection
```

**Tuning guidance:**
- **Vector vs BM25 weight:** If defined-term lookups are weak, nudge `BM25_WEIGHT` up
  to 0.5. If semantic paraphrases are being missed, nudge `VECTOR_WEIGHT` up to 0.7.
  Both must sum to 1.0 or `validate_config()` will fail.
- **`MAX_DEFINITIONS_INJECTED`:** 18 is generous. Reduce to 10–12 if context windows
  fill up; increase if the model frequently misinterprets defined terms.
- **`DEFINITION_UBIQUITY_THRESHOLD`:** Lower this (e.g. 0.15) if common terms like
  "Borrower" are being skipped; raise it (e.g. 0.4) if definition injection is too noisy.

---

## Q&A Engine Configuration

```python
QA_MAX_HISTORY_TURNS    = 3      # Prior conversation turns included in context
QA_MAX_CONTEXT_CHUNKS   = 15     # Maximum retrieved chunks assembled into context
QA_MAX_GENERATION_TOKENS = 1024  # Max tokens the LLM may generate per answer
QA_DEFINITION_MAX_CHARS = 800    # Injected definition text truncated to this length
                                  # (~200 tokens); keeps token budget predictable
QA_CHUNK_TEXT_MAX_CHARS = 1500   # Chunk body truncated to this length in context
                                  # assembly (~400 tokens)
QA_SECTION_TYPES_EXCLUDE = ("miscellaneous",)  # Section types skipped during retrieval
```

---

## PDF Extraction Configuration

```python
OCR_TEXT_LENGTH_THRESHOLD = 100  # Pages with fewer extracted characters than this
                                  # trigger Tesseract OCR fallback

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                # Override via TESSERACT_CMD env var on macOS/Linux:
                #   macOS (Homebrew): /usr/local/bin/tesseract
                #   Linux:           /usr/bin/tesseract
```

---

## Storage Configuration

```python
CHROMA_DATA_DIR = PROJECT_ROOT / "chroma_data"  # ChromaDB persistence directory
```

Each document upload creates a new timestamped ChromaDB collection. Collections
accumulate across sessions and must be pruned manually (or via a future cleanup
utility) to reclaim disk space. This is a known limitation acceptable for demo use.

---

## Config Validation

`validate_config()` checks the following at startup and returns a list of error strings:

1. `ANTHROPIC_API_KEY` is set when `LLM_PROVIDER == "claude"`.
2. `VECTOR_WEIGHT + BM25_WEIGHT == 1.0` (within floating-point tolerance).
3. `DEFINITION_UBIQUITY_THRESHOLD` is in `[0.0, 1.0]`.
4. `EMBEDDING_MODEL` is not empty.

`app.py` calls this at startup and halts with a `st.error()` if any check fails,
so misconfiguration is surfaced immediately rather than mid-pipeline.
