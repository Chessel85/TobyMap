"""The Information panel's group table (P3-T4a, INF-10, UX section 6).

Every group the panel has is one row here. The registry's panel_groups gives their order and
their Shift and number keys (DP156); this table gives how each behaves:

* default_sort: the order its items start in. "natural" is the order the group makes them in,
  such as Within's smallest to largest; "name", "distance" and "bearing" (clockwise from ahead)
  are the orders Ctrl+S cycles through (P3-T4d). UX section 6.1: Within natural, Nearby by
  distance, Bordering by bearing, the rest by name. Passed over (id "crossed") starts in its natural order,
  along the move, and Ctrl+S then sorts it like the others (P3-T29f). The Crossing group went in P3-T29a (INF-10): its content,
  a line's areas in order from its start and an area's lines, is in Overlapping since P3-T29e. Overlapping about a
  line starts in that order, "from its start", and Ctrl+S then sorts it like the others (MapSession._first_order).
  Search starts in the order its results came (P3-T32k): a search's as it ranked them, "best match first"; a query
  within a distance, "nearest first"; a line's areas, "from its start"; browsing and the other queries, by name.
* zoom_limited: whether it shows only visible features (ANN-7, DP80, DP160). Contains, Nearby,
  and Passed over are; Within follows the zoom ranges through "where am I"; the others
  show everything from the layers that are switched on.
* about_current: whether it is about the current feature (LOC-4), so its heading names it:
  "Bordering France, 8 items".
* lazy: filled only when it is open, so a step never waits for it (NFR-1, UX 6.1). The three
  groups of Phase 2 are filled as before, so their headings keep their counts at every step.

Each item is a dict the shells show as it is:

* id: the feature's identifier, or for a heading inside a group, such as Contains' "Regions 13",
  an id starting "heading:", which Enter, Space and the map's highlight ignore.
* label: the words shown and said.
* level: 1 for an item straight under the group, 2 for one under a heading, and so on.
* children: for a heading, the items under it.
* name, distance_m and bearing_deg: the sort keys. bearing_deg is clockwise from ahead, 0 to 360.
"""
from __future__ import annotations

from dataclasses import dataclass

HEADING_PREFIX = "heading:"
SORTS = ("name", "distance", "bearing")


@dataclass(frozen=True)
class Group:
    id: str
    default_sort: str
    zoom_limited: bool
    about_current: bool
    lazy: bool


GROUPS: dict[str, Group] = {g.id: g for g in [
    Group("within", "natural", zoom_limited=False, about_current=False, lazy=False),
    Group("nearby", "distance", zoom_limited=True, about_current=False, lazy=False),
    Group("bordering", "bearing", zoom_limited=False, about_current=True, lazy=True),
    Group("contains", "name", zoom_limited=True, about_current=True, lazy=True),
    Group("overlapping", "name", zoom_limited=False, about_current=True, lazy=True),
    Group("crossed", "natural", zoom_limited=True, about_current=False, lazy=False),   # "Passed over"
    Group("search", "natural", zoom_limited=False, about_current=False, lazy=True),   # as found (P3-T32k)
]}


def is_heading(item_id: str | None) -> bool:
    """A heading inside a group, such as Contains' "Regions 13": not a feature."""
    return bool(item_id) and str(item_id).startswith(HEADING_PREFIX)


def item(feature_id: str, label: str, name: str, distance_m: float, bearing_deg: float, level: int = 1) -> dict:
    """One item of a group, with its sort keys."""
    return {"id": feature_id, "label": label, "level": level, "name": name,
            "distance_m": distance_m, "bearing_deg": bearing_deg % 360.0}


def heading(key: str, label: str, children: list[dict], name: str | None = None) -> dict:
    """A heading inside a group, with its items one level below it."""
    for c in children:
        c["level"] = 2
    return {"id": HEADING_PREFIX + key, "label": label, "level": 1, "name": name or label,
            "children": children}


def walk(items: list[dict]):
    """Every item, and every item under a heading, in order."""
    for i in items:
        yield i
        yield from walk(i.get("children") or [])
