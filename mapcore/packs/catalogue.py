"""The catalogue of published packs (P4-T6a, PCK-2, PCK-4, PCK-5, architecture 6.10).

catalogue.json is read from text the shell hands over; nothing here touches the
network or a file. Messages come from the templates (packs.catalogue_*).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from mapcore.describe import say
from mapcore.packs.pack import _compare, version_tuple

FORMAT = 1
INSTALLED = "installed"
NOT_INSTALLED = "not installed"
UPDATE = "update available"


class CatalogueError(Exception):
    """A catalogue that cannot be used. The message is from the templates."""

    def __init__(self, template: str = "packs.catalogue_unreadable", **values):
        self.values = values
        super().__init__(say(template, **values))

    @property
    def message(self) -> str:
        return str(self)


def _bad(name: str, field_name: str) -> CatalogueError:
    return CatalogueError("packs.catalogue_field", name=name, field=field_name)


def _order(version: str) -> tuple[int, ...] | None:
    """Pack versions may be dotted numbers ("2026.11.1") or dates ("2026-11-20"): the numbers in them, in order."""
    numbers = re.findall(r"\d+", version) if isinstance(version, str) else []
    return tuple(int(n) for n in numbers) or None


@dataclass(frozen=True)
class Entry:
    name: str
    version: str
    date: str
    size: int
    sha256: str
    url_desktop: str
    url_web: str
    app_versions: dict
    title: str = ""
    coverage: str = ""
    depends: list = field(default_factory=list)
    sources: dict = field(default_factory=dict)

    def compatible(self, app_version: str) -> bool:
        have = version_tuple(app_version)
        if have is None:
            return False
        if _compare(have, version_tuple(self.app_versions["from"])) < 0:
            return False
        before = self.app_versions.get("before")
        return not (before and _compare(have, version_tuple(before)) >= 0)


@dataclass(frozen=True)
class Catalogue:
    entries: tuple

    def get(self, name: str) -> Entry | None:
        return next((e for e in self.entries if e.name == name), None)

    def state(self, entry: Entry, installed: dict, app_version: str) -> str:
        """installed maps a pack's name to its installed version. An update is offered only if this app can use it."""
        have = installed.get(entry.name)
        if have is None:
            return NOT_INSTALLED
        mine, theirs = _order(have), _order(entry.version)
        newer = mine is None or (theirs is not None and _compare(theirs, mine) > 0)
        if newer and have != entry.version and entry.compatible(app_version):
            return UPDATE
        return INSTALLED


def _string(raw: dict, key: str, name: str, optional: bool = False) -> str:
    value = raw.get(key, "" if optional else None)
    if not isinstance(value, str) or (not value and not optional):
        raise _bad(name, key)
    return value


def _entry(raw, seen: set) -> Entry:
    if not isinstance(raw, dict):
        raise CatalogueError("packs.catalogue_unreadable")
    name = _string(raw, "name", str(raw.get("name", "?")))
    if name in seen:
        raise CatalogueError("packs.catalogue_twice", name=name)
    seen.add(name)
    text = {k: _string(raw, k, name) for k in ("version", "date", "url_desktop", "url_web")}
    if _order(text["version"]) is None:
        raise _bad(name, "version")
    size = raw.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise _bad(name, "size")
    sha = _string(raw, "sha256", name)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha):
        raise _bad(name, "sha256")
    apps = raw.get("app_versions")
    if (not isinstance(apps, dict) or version_tuple(apps.get("from")) is None
            or ("before" in apps and version_tuple(apps["before"]) is None)):
        raise _bad(name, "app_versions")
    depends, sources = raw.get("depends", []), raw.get("sources", {})
    if not isinstance(depends, list) or not all(isinstance(d, str) for d in depends):
        raise _bad(name, "depends")
    if not isinstance(sources, dict):
        raise _bad(name, "sources")
    return Entry(name=name, size=size, sha256=sha.lower(), app_versions=dict(apps),
                 title=_string(raw, "title", name, True), coverage=_string(raw, "coverage", name, True),
                 depends=list(depends), sources=dict(sources), **text)


def parse(text: str) -> Catalogue:
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        raise CatalogueError("packs.catalogue_unreadable") from None
    if not isinstance(data, dict):
        raise CatalogueError("packs.catalogue_unreadable")
    if data.get("format") != FORMAT:
        raise CatalogueError("packs.catalogue_newer")
    packs = data.get("packs")
    if not isinstance(packs, list):
        raise CatalogueError("packs.catalogue_unreadable")
    seen: set = set()
    return Catalogue(tuple(_entry(p, seen) for p in packs))
