"""Dataset fingerprint — SHA-256 over sorted file contents.

Produces a stable hex digest that depends only on file content,
not on file paths, modification times, or read order.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Files processed in alphabetical order for deterministic fingerprinting.
_DATA_FILES = ("events.csv", "items.csv", "queries.csv", "qrels.csv", "users.csv")


def compute_fingerprint(source_dir: Path) -> str:
    """Compute a SHA-256 fingerprint over all five data files.

    Files are hashed in alphabetical order.  The fingerprint changes only
    when file content changes — not when files are renamed, moved, or
    re-timestamped.
    """
    hasher = hashlib.sha256()
    for filename in sorted(_DATA_FILES):
        filepath = source_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Missing data file: {filepath}")
        # Hash the filename and content together
        hasher.update(filename.encode("utf-8"))
        hasher.update(filepath.read_bytes())
    return hasher.hexdigest()


def compute_file_hashes(source_dir: Path) -> dict[str, str]:
    """Return ``{filename: sha256_hex}`` for all data files."""
    result: dict[str, str] = {}
    for filename in sorted(_DATA_FILES):
        filepath = source_dir / filename
        result[filename] = hashlib.sha256(filepath.read_bytes()).hexdigest()
    return result
