"""Byte sources: where a pack's bytes come from (AD-5).

A byte source has a `size` in bytes and `read(offset, length)`, which returns
exactly those bytes. The pack reader uses nothing else, so the same reader
works on a file on the desktop, on bytes in memory in the tests, and in the
web version on the browser's private storage (P1-T11). Range requests over
the internet come later (PCK-3).

A source may also have a `name`, used in messages, and `close()`.
"""
from __future__ import annotations

from pathlib import Path


class FileSource:
    """A pack's bytes from a file on disk."""

    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self.file = open(self.path, "rb")
        self.size = self.path.stat().st_size

    def read(self, offset: int, length: int) -> bytes:
        self.file.seek(offset)
        return self.file.read(length)

    def close(self) -> None:
        self.file.close()


class MemorySource:
    """A pack's bytes held in memory."""

    def __init__(self, data: bytes, name: str = "pack"):
        self.data = bytes(data)
        self.size = len(self.data)
        self.name = name

    def read(self, offset: int, length: int) -> bytes:
        return self.data[offset:offset + length]

    def close(self) -> None:
        pass
