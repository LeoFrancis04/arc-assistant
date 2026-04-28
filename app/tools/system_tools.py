"""
Starter tools for ARC.

EXTENSION GUIDE: To add a new tool, define a new public function here with:
  - Type-annotated parameters (str, int, float, bool)
  - A docstring whose first line is the tool description
  - An "Args:" section listing each parameter
  - A return value of type str

The registry auto-discovers everything — no other files need to change.
"""
import glob
import os
from datetime import datetime

from app.config import NOTES_DIR


def get_current_datetime() -> str:
    """Returns the current date, time, and day of week.

    No parameters required.
    """
    now = datetime.now()
    return now.strftime("Date: %Y-%m-%d | Time: %H:%M:%S | Day: %A")


def list_directory(path: str) -> str:
    """Lists files and directories at the given path.

    Args:
        path: Filesystem path to list. Use '.' for the current working directory.
    """
    try:
        entries = os.listdir(path)
    except FileNotFoundError:
        return f"Error: '{path}' does not exist."
    except PermissionError:
        return f"Error: Permission denied for '{path}'."

    if not entries:
        return f"'{path}' is empty."

    lines = []
    for entry in sorted(entries):
        tag = "[DIR] " if os.path.isdir(os.path.join(path, entry)) else "[FILE]"
        lines.append(f"{tag} {entry}")
    return f"Contents of '{path}':\n" + "\n".join(lines)


def create_note(title: str, content: str) -> str:
    """Creates or overwrites a markdown note saved to the notes directory.

    Args:
        title: Note title. Used as the filename (spaces become underscores).
        content: Full markdown content to write into the note body.
    """
    os.makedirs(NOTES_DIR, exist_ok=True)
    safe_name = title.strip().replace(" ", "_").replace("/", "-").replace("..", "") + ".md"
    filepath = os.path.join(NOTES_DIR, safe_name)
    with open(filepath, "w") as f:
        f.write(f"# {title}\n\n{content}")
    return f"Note saved: {filepath}"


def search_notes(query: str) -> str:
    """Searches all saved notes for a keyword or phrase and returns matching excerpts.

    Args:
        query: Text to search for across all note titles and content.
    """
    os.makedirs(NOTES_DIR, exist_ok=True)
    files = glob.glob(os.path.join(NOTES_DIR, "*.md"))

    if not files:
        return "No notes exist yet. Use create_note to save some."

    query_lower = query.lower()
    matches = []

    for filepath in sorted(files):
        try:
            with open(filepath, "r") as f:
                content = f.read()
        except IOError:
            continue

        if query_lower in content.lower():
            filename = os.path.basename(filepath)
            # Grab the first line that contains the match as a preview
            preview = next(
                (ln.strip()[:100] for ln in content.split("\n") if query_lower in ln.lower()),
                "",
            )
            matches.append(f"- {filename}: ...{preview}...")

    if not matches:
        return f"No notes found containing '{query}'."
    return f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)
 