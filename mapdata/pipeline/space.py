"""The space a build needs, estimated before it starts (DMT-7).

Each stage that is not already finished is given a figure: a fixed part, in MB,
and a part that grows with the area the pack covers, in MB for each million
square kilometres. The pack's area is taken from the "box" its stages name
(the largest, in degrees west, south, east, north), or the whole Earth,
510 million square kilometres, for a world pack whose stages name no box. A
pack made from samples only has no area, so only the fixed parts count.

The figures are plain numbers here, and rounded up on purpose. They come from
the stage folders of the world build kept in the working folder on 20 November
2026, each measured and divided by 510: osm-areas 3.1 GB, squares 44 MB, then
1.2 GB (join) rising to 1.9 GB (relationships), as each stage's folder keeps
the features of the stage before, and write 0.5 GB, with its copy of the
pack, 0.5 GB, going to the output folder. They are then raised by SAFETY. A stage's folder is kept until the data manager deletes it,
so a stage run again after a change adds a folder rather than replacing one.
"""
from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from mapdata.pipeline.errors import BuildStopped

EARTH_MKM2 = 510.0
EARTH_RADIUS_KM = 6371.0
SAFETY = 1.3          # the estimate is multiplied by this
FLOOR_MB = 50.0       # no stage is thought to need less than this

# (fixed MB, MB for each million square kilometres), by the stage's name in build.STAGES.
STAGE_MB = {
    "samples": (20, 0), "water": (20, 0),
    "osm-areas": (50, 6.0), "squares": (50, 0.2), "join": (50, 2.5),
    "osm-places": (50, 3.5), "graticule": (10, 2.5), "distant-parts": (50, 2.5),
    "continents": (50, 3.0), "osm-layer": (50, 3.2), "osm-rivers": (50, 3.2),
    "osm-lines": (50, 3.6), "physical": (50, 3.3), "disputes": (20, 3.5),
    "enclaves": (20, 3.5), "relationships": (50, 3.8), "coast-stretches": (50, 3.8),
    "wikidata": (20, 3.6), "checks": (10, 0.1), "write": (100, 2.2),
}
UNKNOWN_STAGE_MB = (100, 2.0)


def box_area_mkm2(box) -> float:
    """The area, in million square kilometres, of a box given as west, south, east, north in degrees."""
    west, south, east, north = (float(v) for v in box)
    width = math.radians(east - west)
    band = math.sin(math.radians(north)) - math.sin(math.radians(south))
    return abs(EARTH_RADIUS_KM ** 2 * width * band) / 1e6


def pack_area_mkm2(pack) -> float:
    boxes = [s["box"] for s in pack.stages if isinstance(s.get("box"), (list, tuple)) and len(s["box"]) == 4]
    if boxes:
        return max(box_area_mkm2(b) for b in boxes)
    if any(s["stage"] == "samples" for s in pack.stages):
        return 0.0
    return EARTH_MKM2 if pack.data.get("coverage", {}).get("kind") == "world" else 0.0


def stage_mb(kind: str, area_mkm2: float) -> float:
    fixed, per_area = STAGE_MB.get(kind, UNKNOWN_STAGE_MB)
    return max(FLOOR_MB, (fixed + per_area * area_mkm2) * SAFETY)


def estimate_mb(pack, kinds: list[str]) -> float:
    """The space needed by the stages named in kinds, which are those not already finished. The pack's own
    "space_needed_mb", when it gives one, is a floor for a build that has any stage to run."""
    if not kinds:
        return 0.0
    area = pack_area_mkm2(pack)
    total = sum(stage_mb(k, area) for k in kinds)
    return max(total, float(pack.data.get("space_needed_mb", 0)) if len(kinds) == len(pack.stages) else 0.0)


def free_mb(path: Path) -> float:
    path = Path(path)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 1e6


def stop_if_too_little(pack, kinds: list[str], own: Path) -> None:
    """Raise BuildStopped, naming the stage that needs most, if the drive holding own has too little space."""
    needed = estimate_mb(pack, kinds)
    free = free_mb(own)
    if free < needed:
        area = pack_area_mkm2(pack)
        biggest = max(kinds, key=lambda k: stage_mb(k, area))
        raise BuildStopped(
            f"The pack {pack.name} needs about {needed:,.0f} MB for the {len(kinds)} stage{'s' if len(kinds) != 1 else ''} "
            f"still to run, the biggest being {biggest} at about {stage_mb(biggest, area):,.0f} MB, and the drive "
            f"holding {own} has {free:,.0f} MB free. Free some space on that drive, or choose another data folder, "
            "then build again.")
