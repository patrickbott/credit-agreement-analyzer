# Build Order & Implementation Guide

Step-by-step implementation plan with testing checkpoints.

---

## Prerequisites

Before starting, ensure the following are installed and working:

1. **Python 3.11+** — verify with `python --version`
2. **Anthropic API key** — set `ANTHROPIC_API_KEY` in `.env` (copy `.env.example`)
3. **Ollama** (optional — for local inference without an API key):
   ```bash
   ollama pull llama3.2:3b
   ```
   Set `LLM_PROVIDER=ollama` in `.env` if using this path.
4. **Tesseract OCR** (optional — only needed for scanned PDFs):
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki; set `TESSERACT_CMD` in `.env`
   - macOS: `brew install tesseract`
   - Verify with `tesseract --version`

---

## Phase 1: Project Setup & PDF Processing

### Step 1.1: Initialize project
```bash
mkdir credit_analyzer
cd credit_analyzer
python -m venv venv
venv\Scripts\activate          # Windows
pip install pymupdf pdfplumber pytesseract tiktoken
```

Create the directory structure:
```
credit_analyzer/
├── config.py
├── processing/
│   ├── __init__.py
│   ├── pdf_extractor.py
│   ├── section_detector.py
│   ├── chunker.py
│   └── definitions.py
└── utils/
    ├── __init__.py
    └── text_cleaning.py
```

### Step 1.2: Build pdf_extractor.py
- Implement `PDFExtractor.extract()` 
- Handle digital text extraction (PyMuPDF) and table extraction (pdfplumber)
- Add OCR fallback path

**TEST CHECKPOINT 1.2:**
```python
extractor = PDFExtractor()
doc = extractor.extract("path/to/test_credit_agreement.pdf")
print(f"Pages: {doc.total_pages}")
print(f"Method: {doc.extraction_method}")
print(f"Sample text (page 1): {doc.pages[0].text[:500]}")
print(f"Tables found on page 10: {len(doc.pages[9].tables)}")
```
✅ Text is readable and complete
✅ Tables are captured as markdown
✅ Page numbers are correct

### Step 1.3: Build section_detector.py
- Implement regex patterns for article and section detection
- Implement section type classification
- Handle fallback for unusual formatting

**TEST CHECKPOINT 1.3:**
```python
detector = SectionDetector()
sections = detector.detect_sections(doc)
for s in sections:
    print(f"{s.section_id} | {s.section_title} | type={s.section_type} | pages {s.page_start}-{s.page_end}")
```
✅ Major articles detected (Definitions, Negative Covenants, etc.)
✅ Section types correctly classified
✅ Coverage: most of the document is assigned to a section

### Step 1.4: Build definitions.py
- Parse Article 1 defined terms
- Build lookup dictionary
- Implement `find_terms_in_text()`

**TEST CHECKPOINT 1.4:**
```python
defn_section = [s for s in sections if s.section_type == "definitions"][0]
parser = DefinitionsParser()
defn_index = parser.parse(defn_section)
print(f"Defined terms found: {len(defn_index.definitions)}")
print(f"Sample: 'Available Amount' = {defn_index.lookup('Available Amount')[:200]}")

# Test term detection
test_text = "The Borrower may make Restricted Payments not to exceed the Available Amount"
found_terms = defn_index.find_terms_in_text(test_text)
print(f"Terms found in sample: {found_terms}")
```
✅ 100+ defined terms extracted (typical for a credit agreement)
✅ Definitions are complete (not truncated)
✅ Term detection finds capitalized defined terms in text

### Step 1.5: Build chunker.py
- Implement section-aware chunking
- Handle definitions, tables, and regular text differently
- Enrich chunks with metadata

**TEST CHECKPOINT 1.5:**
```python
chunker = Chunker()
chunks = chunker.chunk_document(sections, defn_index)
print(f"Total chunks: {len(chunks)}")
print(f"Chunk types: {Counter(c.chunk_type for c in chunks)}")
print(f"Section types: {Counter(c.section_type for c in chunks)}")
print(f"Avg token count: {sum(c.token_count for c in chunks) / len(chunks):.0f}")
print(f"Max token count: {max(c.token_count for c in chunks)}")

# Inspect a negative covenant chunk
nc_chunk = [c for c in chunks if c.section_type == "negative_covenants"][0]
print(f"\nSample chunk: {nc_chunk.section_title}")
print(f"Defined terms: {nc_chunk.defined_terms_present}")
print(f"Text: {nc_chunk.text[:300]}")
```
✅ Chunks are within token limits
✅ Metadata is populated correctly
✅ Defined terms are detected in chunks
✅ No chunks are empty or corrupted

---

## Phase 2: LLM Provider Layer

### Step 2.1: Install dependencies
```bash
pip install anthropic ollama
```

### Step 2.2: Build LLM provider
- Create abstract `LLMProvider` base class
- Implement `ClaudeProvider` (primary) and `OllamaProvider` (local alternative)
- Create stub `InternalLLMProvider`
- Add config-driven provider factory (`llm/factory.py`)

**TEST CHECKPOINT 2.2:**
```python
from credit_analyzer.llm.factory import get_provider
provider = get_provider()  # Returns ClaudeProvider or OllamaProvider per config
print(f"Provider: {provider.model_name()}")
print(f"Available: {provider.is_available()}")

response = provider.complete(
    system_prompt="You are extracting information from a document.",
    user_prompt="Given this text: 'The Revolving Commitment is $50,000,000.' Extract: Facility type and amount.",
    temperature=0.0
)
print(f"Response: {response.text}")
print(f"Duration: {response.duration_seconds:.1f}s")
```
✅ Provider responds successfully
✅ Response is structured and follows instructions
✅ Duration is reasonable

---

## Phase 3: Retrieval Layer

### Step 3.1: Install dependencies
```bash
pip install chromadb sentence-transformers rank-bm25
```

### Step 3.2: Build embedder.py and vector_store.py
- Sentence transformer embedding wrapper
- ChromaDB wrapper with collection management and filtered search

**TEST CHECKPOINT 3.2:**
```python
embedder = Embedder()
store = VectorStore()

# Embed and store chunks from Phase 1
embeddings = embedder.embed([c.text for c in chunks])
store.create_collection("test_agreement")
store.add_chunks("test_agreement", chunks, embeddings)

# Test search
query_emb = embedder.embed_query("What is the restricted payments basket?")
results = store.search("test_agreement", query_emb, top_k=5)
for r in results:
    print(f"Score: {r.score:.3f} | {r.chunk.section_title} (Section {r.chunk.section_id})")
```
✅ Embeddings generated without errors
✅ Storage and retrieval works
✅ Results are relevant to the query
✅ Section filtering works

### Step 3.3: Build bm25_store.py
- BM25 index construction and search
- Section-filtered search support

### Step 3.4: Build hybrid_retriever.py
- Score normalization and merging
- Deduplication
- Definition injection

**TEST CHECKPOINT 3.4:**
```python
retriever = HybridRetriever(store, bm25, embedder, defn_index)
result = retriever.retrieve(
    query="How much incremental debt can the borrower incur?",
    document_id="test_agreement",
    top_k=5
)
for chunk in result.chunks:
    print(f"Score: {chunk.score:.3f} | Source: {chunk.source} | {chunk.chunk.section_title}")
print(f"\nInjected definitions: {list(result.injected_definitions.keys())}")
```
✅ Results combine vector and BM25 (see `source` field)
✅ Definitions are auto-injected
✅ Results are more relevant than vector-only or BM25-only

---

## Phase 4: Q&A Engine

### Step 4.1: Build qa_engine.py
- Question handling with retrieval
- Context assembly
- Conversation history management
- Response parsing (answer + citations + confidence)

**TEST CHECKPOINT 4.1:**
```python
qa = QAEngine(retriever, provider)

# Test basic question
response = qa.ask("What is the total revolving commitment amount?", "test_agreement")
print(f"Answer: {response.answer}")
print(f"Confidence: {response.confidence}")
print(f"Sources: {[(s.section_id, s.section_title) for s in response.sources]}")

# Test follow-up
response2 = qa.ask("What about the term loan?", "test_agreement")
print(f"\nFollow-up answer: {response2.answer}")
```
✅ Answers are accurate (verify against manual review)
✅ Citations are present and correct
✅ Confidence ratings make sense
✅ Follow-up questions work with conversation context
✅ "I don't know" responses work for questions not in document

### Step 4.2: Build basic Streamlit chat UI
```bash
pip install streamlit
```
- Upload page (minimal — just file upload + processing)
- Chat page with source citations

**TEST CHECKPOINT 4.2:**
```bash
streamlit run app.py
```
✅ Can upload a PDF and see processing progress
✅ Can ask questions and get answers
✅ Source citations display correctly
✅ Conversation flows naturally

---

## Phase 5: Report Generator

### Step 5.1: Build report_template.py
- Define report sections with retrieval queries and extraction prompts
- Reference prompts from REPORT_TEMPLATE.md

### Step 5.2: Build report_generator.py
- Orchestration loop: iterate sections, retrieve, extract, assemble
- Progress callback for UI
- Markdown assembly

**TEST CHECKPOINT 5.2:**
```python
generator = ReportGenerator(retriever, provider)
report = generator.generate("test_agreement", progress_callback=print)

print(f"Sections generated: {len(report.sections)}")
for s in report.sections:
    print(f"  {s.title}: {s.status} ({s.confidence})")
    print(f"  Sources: {s.sources}")

# Save and review
with open("test_report.md", "w") as f:
    f.write(report.to_markdown())
```
✅ All 10 sections generated
✅ Extracted data matches manual review
✅ NOT FOUND used appropriately (not hallucinated)
✅ Citations present throughout
✅ Total length reasonable (~7-10 pages)
✅ Generation completes in < 15 minutes

### Step 5.3: Add report UI page
- Generate button with progress indicator
- Section-by-section rendering
- Export functionality (PDF via fpdf2)

---

## Phase 6: Polish & Hardening

### Step 6.1: Error handling
- LLM provider unavailable → clear error message at startup via `validate_config()`
- Bad PDF → graceful failure with specific error
- LLM transient failure → automatic retry (built into `ClaudeProvider` and `OllamaProvider`)
- Empty retrieval results → inform user, suggest alternative query

### Step 6.2: Validation layer (not built in V1)
- Planned: number and section-reference cross-checking (`utils/validation.py`)
- Current: confidence ratings and source citations are the primary uncertainty signal

### Step 6.3: UI polish
- Suggested starter questions in chat
- Help text / onboarding for new users
- Clean loading states
- Error messages that non-technical users can understand
- Document management (list processed docs, delete old ones)

### Step 6.4: User documentation
- README with install instructions
- Quick start guide for analysts
- Troubleshooting common issues

### Step 6.5: Testing with multiple agreements
- Test with at least 3-5 different credit agreements
- Compare extracted data against manual review
- Tune prompts based on failure patterns
- Adjust chunking and retrieval parameters

---

## Estimated Timeline

| Phase | Effort | Cumulative |
|---|---|---|
| Phase 1: PDF Processing | 3-5 days | 3-5 days |
| Phase 2: LLM Provider | 1 day | 4-6 days |
| Phase 3: Retrieval | 2-3 days | 6-9 days |
| Phase 4: Q&A + Basic UI | 2-3 days | 8-12 days |
| Phase 5: Report Generator | 3-4 days | 11-16 days |
| Phase 6: Polish | 3-5 days | 14-21 days |

This assumes working on it part-time alongside normal work. Full-time focus could compress significantly.

The biggest variable is **prompt tuning** — how quickly you get the extraction prompts working well against real credit agreements. Budget extra time for this in Phases 4 and 5.
