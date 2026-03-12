FROM python:3.11-slim

# System dependencies for PyMuPDF, pdfplumber, pytesseract, OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (no dev packages, no pip cache)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    $(grep -v -E '^\s*#|^\s*$' requirements.txt \
      | grep -v -E 'pytest|ruff|pyright' \
      | tr '\n' ' ')

# ---------------------------------------------------------------------------
# Pre-cache models during build so the image is fully offline-capable.
# ---------------------------------------------------------------------------

# tiktoken cache directory
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN mkdir -p "$TIKTOKEN_CACHE_DIR"

# Download and cache tiktoken encoding
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

# Download and cache HuggingFace embedding model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Download and cache HuggingFace reranker model
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# ---------------------------------------------------------------------------
# Copy application code
# ---------------------------------------------------------------------------
COPY . .

# Ensure .streamlit config disables telemetry
RUN mkdir -p /app/.streamlit && \
    if [ -f /app/.streamlit/config.toml ]; then \
        grep -q '^\[browser\]' /app/.streamlit/config.toml \
        || printf '\n[browser]\ngatherUsageStats = false\n' >> /app/.streamlit/config.toml; \
    else \
        printf '[browser]\ngatherUsageStats = false\n' > /app/.streamlit/config.toml; \
    fi

# ---------------------------------------------------------------------------
# Runtime environment
# ---------------------------------------------------------------------------

# Force offline mode for HuggingFace and tiktoken after build
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache

# Tesseract language data location
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Streamlit settings
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
