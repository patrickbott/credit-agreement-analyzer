# Codebase Audit -- Improvement Plan

**Date:** 2026-03-08
**Branch:** `feat/ui-overhaul`
**Audited by:** 11 research agents (8 parallel + 3 follow-up) covering bugs, dead code, quality, async, incomplete features, RAG best practices, Streamlit/Python practices, and credit agreement domain analysis.

## Executive Summary

The credit-analyzer codebase is architecturally sound: the RAG pipeline (extract -> detect -> chunk -> embed -> retrieve -> generate) is well-designed, report generation is already parallelized with ThreadPoolExecutor, hybrid retrieval with RRF fusion and cross-encoder reranking is correctly implemented, and the 10-section report template covers the core areas a credit analyst expects. The codebase has zero TODO/FIXME/HACK comments in Python source, all config keys are actively used, lazy-loading patterns in `__init__.py` files are excellent, and dataclass usage is well-designed.

The main areas for improvement fall into three categories:

1. **Bugs and correctness issues** -- A handful of real bugs: the `stream_complete` method silently drops the `temperature` parameter (affects all streaming), the stop generation button is completely non-functional (renders but does nothing), citation metadata fields are always empty strings, and broad exception suppression hides real errors. None are critical/crash-level, but the temperature bug affects generation quality.

2. **Performance bottlenecks** -- Redundant token counting during chunking and O(n*m) definition sub-term detection are the two hottest paths. Session state bloat and missing Streamlit caching add unnecessary rerun overhead. PDF extraction is sequential when it could be parallelized for 3-5x speedup on large documents.

3. **Code quality and modernization** -- Broad exception catches throughout (8 files), underutilized logging, 37 instances of `unsafe_allow_html`, 25 `st.rerun()` calls, and 2 dead exported functions in citation_building.py. The PDF export has a NOT FOUND formatting path that contradicts the strict omission rule in prompts.

**Feature completeness:** The stop button is fully broken (does NOT cancel the LLM stream -- purely cosmetic). Multi-doc comparison backend exists but UI was intentionally removed. Ollama provider lacks streaming support. Commentary mode may truncate (per TODO.txt). The demo_report module is actively used. The cross-encoder reranker is properly integrated and always active. All 10 report sections are fully implemented.

**Domain assessment:** The tool covers ~55-65% of what professional credit analysis tools provide. The 10 sections handle deal structure well but miss key risk-focused analyses: waterfall/cash sweep mechanics, guarantee/collateral details, borrowing base analysis, MAC clause deep dives, and covenant headroom arithmetic. Adding 3-4 new sections would move it significantly toward professional utility.

## Findings by Category

### Bugs (P0-P1)

| # | File(s) | Description | Severity | Work Package |
|---|---------|-------------|----------|--------------|
| B1 | `llm/claude_provider.py:85` | `stream_complete()` accepts `temperature` parameter but never passes it to `messages.stream()` -- all streaming uses default temperature | P1-High | WP-1 |
| B2 | `retrieval/hybrid_retriever.py:604` | Median calculation uses `len(scores)//2` (upper median) instead of true median for even-length lists, biasing definition promotion scores upward | P2-Medium | WP-2 |
| B3 | `ui/sidebar.py:103` | `contextlib.suppress(Exception)` on ChromaDB collection delete swallows all errors including programming bugs | P2-Medium | WP-3 |
| B4 | `generation/qa_engine.py:373,381` | Uses `__import__("time").perf_counter()` instead of normal import -- works but non-idiomatic | P3-Low | WP-3 |
| B5 | `generation/qa_engine.py:456-460` | Broad `except Exception` in query reformulation catches too much | P3-Low | WP-3 |
| B6 | `generation/citation_building.py:277-286` | Citation index bounds check is technically safe but fragile -- relies on prior validation not changing | P3-Low | WP-3 |

### Dead Code & Stale Artifacts

| # | Item | Location | Action | Work Package |
|---|------|----------|--------|--------------|
| D1 | Stale worktree branches (7) | `worktree-agent-*`, `worktree-keen-oak-*`, `worktree-swift-owl-*` (all merged into master) | Delete branches (requires approval) | WP-4 |
| D2 | Stale feature branches (6) | `claude/angry-jang`, `claude/sleepy-lalande`, `phase3_retrieval`, `refactor`, `chore/git-cleanup`, `rag-improvement` (all merged into master) | Delete branches (requires approval) | WP-4 |
| D3 | Dead function: `inline_citations_from_sources()` | `generation/citation_building.py:308` | Exported in `__all__` but never imported or called anywhere | WP-3 |
| D4 | Dead function: `enrich_inline_citations()` | `generation/citation_building.py:156` | Exported in `__all__` but never imported or called anywhere | WP-3 |
| D5 | Stale handoff doc references | `.claude/handoffs/*.md` reference removed docs (BUILD_ORDER.md, etc.) | Update or archive handoff files | WP-4 |
| D6 | Worktree directories | `.claude/worktrees/angry-jang`, `keen-oak-6jqy`, `sleepy-lalande`, `swift-owl-r2ao` | Per constraints, do NOT touch | -- |
| D7 | egg-info directory | `credit_analyzer.egg-info/` | Already in `.gitignore` -- no action needed | -- |
| D8 | Removed docs | BUILD_ORDER.md, MODULE_SPECS.md, etc. | No references in Python source -- removal was clean | -- |

### Performance

| # | File(s) | Current | Proposed | Impact | Work Package |
|---|---------|---------|----------|--------|--------------|
| P1 | `processing/chunker.py` | `_count_tokens()` called repeatedly on overlapping text during splitting (~8 call sites) | Cache token counts as text is processed; store count alongside text | High (20-30% chunking speedup) | WP-5 |
| P2 | `processing/definitions.py:98-126` | `find_terms_in_text` does O(n*m) sub-term detection: for each regex match, loops through all definitions | Pre-compute parent-child term relationships at index build time | High (for large definition sets) | WP-5 |
| P3 | `retrieval/hybrid_retriever.py:398-502` | `find_terms_in_text` called repeatedly on same chunks during definition injection | Cache term lists when chunks are first retrieved | Medium (10-20ms per query) | WP-5 |
| P4 | `generation/query_expansion.py:94-116` | `_TERM_ALIASES` dict rebuilt inside function on every call | Make module-level constant | Low | WP-5 |

### Async/Parallelism

| # | File(s) | Current | Proposed | Speedup | Work Package |
|---|---------|---------|----------|---------|--------------|
| A1 | `processing/pdf_extractor.py:97-161` | Pages extracted sequentially in a for-loop | Use ThreadPoolExecutor to extract pages in parallel (4-6 workers) | 3-5x for large PDFs | WP-6 |
| A2 | `config.py:63` | `REPORT_MAX_WORKERS=3` | Increase to 4-5 (with rate limit awareness) | ~30% faster reports | WP-6 |

Note: Report generation, multi-query retrieval, embed+BM25, and document comparison are already well-parallelized. Pipeline parallelism (overlapping extract/chunk/embed stages) is high complexity for marginal gain -- not recommended.

### Incomplete Features

| # | Feature | Current State | What's Missing | Effort | Work Package |
|---|---------|---------------|----------------|--------|--------------|
| I1 | Stop generation button | Button renders during streaming but is **purely cosmetic** -- clicking does nothing to the active stream. `streaming_active` flag is never checked during streaming loop. No cancellation mechanism in LLM providers. | Wire stop button to set cancellation flag; check flag in `ask_stream` loop; add early-exit to LLM provider streams | Medium | WP-7 |
| I2 | Citation metadata always empty | `parse_sources_from_llm()` sets `section_title=""` and `relevant_text_snippet=""` (citation_parsing.py:153) -- never enriched after retrieval | Enrich SourceCitation by looking up chunk data after parsing | Small | WP-3 |
| I3 | Commentary mode truncation | TODO.txt: "figure out why commentary gets cut off" -- likely `QA_MAX_GENERATION_TOKENS=1024` too low for answer + commentary, or `extract_answer_body()` stripping it | Investigate; probably increase max tokens when commentary enabled | Small | WP-7 |
| I4 | Ollama missing streaming | `OllamaProvider` only implements `complete()`; falls back to non-streaming (entire response appears at once) | Add `stream_complete()` using `ollama.Client.chat(stream=True)` | Small | WP-1 |
| I5 | Multi-doc comparison (UI removed) | Backend exists (`compare()` in qa_engine.py, prompts in prompts.py) but UI intentionally removed; TODO.txt says "remove / rethink" | Either restore UI or remove dead backend code | Large | -- (deferred) |
| I6 | PDF export NOT FOUND contradiction | `pdf_export.py:293-295` formats "NOT FOUND" text in italics, but `report_template.py:75-80` instructs LLM to never write "NOT FOUND" | Remove NOT FOUND formatting from PDF or keep as defensive fallback | Small | WP-3 |
| I7 | Internal LLM provider stub | `internal_provider.py` methods raise `NotImplementedError` -- will crash if `LLM_PROVIDER=internal` | Document as intentional stub; no fix needed until internal API available | -- | -- |
| I8 | No reranker toggle | Reranker always loaded on startup (~2-3s, ~300MB model); no config flag to disable | Add `ENABLE_RERANKER` config flag | Small | -- (optional) |

### Missing Features (from RAG & Domain Research)

| # | Feature | Rationale | Effort | Work Package |
|---|---------|-----------|--------|--------------|
| M1 | Lost-in-the-middle mitigation | Reorder retrieved chunks so most relevant are at start/end of context, not middle (proven 5-10% answer quality improvement) | Small | WP-8 |
| M2 | RAG evaluation suite | No quantitative metrics for retrieval quality or answer faithfulness; need 20-30 curated Q&A pairs with ground truth | Medium | -- (separate effort) |
| M3 | Citation validation | No verification that LLM citations actually reference claims in retrieved chunks | Medium | -- (separate effort) |
| M4 | Embedding model upgrade | `bge-small-en-v1.5` (384d) could be upgraded to `bge-base-en-v1.5` (768d) for ~5-10% retrieval improvement | Small (config change + reindex) | -- (requires approval) |

### Code Quality

| # | File(s) | Issue | Recommendation | Work Package |
|---|---------|-------|----------------|--------------|
| Q1 | 8 files | Broad `except Exception` catches throughout | Catch specific exceptions; create lightweight exception hierarchy | WP-3 |
| Q2 | 6 files | Logging underutilized; key operations not logged | Add logging to processing pipeline, retrieval, LLM calls | WP-9 |
| Q3 | 9 files | 37 instances of `unsafe_allow_html=True` | Audit and document which are necessary; centralize HTML generation | WP-10 |
| Q4 | 5 files | 25 `st.rerun()` calls; many could use callbacks | Reduce reruns using `on_click` callbacks and session state flags | WP-10 |
| Q5 | `app.py:122-134` | 12 flat session state keys with no schema | Group related state; add TypedDict or dataclass for state shape | WP-10 |

### Documentation

| # | Doc | Issue | Action | Work Package |
|---|-----|-------|--------|--------------|
| DC1 | TODO.txt | Contains 3 items -- should be tracked properly or resolved | Resolve items as part of this audit | WP-7 |

## Work Packages (Implementation Order)

### WP-1: Fix LLM provider bugs
- **Priority:** P1
- **Files:** `credit_analyzer/llm/claude_provider.py`, `credit_analyzer/llm/ollama_provider.py`
- **Changes:**
  - Pass `temperature` parameter to `self._client.messages.stream()` in ClaudeProvider `stream_complete()`
  - Add `stream_complete()` to OllamaProvider using `ollama.Client.chat(stream=True)`
- **Tests:** Verify streaming with non-default temperature; verify Ollama streaming works token-by-token
- **Risk:** Low -- targeted fixes in provider layer

### WP-2: Fix median calculation for definition promotion
- **Priority:** P2
- **Files:** `credit_analyzer/retrieval/hybrid_retriever.py`
- **Changes:** Replace `sorted(scores)[len(scores) // 2]` with proper median (average of two middle values for even-length lists)
- **Tests:** Add unit test for definition promotion scoring with even/odd score lists
- **Risk:** Low -- localized math fix

### WP-3: Tighten exception handling and clean up dead code
- **Priority:** P2
- **Files:** `credit_analyzer/ui/sidebar.py`, `credit_analyzer/generation/qa_engine.py`, `credit_analyzer/generation/citation_building.py`, `credit_analyzer/generation/citation_parsing.py`, `credit_analyzer/generation/pdf_export.py`
- **Changes:**
  - Replace `contextlib.suppress(Exception)` with specific exceptions in sidebar.py:103
  - Replace `__import__("time")` with proper `import time` in qa_engine.py
  - Narrow `except Exception` in qa_engine.py:456-460 to catch LLM-specific errors
  - Add defensive bounds check in citation_building.py
  - Remove dead functions `inline_citations_from_sources()` and `enrich_inline_citations()` from citation_building.py and their `__all__` entries
  - Enrich citation metadata: populate `section_title` and `relevant_text_snippet` in `parse_sources_from_llm()`
  - Remove or guard the NOT FOUND italic formatting in pdf_export.py (contradicts strict omission rule)
- **Tests:** Existing tests should pass; verify error messages surface correctly; verify citations have metadata
- **Risk:** Low -- narrowing catches and removing dead code, not changing logic

### WP-4: Clean up stale git branches
- **Priority:** P3
- **Files:** None (git operations only)
- **Changes:** Delete merged branches listed in D1 and D2 (13 branches total)
- **Tests:** N/A
- **Risk:** Low -- all confirmed merged into master
- **NOTE:** Requires explicit user approval before execution

### WP-5: Performance hotpath optimizations
- **Priority:** P1
- **Files:** `credit_analyzer/processing/chunker.py`, `credit_analyzer/processing/definitions.py`, `credit_analyzer/retrieval/hybrid_retriever.py`, `credit_analyzer/generation/query_expansion.py`
- **Changes:**
  - Cache token counts during chunking to avoid redundant `_count_tokens()` calls
  - Pre-compute parent-child term relationships in definitions index to eliminate O(n*m) sub-term scan
  - Cache `find_terms_in_text` results during hybrid retrieval to avoid scanning same chunks twice
  - Move `_TERM_ALIASES` to module-level constant
- **Tests:** Run existing tests; verify chunk counts and retrieval results unchanged
- **Risk:** Medium -- touching hot paths; need careful verification that outputs don't change

### WP-6: PDF extraction parallelism
- **Priority:** P2
- **Files:** `credit_analyzer/processing/pdf_extractor.py`, `credit_analyzer/config.py`
- **Changes:**
  - Parallelize page-by-page extraction using ThreadPoolExecutor
  - Increase `REPORT_MAX_WORKERS` default from 3 to 4
- **Tests:** Process a multi-page PDF and verify identical output to sequential extraction
- **Risk:** Medium -- need to verify PyMuPDF/pdfplumber thread safety; may need to fall back to ProcessPoolExecutor

### WP-7: Fix stop button and commentary truncation
- **Priority:** P2
- **Files:** `credit_analyzer/ui/chat.py`, `credit_analyzer/generation/qa_engine.py`
- **Changes:**
  - Wire stop button to set a cancellation flag that `ask_stream` checks between tokens
  - Investigate and fix commentary truncation (TODO.txt item 1)
  - Update TODO.txt to reflect resolved items
- **Tests:** Manual testing: start stream, click stop, verify stream stops and partial response saved
- **Risk:** Medium -- requires coordination between UI and engine layers

### WP-8: Lost-in-the-middle mitigation
- **Priority:** P2
- **Files:** `credit_analyzer/generation/prompts.py`
- **Changes:** Reorder context chunks so highest-relevance chunks appear at start and end of the context block, with lower-relevance in the middle
- **Tests:** Verify prompt construction produces reordered chunks; run Q&A and check answer quality
- **Risk:** Low -- simple reorder logic in prompt builder

### WP-9: Add structured logging
- **Priority:** P3
- **Files:** `credit_analyzer/processing/pdf_extractor.py`, `credit_analyzer/processing/chunker.py`, `credit_analyzer/retrieval/hybrid_retriever.py`, `credit_analyzer/generation/qa_engine.py`, `credit_analyzer/generation/report_generator.py`, `credit_analyzer/llm/claude_provider.py`
- **Changes:**
  - Add `logger = logging.getLogger(__name__)` to modules missing it
  - Add INFO-level logging for pipeline milestones (extraction start/end, chunk count, retrieval timing)
  - Add DEBUG-level logging for retrieval details (scores, reranking, definition injection)
  - Replace any remaining print() calls with logger
- **Tests:** Existing tests pass; verify no output pollution
- **Risk:** Low -- additive only

### WP-10: Streamlit modernization (session state, reruns, HTML cleanup)
- **Priority:** P3
- **Files:** `app.py`, `credit_analyzer/ui/chat.py`, `credit_analyzer/ui/sidebar.py`, `credit_analyzer/ui/theme_css.py`, `credit_analyzer/ui/report_pipeline.py`
- **Changes:**
  - Group session state keys into logical sub-dicts with TypedDict schema
  - Replace 5-10 highest-frequency `st.rerun()` calls with `on_click` callbacks
  - Audit `unsafe_allow_html` usage and document which are necessary
  - Add `@st.cache_data` to static functions (prompts, theme constants)
- **Tests:** Manual UI testing; verify all flows work (upload, chat, report, definitions dialog)
- **Risk:** High -- UI changes require careful testing across all user flows
