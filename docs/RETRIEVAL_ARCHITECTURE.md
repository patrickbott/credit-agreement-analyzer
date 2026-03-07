# Retrieval Architecture

Current retrieval behavior implemented in:

- [hybrid_retriever.py](../credit_analyzer/retrieval/hybrid_retriever.py)
- [vector_store.py](../credit_analyzer/retrieval/vector_store.py)
- [bm25_store.py](../credit_analyzer/retrieval/bm25_store.py)
- [reranker.py](../credit_analyzer/retrieval/reranker.py)

## End-to-End Flow

1. Build candidate sets from vector search and BM25 search.
2. Fuse candidates with Reciprocal Rank Fusion (RRF), not weighted score blending.
3. Optionally rerank with cross-encoder model.
4. Apply minimum score threshold (while keeping a small floor of chunks).
5. Expand sibling chunks from the same section within token budget.
6. Inject or promote definitions based on term relevance and length.

## Stage Details

### 1) Dual Retrieval

- Vector: query embedding -> ChromaDB similarity search
- BM25: tokenized query -> BM25Plus ranking
- Section include/exclude filters are supported in both paths.

### 2) Fusion

- Uses RRF with `RRF_K`.
- Uses rank positions from each source, not raw score normalization.
- Source attribution is tracked (`vector`, `bm25`, `both`).

### 3) Reranking

- Optional cross-encoder reranker rescoring over-fetched candidates.
- Controlled by `RERANK_CANDIDATES_MULTIPLIER` and `RERANKER_MODEL`.

### 4) Thresholding

- Chunks below `MIN_RETRIEVAL_SCORE` are dropped.
- A floor of chunks is retained to avoid empty context on hard queries.

### 5) Sibling Expansion

- Pulls adjacent chunks from the same section.
- Budgeted by `SIBLING_EXPANSION_MAX_TOKENS`.
- Query-term overlap filter prevents unrelated sibling noise.

### 6) Definition Injection and Promotion

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
