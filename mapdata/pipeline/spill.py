"""Things set aside on disk while a stage runs, so millions of them are not all held in memory (P4-T1m).

A Spill keeps one value for each numbered item in a file of its own, pickled, and only where each is in memory: an
England pack has 6 to 9 million features, and a Python record for each, held several times over, would need 20 to
30 GB. The file is deleted when the spill is closed.

RelStore holds each feature's relationships in a spill, by identifier, and behaves enough like a dictionary for the
writing stage: what is changed is kept in memory, the rest read back when asked.
"""
from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path

import numpy as np

PROTOCOL = pickle.HIGHEST_PROTOCOL


class Spill:
    """Values by number 0 to n - 1, each pickled into a file in `folder` (a temporary folder if None)."""

    def __init__(self, n: int, folder: Path | None = None, name: str = "spill"):
        fd, path = tempfile.mkstemp(prefix=f".{name}-", suffix=".tmp", dir=None if folder is None else str(folder))
        os.close(fd)
        self.path = Path(path)
        self._out = open(self.path, "w+b")
        self._at = 0
        self.offset = np.full(n, -1, dtype=np.int64)
        self.length = np.zeros(n, dtype=np.int64)

    def __len__(self) -> int:
        return len(self.offset)

    def put_bytes(self, i: int, data: bytes) -> None:
        self._out.seek(self._at)
        self._out.write(data)
        self.offset[i] = self._at
        self.length[i] = len(data)
        self._at += len(data)

    def put(self, i: int, value) -> None:
        self.put_bytes(i, pickle.dumps(value, PROTOCOL))

    def has(self, i: int) -> bool:
        return bool(self.offset[i] >= 0)

    def get_bytes(self, i: int) -> bytes | None:
        a = int(self.offset[i])
        if a < 0:
            return None
        self._out.seek(a)
        return self._out.read(int(self.length[i]))

    def get(self, i: int, default=None):
        data = self.get_bytes(i)
        return default if data is None else pickle.loads(data)

    def close(self) -> None:
        if self._out is not None:
            self._out.close()
            self._out = None
            try:
                self.path.unlink()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class RelStore:
    """Each feature's relationships by identifier, read from a spill (P4-T1m). ids are the features' identifiers
    by number, index_of each identifier's number.

    * get(fid), items() and values() give copies read from the file, for reading only.
    * store[fid] and setdefault(fid, default) give the relationships kept in memory, so a change to them is kept.
    * A feature with no stored relationships has none until setdefault gives it some.
    """

    def __init__(self, ids: list[str], index_of: dict[str, int], folder: Path | None = None):
        self.ids = ids
        self.index_of = index_of
        self.spill = Spill(len(ids), folder, "relations")
        self.live: dict[str, dict] = {}
        self.extra: dict[str, dict] = {}   # given to identifiers not among the features, so writing can refuse them
        self._count = 0

    def put(self, i: int, rel: dict) -> None:
        """Store feature i's relationships, while the store is filled."""
        if not self.spill.has(i):
            self._count += 1
        self.spill.put(i, rel)

    def close(self) -> None:
        self.spill.close()

    def __len__(self) -> int:
        return self._count + len(self.extra) + sum(1 for f in self.live if not self.spill.has(self.index_of[f]))

    def __bool__(self) -> bool:
        return len(self) > 0

    def __contains__(self, fid) -> bool:
        if fid in self.live or fid in self.extra:
            return True
        i = self.index_of.get(fid)
        return i is not None and self.spill.has(i)

    def at(self, i: int) -> dict | None:
        """Feature i's relationships, for reading only, or None."""
        fid = self.ids[i]
        if fid in self.live:
            return self.live[fid]
        return self.spill.get(i)

    def get(self, fid, default=None):
        if fid in self.live:
            return self.live[fid]
        if fid in self.extra:
            return self.extra[fid]
        i = self.index_of.get(fid)
        if i is None:
            return default
        got = self.spill.get(i)
        return default if got is None else got

    def __getitem__(self, fid) -> dict:
        if fid not in self:
            raise KeyError(fid)
        return self.setdefault(fid, {})

    def setdefault(self, fid, default=None) -> dict:
        if fid in self.live:
            return self.live[fid]
        if fid in self.extra:
            return self.extra[fid]
        i = self.index_of.get(fid)
        if i is None:
            self.extra[fid] = default
            return default
        got = self.spill.get(i)
        self.live[fid] = default if got is None else got
        return self.live[fid]

    def items(self):
        """(identifier, relationships) for each feature that has any, in feature order, then any others."""
        for i, fid in enumerate(self.ids):
            rel = self.live.get(fid)
            if rel is None:
                rel = self.spill.get(i)
                if rel is None:
                    continue
            yield fid, rel
        yield from self.extra.items()

    def values(self):
        for _fid, rel in self.items():
            yield rel

    def keys(self):
        for fid, _rel in self.items():
            yield fid

    def __iter__(self):
        return self.keys()
