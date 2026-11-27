"""Downloading a pack on the desktop (P4-T6b, PCK-5, architecture 6.10).

The core decides (mapcore.packs.install): whether this version may install the pack, the file
names, the progress to say and whether the bytes are right. This only moves the bytes: on a thread
of its own, from the catalogue's desktop address into name.pack.part in the packs folder, hashing
them as they come; then, when they match, renamed into place as name.pack. A download that does not
match is removed. The words come back to the window's thread through signals.

The opener is given, so the tests pass a stand-in for the internet and none opens a connection
(rule 5). opener(url) fetches the whole file; opener(url, start) asks for the bytes from start on, and the reply's
status (206 or 200) says what came.

Cancel and resume (P4-T6f): cancel() stops the download and keeps its .part file, as a lost connection or closing
TobyMap does. Beside it, name.pack.part.json records which version it holds. The next download of the same entry
hashes what is held, a megabyte at a time, and asks for the rest; the core decides whether the part is carried on
or started again, from the record and the reply.
"""
from __future__ import annotations

import os
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from mapcore import version
from mapcore.packs import install

CHUNK = 1 << 20      # 1 MB at a time
MAX_TEXT = 4 << 20    # the catalogue is text: never more than 4 MB
TIMEOUT = 60         # seconds without a byte before the connection is given up


def open_url(url: str, start: int = 0):
    """The real internet: a file-like object over the bytes at url, from start on when start is not 0."""
    headers = {"User-Agent": f"TobyMap/{version()}"}
    if start:
        headers["Range"] = f"bytes={int(start)}-"
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=TIMEOUT)


def parts(folder: Path | None) -> dict:
    """The .part files in the packs folder, for the pack manager (P4-T6f): pack name -> {"record": the text of the
    record beside it, or None, "size": its size in bytes}."""
    found: dict = {}
    if folder is None:
        return found
    try:
        files = list(Path(folder).glob("*.pack" + install.PART))
    except OSError:
        return found
    for part in files:
        record = part.with_name(part.name + install.RECORD)
        try:
            text = record.read_text(encoding="utf-8") if record.exists() else None
            found[part.name[:-len(".pack" + install.PART)]] = {"record": text, "size": part.stat().st_size}
        except OSError:
            continue
    return found


def read_text(url: str, opener=None) -> str:
    """The text at url: the catalogue (P4-T6d). OSError or ValueError when it cannot be read."""
    source = (opener or open_url)(url)
    try:
        return source.read(MAX_TEXT).decode("utf-8")
    finally:
        close = getattr(source, "close", None)
        if close:
            close()


class CatalogueFetcher(QObject):
    """The catalogue's text, fetched on a thread of its own. done(callback, text, ok) comes back on the window's
    thread; ok is False when it could not be read at all."""

    done = Signal(object, str, bool)

    def __init__(self, parent=None, opener=None):
        super().__init__(parent)
        self.opener = opener
        self.threads: list[threading.Thread] = []

    def start(self, url: str, callback) -> None:
        def run():
            try:
                text, ok = read_text(url, self.opener), True
            except (OSError, ValueError):
                text, ok = "", False
            self.done.emit(callback, text, ok)

        thread = threading.Thread(target=run, name="catalogue", daemon=True)
        self.threads.append(thread)
        thread.start()

    def wait(self, timeout: float | None = None) -> None:
        for thread in self.threads:
            thread.join(timeout)


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

    def cancel(self, name: str | None = None) -> None:
        """Stop the download in progress, or only if it is of the pack named, keeping its .part file (P4-T6f)."""
        if name is None or (self.busy and self.entry is not None and self.entry.name == name):
            self._cancel.set()

    @property
    def downloading(self) -> list:
        """The pack being downloaded, by name, for the pack manager (P4-T6f)."""
        return [self.entry.name] if self.busy and not self._cancel.is_set() else []

    def wait(self, timeout: float | None = None) -> None:
        if self.thread is not None:
            self.thread.join(timeout)

    def _run(self, entry, folder: Path) -> None:
        part = folder / install.part_name(entry)
        record = folder / install.record_name(entry)
        final = folder / install.file_name(entry)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            ok = self._fetch(entry, part, record)
        except (OSError, ValueError):   # no connection, a bad address, a full disk: the part is kept to carry on
            self.finished.emit(entry, None, install.failed(entry))
            return
        if ok is None:   # cancelled: the part is kept to carry on (P4-T6f)
            self.finished.emit(entry, None, "")
            return
        if not ok:
            self._remove(part)
            self._remove(record)
            self.finished.emit(entry, None, install.damaged(entry))
            return
        self._remove(record)
        if final.exists():
            # An update (P4-T6d): the pack in use is open, and Windows cannot replace an open file, so the window,
            # on its own thread, closes it and puts this one in its place. The checked file is left as .part.
            self.finished.emit(entry, part, install.done(entry))
            return
        try:
            os.replace(part, final)
        except OSError:
            self._remove(part)
            self.finished.emit(entry, None, install.failed(entry))
            return
        self.finished.emit(entry, final, install.done(entry))

    @staticmethod
    def _held(part: Path, record: Path, entry) -> int:
        """Where this download starts: the bytes of a .part file of this very version, else 0 (the core decides)."""
        try:
            size = part.stat().st_size if part.exists() else 0
            text = record.read_text(encoding="utf-8") if record.exists() else None
        except OSError:
            return 0
        return install.resume_from(entry, text, size)

    def _fetch(self, entry, part: Path, record: Path) -> bool | None:
        """The bytes into the .part file. True when they match the catalogue, False when not, None when cancelled."""
        download = install.Download(entry)
        asked = self._held(part, record, entry)
        if asked:   # what is held is hashed first, so the checksum covers the whole file
            with open(part, "rb") as held:
                while download.received < asked:
                    if self._cancel.is_set():
                        return None
                    chunk = held.read(min(CHUNK, asked - download.received))
                    if not chunk:
                        break
                    download.held(chunk)
            asked = download.received
        source = self.opener(entry.url_desktop, asked) if asked else self.opener(entry.url_desktop)
        try:
            start = install.reply_start(asked, getattr(source, "status", None) or 200)
            if start is None:
                raise OSError("the reply to the range request was no use")
            if start == 0:
                download.restart()
                record.write_text(install.part_record(entry), encoding="utf-8")
                out = open(part, "wb")
            else:
                self.said.emit(install.carrying_on(entry, start))
                out = open(part, "r+b")
                out.seek(start)
                out.truncate()
            with out:
                while True:
                    if self._cancel.is_set():
                        return None
                    chunk = source.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    words = download.add(chunk)
                    if download.too_long:   # more than the catalogue says: not the pack it names
                        return False
                    if words:
                        self.said.emit(words)
        finally:
            close = getattr(source, "close", None)
            if close:
                close()
        return download.end()[0]

    @staticmethod
    def _remove(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass
