"""What the application says about the location (P1-T7; ANN-1, LOC-1, LOC-2, LOC-7, INF-7).

Pure functions over areas, distances and the world state. They return text; the
session decides when to speak it.
"""
from __future__ import annotations

from mapcore.describe import say
from mapcore.describe import words
from mapcore.geo import formats

HERE_M = 1.0   # closer than this, an item is "here", with no distance or direction (P2-T18e)
# The layer whose area is "its country" in the normal preset's place when nothing changed (DP162).
# Named here so the continents of Phase 3 (P3-T1e), larger than a country, are not taken for it.
COUNTRY_LAYER = "countries"


# Where am I names a town you are near (P3-T28p, Q6, LOC-5). The places of this layer are its towns.
TOWN_LAYER = "towns"
# A town's reach, the distance within which it is near: this many metres times the square root of its population,
# as a town's built-up area grows about with its population, so its width with the root. 25 metres is about two
# and a half times the radius of a town of 3,000 people to the square kilometre: Winchester, 35,000 people, 4.7 km.
TOWN_REACH_PER_ROOT_M = 25.0
TOWN_REACH_MIN_M = 2_000.0    # a small town: 2 km, a walk from its centre
TOWN_REACH_MAX_M = 30_000.0   # London and Paris: 30 km, the edge of their built-up areas
# The types that are near, and the reach of one with no population known: a city as one of about 100,000 people,
# a town as one of about 15,000, the middle of each in the Western Europe trial. Villages, hamlets and suburbs are
# not named: they are many, and a suburb is inside its town.
TOWN_REACH_BY_TYPE_M = {"city": 8_000.0, "town": 3_000.0}


def population(record: dict) -> float | None:
    """A place's population: Wikidata's, else OpenStreetMap's; None when neither is a number above 0."""
    for value in (((record.get("facts") or {}).get("population") or {}).get("value"), record.get("population")):
        try:
            if value is not None and float(value) > 0:
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def town_reach_m(record: dict) -> float | None:
    """The distance within which a town is near (P3-T28p), or None for a place of a type that is never near."""
    kind = record.get("type")
    if kind not in TOWN_REACH_BY_TYPE_M:
        return None
    people = population(record)
    if people is None:
        return TOWN_REACH_BY_TYPE_M[kind]
    return min(TOWN_REACH_MAX_M, max(TOWN_REACH_MIN_M, TOWN_REACH_PER_ROOT_M * people ** 0.5))


def near_town(nears, said_names):
    """The town to name as near (P3-T28p): of the towns within their reach, the nearest for its reach, so a small
    town you are in is said before the large city whose edge you are on; a tie goes to the larger. None when no
    town is near, or when the one chosen has the name of an area said, as Paris in the department of Paris, which
    the place says already. `nears` are Store Near results; `said_names` the names the place says."""
    best, best_key = None, None
    for n in nears:
        reach = town_reach_m(n.area.record)
        if reach is None or n.distance_m > reach:
            continue
        key = (n.distance_m / reach, -reach, n.area.id)
        if best_key is None or key < best_key:
            best, best_key = n.area, key
    if best is None or str(best.name) in {str(s) for s in said_names}:
        return None
    return best


SAME_SIZE = 0.01   # two areas of one name within this share of each other's size are the same land, said once


def same_land(a, b) -> bool:
    """Whether two areas of one name are the same land: one is named from the other, as a distant part is from
    its region (DP191), or is the other's parent, as French Guiana the country unit is of its region (DP86), or
    they are within SAME_SIZE of each other's size."""
    if a.name != b.name:
        return False
    ra, rb = getattr(a, "record", None) or {}, getattr(b, "record", None) or {}
    if ra.get("named_from") == b.id or rb.get("named_from") == a.id or rb.get("parent") == a.id \
            or ra.get("parent") == b.id:
        return True
    sa, sb = getattr(a, "area_km2", None), getattr(b, "area_km2", None)
    return sa is not None and sb is not None and abs(sa - sb) <= SAME_SIZE * max(sa, sb)


def said_once(areas) -> list:
    """The areas, leaving out one that is the same land as a smaller one already there, with its name, so it is
    said once: Hawaii the region and Hawaii the distant part of the United States (DP191, DP71)."""
    out = []
    for a in areas:
        if not any(same_land(a, b) for b in out):
            out.append(a)
    return out


def area_names(areas) -> list[str]:
    """The areas' names, smallest first, with "disputed" after the largest disputed one, so it is said once
    (P3-T2c, ANN-6). The same land in two layers, with one name, is said once."""
    areas = said_once(areas)
    names = [a.name for a in areas]
    last = max((i for i, a in enumerate(areas) if (getattr(a, "record", None) or {}).get("disputed")), default=None)
    if last is not None:
        names[last] = say("place.disputed", name=names[last])
    return names


def changed_areas(old, new) -> list:
    """ANN-1: the areas of the new place that were not in the old one, from
    smallest to largest. `old` and `new` are lists of areas, smallest first.
    Nothing changed gives an empty list: only the tick plays."""
    seen = {a.id for a in old}
    return [a for a in new if a.id not in seen]


def zoom_change_text(old, new, why_none: str | None = None) -> str:
    """What a zoom says of the place when what Space would say has changed (P4-T14a, the PO's notes on checklist
    steps 1.9 and 1.10): the smallest area added; if none was added but some went, the smallest left; with none
    left, why. `old` and `new` are the areas as said, smallest first. When nothing was said before (no data at the
    old zoom), the whole place is said, as there is nothing to hear it against."""
    kept = said_once(new)
    if not old:
        return place_text(new, why_none)
    before = {a.id for a in old}
    added = [a for a in kept if a.id not in before]
    if added:
        return area_names(added[:1])[0]
    if kept and before - {a.id for a in new}:
        return area_names(kept[:1])[0]
    return place_text(new, why_none)


def place_text(areas, why_none: str | None = None) -> str:
    """The smallest area and its parents, such as "England, United Kingdom" (LOC-2).
    No place is ever blank (LOC-3). why_none, when there are areas here but none is
    said: "layers_off", every one is in a layer that is switched off (LOC-6, SCP-6),
    or "out_of_zoom", every one is in a layer outside its zoom range (DP160). It is
    said, so you are never left in silence."""
    if not areas:
        return say(f"place.{why_none}") if why_none else say("place.none")
    return say("place.list_separator").join(area_names(areas))


def announcement(old, new, why_none: str | None = None, say_area: str = "changed",
                 always: bool = False) -> str | None:
    """What to say after a move, or None when only the tick plays (ANN-1). say_area is the
    verbosity switch (ACC-5, DP144): "changed", every area that changed; "smallest", only the
    smallest of them; "whole", the whole place, as Where am I says it; "off", nothing.
    always is the switch to say the place even when nothing changed (P2-T17q, DP162)."""
    if say_area == "off":
        return None
    changed = changed_areas(old, new)
    if changed:
        if say_area == "whole":
            return place_text(new)
        return say("place.list_separator").join(area_names(changed[:1] if say_area == "smallest" else changed))
    if not new and (old or always):
        return place_text(new, why_none)
    if always:
        return unchanged_place(new, say_area)
    return None


def unchanged_place(areas, say_area: str) -> str:
    """The place said when nothing changed and the switch says to say it anyway (P2-T17q, DP162):
    "smallest", the smallest area; "changed", the smallest area and its country, or the largest
    area where there is no country, such as at sea; "whole", the whole place."""
    if say_area == "whole":
        return place_text(areas)
    said = [areas[0]]
    if say_area == "changed":
        top = next((a for a in areas if a.layer == COUNTRY_LAYER), areas[-1])
        if top is not areas[0]:
            said.append(top)
    return say("place.list_separator").join(area_names(said))


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
    key = "nearby.here" if near.distance_m < HERE_M else "nearby.item"   # such as a station you went to (P2-T18e)
    return say(key, name=near.area.name, distance=words.distance_text(near.distance_m, units),
               direction=words.direction_text(near.bearing_deg, bearing, heading))
