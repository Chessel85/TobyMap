"""Bookmarks and bookmark lists, and the one GeoJSON file that keeps them (P4-T8a; USR-1, USR-3,
USR-5, DP219, architecture 6.11).

A bookmark is always a point with a name (DP210). It keeps the name of the current feature it was
made at only as words, and a note. Bookmarks are kept in bookmark lists, each in an order the user
can change, each on or off with its own zoom range (DP212, DP213). One list, "Bookmarks", exists at
first, and there is always at least one.

The file is a GeoJSON FeatureCollection, so it opens in QGIS with each bookmark at its place under
its name. Each bookmark is a Point feature, with the properties name, list, feature and note; the
features come list by list, each list's bookmarks in its own order. The lists themselves, in their
order, with whether each is on and its zoom range, and the list used last, are in the top-level
member "tobymap", which GeoJSON readers that do not know it leave alone (RFC 7946, 6.1).

This module does no I/O. The session makes the file's text and the shells write it (rule 2).
Reading checks everything first, so a file that is not a bookmark file changes nothing.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field

from mapcore.describe import say

FORMAT = "TobyMap bookmarks"
VERSION = 1
FIRST_LIST = "Bookmarks"
LAYER = "bookmarks"   # the Bookmarks layer, a layer of TobyMap's own, in no pack (P4-T8f, SCP-6)


class BookmarkFileError(ValueError):
    """A file that is not a bookmark file, or a damaged one. reason is one of not_json, not_geojson,
    not_bookmarks, newer and damaged, and, for a file opened in the bookmark manager (P4-T9b, P4-T9c), neither
    (neither GeoJSON nor GPX) and no_waypoints (a GPX file without any); text is what TobyMap says about it,
    from the templates."""

    def __init__(self, reason: str):
        self.reason = reason
        self.text = say(f"bookmarks.file.{reason}")
        super().__init__(self.text)


@dataclass
class Bookmark:
    name: str
    lat: float
    lon: float
    feature: str = ""   # the current feature's name when it was made, as words only (DP210)
    note: str = ""


@dataclass
class BookmarkList:
    name: str
    bookmarks: list[Bookmark] = field(default_factory=list)
    on: bool = True
    min_zoom_m: float = 0.0             # the closest zoom it is shown at, as a layer's (NAV-13, DP213)
    max_zoom_m: float | None = None     # the farthest; None for no limit

    def in_zoom(self, zoom_m: float) -> bool:
        """Whether a zoom distance is within the list's zoom range, as a layer's (P4-T8f)."""
        return self.min_zoom_m <= zoom_m <= (math.inf if self.max_zoom_m is None else self.max_zoom_m)


@dataclass(frozen=True)
class Spot:
    """A bookmark as the Bookmarks group of the Information panel holds it (P4-T8c): enough of a feature's
    shape (id, name, layer) for Space to hear it and the panel to say it. It is a point, never a feature (DP210)."""
    id: str
    name: str
    lat: float
    lon: float
    layer: str = LAYER
    record: dict = field(default_factory=dict)


def _name(text) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("a name must have something in it")
    return text.strip()


def _point(lat, lon) -> tuple[float, float]:
    lat, lon = float(lat), float(lon)
    if not (math.isfinite(lat) and math.isfinite(lon)) or abs(lat) > 90:
        raise ValueError("the point is not on the globe")
    if not -180.0 <= lon <= 180.0:
        lon = (lon + 180.0) % 360.0 - 180.0
    return lat, lon


def _zoom(low, high) -> tuple[float, float | None]:
    low = float(low or 0.0)
    high = None if high is None else float(high)
    if low < 0 or not math.isfinite(low) or (high is not None and (not math.isfinite(high) or high < low)):
        raise ValueError("the minimum zoom must not be larger than the maximum zoom")
    return low, high


@dataclass
class Bookmarks:
    """Every bookmark list, in order, and the list used last (by its place in that order). Lists and
    bookmarks are given by their place: li for a list, bi for a bookmark in it."""

    lists: list[BookmarkList] = field(default_factory=lambda: [BookmarkList(FIRST_LIST)])
    last_used: int = 0

    # Names ----------------------------------------------------------------------------------------

    def unique_name(self, name: str) -> str:
        """The name for a new bookmark, numbered if a bookmark in any list already has it: Rome,
        Rome_1, Rome_2, the first number free (USR-1, DP211). Every list is looked in, because a
        bookmark is said with its list only in the Bookmarks group; on the map, in Details and as the
        current feature, two lists' Romes would sound the same. The user may still keep a used name."""
        used = {m.name for l in self.lists for m in l.bookmarks}
        if name not in used:
            return name
        n = 1
        while f"{name}_{n}" in used:
            n += 1
        return f"{name}_{n}"

    def _list_name_used(self, name: str, besides: int | None = None) -> bool:
        key = name.casefold()
        return any(l.name.casefold() == key for i, l in enumerate(self.lists) if i != besides)

    def free_list_name(self, name: str) -> str:
        """A list name not yet used, for a list opened from a file: "My favourite castles 2" (USR-5, DP217)."""
        name = _name(name)
        if not self._list_name_used(name):
            return name
        n = 2
        while self._list_name_used(f"{name} {n}"):
            n += 1
        return f"{name} {n}"

    def index_of(self, list_name: str) -> int | None:
        key = list_name.casefold()
        return next((i for i, l in enumerate(self.lists) if l.name.casefold() == key), None)

    # Bookmarks ------------------------------------------------------------------------------------

    def add(self, li: int, name: str, lat: float, lon: float, feature: str = "", note: str = "") -> int:
        """A new bookmark at the end of list li, which becomes the list used last (DP211). The name is
        kept as given: unique_name() is what the bookmark dialog fills in. Returns its place."""
        target = self.lists[li]
        lat, lon = _point(lat, lon)
        target.bookmarks.append(Bookmark(_name(name), lat, lon, feature or "", note or ""))
        self.last_used = li
        return len(target.bookmarks) - 1

    def rename(self, li: int, bi: int, name: str) -> None:
        self.lists[li].bookmarks[bi].name = _name(name)

    def set_note(self, li: int, bi: int, note: str) -> None:
        self.lists[li].bookmarks[bi].note = note or ""

    def delete(self, li: int, bi: int) -> Bookmark:
        return self.lists[li].bookmarks.pop(bi)

    def move(self, li: int, bi: int, by: int) -> int:
        """Up (by -1) or down (+1) in its list; at either end it stays. Returns its new place."""
        marks = self.lists[li].bookmarks
        to = max(0, min(len(marks) - 1, bi + by))
        marks.insert(to, marks.pop(bi))
        return to

    def copy_to(self, li: int, bi: int, target: int) -> int:
        """A copy at the end of another list; the original stays. Returns the copy's place."""
        marks = self.lists[target].bookmarks
        marks.append(copy.copy(self.lists[li].bookmarks[bi]))
        return len(marks) - 1

    def move_to(self, li: int, bi: int, target: int) -> int:
        """Out of its list and onto the end of another. Returns its new place there."""
        marks = self.lists[target].bookmarks
        marks.append(self.lists[li].bookmarks.pop(bi))
        return len(marks) - 1

    # Lists ----------------------------------------------------------------------------------------

    def new_list(self, name: str) -> int:
        """A new, empty list at the end. A name already used, in any capitals, is refused (ValueError),
        so the dialog can ask for another. Returns its place."""
        name = _name(name)
        if self._list_name_used(name):
            raise ValueError("there is already a bookmark list with that name")
        self.lists.append(BookmarkList(name))
        return len(self.lists) - 1

    def add_lists(self, lists: list[BookmarkList]) -> list[int]:
        """Lists opened from a file, after yours, each under a free name: "Castles 2" beside your Castles. Nothing is
        merged or replaced, and the list used last stays the same (USR-5, DP217). Returns their places."""
        places = []
        for lst in lists:
            made = copy.deepcopy(lst)
            made.name = self.free_list_name(lst.name)
            self.lists.append(made)
            places.append(len(self.lists) - 1)
        return places

    def rename_list(self, li: int, name: str) -> None:
        name = _name(name)
        if self._list_name_used(name, besides=li):
            raise ValueError("there is already a bookmark list with that name")
        self.lists[li].name = name

    def move_list(self, li: int, by: int) -> int:
        """Up or down in the order of lists; the list used last stays the same list. Returns its new place."""
        used = self.lists[self.last_used]
        to = max(0, min(len(self.lists) - 1, li + by))
        self.lists.insert(to, self.lists.pop(li))
        self.last_used = self.lists.index(used)
        return to

    def delete_list(self, li: int) -> BookmarkList:
        """A list and its bookmarks. The last list left is replaced by an empty "Bookmarks", so there is
        always a list to bookmark into. The list used last becomes the first if it was this one."""
        used = self.lists[self.last_used]
        gone = self.lists.pop(li)
        if not self.lists:
            self.lists.append(BookmarkList(FIRST_LIST))
        self.last_used = 0 if used is gone else self.lists.index(used)
        return gone

    def set_on(self, li: int, on: bool) -> None:
        self.lists[li].on = bool(on)

    def set_zoom(self, li: int, min_zoom_m: float, max_zoom_m: float | None) -> None:
        """The list's zoom range, as a layer's: ValueError if the minimum is larger than the maximum."""
        self.lists[li].min_zoom_m, self.lists[li].max_zoom_m = _zoom(min_zoom_m, max_zoom_m)

    def use(self, li: int) -> None:
        self.lists[li]   # IndexError for a list that is not there
        self.last_used = li

    # The file ------------------------------------------------------------------------------------

    def to_geojson(self) -> dict:
        features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [m.lon, m.lat]},
                     "properties": {"name": m.name, "list": l.name, "feature": m.feature, "note": m.note}}
                    for l in self.lists for m in l.bookmarks]
        lists = [{"name": l.name, "on": l.on, "min_zoom_m": l.min_zoom_m, "max_zoom_m": l.max_zoom_m}
                 for l in self.lists]
        return {"type": "FeatureCollection",
                "tobymap": {"format": FORMAT, "version": VERSION, "last_used": self.lists[self.last_used].name,
                            "lists": lists},
                "features": features}

    def to_text(self) -> str:
        """The file's text: the same bookmarks always give the same text."""
        return json.dumps(self.to_geojson(), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_geojson(cls, data) -> "Bookmarks":
        """Everything is checked before anything is made: BookmarkFileError if it is not a bookmark file."""
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection" \
                or not isinstance(data.get("features"), list):
            raise BookmarkFileError("not_geojson")
        own = data.get("tobymap")
        if not isinstance(own, dict) or own.get("format") != FORMAT:
            raise BookmarkFileError("not_bookmarks")
        version = own.get("version")
        if isinstance(version, int) and not isinstance(version, bool) and version > VERSION:
            raise BookmarkFileError("newer")
        try:
            return cls._read(own, data["features"])
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise BookmarkFileError("damaged") from error

    @classmethod
    def _read(cls, own: dict, features: list) -> "Bookmarks":
        if own.get("version") != VERSION or not isinstance(own.get("lists"), list) or not own["lists"]:
            raise ValueError("no lists")
        made = cls(lists=[])
        for entry in own["lists"]:
            if not isinstance(entry["on"], bool):
                raise ValueError("on is not true or false")
            name = _name(entry["name"])
            if made._list_name_used(name):
                raise ValueError("a list twice")
            low, high = _zoom(_number(entry.get("min_zoom_m", 0.0)), _number(entry.get("max_zoom_m")))
            made.lists.append(BookmarkList(name, on=entry["on"], min_zoom_m=low, max_zoom_m=high))
        for f in features:
            geometry, props = f["geometry"], f["properties"]
            if f["type"] != "Feature" or geometry["type"] != "Point" or len(geometry["coordinates"]) < 2:
                raise ValueError("not a point")
            lon, lat = (_number(v) for v in geometry["coordinates"][:2])
            if lon is None or lat is None or abs(lon) > 180:
                raise ValueError("not a point")
            li = made.index_of(_name(props["list"]))
            if li is None:
                raise ValueError("a bookmark in no list")
            feature, note = props.get("feature"), props.get("note")
            if not all(v is None or isinstance(v, str) for v in (feature, note)):
                raise ValueError("feature and note are words")
            made.lists[li].bookmarks.append(Bookmark(_name(props["name"]), *_point(lat, lon), feature or "", note or ""))
        used = own.get("last_used")
        made.last_used = (made.index_of(used) if isinstance(used, str) else None) or 0
        return made

    @classmethod
    def from_text(cls, text: str) -> "Bookmarks":
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as error:
            raise BookmarkFileError("not_json") from error
        return cls.from_geojson(data)

    def replace_from_text(self, text: str) -> None:
        """These bookmarks become the file's; on BookmarkFileError nothing changes."""
        made = Bookmarks.from_text(text)
        self.lists, self.last_used = made.lists, made.last_used


def _number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("not a number")
    return float(value)


def load(text: str | None) -> tuple[Bookmarks, bool]:
    """The bookmarks from the file's text as the shell read it at start, and whether the file was
    damaged. No file (None or empty) gives one empty "Bookmarks" list; so does a damaged file, which
    the shell then sets aside (P4-T8a)."""
    if text is None or not text.strip():
        return Bookmarks(), False
    try:
        return Bookmarks.from_text(text), False
    except BookmarkFileError:
        return Bookmarks(), True
