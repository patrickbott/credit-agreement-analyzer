"""Central configuration for the credit agreement analyzer."""

from pathlib import Path

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
MAX_DEFINITIONS_INJECTED: int = 5

# --- LLM ---
LLM_PROVIDER: str = "ollama"  # "ollama" | "internal"
OLLAMA_MODEL: str = "llama3:8b"
OLLAMA_BASE_URL: str = "http://localhost:11434"

# --- Embedding ---
EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
