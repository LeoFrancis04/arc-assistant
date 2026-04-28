"""
Sliding window conversation memory with JSON file persistence.

Keeps the last MAX_MEMORY_MESSAGES messages so the AI has context without
unbounded token growth. Thread-safe for multiple concurrent WebSocket connections.
"""
import json
import os
import threading
from typing import Dict, List

from app.config import MAX_MEMORY_MESSAGES, MEMORY_FILE


class Memory:
    def __init__(self):
        self._lock = threading.Lock()
        self.messages: List[Dict] = []
        self._load()

    def _load(self) -> None:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self.messages = json.load(f).get("messages", [])
            except (json.JSONDecodeError, IOError):
                self.messages = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump({"messages": self.messages}, f, indent=2)

    # filepath as property so tests can override it easily
    @property
    def filepath(self) -> str:
        return MEMORY_FILE

    def add(self, role: str, content: str) -> None:
        """Append a message and enforce the sliding window, then persist."""
        with self._lock:
            self.messages.append({"role": role, "content": content})
            if len(self.messages) > MAX_MEMORY_MESSAGES:
                self.messages = self.messages[-MAX_MEMORY_MESSAGES:]
            self._save()

    def get(self) -> List[Dict]:
        """Return a snapshot of the current message history."""
        with self._lock:
            return list(self.messages)

    def clear(self) -> None:
        with self._lock:
            self.messages = []
            self._save()


# Single shared instance — personal assistant has one conversation history
memory = Memory()
 