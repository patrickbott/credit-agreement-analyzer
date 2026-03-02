"""Central configuration for the credit agreement analyzer.

All runtime knobs live here. Override any value via environment variable
(see .env.example at the project root). Call ``validate_config()`` at
app startup to catch misconfiguration before it surfaces mid-pipeline.
"""

import os
from pathlib import Path

from dotenv import load_dotenv  # pyright: ignore[reportMissingTypeStubs]

load_dotenv(Path(__file__).parent.parent / ".env")

# --- Paths ---
PROJECT_ROOT: Path = Path(__file__).parent.parent
CHROMA_DATA_DIR: Path = PROJECT_ROOT / "chroma_data"

# Override via TESSERACT_CMD env var (macOS/Linux: /usr/local/bin/tesseract).
TESSERACT_CMD: str = os.environ.get(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

# --- PDF Extraction ---
# Pages with fewer extracted characters than this threshold trigger OCR fallback.
OCR_TEXT_LENGTH_THRESHOLD: int = 100

# --- Chunking ---
CHUNK_TARGET_TOKENS: int = 600
CHUNK_MAX_TOKENS: int = 800
CHUNK_OVERLAP_TOKENS: int = 100
MIN_DEFINITION_CHUNK_TOKENS: int = 50
TIKTOKEN_ENCODING: str = "cl100k_base"

# --- Retrieval ---
# Reciprocal Rank Fusion constant (standard default is 60).
RRF_K: int = 60
# Upper bound on injected definition chunks per query (primary + recursive expansion).
MAX_DEFINITIONS_INJECTED: int = 18
# Total sibling-chunk token budget added per section during context expansion.
SIBLING_EXPANSION_MAX_TOKENS: int = 800
# Minimum relevance score (after reranking) to keep a chunk. Chunks below this
# threshold are dropped even if top_k hasn't been filled. A floor of 3 chunks
# is always retained regardless of this threshold.
MIN_RETRIEVAL_SCORE: float = 0.15
# Cross-encoder reranker model for second-stage scoring.
RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Number of candidates to over-fetch from hybrid search for reranking.
RERANK_CANDIDATES_MULTIPLIER: int = 3

# --- Report Generation ---
# Maximum parallel workers for report section generation.
REPORT_MAX_WORKERS: int = 2

# --- LLM ---
LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "claude")  # claude | ollama | internal
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CLAUDE_MODEL: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
CLAUDE_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY") or None

# --- Q&A Engine ---
QA_MAX_HISTORY_TURNS: int = 3
QA_MAX_CONTEXT_CHUNKS: int = 15
QA_MAX_GENERATION_TOKENS: int = 1024
# Injected definition text is truncated to this length to control token budget (~200 tok).
QA_DEFINITION_MAX_CHARS: int = 800
QA_SECTION_TYPES_EXCLUDE: tuple[str, ...] = ("miscellaneous",)
# Terms present in more than this fraction of chunks are treated as "ubiquitous"
# and excluded from definition injection to avoid polluting context.
DEFINITION_UBIQUITY_THRESHOLD: float = 0.25

# --- Embedding ---
EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"


def validate_config() -> list[str]:
    """Check that required config values are present and internally consistent.

    Returns a list of human-readable error strings. An empty list means the
    config is valid. Callers (e.g. app.py) should surface any errors before
    doing pipeline work.
    """
    errors: list[str] = []

    if LLM_PROVIDER == "claude" and not CLAUDE_API_KEY:
        errors.append(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file or set it as "
            "an environment variable before starting the app."
        )

    if not (0.0 <= DEFINITION_UBIQUITY_THRESHOLD <= 1.0):
        errors.append(
            f"DEFINITION_UBIQUITY_THRESHOLD ({DEFINITION_UBIQUITY_THRESHOLD}) must "
            "be between 0.0 and 1.0."
        )

    if not EMBEDDING_MODEL:
        errors.append("EMBEDDING_MODEL must not be empty.")

    return errors
