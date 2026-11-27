"""Installing a pack from the catalogue (P4-T6b, PCK-5, architecture 6.10).

What both shells need when they download a pack, so neither has its own copy (AD-1): whether this
version of TobyMap may install it, the file names to write, the progress to say at most every 10
percent, and whether the bytes that came are the pack the catalogue named. Nothing here touches the
network or a file: the shell fetches the bytes, hashes them as they come, and asks.
Every word is from the templates (packs.install_*).
"""
from __future__ import annotations

import hashlib
import json
import re

from mapcore.describe import say
from mapcore.packs.catalogue import CatalogueError, Entry
from mapcore.packs.pack import _compare, version_tuple

STEP = 10                  # progress is said at most every 10 percent
MEGABYTE = 1_000_000
PART = ".part"             # a download in progress: name.pack.part, renamed into place when checked (P4-T6f resumes it)
RECORD = ".json"           # beside it, name.pack.part.json: which version of the pack the .part file holds (P4-T6f)
PARTIAL = 206              # the reply to a range request that was honoured
WHOLE = 200                # the reply with the whole file: the server ignored the range
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def label(entry: Entry) -> str:
    """The pack as it is said: its title, or its name when it has none."""
    return entry.title or entry.name


def file_name(entry: Entry) -> str:
    """The installed pack's file name in the packs folder. A name that could reach outside the folder is refused."""
    if not _SAFE_NAME.fullmatch(entry.name) or ".." in entry.name:
        raise CatalogueError("packs.catalogue_field", name=entry.name, field="name")
    return f"{entry.name}.pack"


def part_name(entry: Entry) -> str:
    """The file a download goes into until it is checked."""
    return file_name(entry) + PART


def record_name(entry: Entry) -> str:
    """The small file beside the .part file that says which version of the pack it holds (P4-T6f)."""
    return part_name(entry) + RECORD


# Cancel and resume (P4-T6f, PCK-5) ------------------------------------------------------------------
# A download that stops (cancelled, the connection lost, TobyMap closed) keeps its .part file. The next download of
# the same entry carries on from the bytes held, by a range request, if the record beside the part says it is the
# same version; otherwise it starts again from the beginning.

def part_record(entry: Entry) -> str:
    """The text of the record written beside a new .part file."""
    return json.dumps({"name": entry.name, "version": entry.version, "size": entry.size, "sha256": entry.sha256.lower()})


def _record_fits(entry: Entry, record) -> bool:
    if isinstance(record, str):
        try:
            record = json.loads(record)
        except ValueError:
            return False
    if not isinstance(record, dict):
        return False
    return (record.get("name") == entry.name and record.get("version") == entry.version
            and record.get("size") == entry.size and str(record.get("sha256", "")).lower() == entry.sha256.lower())


def resume_from(entry: Entry, record, held: int) -> int:
    """Where a download of entry starts: the bytes already held in its .part file, when the record beside it (its text
    or a dictionary, None when there is none) is for this very version and the part is not yet whole; otherwise 0,
    and the part is started again. A part that is whole, or more, is started again too: it was not the pack."""
    held = int(held or 0)
    if held <= 0 or held >= entry.size or not _record_fits(entry, record):
        return 0
    return held


def reply_start(asked: int, status: int) -> int | None:
    """Where the bytes of a reply begin, from what was asked for and the reply's status: the place asked for when a
    range was honoured, 0 when the whole file came (the part is started again), None when the reply is no use."""
    if asked > 0 and status == PARTIAL:
        return asked
    if status == WHOLE or (asked == 0 and status == PARTIAL):
        return 0
    return None


def part_held(entry: Entry, parts: dict | None) -> int:
    """The bytes of entry held in a .part file that a download would carry on from. parts maps a pack's name to
    {"record": the record's text, "size": the .part file's size}, as the shell finds them."""
    part = (parts or {}).get(entry.name)
    if not isinstance(part, dict):
        return 0
    return resume_from(entry, part.get("record"), part.get("size", 0))


def percent(entry: Entry, done: int) -> int:
    """How much of the pack is held, in whole percent, rounded down."""
    return min(int(done) * 100 // entry.size, 99) if entry.size > 0 else 0


def cancelled(entry: Entry) -> str:
    return say("packs.install_cancelled", name=label(entry))


def carrying_on(entry: Entry, done: int) -> str:
    return say("packs.install_carry_on", name=label(entry), percent=percent(entry, done))


def refusal(entry: Entry, app_version: str) -> str | None:
    """Why this version of TobyMap will not install the pack, in words, or None when it may."""
    try:
        file_name(entry)
    except CatalogueError as e:
        return e.message
    if entry.compatible(app_version):
        return None
    have = version_tuple(app_version)
    need = version_tuple(entry.app_versions["from"])
    if have is not None and need is not None and _compare(have, need) >= 0 and entry.app_versions.get("before"):
        return say("packs.install_too_new", name=label(entry), before=entry.app_versions["before"], have=app_version)
    return say("packs.install_too_old", name=label(entry), need=entry.app_versions["from"], have=app_version)


def _megabytes(size: int, up: bool) -> int:
    whole, rest = divmod(max(int(size), 0), MEGABYTE)
    return whole + (1 if up and rest else 0)


def no_room(entry: Entry, free: int | None) -> str | None:
    """Why the pack will not fit in the space the browser has left for TobyMap, with what is left, or None when
    it fits or the space is not known (P4-T6c, architecture 9.3). The need is rounded up and what is left down."""
    if free is None or free >= entry.size:
        return None
    return say("packs.install_no_room", name=label(entry), need=_megabytes(entry.size, True),
               left=_megabytes(free, False))


def matches(entry: Entry, size: int, sha256: str) -> bool:
    """Whether the bytes downloaded are the pack the catalogue names: its size and its checksum."""
    return size == entry.size and isinstance(sha256, str) and sha256.lower() == entry.sha256.lower()


class Progress:
    """The words to say as a download goes on: at most one line for each 10 percent passed, never 100
    (the end is said by done or damaged)."""

    def __init__(self, entry: Entry, done: int = 0):
        self.entry = entry
        self.said = 0
        if done:
            self.update(done)   # a download that carries on: the percent held is not said again

    def update(self, done: int) -> str | None:
        total = self.entry.size
        if total <= 0:
            return None
        percent = min(done * 100 // total, 100) // STEP * STEP
        if percent <= self.said or percent >= 100:
            return None
        self.said = percent
        return say("packs.install_progress", name=label(self.entry), percent=percent)


def done(entry: Entry) -> str:
    return say("packs.install_done", name=label(entry))


def damaged(entry: Entry) -> str:
    return say("packs.install_damaged", name=label(entry))


def failed(entry: Entry) -> str:
    return say("packs.install_failed", name=label(entry))


def busy(entry: Entry) -> str:
    return say("packs.install_busy", name=label(entry))


class Download:
    """One download as it goes on, for a shell that hands over the bytes as they come (both versions, P4-T6c,
    P4-T6f): their checksum, the progress to say, and at the end whether they are the pack the catalogue
    names, with the words to say. A download that carries on hands over the bytes already held first, with held,
    a piece at a time, so the checksum covers the whole file and nothing is said for them."""

    def __init__(self, entry: Entry):
        self.entry = entry
        self.progress = Progress(entry)
        self.digest = hashlib.sha256()
        self.received = 0

    def held(self, data: bytes) -> None:
        self.digest.update(data)
        self.received += len(data)
        self.progress = Progress(self.entry, self.received)

    def restart(self) -> None:
        """The server sent the whole file after all: everything is counted again from the beginning."""
        self.progress = Progress(self.entry)
        self.digest = hashlib.sha256()
        self.received = 0

    @property
    def too_long(self) -> bool:
        """More bytes than the catalogue says: not the pack it names."""
        return self.received > self.entry.size

    def add(self, data: bytes) -> str | None:
        self.digest.update(data)
        self.received += len(data)
        return self.progress.update(self.received)

    def end(self) -> tuple[bool, str]:
        ok = matches(self.entry, self.received, self.digest.hexdigest())
        return ok, done(self.entry) if ok else damaged(self.entry)
