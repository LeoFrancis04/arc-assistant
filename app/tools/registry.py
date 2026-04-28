"""
Central tool registry.

Auto-discovers every public function in system_tools.py, builds JSON schemas
from type annotations and Google-style docstrings, and exposes the tool list
in both Anthropic and Ollama (OpenAI-compatible) formats.

Adding a tool: define it in system_tools.py. Nothing here needs to change.
"""
import inspect
from typing import Any, Callable, Dict, List, get_type_hints

from app.tools import system_tools

# Python type → JSON Schema type
_TYPE_MAP: Dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _json_type(annotation: Any) -> str:
    return _TYPE_MAP.get(annotation, "string")


def _parse_docstring(func: Callable) -> tuple[str, Dict[str, str]]:
    """Return (description, {param: description}) parsed from a Google docstring."""
    doc = inspect.getdoc(func) or ""
    lines = doc.split("\n")

    desc_lines: List[str] = []
    param_docs: Dict[str, str] = {}
    in_args = False

    for line in lines:
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        # Any unindented non-empty line after Args signals a new section
        if in_args and stripped and not line.startswith(" "):
            in_args = False

        if in_args:
            if ":" in stripped:
                name, _, desc = stripped.partition(":")
                param_docs[name.strip()] = desc.strip()
        else:
            # Collect description lines, skip the boilerplate "No parameters required."
            if stripped and stripped not in ("No parameters required.",):
                desc_lines.append(stripped)

    return " ".join(desc_lines).strip(), param_docs


def _build_schema(func: Callable) -> Dict:
    """Derive a unified tool schema from a function's signature and docstring."""
    description, param_docs = _parse_docstring(func)
    sig = inspect.signature(func)

    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in sig.parameters.items():
        prop: Dict[str, str] = {"type": _json_type(hints.get(name, str))}
        if name in param_docs:
            prop["description"] = param_docs[name]
        properties[name] = prop
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "name": func.__name__,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict] = {}
        self._discover()

    def _discover(self) -> None:
        for name, func in inspect.getmembers(system_tools, inspect.isfunction):
            if name.startswith("_"):
                continue
            self._tools[name] = func
            self._schemas[name] = _build_schema(func)

    def execute(self, name: str, args: Dict) -> str:
        """Call a registered tool by name. Returns a string result or error message."""
        if name not in self._tools:
            return f"Error: unknown tool '{name}'."
        try:
            result = self._tools[name](**args)
            return str(result)
        except TypeError as e:
            return f"Error calling '{name}' (bad arguments): {e}"
        except Exception as e:
            return f"Tool '{name}' raised an exception: {e}"

    def get_anthropic_tools(self) -> List[Dict]:
        """Tool list in Anthropic API format (input_schema key)."""
        return [
            {
                "name": s["name"],
                "description": s["description"],
                "input_schema": s["parameters"],
            }
            for s in self._schemas.values()
        ]

    def get_ollama_tools(self) -> List[Dict]:
        """Tool list in Ollama / OpenAI-compatible format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": s["name"],
                    "description": s["description"],
                    "parameters": s["parameters"],
                },
            }
            for s in self._schemas.values()
        ]


# Module-level singleton
registry = ToolRegistry()
 