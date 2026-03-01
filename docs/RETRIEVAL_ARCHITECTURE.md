# Retrieval Architecture: Original Plan vs Current State

## Document Processing (Phase 1 - unchanged)

The processing pipeline converts a raw PDF into retrieval-ready chunks:

```
PDF (289 pages)
  -> PDFExtractor: page-by-page text + table extraction
  -> SectionDetector: 157 sections with article/section structure + preamble
  -> DefinitionsParser: 391 defined terms from Article I
  -> Chunker: 705 chunks
```

### Chunking Strategy

Three chunk types, each handled differently:

**Definition chunks** (chunk_type="definition"):
Each defined term with >= 50 tokens gets its own chunk. Smaller definitions
are grouped together (3-5 per chunk) to avoid fragmentation. The Applicable
Margin definition, for example, produces a single 750-token chunk containing
the full pricing grid. Each definition chunk records which terms it contains
in `defined_terms_present`.

**Table chunks** (chunk_type="table"):
Each table detected by pdfplumber becomes its own chunk, converted to
markdown pipe format. The Section 7.1 covenant ratio table is 144 tokens.
These are small but contain critical structured data.

**Text chunks** (chunk_type="text"):
Regular section text. Target is 600 tokens, max 800, with 100-token overlap
at paragraph boundaries. A section like 7.1 Financial Condition Covenants
(~900 tokens of text) splits into 2-3 text chunks plus its table chunk.

All chunks carry metadata: section_id, section_title, article info,
section_type classification, page numbers (estimated from character offset),
and a chunk_index tracking position within the section.

### What Changed from the Original Plan

- **Preamble parsing added**: The section detector now captures everything
  before Article I as a "preamble" section (borrower name, facility sizes,
  dates, agent). Originally this was completely dropped.
- **build_search_text()**: Chunks are embedded/indexed with a prepended
  header like `[Section 2.15: Interest Rates and Payment Dates]` so the
  embedding model and BM25 associate chunks with their structural context.
  The raw `chunk.text` is still used in the LLM prompt (no redundant headers).
- **BamSEC/SEC noise stripping**: PDF extraction artifacts from BamSEC
  (page headers, filing metadata) are stripped from definitions.


## Indexing (Phase 3)

Each chunk is indexed in two parallel systems:

**Vector store (ChromaDB)**:
`build_search_text(chunk)` is embedded with BAAI/bge-small-en-v1.5 (384-dim).
Stored in ChromaDB with metadata for filtering. Embedding the 705 chunks
takes ~24 seconds on your hardware.

**BM25 store (rank-bm25)**:
Same `build_search_text(chunk)` is tokenized (lowercase + strip punctuation)
and indexed with BM25Plus. In-memory, rebuilt per document. Catches exact
matches on dollar amounts, ratios, and legal terms that embeddings miss.


## Retrieval Pipeline (Phase 3+4 - heavily modified)

When a user asks a question, the retrieval pipeline has 6 stages. This is
where most of the Phase 4 changes happened.

### Stage 0: Query Reformulation (if multi-turn)

If conversation history exists, the QA engine sends the last 3 turns + the
new question to Claude with a reformulation prompt. "What is the interest
rate on it?" becomes "What is the interest rate on the term loan facility?"
This standalone query is used for retrieval; the original question goes to
the final LLM prompt.

### Stage 1: Dual Search

The query runs against both indexes simultaneously:

- **Vector search**: embed query -> cosine similarity -> top 30 results
- **BM25 search**: tokenize query -> BM25Plus scoring -> top 30 results

(fetch_k = top_k * 2 = 30 to give the merge step enough candidates)

### Stage 2: Score Merge + Dedup

Scores from each system are min-max normalized to [0,1], then combined:

```
combined = 0.6 * vector_score + 0.4 * bm25_score
```

Chunks found by both systems get both weights added ("both" source label).
Deduplicated by chunk_id. Sorted descending, top 15 selected.

**Original plan**: top_k=5, only 5 chunks. Changed to 15 because Claude
can handle far more context and 5 chunks was severely context-starved.

### Stage 3: Sibling Expansion (NEW - not in original plan)

For each non-definition chunk in the top 15, check if its section has
other chunks that weren't retrieved. Pull in missing siblings up to 800
tokens per section.

This solves the "split section" problem: Section 7.1 has 4 chunks (table +
3 text), and query phrasing might only retrieve 1-2 of them. Sibling
expansion ensures that if ANY chunk from 7.1 is retrieved, the table chunk
and adjacent text come along.

Siblings score at 90% of the parent chunk to sort below direct matches.
If the result set is already at capacity (15), siblings replace the
lowest-scoring chunks from OTHER sections (never evicts same-section chunks).

### Stage 4: Definition Injection + Promotion (heavily modified)

This is the most complex stage. Three passes:

**Pass 1 - Term Discovery + Scoring:**
Scan all retrieved chunks for defined terms using whole-word regex matching.
Also check if the query itself contains any defined terms. Score each term:

```
base_score = count of chunks mentioning the term
if term in query:     score += 100  (massive boost)
if term is ubiquitous: score -= 50  (penalize boilerplate)
if term is long + has chunk + not ubiquitous + mentioned in chunks:
                      score += 15   (promotion boost)
```

**Ubiquity detection** is corpus-level: compute what fraction of all 705
chunks mention each term. Terms in >25% of chunks are "ubiquitous"
(currently: Administrative Agent, Loan, Agreement, Communications, Borrower).
This replaced the original hardcoded stoplist and adapts to each agreement.

**Promotion boost** (+15) is new. Without it, long definitions like
Applicable Margin (3326 chars, score=1.0 from a single mention) would rank
29th and get cut off by the top-18 budget. The boost ensures definitions
that NEED full-chunk promotion outrank short definitions that survive
truncation fine.

Top 18 terms by score become "primary terms."

**Original plan**: MAX_DEFINITIONS_INJECTED=5, no scoring, no promotion.
Changed to 18 with multi-factor scoring and promotion.

**Pass 2 - Recursive Expansion:**
For each primary definition's text, scan for additional defined terms not
already in the primary set. Add the most-referenced expansion terms to fill
remaining slots (up to 18 total). This handles chains like "Interest Rate"
-> section mentions "Applicable Margin" -> AM definition mentions "SOFR" ->
SOFR definition gets pulled in.

**Original plan**: No recursive expansion.

**Pass 3 - Promote or Inject:**
For each term in the combined primary + expansion set:

- **If definition > 800 chars AND has a dedicated chunk AND not ubiquitous**:
  PROMOTE the full definition chunk into the result set. This preserves
  pricing grids, ratio tables, and other structured content that would be
  destroyed by truncation. Promoted chunks score at 95% of the median
  retrieved chunk score. If at capacity, they replace the lowest-scoring
  non-promoted chunk.

- **Otherwise**: INJECT the definition as truncated text (up to 800 chars,
  cut at sentence boundary) in the definitions section of the prompt.


## Context Assembly (Phase 4)

The QA engine assembles the final LLM prompt from all the retrieval outputs:

### System Prompt (~400 tokens)
Fixed prompt instructing Claude to act as a leveraged finance analyst.
Rules: only use provided context, cite sections, state numbers exactly,
plain text formatting (no markdown bold/headers). Confidence rating at end.

### User Prompt Structure

```
=== CONTEXT FROM CREDIT AGREEMENT ===

--- Source: Preamble and Recitals (Pages 1-2) ---
[full preamble text - always injected, ~200-400 tokens]
[contains: borrower name, facility sizes, agent, date]

--- Source: Interest Rates and Payment Dates (Section 2.15, Pages 68) ---
[chunk text, up to 1500 chars unless promoted definition]
...
[up to 15 chunks, each with section/page attribution]

=== RELEVANT DEFINITIONS ===
"SOFR" means [truncated to 800 chars]
"ABR Loans" means [full text if under 800 chars]
...
[up to 18 definitions, deduped against chunk text]

=== PREVIOUS Q&A IN THIS SESSION ===
User: [previous question]
Assistant: [previous answer]
[up to 3 turns]

=== CURRENT QUESTION ===
[the actual question]
```

### Truncation Rules

- **Regular chunks**: capped at 1500 chars (~400 tokens)
- **Promoted definition chunks**: NO truncation (the whole point of promotion)
- **Injected definitions**: capped at 800 chars (~200 tokens), cut at sentence boundary
- **Definitions already in a retrieved chunk**: automatically skipped (first 80 chars
  checked against concatenated chunk text)

### Token Budget (approximate worst case)

```
System prompt:                    ~400 tokens
Preamble:                         ~300 tokens
15 chunks * ~400 tokens avg:    ~6,000 tokens
Promoted def chunks (2-3):      ~2,000 tokens  (no truncation)
18 injected definitions:        ~3,000 tokens
3 history turns:                ~1,500 tokens
Question:                          ~50 tokens
                                -----------
Total context:                 ~13,250 tokens
Max generation:                 1,024 tokens
                                -----------
Grand total:                   ~14,274 tokens
```


## What Changed: Summary

| Parameter / Feature            | Original Plan    | Current State     |
|-------------------------------|------------------|-------------------|
| LLM                           | Ollama llama3:8b | Claude Sonnet     |
| Max context chunks            | 5                | 15                |
| Max definitions injected      | 5                | 18                |
| Definition truncation limit   | 300 chars        | 800 chars         |
| Chunk text truncation         | none             | 1500 chars        |
| Preamble injection            | not planned      | always injected   |
| Definitions in retrieval      | excluded         | included          |
| Definition promotion          | not planned      | long defs -> full chunks |
| Recursive def expansion       | not planned      | 2-pass expansion  |
| Ubiquity detection            | hardcoded list   | corpus-level TF   |
| Long def score boost          | not planned      | +15 for promotable defs |
| Sibling chunk expansion       | not planned      | 800 tokens/section |
| Query reformulation           | not planned      | LLM-based for multi-turn |
| Section type boosting         | added then removed| removed (band-aid) |
| build_search_text()           | not planned      | section title prepended |
| BamSEC noise stripping        | not planned      | regex cleanup     |
| Markdown stripping            | not planned      | post-process LLM output |
| System prompt                 | basic            | analyst-style, plain text |
