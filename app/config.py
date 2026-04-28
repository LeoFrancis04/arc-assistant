"""
All settings come from environment variables populated by python-dotenv.
Switching providers is one env var change: PROVIDER=anthropic or PROVIDER=ollama.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Provider selection
PROVIDER = os.getenv("PROVIDER", "anthropic")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Paths
DATA_DIR = os.getenv("DATA_DIR", "data")
NOTES_DIR = os.path.join(DATA_DIR, "notes")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

# Memory window
MAX_MEMORY_MESSAGES = int(os.getenv("MAX_MEMORY_MESSAGES", "20"))
 