"""Downloading a pack on the desktop (P4-T6b, PCK-5, architecture 6.10).

The core decides (mapcore.packs.install): whether this version may install the pack, the file
names, the progress to say and whether the bytes are right. This only moves the bytes: on a thread
of its own, from the catalogue's desktop address into name.pack.part in the packs folder, hashing
them as they come; then, when they match, renamed into place as name.pack. A download that does not
match is removed. The words come back to the window's thread through signals.

The opener is given, so the tests pass a stand-in for the internet and none opens a connection
(rule 5). cancel() is the hook for P4-T6f, which will also resume a .part file by range requests.
"""
from __future__ import annotations

import hashlib
import os
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from mapcore import version
from mapcore.packs import install

CHUNK = 1 << 20      # 1 MB at a time
TIMEOUT = 60         # seconds without a byte before the connection is given up


def open_url(url: str):
    """The real internet: a file-like object over the bytes at url."""
    request = urllib.request.Request(url, headers={"User-Agent": f"TobyMap/{version()}"})
    return urllib.request.urlopen(request, timeout=TIMEOUT)


class Downloader(QObject):
    """One download at a time. said(text) is progress; finished(entry, path, text) ends each download,
    with the installed pack's path, or None when it failed, and the words to say."""

    said = Signal(str)
    finished = Signal(object, object, str)

    def __init__(self, parent=None, folder: Path | None = None, opener=None, app_version: str | None = None):
        super().__init__(parent)
        self.folder = Path(folder) if folder is not None else None
        self.opener = opener or open_url
        self.app_version = app_version or version()
        self.thread: threading.Thread | None = None
        self.entry = None
        self._cancel = threading.Event()

    @property
    def busy(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, entry, folder: Path | None = None) -> str | None:
        """Begin downloading a catalogue entry. Returns the words to say at once when it is refused (another
        download running, or a pack this version cannot use), else None, and the thread is started."""
        if self.busy:
            return install.busy(self.entry)
        refused = install.refusal(entry, self.app_version)
        if refused:
            return refused
        target = Path(folder) if folder is not None else self.folder
        self.entry = entry
        self._cancel.clear()
        self.thread = threading.Thread(target=self._run, args=(entry, target), name="pack download", daemon=True)
        self.thread.start()
        return None

    def cancel(self) -> None:
        """Stop the download in progress (P4-T6f will keep its .part file to resume)."""
        self._cancel.set()

    def wait(self, timeout: float | None = None) -> None:
        if self.thread is not None:
            self.thread.join(timeout)

    def _run(self, entry, folder: Path) -> None:
        part = folder / install.part_name(entry)
        final = folder / install.file_name(entry)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            ok = self._fetch(entry, part)
        except (OSError, ValueError):   # no connection, a bad address, a full disk
            self._remove(part)
            self.finished.emit(entry, None, install.failed(entry))
            return
        if ok is None:   # cancelled
            self._remove(part)
            self.finished.emit(entry, None, "")
            return
        if not ok:
            self._remove(part)
            self.finished.emit(entry, None, install.damaged(entry))
            return
        try:
            os.replace(part, final)
        except OSError:
            self._remove(part)
            self.finished.emit(entry, None, install.failed(entry))
            return
        self.finished.emit(entry, final, install.done(entry))

    def _fetch(self, entry, part: Path) -> bool | None:
        """The bytes into the .part file. True when they match the catalogue, False when not, None when cancelled."""
        progress = install.Progress(entry)
        digest = hashlib.sha256()
        done = 0
        source = self.opener(entry.url_desktop)
        try:
            with open(part, "wb") as out:
                while True:
                    if self._cancel.is_set():
                        return None
                    chunk = source.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if done > entry.size:   # more than the catalogue says: not the pack it names
                        return False
                    words = progress.update(done)
                    if words:
                        self.said.emit(words)
        finally:
            close = getattr(source, "close", None)
            if close:
                close()
        return install.matches(entry, done, digest.hexdigest())

    @staticmethod
    def _remove(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass
