# Comprehensive Codebase Audit & Improvement Prompt

> **Usage:** Paste this entire prompt into a fresh Claude Code session from the project root. Run in `auto` or `bypassPermissions` mode for uninterrupted execution.

---

## System Context

You are performing a comprehensive audit and improvement of the `credit-analyzer` project — a Python/Streamlit application that ingests credit agreement PDFs, processes them through a RAG pipeline (extraction → section detection → chunking → embedding → hybrid retrieval), and provides LLM-powered Q&A and 10-section report generation.

**Tech stack:** Python 3.11, Streamlit, ChromaDB, sentence-transformers, rank-bm25, Anthropic SDK, Ollama, fpdf2, PyMuPDF, pdfplumber, pytesseract, tiktoken.

**Package structure:**
```
app.py                          # Streamlit entry point
credit_analyzer/
  processing/                   # PDF extraction, section detection, chunking, definitions
  retrieval/                    # Vector store, BM25, hybrid retriever, reranker, fusion
  generation/                   # QA engine, report generator, prompts, citations, PDF export
  llm/                          # Provider abstraction (Claude, Ollama, Internal)
  ui/                           # Chat, sidebar, dialogs, theme, workflows
  utils/                        # Text cleaning
  config.py                     # Central configuration
tests/                          # pytest suite
docs/                           # CONFIG_REFERENCE.md, RETRIEVAL_ARCHITECTURE.md
```

**Key behaviors to preserve:**
- Report extraction uses strict omission for missing fields (no "NOT FOUND" fill-ins except fully empty section fallback)
- Imports are lazy-loaded in package `__init__.py` to avoid heavy dependency failures
- Pyright is set to `strict` mode
- Ruff linting with rules: E, F, W, I, UP, B, SIM

---

## Phase 1: Research & Audit

Deploy a team of parallel research agents to investigate the codebase. Each agent focuses on a specific audit domain. **Do not make any code changes in this phase — research only.**

### Agent Team 1: Codebase Analysis (run all in parallel)

**Agent 1 — Bug & Logic Errors:**
- Read every Python file in `credit_analyzer/` and `app.py`
- Look for: off-by-one errors, incorrect conditional logic, swallowed exceptions, race conditions in Streamlit session state, incorrect type narrowing, unhandled edge cases (empty PDFs, zero chunks, missing API keys, network failures)
- Check that all error paths produce meaningful user feedback, not silent failures
- Verify that retrieval score normalization and RRF fusion math is correct
- Check for any mismatch between function signatures and their call sites
- Flag any `type: ignore` comments that may be masking real issues
- Report: list each bug with file, line, description, and severity (critical/high/medium/low)

**Agent 2 — Dead Code & Stale Artifacts:**
- Identify Python functions, classes, methods, constants, and imports that are never referenced
- Check for stale git branches (there are 17+ branches, many likely merged or abandoned): list each with last commit date and whether it's been merged into master or the current branch
- Check `.claude/worktrees/` — there are 3 leftover worktree directories (angry-jang, keen-oak-6jqy, swift-owl-r2ao) that should likely be cleaned up
- Check if docs that were removed from `docs/` (BUILD_ORDER.md, MODULE_SPECS.md, PROJECT_PLAN.md, PROMPTS.md, REPORT_TEMPLATE.md) are still referenced anywhere or if their removal was complete
- Look for any config keys in `config.py` that are defined but never read
- Check if `credit_analyzer.egg-info/` should be gitignored
- Look for commented-out code blocks
- Report: list each item with location and recommendation (delete/archive/update)

**Agent 3 — Code Quality & Efficiency:**
- Review each module for: unnecessary allocations, redundant computations, O(n²) patterns where O(n) is possible, repeated string concatenation in loops, inefficient list/dict operations
- Check embedding and retrieval hot paths for performance — are embeddings cached? Are there redundant re-computations?
- Look for places where generators/iterators should be used instead of materializing full lists
- Check Streamlit patterns: unnecessary reruns, missing `@st.cache_data` / `@st.cache_resource`, session state bloat, widget key conflicts
- Check if PDF processing could be more memory-efficient (streaming vs loading entire document)
- Review prompt construction — are prompts being rebuilt on every call when they could be templated once?
- Report: list each issue with file, line, current approach, recommended approach, and estimated impact

**Agent 4 — Async & Parallelism Opportunities:**
- Identify all I/O-bound operations: LLM API calls, embedding generation, PDF extraction, ChromaDB operations
- Map out which operations in the report generation pipeline (10 sections) could run in parallel vs must be sequential
- Check if `ask_stream` and non-streaming `ask` properly handle concurrent Streamlit sessions
- Look for places where `asyncio`, `concurrent.futures`, or batch APIs could be used (e.g., batch embedding instead of one-at-a-time)
- Check if ChromaDB batch operations are being used where possible
- Evaluate whether the processing pipeline (extract → detect → chunk → embed) could pipeline stages
- Report: list each opportunity with current flow, proposed parallel flow, expected speedup, and implementation complexity

**Agent 5 — Incomplete & Poorly Integrated Features:**
- Look for TODO/FIXME/HACK/XXX comments throughout the codebase
- Check the multi-document comparison feature — the TODO.txt mentions it needs rethinking. Analyze what's implemented, what's half-baked, and what the UX issues are
- Check the stop generation button — is it actually wired up and working?
- Check the demo_report module — is it actively used or vestigial?
- Look for feature flags or config options that exist but aren't exposed in the UI
- Check if all report sections are fully implemented or if some are stubs
- Check if the cross-encoder reranker is actually being used or just imported
- Verify that PDF export produces well-formatted output for all 10 report sections
- Review the citation system end-to-end: are citations actually accurate and clickable?
- Report: list each incomplete feature with current state, what's missing, and effort estimate

### Agent Team 2: Industry Standards Research (run in parallel with Team 1)

**Agent 6 — RAG Best Practices:**
- Research current best practices for RAG systems (2025-2026):
  - Chunking strategies (semantic chunking, late chunking, contextual retrieval)
  - Retrieval: hybrid search, reranking, query expansion/decomposition
  - Context window management and prompt optimization
  - Evaluation frameworks (RAGAS, etc.)
  - Citation and grounding techniques
- Compare against what this codebase implements
- Report: list gaps between current implementation and industry best practices, with specific recommendations

**Agent 7 — Streamlit & Python Best Practices:**
- Research current Streamlit best practices:
  - Session state management patterns
  - Performance optimization (caching, lazy loading)
  - Multi-page app architecture
  - Custom components vs CSS hacking
  - Deployment best practices
- Research Python 3.11+ best practices:
  - Modern typing patterns (TypeAlias, Self, override, etc.)
  - Dataclasses vs Pydantic for data models
  - Structured logging vs print/st.write debugging
  - Error handling patterns
- Report: list recommendations specific to this codebase

**Agent 8 — Credit Agreement Analysis Domain:**
- Research what professional credit agreement analysis tools and workflows look like
- What sections/analysis do professional analysts expect in a credit agreement review?
- Are there standard taxonomies or frameworks for classifying credit agreement provisions?
- What would make this tool more useful to actual credit analysts?
- Report: list feature and analysis gaps compared to professional-grade tools

---

## Phase 2: Consolidation & Planning

After all agents complete, synthesize their findings into a single comprehensive improvement plan.

### Consolidation Steps:

1. **Deduplicate** — Multiple agents may flag the same issue. Merge duplicates.

2. **Categorize** every finding into one of:
   - `BUG` — Incorrect behavior that needs fixing
   - `DEAD_CODE` — Remove unused code/files/branches
   - `PERFORMANCE` — Optimization opportunity
   - `ASYNC` — Parallelism/async opportunity
   - `INCOMPLETE` — Feature that needs finishing or rethinking
   - `MISSING` — Feature or capability gap
   - `QUALITY` — Code quality, patterns, modernization
   - `DOCS` — Documentation that's stale, missing, or wrong

3. **Prioritize** using this matrix:
   - **P0 (Critical):** Bugs causing incorrect results, data loss, or crashes
   - **P1 (High):** Performance bottlenecks, incomplete features that affect UX, security issues
   - **P2 (Medium):** Code quality, modernization, missing features that would add value
   - **P3 (Low):** Nice-to-haves, minor cleanup, cosmetic issues

4. **Group into work packages** — Cluster related changes that should be implemented together. Each work package should be:
   - Independently implementable (no circular dependencies between packages)
   - Testable in isolation
   - Small enough for a single agent to complete (roughly 1-5 files changed)

5. **Write the plan** to `docs/plans/YYYY-MM-DD-codebase-audit-plan.md` with this structure:

```markdown
# Codebase Audit — Improvement Plan

## Executive Summary
[2-3 paragraph overview of findings and recommended action]

## Findings by Category
### Bugs (P0-P1)
| # | File(s) | Description | Severity | Work Package |
### Dead Code & Stale Artifacts
| # | Item | Location | Action | Work Package |
### Performance
| # | File(s) | Current | Proposed | Impact | Work Package |
### Async/Parallelism
| # | File(s) | Current | Proposed | Speedup | Work Package |
### Incomplete Features
| # | Feature | Current State | What's Missing | Effort | Work Package |
### Missing Features
| # | Feature | Rationale | Effort | Work Package |
### Code Quality
| # | File(s) | Issue | Recommendation | Work Package |
### Documentation
| # | Doc | Issue | Action | Work Package |

## Work Packages (Implementation Order)
### WP-1: [Name]
- **Priority:** P0
- **Files:** [list]
- **Changes:** [description]
- **Tests:** [what to test]
- **Risk:** [low/medium/high]

### WP-2: [Name]
...
```

6. **Present the plan to me for review** — Show the executive summary and work package list. Wait for my approval before proceeding to Phase 3. I may want to skip, reorder, or modify packages.

---

## Phase 3: Implementation

After I approve the plan (or a subset of it), deploy implementation agents.

### Implementation Rules:

1. **Branch strategy:** Create a new branch `audit/codebase-improvements` from the current branch.

2. **One commit per work package.** Each commit message should reference the work package number: `audit(WP-N): description`.

3. **Run validation after each work package:**
   - `.venv/Scripts/python -m pytest tests/ -x` (tests pass)
   - `.venv/Scripts/python -m ruff check .` (lint clean)
   - `.venv/Scripts/python -m pyright` (types clean, or no new errors)

4. **Parallelism:** Use isolated worktree agents for work packages that touch completely different files. But if two packages touch the same file, they must be sequential.

5. **Preserve behavior:** Every change must preserve existing functionality unless the explicit goal is to change it. When removing dead code, verify it's truly unreferenced. When refactoring, ensure all call sites are updated.

6. **Test changes:** If a work package changes logic, add or update tests. Don't just change code and hope existing tests catch regressions.

7. **Don't over-engineer:** Follow the existing code style. Don't introduce new frameworks, abstractions, or patterns unless the plan specifically calls for it. Keep changes minimal and focused.

8. **After all work packages are complete:**
   - Run the full test suite one final time
   - Run lint and type checking
   - Show me a summary of all changes made (files changed, lines added/removed per work package)
   - Ask if I want to squash, keep granular commits, or create a PR

---

## Constraints

- **Do NOT touch** any files in `.claude/worktrees/` — those are managed separately
- **Do NOT modify** test files unless the test is wrong or you're adding new tests for changed code
- **Do NOT change** the public API of `QAEngine.ask()`, `QAEngine.ask_stream()`, or `ReportGenerator.generate()` without flagging it for approval first
- **Do NOT upgrade or add dependencies** without flagging for approval first
- **Do NOT delete git branches** without listing them for my approval first
- **Preserve** the lazy-import pattern in all `__init__.py` files
- **Preserve** the strict pyright configuration
- **Windows paths:** This runs on WSL2; the venv uses `.venv/Scripts/python` not `.venv/bin/python`

---

Begin with Phase 1. Deploy all 8 research agents in parallel, then proceed to Phase 2 consolidation when they complete.
