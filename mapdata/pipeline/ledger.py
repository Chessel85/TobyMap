"""The record of every file the pipeline creates (DMT-7, architecture 8.5, DP75).

The data folder is shared with the data manager's own files. mapdata writes
only inside its own folder, tobymap, and keeps a list there, created
files.txt, of every file it has made. Before writing a file, the pipeline
asks the ledger: a path outside the tobymap folder is refused, and so is an
existing file that is not on the list, so nothing the pipeline did not
create is ever overwritten. The pipeline never deletes files.

Files made before the list existed, such as the spike S2 caches, are not on
it, so they are never overwritten either.
"""
from __future__ import annotations

from pathlib import Path

from mapdata.pipeline.errors import BuildStopped

LEDGER_NAME = "created files.txt"


class Ledger:
    def __init__(self, own: Path):
        self.own = Path(own).resolve()
        self.path = self.own / LEDGER_NAME
        self.known: set[str] = set()
        if self.path.is_file():
            self.known = {line.strip() for line in self.path.read_text(encoding="utf-8").splitlines()
                          if line.strip()}

    def _relative(self, path: Path) -> str:
        resolved = Path(path).resolve()
        if resolved != self.own and self.own not in resolved.parents:
            raise BuildStopped(f"mapdata was about to write {resolved}, which is outside its own folder, "
                               f"{self.own}. Nothing was written. This is a fault in mapdata: please report it.")
        return resolved.relative_to(self.own).as_posix()

    def created(self, path: Path) -> bool:
        return self._relative(path) in self.known

    def claim(self, path: Path) -> Path:
        """Get ready to write a file: refuse if it is outside the tobymap folder, or exists and
        mapdata did not create it. Otherwise record it, make its folder, and return the path."""
        path = Path(path)
        rel = self._relative(path)
        if rel == LEDGER_NAME:
            raise BuildStopped("mapdata was about to overwrite its own list of created files. "
                               "This is a fault in mapdata: please report it.")
        if path.exists() and rel not in self.known:
            raise BuildStopped(f"{path} already exists, and mapdata did not create it, so it is not overwritten. "
                               "Move or rename that file if it is not needed, then run the command again.")
        if rel not in self.known:
            self.own.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as out:
                out.write(rel + "\n")
            self.known.add(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
