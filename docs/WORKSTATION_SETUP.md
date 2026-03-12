# Workstation Setup Guide

Step-by-step guide for deploying the Credit Agreement Analyzer on your work computer and sharing it with your team.

---

## Overview

The app runs as two Docker containers (the Streamlit app + an Nginx reverse proxy) on your workstation. Team members connect via your machine's IP address in their browser. Basic auth protects access.

```
Team member's browser
    |
    v
http://<your-ip>  (port 80)
    |
    v
[Nginx] -- basic auth --> [Streamlit App] -- LLM calls --> [Internal LLM / Claude API]
```

---

## Step 1: Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. Run the installer. Accept defaults.
3. When prompted, enable **WSL2** backend (not Hyper-V).
4. Restart your computer if asked.
5. Open Docker Desktop and wait for the engine to start (whale icon in the system tray turns steady).
6. Open a terminal (PowerShell or WSL2) and verify:

```powershell
docker --version
docker compose version
```

Both should print version numbers. If `docker compose` is not found, update Docker Desktop to the latest version.

### If Docker Desktop requires a license

Docker Desktop is free for personal use and small businesses. If your organization requires a paid license, you can install Docker Engine directly in WSL2 instead:

```bash
# Open a WSL2 terminal (Ubuntu)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# Close and reopen the terminal
```

---

## Step 2: Get the project onto your work machine

### Option A: Git clone (if you have network access to GitHub)

```bash
git clone https://github.com/patrickbott/credit-agreement-analyzer.git
cd credit-agreement-analyzer
```

### Option B: Offline transfer (air-gapped environment)

At home (with internet):

```bash
cd /path/to/credit-analyzer

# Build the Docker image (downloads all dependencies)
docker compose build

# Pull the Nginx image
docker pull nginx:alpine

# Export everything to a single file (~3-4 GB)
docker save credit-analyzer-app:latest nginx:alpine | gzip > credit-analyzer-images.tar.gz

# Copy the project + images to a USB drive
rsync -av --exclude='.git' --exclude='.venv' --exclude='chroma_data' --exclude='__pycache__' \
    . /mnt/d/transfer/credit-analyzer/
cp credit-analyzer-images.tar.gz /mnt/d/transfer/
```

At work (no internet):

```bash
# Load the pre-built images
docker load < /path/to/transfer/credit-analyzer-images.tar.gz

# Copy the project into place
cp -r /path/to/transfer/credit-analyzer C:\users\<you>\projects\credit-analyzer
```

---

## Step 3: Configure the LLM provider

Create your `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` based on which LLM you're using:

### Using your internal LLM

```env
LLM_PROVIDER=internal
```

You also need to provide your `internal_provider.py` implementation. Place it in the project root and uncomment the volume mount in `docker-compose.yml`:

```yaml
services:
  app:
    volumes:
      - ./chroma_data:/app/chroma_data
      - ./internal_provider.py:/app/credit_analyzer/llm/internal_provider.py:ro   # <-- uncomment this line
```

Your `internal_provider.py` must implement the `LLMProvider` interface:

```python
from credit_analyzer.llm.base import LLMProvider, LLMResponse

class InternalLLMProvider(LLMProvider):
    def complete(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.0, max_tokens: int = 2048) -> LLMResponse:
        # Call your internal API here
        response_text = call_your_api(system_prompt, user_prompt, temperature, max_tokens)
        return LLMResponse(
            text=response_text,
            tokens_used=0,  # or actual count if available
            model="your-model-name",
            duration_seconds=0.0,  # or actual duration
        )

    def is_available(self) -> bool:
        # Return True if your API is reachable
        return True

    def model_name(self) -> str:
        return "your-model-name"
```

If you already wrote an `internal_provider.py` on your work computer, just place it in the project root. The `:ro` mount makes it read-only inside the container and `.gitignore` prevents it from being committed.

### Using Claude API

```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Using Ollama (local open-source models)

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Note: use `host.docker.internal` instead of `localhost` so the Docker container can reach Ollama running on your host machine.

---

## Step 4: Set up basic auth

Generate credentials so only authorized users can access the app:

```bash
# Create a user (replace admin/yourpassword with real values)
docker run --rm httpd:alpine htpasswd -nb admin yourpassword > nginx/.htpasswd

# Add more users
docker run --rm httpd:alpine htpasswd -nb analyst1 theirpassword >> nginx/.htpasswd
```

---

## Step 5: Build and start

```bash
docker compose up -d --build
```

First build takes 2-3 minutes (downloads Python packages and ML models). Subsequent builds use cache.

Verify everything is running:

```bash
docker compose ps
# Both "credit-analyzer-app" and "credit-analyzer-nginx" should show "running"
```

Open `http://localhost` in your browser and log in with the credentials from Step 4.

---

## Step 6: Let your team connect

Team members connect by opening `http://<your-ip>` in their browser, where `<your-ip>` is your workstation's IP address on the network.

### Find your IP address

```powershell
# PowerShell
ipconfig | findstr "IPv4"
```

Look for the IP on your corporate network (e.g., `10.x.x.x` or `192.168.x.x`). Share this with your team.

### Windows Firewall

You may need to allow inbound connections on port 80:

1. Open **Windows Defender Firewall with Advanced Security**
2. Click **Inbound Rules** > **New Rule**
3. Select **Port** > **TCP** > **Specific local ports: 80**
4. Select **Allow the connection**
5. Check **Domain** and **Private** (uncheck Public)
6. Name it "Credit Analyzer"

### If port 80 is blocked

Change the port in `docker-compose.yml`:

```yaml
nginx:
  ports:
    - "8080:80"   # access at http://<your-ip>:8080
```

Then `docker compose up -d` and tell your team to use port 8080.

---

## Day-to-Day Operations

### Starting the app (after a reboot)

```bash
docker compose up -d
```

Docker Desktop can also be configured to start on login (Settings > General > Start Docker Desktop when you sign in).

### Stopping the app

```bash
docker compose stop       # keeps containers, fast restart later
docker compose down       # removes containers, next start is fresh
```

### Updating after code changes

```bash
docker compose up -d --build
```

In an offline environment, rebuild at home, re-export with `docker save`, and transfer again.

### Viewing logs

```bash
docker compose logs -f app      # app logs (streaming)
docker compose logs -f nginx    # nginx access/error logs
docker compose logs --tail=50 app   # last 50 lines
```

### Adding/removing users

```bash
# Add
docker run --rm httpd:alpine htpasswd -nb newuser password >> nginx/.htpasswd
docker compose restart nginx

# Remove — edit nginx/.htpasswd and delete the line, then:
docker compose restart nginx
```

### Resetting the vector store

If indexed documents get corrupted or you want a clean slate:

```bash
rm -rf chroma_data/
docker compose restart app
```

---

## Troubleshooting

### "Cannot connect to the Docker daemon"

Docker Desktop isn't running. Open it from the Start menu and wait for the engine to start.

### Build fails with network errors

Your machine can't reach the internet to download packages. Use the offline transfer workflow (Step 2, Option B).

### App starts but LLM calls fail

- **Internal provider**: Check that `internal_provider.py` exists in the project root, the volume mount is uncommented in `docker-compose.yml`, and your internal API is reachable from the container. Check logs: `docker compose logs app`.
- **Claude**: Verify `ANTHROPIC_API_KEY` is set correctly in `.env` (no quotes around the value).
- **Ollama**: Make sure Ollama is running on your host and use `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

### Team members can't connect

1. Verify the app is running: `docker compose ps`
2. Verify you can access it locally: `http://localhost`
3. Check your IP: `ipconfig | findstr "IPv4"`
4. Check Windows Firewall allows port 80 (see Step 6)
5. Have them try `http://<your-ip>:80` explicitly
6. If on VPN, your IP may change — re-check and re-share

### WebSocket errors (page loads but doesn't update)

Streamlit uses WebSockets for live streaming. This should work out of the box with the included Nginx config. If you modified `nginx/nginx.conf`, ensure it includes:

```
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

Then `docker compose restart nginx`.

### Slow first request after startup

Normal. The first request loads ML models (embeddings + reranker) into memory. Takes 10-15 seconds. Subsequent requests are fast.

### Container keeps restarting

```bash
docker compose logs --tail=50 app
```

Common causes:
- Missing `.env` or missing required keys
- Corrupt `chroma_data/` — fix with `rm -rf chroma_data/ && docker compose restart app`

### WSL2 can't reach localhost

- Ensure Docker Desktop's WSL2 integration is enabled (Settings > Resources > WSL Integration)
- Try `http://127.0.0.1` instead
- Check Windows Firewall

