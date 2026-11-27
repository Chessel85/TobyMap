"""Installing a pack from the catalogue (P4-T6b, PCK-5, architecture 6.10).

What both shells need when they download a pack, so neither has its own copy (AD-1): whether this
version of TobyMap may install it, the file names to write, the progress to say at most every 10
percent, and whether the bytes that came are the pack the catalogue named. Nothing here touches the
network or a file: the shell fetches the bytes, hashes them as they come, and asks.
Every word is from the templates (packs.install_*).
"""
from __future__ import annotations

import re

from mapcore.describe import say
from mapcore.packs.catalogue import CatalogueError, Entry
from mapcore.packs.pack import _compare, version_tuple

STEP = 10                  # progress is said at most every 10 percent
PART = ".part"             # a download in progress: name.pack.part, renamed into place when checked (P4-T6f resumes it)
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


def matches(entry: Entry, size: int, sha256: str) -> bool:
    """Whether the bytes downloaded are the pack the catalogue names: its size and its checksum."""
    return size == entry.size and isinstance(sha256, str) and sha256.lower() == entry.sha256.lower()


class Progress:
    """The words to say as a download goes on: at most one line for each 10 percent passed, never 100
    (the end is said by done or damaged)."""

    def __init__(self, entry: Entry):
        self.entry = entry
        self.said = 0

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
