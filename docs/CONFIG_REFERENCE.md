# Configuration Reference

Canonical runtime configuration for the Credit Agreement Analyzer.

All values live in [credit_analyzer/config.py](../credit_analyzer/config.py).

## Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes when `LLM_PROVIDER=claude` | unset | Claude API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model id |
| `LLM_PROVIDER` | No | `claude` | `claude`, `ollama`, `internal` |
| `OLLAMA_MODEL` | No | `llama3.2:3b` | Used only for Ollama provider |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama endpoint |
| `TESSERACT_CMD` | No | OS-specific auto default | OCR binary path |
| `CHUNK_TARGET_TOKENS` | No | `800` | Target chunk size |
| `CHUNK_MAX_TOKENS` | No | `1200` | Hard chunk ceiling |
| `CHUNK_OVERLAP_TOKENS` | No | `200` | Overlap between adjacent chunks |
| `MIN_DEFINITION_CHUNK_TOKENS` | No | `50` | Min definition size before standalone chunk |
| `MAX_DEFINITIONS_INJECTED` | No | `12` | Primary definition-injection cap |
| `MIN_RETRIEVAL_SCORE` | No | `0.15` | Post-rerank filtering threshold |
| `REPORT_MAX_WORKERS` | No | `3` | Parallel report section workers |

## Key Constants (Code Defaults)

### Paths

- `PROJECT_ROOT`
- `CHROMA_DATA_DIR = PROJECT_ROOT / "chroma_data"`

### PDF Extraction

- `OCR_TEXT_LENGTH_THRESHOLD = 100`

### Chunking

- `CHUNK_TARGET_TOKENS = 800`
- `CHUNK_MAX_TOKENS = 1200`
- `CHUNK_OVERLAP_TOKENS = 200`
- `MIN_DEFINITION_CHUNK_TOKENS = 50`
- `TIKTOKEN_ENCODING = "cl100k_base"`

### Retrieval

- `RRF_K = 50`
- `MAX_DEFINITIONS_INJECTED = 12`
- `SIBLING_EXPANSION_MAX_TOKENS = 1200`
- `MIN_RETRIEVAL_SCORE = 0.15`
- `RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"`
- `RERANK_CANDIDATES_MULTIPLIER = 3`
- `BM25_K1 = 1.2`
- `BM25_B = 0.5`
- `DEFINITION_UBIQUITY_THRESHOLD = 0.25`

### Report Generation

- `REPORT_MAX_WORKERS = 3`

### LLM

- `LLM_PROVIDER = "claude"`
- `OLLAMA_MODEL = "llama3.2:3b"`
- `OLLAMA_BASE_URL = "http://localhost:11434"`
- `CLAUDE_MODEL = "claude-sonnet-4-6"`
- `CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")`

### Q&A

- `QA_MAX_HISTORY_TURNS = 3`
- `QA_MAX_CONTEXT_CHUNKS = 15`
- `QA_MAX_GENERATION_TOKENS = 1024`
- `QA_DEFINITION_MAX_CHARS = 800`
- `QA_SECTION_TYPES_EXCLUDE = ("miscellaneous",)`

### Embeddings

- `EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"`

## Validation Behavior

`validate_config()` currently checks:

1. Claude key presence when `LLM_PROVIDER == "claude"`.
2. `DEFINITION_UBIQUITY_THRESHOLD` is between `0.0` and `1.0`.
3. `EMBEDDING_MODEL` is non-empty.

The app stops at startup if validation fails.
