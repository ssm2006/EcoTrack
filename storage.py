"""
storage.py
----------
Lightweight, file-based storage for user footprint history.

For a hackathon-scale project, a simple JSON file per user avoids the
overhead of a database while still providing persistence between runs.
Each user is identified by a simple username string (no auth required
for this demo -- see README for security notes / production guidance).
"""

import json
import os
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "users")
os.makedirs(DATA_DIR, exist_ok=True)

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,40}$")


def _safe_path(username):
    """Return a safe file path for a given username, preventing path traversal."""
    if not _SAFE_NAME_RE.match(username):
        raise ValueError("Invalid username. Use only letters, numbers, '-' and '_' (max 40 chars).")
    return os.path.join(DATA_DIR, f"{username}.json")


def load_history(username):
    """Load a user's history list. Returns [] if none exists."""
    path = _safe_path(username)
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_entry(username, breakdown):
    """Append a new footprint entry (with timestamp) to the user's history."""
    path = _safe_path(username)
    history = load_history(username)

    entry = dict(breakdown)
    entry["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    history.append(entry)

    # Keep only the most recent 100 entries to bound file size
    history = history[-100:]

    with open(path, "w") as f:
        json.dump(history, f, indent=2)

    return history
