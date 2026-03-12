# Retrieval Architecture

Current retrieval behavior implemented in:

- [hybrid_retriever.py](../credit_analyzer/retrieval/hybrid_retriever.py)
- [vector_store.py](../credit_analyzer/retrieval/vector_store.py)
- [bm25_store.py](../credit_analyzer/retrieval/bm25_store.py)
- [reranker.py](../credit_analyzer/retrieval/reranker.py)
- [quality_gate.py](../credit_analyzer/retrieval/quality_gate.py)

Knowledge layer modules:

- [registry.py](../credit_analyzer/knowledge/registry.py)
- [concepts.yaml](../credit_analyzer/knowledge/concepts.yaml)
- [synonyms.yaml](../credit_analyzer/knowledge/synonyms.yaml)
- [query_expansion.py](../credit_analyzer/generation/query_expansion.py)
- [query_decomposer.py](../credit_analyzer/generation/query_decomposer.py)

## End-to-End Flow

```
User Question
  |
  v
1. Knowledge Layer (deterministic)
   - Concept alias matching (J.Crew -> IP transfer provisions)
   - Synonym expansion (revolver -> revolving credit facility)
   - Generates additional retrieval queries from concept search terms
  |
  v
2. Dual Retrieval (vector + BM25) per query
  |
  v
3. RRF Fusion
  |
  v
4. Optional Cross-Encoder Reranking
  |
  v
5. Score Thresholding
  |
  v
6. Quality Gate (conditional)
   - Checks: top score, mean top-3, query term overlap
   - If INSUFFICIENT + concepts matched -> LLM Query Decomposition
   - Decomposed sub-queries run through stages 2-5 again
  |
  v
7. Sibling Expansion
  |
  v
8. Definition Injection/Promotion
  |
  v
Retrieved Context -> LLM Generation
```

## Stage Details

### 1) Knowledge Layer

Three deterministic preprocessing steps before retrieval:

**Concept Matching** — The `DomainRegistry` scans the query for aliases of ~20 leveraged finance concepts (e.g., "J.Crew provisions", "trap-door", "Serta"). Each matched concept provides:
- `search_terms`: phrases the document actually uses (e.g., "intellectual property", "unrestricted subsidiary")
- `description`: domain context injected into the LLM prompt
- `sections`: section types likely to contain the concept

**Synonym Expansion** — Maps jargon variants to canonical terms (e.g., "revolver" -> "Revolving Credit Facility", "leverage ratio" -> "Total Net Leverage Ratio"). All terms from a matched synonym group that aren't already in the query are added as retrieval queries.

**Query Expansion** — Combines concept search terms and synonym expansions into additional retrieval queries. Capped at 5 queries when concepts match, 3 otherwise.

### 2) Dual Retrieval

- Vector: query embedding -> ChromaDB similarity search
- BM25: tokenized query -> BM25Plus ranking
- Section include/exclude filters are supported in both paths.

### 3) Fusion

- Uses RRF with `RRF_K`.
- Uses rank positions from each source, not raw score normalization.
- Source attribution is tracked (`vector`, `bm25`, `both`).

### 4) Reranking

- Optional cross-encoder reranker rescoring over-fetched candidates.
- Controlled by `RERANK_CANDIDATES_MULTIPLIER` and `RERANKER_MODEL`.

### 5) Thresholding

- Chunks below `MIN_RETRIEVAL_SCORE` are dropped.
- A floor of chunks is retained to avoid empty context on hard queries.

### 6) Quality Gate

After initial retrieval, a quality check determines if results are good enough:

- **Top score threshold** (>= 0.35): Is the best chunk relevance above minimum?
- **Mean top-3 threshold** (>= 0.25): Are the top results collectively relevant?
- **Query term overlap** (>= 0.3): Do retrieved chunks contain the words the user asked about?

If the gate returns `INSUFFICIENT` and domain concepts were matched, the system escalates to LLM query decomposition. The decomposer breaks the original question into 2-5 targeted sub-queries using the concept's domain context, then runs each sub-query through retrieval stages 2-5. Results are merged via round-robin interleaving.

This handles the core "vocabulary mismatch" problem: the user says "J.Crew provisions" but the document says "transfer of intellectual property to unrestricted subsidiaries."

### 7) Sibling Expansion

- Pulls adjacent chunks from the same section.
- Budgeted by `SIBLING_EXPANSION_MAX_TOKENS`.
- Query-term overlap filter prevents unrelated sibling noise.

### 8) Definition Injection and Promotion

- Terms are discovered from retrieved chunk text and metadata.
- Scoring uses query matches, term frequency, metadata boosts, ubiquity penalties.
- `DEFINITION_UBIQUITY_THRESHOLD` suppresses boilerplate terms.
- Short definitions are injected as text (truncated to `QA_DEFINITION_MAX_CHARS`).
- Long definitions can be promoted as full chunks when available.
- `MAX_DEFINITIONS_INJECTED` controls the primary injection budget.

## Multi-Query Merge

Q&A and report sections can run multiple retrieval queries and merge via round-robin interleaving to preserve query diversity:

- `merge_multi_query_results(...)`
- deduplicates by chunk id
- merges definition maps across query results

## Notes

- Chunk metadata is persisted in Chroma using primitive metadata fields.
- Metadata list serialization uses `|` separator to avoid comma ambiguity in legal text.
- The knowledge layer is fully deterministic (no LLM calls) except for query decomposition, which is conditional and only fires when retrieval quality is insufficient for concept-level queries.
