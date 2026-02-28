"""Central configuration for the credit agreement analyzer."""

import os
from pathlib import Path

from dotenv import load_dotenv  # pyright: ignore[reportMissingTypeStubs]

load_dotenv(Path(__file__).parent.parent / ".env")

# --- Paths ---
PROJECT_ROOT: Path = Path(__file__).parent.parent
CHROMA_DATA_DIR: Path = PROJECT_ROOT / "chroma_data"
TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- PDF Extraction ---
OCR_TEXT_LENGTH_THRESHOLD: int = 100  # Pages with fewer chars trigger OCR fallback

# --- Chunking ---
CHUNK_TARGET_TOKENS: int = 600
CHUNK_MAX_TOKENS: int = 800
CHUNK_OVERLAP_TOKENS: int = 100
MIN_DEFINITION_CHUNK_TOKENS: int = 50
TIKTOKEN_ENCODING: str = "cl100k_base"

# --- Retrieval ---
VECTOR_WEIGHT: float = 0.6
BM25_WEIGHT: float = 0.4
MAX_DEFINITIONS_INJECTED: int = 12

# --- LLM ---
LLM_PROVIDER: str = "claude"  # "ollama" | "claude" | "internal"
OLLAMA_MODEL: str = "llama3.2:3b"
OLLAMA_BASE_URL: str = "http://localhost:11434"
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
CLAUDE_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")

# --- Q&A Engine ---
QA_MAX_HISTORY_TURNS: int = 3
QA_MAX_CONTEXT_CHUNKS: int = 15
QA_MAX_GENERATION_TOKENS: int = 1024
QA_DEFINITION_MAX_CHARS: int = 800  # Truncate long definitions (~200 tokens)
QA_CHUNK_TEXT_MAX_CHARS: int = 1500  # Truncate chunk text in context assembly (~400 tokens)
QA_SECTION_TYPES_EXCLUDE: tuple[str, ...] = ("miscellaneous",)

# --- Embedding ---
EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
