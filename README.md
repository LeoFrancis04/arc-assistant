# A.R.C. — Adaptive Reasoning Core

Personal AI assistant with streaming chat, tool use, and persistent memory.
Switch between Anthropic (cloud) and Ollama (local) with one env var.

---

## Quick start — Corporate PC (Anthropic)

**Prerequisites:** Docker Desktop, an Anthropic API key.

```bash
# 1. Clone and enter the project
git clone <your-repo-url> arc-assistant
cd arc-assistant

# 2. Configure environment
cp .env.example .env
#    Open .env and set ANTHROPIC_API_KEY=sk-ant-...
#    Leave PROVIDER=anthropic

# 3. Build and run
docker-compose up --build

# 4. Open in browser
#    http://localhost:8000
```

To run in the background: `docker-compose up -d --build`  
To view logs: `docker-compose logs -f`  
To stop: `docker-compose down`

---

## Migrating to MacBook (Ollama / local LLM)

**Prerequisites:** Docker Desktop for Mac, [Ollama](https://ollama.ai).

```bash
# 1. Install Ollama and pull the model
brew install ollama          # or download from ollama.ai
ollama pull llama3.1

# 2. Start the Ollama server (runs on http://localhost:11434)
ollama serve                 # keep this terminal open

# 3. Update your .env
#    PROVIDER=ollama
#    OLLAMA_BASE_URL=http://host.docker.internal:11434
#      ↑ use host.docker.internal so the container can reach the host's Ollama

# 4. Rebuild and run
docker-compose up --build
```

> **Note:** `host.docker.internal` is how Docker containers on Mac (and Windows)
> reach services running on the host machine. On Linux, use `172.17.0.1` or your
> host's actual IP address instead.

---

## Architecture

```
arc-assistant/
├── app/
│   ├── main.py          # FastAPI app, WebSocket endpoint, REST helpers
│   ├── ai_core.py       # Streaming AI logic, tool-use loop (Anthropic + Ollama)
│   ├── memory.py        # Sliding window memory → data/memory.json
│   ├── config.py        # All settings from .env via python-dotenv
│   ├── tools/
│   │   ├── registry.py  # Auto-discovers tools, builds JSON schemas
│   │   └── system_tools.py  # Tool functions (add yours here)
│   └── static/          # Single-page frontend (HTML/CSS/JS)
├── data/
│   ├── memory.json      # Conversation history (auto-created)
│   └── notes/           # Markdown notes saved by ARC
├── Dockerfile
├── docker-compose.yml
└── .env
```

### WebSocket message protocol

| Direction | Type | Payload |
|-----------|------|---------|
| client → server | — | `{"message": "your text"}` |
| server → client | `token` | `{"type":"token","content":"..."}` |
| server → client | `tool_call` | `{"type":"tool_call","tool":"...","args":{...}}` |
| server → client | `tool_result` | `{"type":"tool_result","tool":"...","result":"..."}` |
| server → client | `done` | `{"type":"done"}` |
| server → client | `error` | `{"type":"error","message":"..."}` |

---

## Adding a new tool

Open `app/tools/system_tools.py` and add a function:

```python
def web_search(query: str) -> str:
    """Searches the web and returns a summary of results.

    Args:
        query: The search query to look up.
    """
    # ... your implementation ...
    return results_string
```

That's it. The registry auto-discovers it on next startup — no other files need
to change.

**Supported parameter types:** `str`, `int`, `float`, `bool`

---

## REST endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Chat UI |
| `WS` | `/ws/chat` | Streaming chat |
| `GET` | `/api/history` | Current conversation memory |
| `POST` | `/api/clear` | Wipe conversation memory |
| `GET` | `/api/health` | Provider + status check |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER` | `anthropic` | `anthropic` or `ollama` |
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Ollama model name |
| `MAX_MEMORY_MESSAGES` | `20` | Sliding window size |
| `DATA_DIR` | `data` | Root for memory + notes |
 