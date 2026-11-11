"""Named seas, bays and straits from Natural Earth's marine areas (P3-T1b, DP168, DAT-4).

The IHO Sea Areas from Marine Regions are still non-commercial and share-alike
(CC BY-NC-SA 4.0, checked on 11 November 2026), which does not fit the ODbL
packs, so, as DP168 decided, the seas come from Natural Earth's marine areas at
1:10 million, which are public domain. They cover the sea with no overlaps but
one (a reef), in classes:

* named water, each a sea in the Seas layer: sea, gulf, bay, strait, sound,
  channel, fjord, lagoon and inlet. The class is the sea's type.
* water that names no sea: Natural Earth's own oceans (the VLIZ oceans are the
  top of the water hierarchy instead), its unnamed areas, and the mouths of
  three rivers (rivers come with P3-T1g).
* left out: reefs, which are not water to be in.

The squares stage names each face of water with the smallest sea it is in.
Natural Earth's coasts are rough, so water between a sea's edge and the real
coast is in no marine area: it takes the sea beside it (grid.settle_waiting_seas,
then join.settle_seas).

This module has no reading of files, so it is tested on small made-up features.
"""
from __future__ import annotations

import shapely

from mapdata.stages import grid

SEA_CLASSES = ("sea", "gulf", "bay", "strait", "sound", "channel", "fjord", "lagoon", "inlet")
NO_SEA_CLASSES = ("ocean", "generic", "river")


def marine_areas(features: list[dict]) -> tuple[list[dict], list]:
    """Natural Earth's marine areas as records and shapes for the squares stage: kind "sea" for a named sea,
    "nosea" for water that names none, in Natural Earth's order. Reefs and unknown classes are left out."""
    records, geoms = [], []
    for f in features:
        p = f["properties"]
        cls = (p.get("featurecla") or "").lower()
        if cls not in SEA_CLASSES and cls not in NO_SEA_CLASSES:
            continue
        g = shapely.geometry.shape(f["geometry"])
        if not g.is_valid:
            g = shapely.make_valid(g)
        g = grid.polygonal(g)
        if g is None or g.is_empty:
            continue
        rid = f"ne:marine:{p['ne_id']}"
        name = p.get("name_en") or p.get("name")
        if cls in SEA_CLASSES and name:
            rec = {"id": rid, "kind": "sea", "name": name, "type": cls, "level": None, "country": None}
            if p.get("name") and p["name"] != name:
                rec["local_name"] = p["name"]
            if p.get("wikidataid"):
                rec["wikidata"] = p["wikidataid"]
        else:
            rec = {"id": rid, "kind": "nosea", "level": None, "country": None}
        records.append(rec)
        geoms.append(g)
    return records, geoms
