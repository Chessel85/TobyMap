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


def place_text(areas, why_none: str | None = None) -> str:
    """The smallest area and its parents, such as "England, United Kingdom" (LOC-2).
    No place is ever blank (LOC-3). why_none, when there are areas here but none is
    said: "layers_off", every one is in a layer that is switched off (LOC-6, SCP-6),
    or "out_of_zoom", every one is in a layer outside its zoom range (DP160). It is
    said, so you are never left in silence."""
    if not areas:
        return say(f"place.{why_none}") if why_none else say("place.none")
    return say("place.list_separator").join(area_names(areas))


def announcement(old, new, why_none: str | None = None, say_area: str = "changed") -> str | None:
    """What to say after a move, or None when only the tick plays (ANN-1). say_area is the
    verbosity switch (ACC-5, DP144): "changed", every area that changed; "smallest", only the
    smallest of them; "whole", the whole place, as Where am I says it; "off", nothing."""
    if say_area == "off":
        return None
    changed = changed_areas(old, new)
    if changed:
        if say_area == "whole":
            return place_text(new)
        return say("place.list_separator").join(area_names(changed[:1] if say_area == "smallest" else changed))
    if not new and old:
        return place_text(new, why_none)
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
    """The heading sound in space is relative to: the way the user faces in cardinal and
    free facing, or None in north-fixed (NAV-12, SON-2)."""
    return None if world.orientation == "north-fixed" else world.heading


def words_facing(world, settings) -> float | None:
    """The heading spoken directions are measured from: as facing(), but only when the
    setting asks for directions from the way you face (DP159). Otherwise None, and every
    direction is a compass direction in the chosen format, in every orientation."""
    return facing(world) if settings["relative_directions"] else None


def nearby_label(near, units: str, bearing: str, heading: float | None = None) -> str:
    """One Nearby item: the area, and the distance and direction to its nearest point (INF-3),
    relative to the way the user faces when heading is given (NAV-12)."""
    return say("nearby.item", name=near.area.name, distance=words.distance_text(near.distance_m, units),
               direction=words.direction_text(near.bearing_deg, bearing, heading))
