"""mapcore: the shared TobyMap core (architecture AD-1).

It knows nothing about windows, browsers, speakers or screen readers, and must
import cleanly in Pyodide. It never imports PySide6 or any shell module.
"""
from __future__ import annotations

from pathlib import Path


def version() -> str:
    """The application version, from version.txt at the repository root.

    In Pyodide or a frozen build the file may be elsewhere, so "unknown" is
    returned rather than failing.
    """
    try:
        return (Path(__file__).resolve().parent.parent / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
