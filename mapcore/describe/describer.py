"""What the application says about the location (P1-T7; ANN-1, LOC-1, LOC-2, LOC-7, INF-7).

Pure functions over areas, distances and the world state. They return text; the
session decides when to speak it.
"""
from __future__ import annotations

from mapcore.describe import say
from mapcore.describe import words


def area_names(areas) -> list[str]:
    return [a.name for a in areas]


def changed_areas(old, new) -> list:
    """ANN-1: the areas of the new place that were not in the old one, from
    smallest to largest. `old` and `new` are lists of areas, smallest first.
    Nothing changed gives an empty list: only the tick plays."""
    seen = {a.id for a in old}
    return [a for a in new if a.id not in seen]


def place_text(areas) -> str:
    """The smallest area and its parents, such as "England, United Kingdom" (LOC-2).
    No place is ever blank (LOC-3)."""
    if not areas:
        return say("place.none")
    return say("place.list_separator").join(area_names(areas))


def announcement(old, new) -> str | None:
    """What to say after a move, or None when only the tick plays (ANN-1)."""
    changed = changed_areas(old, new)
    if changed:
        return say("place.list_separator").join(area_names(changed))
    if not new and old:
        return say("place.none")
    return None


def zoom_step_text(world, units: str) -> str:
    return say("movement.zoom_step", zoom=words.distance_text(world.zoom_m, units),
               step=words.distance_text(world.step_m, units))


def heading_report(world, units: str) -> str:
    """H (LOC-7): "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres." """
    return say("movement.heading", facing=say("movement.facing", heading=words.heading_text(world.heading)),
               orientation=say(f"movement.orientation.{world.orientation}"),
               mode=say(f"movement.mode.{world.movement_mode}"),
               zoom=words.distance_text(world.zoom_m, units), step=words.distance_text(world.step_m, units))


def nearby_label(near, units: str, bearing: str) -> str:
    """One Nearby item: the area, and the distance and direction to its nearest point (INF-3)."""
    return say("nearby.item", name=near.area.name, distance=words.distance_text(near.distance_m, units),
               direction=words.bearing_text(near.bearing_deg, bearing))
