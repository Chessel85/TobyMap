"""Saving and opening bookmark files, as GeoJSON or GPX (P4-T9b, P4-T9c; USR-5, DP209, DP217, DP219).

Saving makes a file's text from one bookmark list or all of them:

* GeoJSON: the same format as TobyMap's own bookmarks file (mapcore.bookmarks), so a file of all the lists is that file,
  and a file of one list holds that list alone, with whether it is on and its zoom range. It opens in QGIS with each
  bookmark at its place under its name.
* GPX 1.1: one waypoint (wpt) for each bookmark, with its name, its note as desc, and the list's name and the feature's
  name in extensions of TobyMap's own, which other programs leave alone. The list's name, or "TobyMap bookmarks" for
  all lists, is the file's metadata name.

Opening reads a file's text, choosing GeoJSON or GPX from its content, not its name, into new bookmark lists. Nothing
is changed here: the session adds the lists after yours, each under a free name (Bookmarks.add_lists). Everything is
checked first, so a file that is not a bookmark file raises BookmarkFileError and changes nothing (DP217).

* A GeoJSON file of TobyMap's opens as its lists. A GeoJSON file of points from another program, such as QGIS, opens
  into one list named from the file, or into the lists named in each point's "list".
* A GPX file's waypoints open into one new list, named from its metadata name, else the file's name, else "Opened
  waypoints". A GPX file saved by TobyMap with all the lists opens as those lists again. Routes and tracks are left out,
  and counted, so the session can say how many.

This module does no I/O, and uses only the standard library (json, xml.etree).
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from mapcore.bookmarks import Bookmark, BookmarkFileError, BookmarkList, Bookmarks, _name, _point
from mapcore.describe import say

GPX_NS = "http://www.topografix.com/GPX/1/1"
GPX_10_NS = "http://www.topografix.com/GPX/1/0"
OWN_NS = "https://github.com/Chessel85/TobyMap/gpx/1"   # TobyMap's own extensions: the list and the feature
TYPES = {   # each kind of file: its extension, the Save box's filter and the browser download's type
    "geojson": {"extension": "geojson", "mime": "application/geo+json"},
    "gpx": {"extension": "gpx", "mime": "application/gpx+xml"},
}
_NOT_IN_A_FILE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class Opened:
    """What a file held: its lists, with their own names (the session gives each a free name), the kind of file, and
    how many GPX routes and tracks were left out."""
    lists: list[BookmarkList] = field(default_factory=list)
    kind: str = "geojson"
    left_out: int = 0


def _chosen(b: Bookmarks, li: int | None) -> Bookmarks:
    return b if li is None else Bookmarks(lists=[b.lists[li]], last_used=0)


# Saving --------------------------------------------------------------------------------------------------

def geojson_text(b: Bookmarks, li: int | None = None) -> str:
    """The GeoJSON file of list li, or of all the lists when li is None."""
    return _chosen(b, li).to_text()


def _decimal(value: float) -> str:
    """A coordinate as GPX wants it, a plain decimal with no exponent, to a nine-figure fraction (under a millimetre)."""
    return f"{value:.9f}".rstrip("0").rstrip(".")


def gpx_text(b: Bookmarks, li: int | None = None) -> str:
    """The GPX 1.1 file of list li, or of all the lists when li is None: one waypoint for each bookmark, in order."""
    chosen = _chosen(b, li)
    ET.register_namespace("", GPX_NS)
    ET.register_namespace("tobymap", OWN_NS)
    root = ET.Element(f"{{{GPX_NS}}}gpx", {"version": "1.1", "creator": "TobyMap"})
    metadata = ET.SubElement(root, f"{{{GPX_NS}}}metadata")
    ET.SubElement(metadata, f"{{{GPX_NS}}}name").text = b.lists[li].name if li is not None else say("bookmark_files.all_name")
    for lst in chosen.lists:
        for m in lst.bookmarks:
            wpt = ET.SubElement(root, f"{{{GPX_NS}}}wpt", {"lat": _decimal(m.lat), "lon": _decimal(m.lon)})
            ET.SubElement(wpt, f"{{{GPX_NS}}}name").text = m.name
            if m.note:
                ET.SubElement(wpt, f"{{{GPX_NS}}}desc").text = m.note
            extensions = ET.SubElement(wpt, f"{{{GPX_NS}}}extensions")
            ET.SubElement(extensions, f"{{{OWN_NS}}}list").text = lst.name
            if m.feature:
                ET.SubElement(extensions, f"{{{OWN_NS}}}feature").text = m.feature
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def file_text(b: Bookmarks, li: int | None, kind: str) -> str:
    return gpx_text(b, li) if kind == "gpx" else geojson_text(b, li)


def file_name(b: Bookmarks, li: int | None, extension: str) -> str:
    """The file name the Save box suggests: the list's name, without the characters Windows refuses in a file name, or
    "TobyMap bookmarks" for all the lists."""
    stem = say("bookmark_files.all_name") if li is None else b.lists[li].name
    stem = " ".join(_NOT_IN_A_FILE_NAME.sub(" ", stem).split()).strip(" .") or say("bookmark_files.all_name")
    return f"{stem}.{extension}"


# Opening -------------------------------------------------------------------------------------------------

def _stem(file_name: str) -> str:
    """A file's name without its folder or its extension: "Walks in Wales" from "C:/walks/Walks in Wales.gpx"."""
    base = re.split(r"[\\/]", file_name or "")[-1]
    stem = base.rsplit(".", 1)[0] if "." in base.strip(".") else base
    return " ".join(stem.split())


def read(text: str, file_name: str = "") -> Opened:
    """A file's text as new lists, GeoJSON or GPX by its content. file_name, as the shell gives it, names a list when the
    file does not. BookmarkFileError, and nothing is made, if it is not a bookmark file."""
    text = (text or "").lstrip("\ufeff \t\r\n")
    if text.startswith("<"):
        return _read_gpx(text, _stem(file_name))
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as error:
        raise BookmarkFileError("neither") from error
    if isinstance(data, dict) and data.get("type") == "FeatureCollection" and "tobymap" not in data \
            and isinstance(data.get("features"), list):
        return _read_points(data["features"], _stem(file_name))
    return Opened(Bookmarks.from_geojson(data).lists, "geojson")


def _list_name(name, fallback: str) -> str:
    for candidate in (name, fallback):
        if isinstance(candidate, str) and candidate.strip():
            return " ".join(candidate.split())
    return say("bookmark_files.opened_waypoints")


def _grouped(marks: list[tuple[str | None, Bookmark]], name: str) -> list[BookmarkList]:
    """The bookmarks in lists: by each one's own list name when every one has it, else all in one list called name."""
    if marks and all(own for own, _m in marks):
        lists: dict[str, BookmarkList] = {}
        for own, m in marks:
            lists.setdefault(own.casefold(), BookmarkList(own)).bookmarks.append(m)
        return list(lists.values())
    return [BookmarkList(name, [m for _own, m in marks])]


def _words(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _read_points(features: list, stem: str) -> Opened:
    """A GeoJSON FeatureCollection of points from another program: each point a bookmark, named by its name property
    (name, Name or NAME), else "Bookmark 2" by its place. Anything but points is not a bookmark file."""
    if not features:
        raise BookmarkFileError("not_bookmarks")
    marks = []
    try:
        for number, f in enumerate(features, 1):
            geometry = f.get("geometry") if isinstance(f, dict) else None
            if not isinstance(geometry, dict) or geometry.get("type") != "Point":
                raise BookmarkFileError("not_bookmarks")
            props = f.get("properties") or {}
            if not isinstance(props, dict):
                raise ValueError("properties are not an object")
            lon, lat = (float(v) for v in geometry["coordinates"][:2])
            if not (math.isfinite(lon) and abs(lon) <= 180):
                raise ValueError("not on the globe")
            name = next((_words(props.get(k)) for k in ("name", "Name", "NAME") if _words(props.get(k))), "") \
                or say("bookmark_files.unnamed", number=number)
            mark = Bookmark(name, *_point(lat, lon), _words(props.get("feature")), _text(props.get("note")))
            marks.append((_words(props.get("list")) or None, mark))
    except BookmarkFileError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise BookmarkFileError("damaged") from error
    return Opened(_grouped(marks, _list_name(stem, "")), "geojson")


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element, name: str):
    """The first child with this local name, in whatever GPX namespace."""
    return next((c for c in element if _local(c.tag) == name), None)


def _child_text(element, name: str) -> str:
    child = _child(element, name)
    return (child.text or "").strip() if child is not None else ""


def _read_gpx(text: str, stem: str) -> Opened:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise BookmarkFileError("neither") from error
    if root.tag not in ("gpx", f"{{{GPX_NS}}}gpx", f"{{{GPX_10_NS}}}gpx"):
        raise BookmarkFileError("neither")
    wpts = [c for c in root if _local(c.tag) == "wpt"]
    left_out = sum(1 for c in root if _local(c.tag) in ("rte", "trk"))
    if not wpts:
        raise BookmarkFileError("no_waypoints")
    marks = []
    try:
        for number, wpt in enumerate(wpts, 1):
            lat, lon = float(wpt.attrib["lat"]), float(wpt.attrib["lon"])
            if not (math.isfinite(lat) and math.isfinite(lon)) or abs(lat) > 90 or abs(lon) > 180:
                raise ValueError("not on the globe")
            own = {}
            extensions = _child(wpt, "extensions")
            if extensions is not None:
                own = {_local(c.tag): " ".join((c.text or "").split()) for c in extensions
                       if c.tag.startswith(f"{{{OWN_NS}}}")}
            name = " ".join(_child_text(wpt, "name").split()) or say("bookmark_files.unnamed_waypoint", number=number)
            note = _child_text(wpt, "desc") or _child_text(wpt, "cmt")
            marks.append((own.get("list") or None, Bookmark(_name(name), lat, lon, own.get("feature", ""), note)))
    except (KeyError, ValueError) as error:
        raise BookmarkFileError("damaged") from error
    metadata = _child(root, "metadata")
    named = _child_text(metadata, "name") if metadata is not None else _child_text(root, "name")   # GPX 1.1, or 1.0
    return Opened(_grouped(marks, _list_name(named, stem)), "gpx", left_out)
