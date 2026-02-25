# Module Specifications

## Module 1: PDF Extractor (`processing/pdf_extractor.py`)

### Purpose
Extract text and tables from credit agreement PDFs, handling both digital and scanned documents.

### Interface
```python
class PDFExtractor:
    def extract(self, pdf_path: str) -> ExtractedDocument

@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: list[str]          # Tables converted to markdown format
    is_ocr: bool               # Whether OCR was used for this page

@dataclass  
class ExtractedDocument:
    pages: list[ExtractedPage]
    total_pages: int
    source_path: str
    extraction_method: str     # "digital" or "ocr" or "mixed"
```

### Logic
1. Open PDF with PyMuPDF (`fitz`)
2. For each page:
   a. Extract text via PyMuPDF
   b. If text length < 100 chars → likely scanned → run Tesseract OCR
   c. Use pdfplumber to detect and extract tables on the page
   d. Convert tables to markdown format (pipe-delimited)
3. Return `ExtractedDocument`

### Edge Cases
- Scanned PDFs: OCR fallback with Tesseract. Quality will vary — acceptable for V1.
- Password-protected PDFs: PyMuPDF supports password param. Add to UI if needed.
- Multi-column layouts: Rare in credit agreements but possible in exhibits. PyMuPDF handles this reasonably well.
- Headers/footers/page numbers: These will be in the extracted text. Section detector should be robust enough to ignore them.

### Dependencies
- `pymupdf` (fitz)
- `pdfplumber`
- `pytesseract` + Tesseract binary installed on system

---

## Module 2: Section Detector (`processing/section_detector.py`)

### Purpose
Identify the structural sections (articles, sections, subsections) of the credit agreement from raw extracted text.

### Interface
```python
class SectionDetector:
    def detect_sections(self, document: ExtractedDocument) -> list[DocumentSection]

@dataclass
class DocumentSection:
    section_id: str            # e.g., "7.06"
    article_number: int        # e.g., 7
    section_title: str         # e.g., "Restricted Payments"
    article_title: str         # e.g., "NEGATIVE COVENANTS"
    text: str                  # Full text of this section
    page_start: int
    page_end: int
    tables: list[str]          # Any tables found within this section
    section_type: str          # "definitions", "financial_covenants", "negative_covenants", etc.
```

### Logic
1. Concatenate all page text with page markers
2. Use regex patterns to detect article headers:
   - `ARTICLE [ROMAN_NUMERAL/NUMBER] — [TITLE]` or `ARTICLE [NUMBER]\n[TITLE]`
   - Common variations: "ARTICLE VII", "ARTICLE 7", "Article VII", etc.
3. Use regex to detect section headers within articles:
   - `Section 7.06` or `SECTION 7.06` or `7.06` at start of line
   - `(a)`, `(b)`, `(i)`, `(ii)` for subsections (tracked but not split into separate sections)
4. Classify each article into a `section_type` based on title keywords:
   - "DEFINITIONS" → `definitions`
   - "FINANCIAL COVENANTS" → `financial_covenants`
   - "NEGATIVE COVENANTS" → `negative_covenants`
   - "AFFIRMATIVE COVENANTS" → `affirmative_covenants`
   - "EVENTS OF DEFAULT" → `events_of_default`
   - "THE CREDITS" / "THE LOANS" / "AMOUNTS AND TERMS" → `facility_terms`
   - "CONDITIONS" / "CONDITIONS PRECEDENT" → `conditions`
   - etc.
5. If regex detection fails (e.g., unusual formatting), fall back to page-based sequential segmentation

### Regex Patterns (Starting Set)
```python
ARTICLE_PATTERN = r'(?:^|\n)\s*ARTICLE\s+([IVXLCDM]+|\d+)\s*[—\-–:.]?\s*\n?\s*([A-Z][A-Z\s,]+)'
SECTION_PATTERN = r'(?:^|\n)\s*(?:Section\s+|SECTION\s+)?(\d+\.\d+)\s+([A-Za-z][^\n.]+)'
```

These will need tuning against real documents. Plan to iterate.

### Edge Cases
- Table of contents at the beginning: Skip pages before Article 1 or detect TOC patterns
- Exhibits and schedules after the main body: Detect "EXHIBIT" or "SCHEDULE" headers, tag as separate section types
- Amendments appended: May have their own article structure — detect and tag separately

---

## Module 3: Definitions Parser (`processing/definitions.py`)

### Purpose
Extract defined terms and their definitions from Article 1 (or wherever definitions are located) into a fast-lookup dictionary.

### Interface
```python
class DefinitionsParser:
    def parse(self, definitions_section: DocumentSection) -> DefinitionsIndex

class DefinitionsIndex:
    def __init__(self, definitions: dict[str, str]):
        self.definitions = definitions  # term → definition text
    
    def lookup(self, term: str) -> str | None
    def find_terms_in_text(self, text: str) -> list[str]  # Find all defined terms present in text
    def get_definitions_for_terms(self, terms: list[str]) -> dict[str, str]
```

### Logic
1. Take the definitions section text
2. Defined terms in credit agreements are typically formatted as:
   - `"Defined Term"` means [definition text that continues until the next defined term]
   - Sometimes: `"Defined Term": ` or `"Defined Term" shall mean`
3. Parse using regex: look for quoted terms followed by "means", "shall mean", "has the meaning", etc.
4. Each definition's text extends until the next quoted defined term pattern
5. Build dictionary and a compiled regex pattern of all defined terms for fast text scanning

### Detecting Defined Terms in Text
Credit agreements capitalize defined terms (e.g., "Consolidated Net Income", "Available Amount"). The `find_terms_in_text` method scans a chunk for multi-word capitalized phrases that match known defined terms. This is used by the retrieval layer to inject relevant definitions.

### Edge Cases
- Definitions that reference other definitions (e.g., "Available Amount" defined using "Consolidated Net Income"): V1 only resolves one level. Could add recursive resolution later.
- Definitions spread across multiple pages: Handled by using the full section text, not page-by-page
- Defined terms with variations (e.g., "Loans" and "Loan"): Store both if both appear; simple pluralization matching as enhancement

---

## Module 4: Chunker (`processing/chunker.py`)

### Purpose
Convert detected sections into appropriately sized chunks with rich metadata for retrieval.

### Interface
```python
class Chunker:
    def chunk_document(self, sections: list[DocumentSection], 
                       definitions_index: DefinitionsIndex) -> list[Chunk]

@dataclass
class Chunk:
    chunk_id: str              # Unique identifier
    text: str                  # Chunk content
    section_id: str            # e.g., "7.06"
    section_title: str         # e.g., "Restricted Payments"
    article_number: int
    article_title: str         # e.g., "NEGATIVE COVENANTS"
    section_type: str          # e.g., "negative_covenants"
    chunk_type: str            # "text", "table", "definition"
    page_numbers: list[int]
    defined_terms_present: list[str]  # Defined terms found in this chunk
    chunk_index: int           # Position within the section (for ordering)
    token_count: int
```

### Logic

**For definition sections:**
- Each defined term becomes its own chunk with `chunk_type = "definition"`
- Small definitions (< 50 tokens) can be grouped (3-5 per chunk) to avoid excessive fragmentation

**For table content:**
- Each table becomes its own chunk with `chunk_type = "table"`
- Include surrounding context (the paragraph before the table) for retrieval relevance

**For all other sections:**
- If section fits within target token limit (600 tokens) → single chunk
- If section exceeds limit → split at paragraph boundaries
  - Find natural break points: double newlines, subsection markers like (a), (b), etc.
  - Apply overlap: ~100 tokens from end of previous chunk prepended to next chunk
  - Preserve subsection context: if splitting mid-subsection, include the subsection header in the continuation chunk

**Metadata enrichment:**
- Scan each chunk's text against the definitions index to populate `defined_terms_present`
- Count tokens using `tiktoken` (cl100k_base encoding, close enough for Llama tokenization)

### Configuration
```python
CHUNK_TARGET_TOKENS = 600
CHUNK_MAX_TOKENS = 800        # Hard cap
CHUNK_OVERLAP_TOKENS = 100
MIN_DEFINITION_CHUNK_TOKENS = 50  # Group smaller definitions together
```

---

## Module 5: Embedding & Vector Store (`retrieval/embedder.py`, `retrieval/vector_store.py`)

### Purpose
Embed chunks and store in ChromaDB for semantic retrieval.

### Embedder Interface
```python
class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = SentenceTransformer(model_name)
    
    def embed(self, texts: list[str]) -> list[list[float]]
    def embed_query(self, query: str) -> list[float]
```

### Vector Store Interface
```python
class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_data"):
        self.client = chromadb.PersistentClient(path=persist_directory)
    
    def create_collection(self, document_id: str) -> None
    def add_chunks(self, document_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None
    def search(self, document_id: str, query_embedding: list[float], 
               top_k: int = 5, section_filter: str = None) -> list[RetrievedChunk]
    def delete_collection(self, document_id: str) -> None
    def list_documents(self) -> list[str]
```

### Storage Design
- Each uploaded document gets its own ChromaDB collection, named by a sanitized version of the filename + upload timestamp
- Chunk metadata stored alongside embeddings in ChromaDB: section_id, section_title, article_number, section_type, chunk_type, page_numbers
- `defined_terms_present` stored as comma-separated string in metadata (ChromaDB metadata must be primitive types)

### Filtered Search
ChromaDB supports metadata filtering via `where` clauses:
```python
# Search only within negative covenants
collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"section_type": "negative_covenants"}
)
```

This is critical for report generation where each section queries a specific part of the document.

---

## Module 6: BM25 Store (`retrieval/bm25_store.py`)

### Purpose
Keyword-based retrieval to complement vector search. Catches exact term matches that embedding models may miss.

### Interface
```python
class BM25Store:
    def __init__(self):
        self.index = None
        self.chunks = []
    
    def build_index(self, chunks: list[Chunk]) -> None
    def search(self, query: str, top_k: int = 5, 
               section_filter: str = None) -> list[tuple[Chunk, float]]
```

### Logic
- Tokenize chunk text (simple whitespace + lowercasing, possibly with legal stopword removal)
- Build BM25 index using `rank_bm25.BM25Okapi`
- For filtered search: pre-filter chunks by section_type, then search within filtered set
- Return chunks with BM25 scores

### Notes
- BM25 is especially important for queries containing specific dollar amounts ("$50,000,000"), ratio numbers ("4.50x"), or exact legal terms ("Incremental Equivalent Debt")
- The BM25 index is rebuilt each time a document is processed (fast, in-memory)

---

## Module 7: Hybrid Retriever (`retrieval/hybrid_retriever.py`)

### Purpose
Combine vector and BM25 retrieval, inject definitions, and return the best context for LLM consumption.

### Interface
```python
class HybridRetriever:
    def __init__(self, vector_store: VectorStore, bm25_store: BM25Store,
                 embedder: Embedder, definitions_index: DefinitionsIndex):
        ...
    
    def retrieve(self, query: str, document_id: str, top_k: int = 5,
                 section_filter: str = None, 
                 inject_definitions: bool = True) -> RetrievalResult

@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]          # Ranked, deduplicated chunks
    injected_definitions: dict[str, str]  # Definitions auto-injected based on chunk content
    
@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float               # Combined score
    source: str                # "vector", "bm25", or "both"
```

### Logic
1. Run vector search → get top-k results with scores
2. Run BM25 search → get top-k results with scores
3. Normalize scores (min-max within each result set)
4. Merge: `combined_score = VECTOR_WEIGHT * vector_score + BM25_WEIGHT * bm25_score`
5. Deduplicate by chunk_id, keeping the higher combined score
6. Sort by combined score, return top-k
7. If `inject_definitions`:
   a. Scan all retrieved chunks for defined terms
   b. Look up definitions for found terms
   c. Cap at MAX_DEFINITIONS_INJECTED (5)
   d. Prioritize definitions for terms that appear most frequently across retrieved chunks

### Configuration
```python
VECTOR_WEIGHT = 0.6
BM25_WEIGHT = 0.4
MAX_DEFINITIONS_INJECTED = 5
```

---

## Module 8: LLM Provider (`llm/base.py`, `llm/ollama_provider.py`)

### Purpose
Abstract interface for LLM calls, with Ollama as the initial implementation.

### Interface
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        pass
    
    @abstractmethod  
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def model_name(self) -> str:
        pass

@dataclass
class LLMResponse:
    text: str
    tokens_used: int
    model: str
    duration_seconds: float
```

### Ollama Implementation
```python
class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=base_url)
    
    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=2048):
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": temperature, "num_predict": max_tokens}
        )
        return LLMResponse(
            text=response['message']['content'],
            tokens_used=response.get('eval_count', 0),
            model=self.model,
            duration_seconds=response.get('total_duration', 0) / 1e9
        )
```

### Internal LLM Stub
```python
class InternalLLMProvider(LLMProvider):
    """
    Stub for future integration with internal enterprise LLM.
    Implement the complete() method to call your internal API endpoint.
    """
    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=2048):
        raise NotImplementedError("Internal LLM provider not yet configured")
```

---

## Module 9: Report Generator (`generation/report_generator.py`, `generation/report_template.py`)

### Purpose
Orchestrate multi-section report generation by running targeted retrieval + LLM extraction for each report section.

### Interface
```python
class ReportGenerator:
    def __init__(self, retriever: HybridRetriever, llm: LLMProvider):
        ...
    
    def generate(self, document_id: str, 
                 progress_callback: Callable = None) -> Report

@dataclass
class Report:
    title: str
    document_name: str
    generated_at: datetime
    sections: list[ReportSection]
    
    def to_markdown(self) -> str
    def to_pdf(self, output_path: str) -> None

@dataclass
class ReportSection:
    title: str
    content: str               # Markdown-formatted content
    sources: list[str]          # Article/section references cited
    confidence: str             # HIGH / MEDIUM / LOW
    status: str                 # "complete", "partial", "not_found"
```

### Logic
For each section in the report template:
1. Run 1-3 retrieval queries (defined in template) with section-type filtering
2. Assemble context from retrieved chunks + injected definitions
3. Send structured extraction prompt to LLM
4. Parse LLM response into `ReportSection`
5. Run validation: check extracted numbers against source chunk text
6. Call `progress_callback` to update UI
7. Assemble all sections into `Report`

See `docs/REPORT_TEMPLATE.md` for the full template specification.

---

## Module 10: Q&A Engine (`generation/qa_engine.py`)

### Purpose
Handle conversational question-answering with source citations and confidence ratings.

### Interface
```python
class QAEngine:
    def __init__(self, retriever: HybridRetriever, llm: LLMProvider):
        self.conversation_history: list[dict] = []
    
    def ask(self, question: str, document_id: str) -> QAResponse
    def clear_history(self) -> None

@dataclass
class QAResponse:
    answer: str
    sources: list[SourceCitation]
    confidence: str            # HIGH / MEDIUM / LOW
    retrieved_chunks: list[RetrievedChunk]  # For debugging/transparency

@dataclass
class SourceCitation:
    section_id: str
    section_title: str
    page_numbers: list[int]
    relevant_text_snippet: str  # Brief excerpt from source
```

### Logic
1. Take user question + last N conversation turns (configurable, default 3)
2. Formulate retrieval query (may augment with context from conversation history)
3. Run hybrid retrieval (no section filter — Q&A is open-ended)
4. Build prompt: system prompt + retrieved context + definitions + conversation history + question
5. Call LLM
6. Parse response to extract answer, citations, confidence
7. Append Q&A pair to conversation history
8. Return `QAResponse`

### System Prompt for Q&A
See `docs/PROMPTS.md` for the full prompt.

Key instructions:
- Answer based ONLY on provided context
- Cite Article/Section numbers for every claim
- If information is not in context, say "I could not find this in the provided sections of the agreement"
- Never supplement with general credit agreement knowledge
- For numerical values, quote exact language
- Rate confidence: HIGH (explicitly stated), MEDIUM (requires interpretation), LOW (uncertain/incomplete)

---

## Module 11: Streamlit UI (`ui/`)

### Upload Page (`ui/upload_page.py`)
- File uploader widget (PDF only)
- Processing progress bar with stage labels:
  - "Extracting text from PDF..." (with page counter)
  - "Detecting document structure..."
  - "Parsing definitions..."
  - "Creating search index..."
  - "Ready!"
- Display document metadata after processing: page count, sections detected, defined terms found
- Option to view detected sections (expandable list) for quick verification

### Report Page (`ui/report_page.py`)
- "Generate Report" button
- Progress indicator showing which section is being generated
- Sections displayed as they complete (streaming UX)
- Each section has:
  - Section title
  - Content (markdown rendered)
  - Collapsible "Sources" showing article/section references
  - Confidence badge (color-coded: green/yellow/red)
  - "Regenerate Section" button
- Export button: download as markdown or PDF
- Status indicator for sections where data was not found ("Not identified in this agreement")

### Chat Page (`ui/chat_page.py`)
- Standard chat interface (st.chat_message)
- User input at bottom
- Each assistant response shows:
  - Answer text
  - Source citations in a collapsible section
  - Confidence badge
- "Clear conversation" button
- Suggested starter questions (e.g., "What is the total revolver commitment?", "Describe the restricted payments basket", "What are the financial covenant test levels?")

---

## Module 12: Validation (`utils/validation.py`)

### Purpose
Cross-check extracted values against source text to catch hallucinations.

### Interface
```python
class Validator:
    def validate_numbers(self, extracted_text: str, source_chunks: list[Chunk]) -> list[ValidationIssue]
    def validate_section_references(self, extracted_text: str, source_chunks: list[Chunk]) -> list[ValidationIssue]

@dataclass
class ValidationIssue:
    issue_type: str            # "number_not_in_source", "section_ref_not_found"
    extracted_value: str       # What the model said
    context: str               # Surrounding text from model output
    severity: str              # "warning", "error"
```

### Logic
**Number validation:**
1. Extract all numbers/dollar amounts from LLM output using regex (matches like $50,000,000, 4.50x, 50%, etc.)
2. For each extracted number, search for it (or common formatting variants) in the source chunk text
3. If not found in any source chunk, flag as `ValidationIssue`

**Section reference validation:**
1. Extract all section references from LLM output (e.g., "Section 7.06", "Article VII")
2. Verify they exist in the document's section index
3. Flag any references to sections that don't exist

### Usage
- Run after each LLM extraction in report generation
- Append validation warnings to the report section (shown in UI as yellow flags)
- For Q&A, include validation issues in the response metadata
