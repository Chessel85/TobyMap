"""What the application says about the location (P1-T7; ANN-1, LOC-1, LOC-2, LOC-7, INF-7).

Pure functions over areas, distances and the world state. They return text; the
session decides when to speak it.
"""
from __future__ import annotations

from mapcore.describe import say
from mapcore.describe import words
from mapcore.geo import formats


def area_names(areas) -> list[str]:
    return [a.name for a in areas]


def changed_areas(old, new) -> list:
    """ANN-1: the areas of the new place that were not in the old one, from
    smallest to largest. `old` and `new` are lists of areas, smallest first.
    Nothing changed gives an empty list: only the tick plays."""
    seen = {a.id for a in old}
    return [a for a in new if a.id not in seen]


def place_text(areas, all_off: bool = False) -> str:
    """The smallest area and its parents, such as "England, United Kingdom" (LOC-2).
    No place is ever blank (LOC-3). all_off: there are areas here, but every one is
    in a layer that is switched off, which is said, so you are never left in
    silence (LOC-6, SCP-6)."""
    if not areas:
        return say("place.layers_off") if all_off else say("place.none")
    return say("place.list_separator").join(area_names(areas))


def announcement(old, new, all_off: bool = False) -> str | None:
    """What to say after a move, or None when only the tick plays (ANN-1)."""
    changed = changed_areas(old, new)
    if changed:
        return say("place.list_separator").join(area_names(changed))
    if not new and old:
        return place_text(new, all_off)
    return None


def zoom_step_text(world, units: str) -> str:
    return say("movement.zoom_step", zoom=words.distance_text(world.zoom_m, units),
               step=words.distance_text(world.step_m, units))


def facing_text(world) -> str:
    """The way the user faces: a compass point in north-fixed and cardinal facing,
    such as "east", and the exact degrees in free facing, such as "47 degrees"."""
    if world.orientation == "free":
        return say("bearing.degrees", value=formats.bearing_parts(world.heading, "exact").value)
    return words.heading_text(world.heading)


def heading_report(world, units: str) -> str:
    """H (LOC-7): "Facing north. North-fixed. Stepping. Zoom 5 kilometres, step 250 metres." """
    return say("movement.heading", facing=say("movement.facing", heading=facing_text(world)),
               orientation=say(f"movement.orientation.{world.orientation}"),
               mode=say(f"movement.mode.{world.movement_mode}"),
               zoom=words.distance_text(world.zoom_m, units), step=words.distance_text(world.step_m, units))


def facing(world) -> float | None:
    """The heading directions are relative to: the way the user faces in cardinal and
    free facing, or None in north-fixed, where directions are compass directions (NAV-12)."""
    return None if world.orientation == "north-fixed" else world.heading


def nearby_label(near, units: str, bearing: str, heading: float | None = None) -> str:
    """One Nearby item: the area, and the distance and direction to its nearest point (INF-3),
    relative to the way the user faces when heading is given (NAV-12)."""
    return say("nearby.item", name=near.area.name, distance=words.distance_text(near.distance_m, units),
               direction=words.direction_text(near.bearing_deg, bearing, heading))
