# Configuration Reference

All tunable parameters for the Credit Agreement Analyzer.

---

## LLM Configuration

```python
# Provider selection: "ollama" or "internal"
LLM_PROVIDER = "ollama"

# Ollama settings
OLLAMA_MODEL = "llama3:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# Generation settings (apply to all providers)
LLM_TEMPERATURE = 0.0           # Always 0 for extraction tasks
LLM_MAX_TOKENS = 2048           # Max tokens per generation
LLM_TIMEOUT_SECONDS = 120       # Timeout for a single LLM call
```

---

## Embedding Configuration

```python
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DEVICE = "cpu"         # "cpu" or "cuda" if GPU available
EMBEDDING_BATCH_SIZE = 32        # Chunks embedded per batch
```

---

## Chunking Configuration

```python
CHUNK_TARGET_TOKENS = 600        # Target size per chunk
CHUNK_MAX_TOKENS = 800           # Hard maximum
CHUNK_OVERLAP_TOKENS = 100       # Overlap between split chunks
MIN_DEFINITION_CHUNK_TOKENS = 50 # Group small definitions together
TOKENIZER_ENCODING = "cl100k_base"  # tiktoken encoding (approximates Llama tokenization)
```

---

## Retrieval Configuration

```python
RETRIEVAL_TOP_K = 5              # Number of chunks to retrieve per query
VECTOR_WEIGHT = 0.6              # Weight for vector similarity in hybrid scoring
BM25_WEIGHT = 0.4                # Weight for BM25 keyword matching
MAX_DEFINITIONS_INJECTED = 5     # Max definitions added to context per query
```

---

## Report Configuration

```python
REPORT_MAX_PAGES = 10            # Target max pages (guidance, not hard enforced)
REPORT_SECTION_MAX_TOKENS = 1500 # Max generation tokens per report section
REPORT_RETRIEVAL_TOP_K = 5      # Chunks retrieved per report section query
```

---

## Q&A Configuration

```python
QA_MAX_CONVERSATION_HISTORY = 3  # Number of previous Q&A turns included in context
QA_RETRIEVAL_TOP_K = 5           # Chunks retrieved per question
```

---

## Storage Configuration

```python
CHROMA_PERSIST_DIR = "./data/chroma"    # ChromaDB storage location
PROCESSED_DOCS_DIR = "./data/documents" # Processed document metadata
```

---

## PDF Processing Configuration

```python
OCR_ENABLED = True                      # Enable Tesseract OCR fallback
OCR_MIN_TEXT_LENGTH = 100               # If page text shorter than this, trigger OCR
TABLE_EXTRACTION_ENABLED = True         # Extract tables via pdfplumber
```

---

## UI Configuration

```python
STREAMLIT_PAGE_TITLE = "Credit Agreement Analyzer"
STREAMLIT_PAGE_ICON = "📄"
MAX_UPLOAD_SIZE_MB = 100                # Max PDF upload size
SHOW_DEBUG_INFO = False                 # Show retrieved chunks in UI (for development)
```

---

## Tuning Notes

### When to adjust RETRIEVAL_TOP_K
- If answers are missing relevant information → increase (try 7-8)
- If answers contain irrelevant context or model gets confused → decrease (try 3-4)
- For report generation, each section may benefit from different k values — can override in report template

### When to adjust VECTOR_WEIGHT vs BM25_WEIGHT
- If semantic queries work well but exact term lookups fail → increase BM25_WEIGHT
- If keyword searches are too literal and miss paraphrased content → increase VECTOR_WEIGHT
- Start with 0.6/0.4 and adjust based on retrieval quality testing

### When to adjust CHUNK_TARGET_TOKENS
- Smaller chunks (400) → more precise retrieval but may lose context
- Larger chunks (800) → more context per chunk but may include noise
- 600 is a good starting point for legal documents with clearly delineated subsections

### When to adjust MAX_DEFINITIONS_INJECTED
- If model struggles with defined terms → increase to 7-8
- If context window is getting too full → decrease to 3
- Monitor the token budget — definitions compete with retrieved chunks for context space
