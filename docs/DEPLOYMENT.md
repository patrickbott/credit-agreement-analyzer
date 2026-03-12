# Deployment Guide

Docker Compose deployment for the Credit Agreement Analyzer, with Nginx reverse proxy and basic auth. Covers both online and fully-offline (air-gapped) workflows.

---

## 1. Prerequisites

- **Windows 10/11** with [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) enabled
- A WSL2 distribution installed (Ubuntu 22.04+ recommended)
- Docker (see Section 2 for installation options)
- ~4 GB disk for the built Docker image (ML models are baked in)

## 2. Installing Docker on WSL2

### Option A: Docker Desktop for Windows (easier)

1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. In Docker Desktop settings, go to **Resources > WSL Integration** and enable your WSL2 distro.
3. Open a WSL2 terminal and verify:

```bash
docker --version
docker compose version
```

### Option B: Docker Engine directly in WSL2 (no Desktop needed)

Run these inside your WSL2 terminal:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
```

Close and reopen your WSL2 terminal (or run `newgrp docker`) for the group change to take effect, then verify:

```bash
docker --version
docker compose version
```

## 3. Quick Start

```bash
# Navigate to the project
cd /mnt/c/users/kbott/projects/credit-analyzer

# Create your .env from the template
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY if using the claude provider
```

### Set up basic auth for Nginx

Generate an `.htpasswd` file. Pick one of these methods:

```bash
# Method 1: Using the httpd Docker image (recommended)
docker run --rm httpd:alpine htpasswd -nb admin yourpassword > nginx/.htpasswd

# Method 2: Using Python (works if Docker isn't available yet)
python3 -c "import crypt; print('admin:' + crypt.crypt('yourpassword', crypt.mksalt(crypt.METHOD_SHA256)))" > nginx/.htpasswd
```

Replace `yourpassword` with a real password.

### Build and start

```bash
docker compose up -d --build
```

The first build downloads Python packages and ML models (~2-3 minutes depending on connection speed). Subsequent builds use Docker layer cache and are much faster.

### Verify

```bash
docker compose ps          # Both app and nginx should show "running"
docker compose logs -f app # Watch app startup; Ctrl+C to stop tailing
```

Open `http://localhost` in a browser. You will be prompted for the basic auth credentials you set above.

## 4. Offline Transfer Workflow

For environments behind strict firewalls where the work machine cannot download Docker images or Python packages.

### At home (with internet)

```bash
cd /mnt/c/users/kbott/projects/credit-analyzer

# 1. Build the app image (downloads all Python deps + ML models)
docker compose build

# 2. Also pull the Nginx base image
docker pull nginx:alpine

# 3. Export both images to a single compressed tar
docker save credit-analyzer-app:latest nginx:alpine | gzip > credit-analyzer-images.tar.gz
```

The resulting file is roughly 3-4 GB.

```bash
# 4. Copy the tar to a USB drive or network share
cp credit-analyzer-images.tar.gz /mnt/d/transfer/

# 5. Copy the project directory (exclude bulky/generated directories)
rsync -av --exclude='.git' \
          --exclude='.venv' \
          --exclude='chroma_data' \
          --exclude='__pycache__' \
          /mnt/c/users/kbott/projects/credit-analyzer/ \
          /mnt/d/transfer/credit-analyzer/
```

### At work (no internet)

```bash
# 1. Load the pre-built images
docker load < /mnt/d/transfer/credit-analyzer-images.tar.gz

# 2. Copy the project into place (if not already there)
cp -r /mnt/d/transfer/credit-analyzer /mnt/c/users/kbott/projects/credit-analyzer

# 3. Navigate to the project
cd /mnt/c/users/kbott/projects/credit-analyzer

# 4. Create .env with work-specific config
cp .env.example .env
# Edit .env — set LLM_PROVIDER, API keys, etc.

# 5. Ensure nginx/.htpasswd exists (see Section 3)

# 6. Start (no --build flag — images are already loaded)
docker compose up -d

# 7. Verify
docker compose ps
```

Because the Dockerfile sets `TRANSFORMERS_OFFLINE=1` and `HF_HUB_OFFLINE=1` at runtime, the app will not attempt any network downloads. All models are baked into the image at build time.

## 5. Configuration

Runtime configuration is read from the `.env` file. See [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) for the full list.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `claude` | LLM backend: `claude`, `ollama`, or `internal` |
| `ANTHROPIC_API_KEY` | (none) | Required when `LLM_PROVIDER=claude` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model identifier |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model name for the Ollama provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `CHUNK_TARGET_TOKENS` | `800` | Target chunk size (tokens) |
| `CHUNK_MAX_TOKENS` | `1200` | Hard chunk size ceiling |
| `CHUNK_OVERLAP_TOKENS` | `200` | Overlap between adjacent chunks |
| `MIN_RETRIEVAL_SCORE` | `0.15` | Post-rerank score filter threshold |
| `REPORT_MAX_WORKERS` | `3` | Parallel report section generation workers |

Changes to `.env` take effect after restarting the app container:

```bash
docker compose restart app
```

## 6. User Management (Basic Auth)

The Nginx reverse proxy authenticates users via the `nginx/.htpasswd` file.

### Adding a user

```bash
# If htpasswd is installed locally:
htpasswd nginx/.htpasswd newuser

# If htpasswd is not installed, use the Docker image:
docker run --rm httpd:alpine htpasswd -nb newuser theirpassword >> nginx/.htpasswd
```

### Removing a user

```bash
# If htpasswd is installed:
htpasswd -D nginx/.htpasswd olduser

# Or manually edit the file and delete the line for that user
```

### After any change to `.htpasswd`

```bash
docker compose restart nginx
```

## 7. Using the Internal LLM Provider

The `internal` provider is an enterprise stub (`credit_analyzer/llm/internal_provider.py`). To use a real implementation without modifying the tracked source:

1. Create your real `internal_provider.py` locally (keep it outside version control).

2. Uncomment the volume mount in `docker-compose.yml`:

```yaml
services:
  app:
    volumes:
      - ./chroma_data:/app/chroma_data
      # Uncomment the line below:
      - ./internal_provider.py:/app/credit_analyzer/llm/internal_provider.py:ro
```

3. Set the provider in `.env`:

```
LLM_PROVIDER=internal
```

4. Restart the app:

```bash
docker compose restart app
```

The `:ro` mount flag makes the file read-only inside the container. Your implementation file stays in the project root and is already covered by `.gitignore` patterns (it won't be committed).

## 8. Managing the Stack

| Action | Command |
|---|---|
| Start | `docker compose up -d` |
| Stop (containers removed) | `docker compose down` |
| Stop (keep containers) | `docker compose stop` |
| View app logs | `docker compose logs -f app` |
| View nginx logs | `docker compose logs -f nginx` |
| Rebuild after code changes | `docker compose up -d --build` |
| Restart a single service | `docker compose restart app` |
| Reset the vector store | `rm -rf chroma_data/ && docker compose restart app` |
| Shell into the app container | `docker compose exec app bash` |
| Check container health | `docker compose ps` |

### Updating the deployment

After pulling new code or transferring an updated project directory:

```bash
docker compose up -d --build   # rebuilds the app image with new code
```

In an offline environment, rebuild the image at home, re-export with `docker save`, and transfer again (see Section 4).

## 9. Troubleshooting

### Port 80 already in use

Another process is bound to port 80. Change the host port in `docker-compose.yml`:

```yaml
nginx:
  ports:
    - "8080:80"   # access at http://localhost:8080 instead
```

Then `docker compose up -d`.

### WebSocket errors in the browser

Streamlit uses WebSockets for live updates. Ensure the Nginx config includes the upgrade headers:

```
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

If you modified `nginx/nginx.conf`, restart: `docker compose restart nginx`.

### Model loading errors at startup

The Docker image pre-downloads all ML models during build. If you see download attempts or model-not-found errors at runtime:

- The image was likely built without internet or the build was interrupted. Rebuild with a working connection: `docker compose build --no-cache`.
- Verify the offline flags are set: `docker compose exec app env | grep -E 'OFFLINE|TIKTOKEN'`.

### Permission denied on `chroma_data/`

The container runs as root by default, but WSL2 filesystem mounts can cause permission mismatches:

```bash
sudo chown -R 1000:1000 chroma_data/
```

### Container keeps restarting

Check the logs for the root cause:

```bash
docker compose logs --tail=50 app
```

Common causes:
- Missing `.env` file or missing required keys (e.g., `ANTHROPIC_API_KEY` when `LLM_PROVIDER=claude`).
- Corrupt `chroma_data/` directory. Fix: `rm -rf chroma_data/ && docker compose restart app`.

### "ANTHROPIC_API_KEY is not set"

The app validates configuration at startup. If using the `claude` provider:

1. Confirm `.env` exists in the project root.
2. Confirm it contains `ANTHROPIC_API_KEY=sk-ant-...` (no quotes around the value).
3. Restart: `docker compose restart app`.

### Slow first request after startup

Expected behavior. The first request triggers:
- ChromaDB collection creation (if a document was previously indexed).
- Embedding and reranker model warm-up (loading weights into memory).

Subsequent requests are fast. The healthcheck (`/_stcore/health`) will report healthy before model warm-up completes, so allow 10-15 seconds after startup before sending the first query.

### WSL2 cannot reach localhost

If `http://localhost` does not resolve from Windows to the WSL2 container:

- Ensure Docker Desktop's WSL2 integration is enabled, or
- Try `http://127.0.0.1` instead, or
- Check that Windows Firewall is not blocking the port.
