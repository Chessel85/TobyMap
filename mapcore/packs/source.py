"""Byte sources: where a pack's bytes come from (AD-5).

A byte source has a `size` in bytes and `read(offset, length)`, which returns
exactly those bytes. The pack reader uses nothing else, so the same reader
works on a file on the desktop, on bytes in memory in the tests, and in the
web version on the browser's private storage (P1-T11), and, while a pack is
downloading in the web version, on range requests over the internet (P4-T6c, PCK-4).

A source may also have a `name`, used in messages, and `close()`.
"""
from __future__ import annotations

import threading
from pathlib import Path


class FileSource:
    """A pack's bytes from a file on disk."""

    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name
        self.file = open(self.path, "rb")
        self.size = self.path.stat().st_size
        self._lock = threading.Lock()  # seek and read together, so threads do not mix them up

    def read(self, offset: int, length: int) -> bytes:
        with self._lock:
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


class DownloadingSource:
    """A pack still downloading (P4-T6c, PCK-4): bytes already stored are read from there, the rest from the
    internet by range requests, so the map can be used before the download ends.

    remote and stored are byte sources. The shell says how much is stored with `have`; `stored_as(source)`
    hands over to the finished file, and `stored_as(None)` reads everything from the internet again, while the
    file is being moved into place or after a download that went wrong.
    """

    def __init__(self, size: int, name: str, remote, stored=None):
        self.size = int(size)
        self.name = name
        self.remote = remote
        self.stored = stored
        self.have = 0

    def read(self, offset: int, length: int) -> bytes:
        if self.stored is not None and offset + length <= self.have:
            return self.stored.read(offset, length)
        return self.remote.read(offset, length)

    def stored_as(self, stored) -> None:
        self.stored = stored
        self.have = self.size if stored is not None else 0

    @property
    def complete(self) -> bool:
        return self.stored is not None and self.have >= self.size

    def close(self) -> None:
        for source in (self.stored, self.remote):
            close = getattr(source, "close", None)
            if close:
                close()
