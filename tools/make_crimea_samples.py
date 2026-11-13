"""Make the test pack's samples of disputed land (P3-T2c): Crimea, held by two countries (DP119).

* tests/samples/osm/crimea.geojson: Ukraine and Russia cut to a box round Crimea, both holding
  Crimea, as their OpenStreetMap outlines do, with Ukraine's Autonomous Republic of Crimea and
  Sevastopol, simplified to 0.002 degrees. Ukraine's land is as the world build cut it to the coast;
  Russia's is its own land there with the land of Ukraine's that Russia's outline holds added, so the
  two overlap exactly where the outlines do. ODbL.
* tests/samples/naturalearth-disputed-crimea.geojson: Natural Earth's Crimea from its breakaway and
  disputed areas, with its note, simplified to 0.01 degrees. Public domain.

    .venv\\Scripts\\python.exe tools\\make_crimea_samples.py

It reads the newest world build in the data folder's working folder: the outlines as read
(osm-areas) and the features of the latest stage that has them all. It takes under a minute.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import shapely  # noqa: E402

SAMPLES = ROOT / "tests" / "samples"
BOX = (32.4, 44.2, 37.2, 46.4)
UKRAINE, RUSSIA, CRIMEA, SEVASTOPOL = "osm:r60199", "osm:r60189", "osm:r72639", "osm:r1574364"
LICENCE = ("Contains information from OpenStreetMap, which is made available under the Open Database "
           "License (ODbL): https://opendatacommons.org/licenses/odbl/1.0/. © OpenStreetMap contributors.")


def newest(folder: Path, pattern: str) -> Path:
    found = sorted((p.parent for p in folder.glob(f"{pattern}/finished.json")), key=lambda p: p.stat().st_mtime)
    if not found:
        raise SystemExit(f"No finished {pattern} in {folder}.")
    return found[-1]


def feature(props: dict, geom) -> dict:
    return {"type": "Feature", "properties": props, "geometry": json.loads(shapely.to_geojson(geom))}


def rounded(geom, digits: int = 4):
    return shapely.set_precision(geom, 10 ** -digits)


def main() -> int:
    from mapdata.paths import resolve_data_folder
    from mapdata.stages.clip import polygonal
    from mapdata.stages.disputes import load_ids

    folders = resolve_data_folder()
    world = folders.working / "world"
    read = newest(world, "*-osm-areas-*")
    last = newest(world, "*-osm-lines-*")
    print(f"Outlines as read from {read.name}; the world's areas from {last.name}.")
    raw = load_ids(read, {RUSSIA})
    joined = load_ids(last, {UKRAINE, RUSSIA, CRIMEA, SEVASTOPOL})
    box = shapely.box(*BOX)
    ukraine = polygonal(shapely.simplify(shapely.intersection(joined[UKRAINE], box), 0.002, preserve_topology=True))
    held = polygonal(shapely.intersection(ukraine, raw[RUSSIA]))
    russia_own = polygonal(shapely.simplify(shapely.intersection(joined[RUSSIA], box), 0.002, preserve_topology=True))
    russia = polygonal(shapely.union_all([russia_own, held]))
    regions = {i: polygonal(shapely.intersection(shapely.simplify(joined[i], 0.002, preserve_topology=True), ukraine))
               for i in (CRIMEA, SEVASTOPOL)}
    out = {"type": "FeatureCollection",
           "about": ("Ukraine and Russia cut to a box round Crimea, both holding Crimea as their OpenStreetMap outlines "
                     "do (DP119), with Ukraine's Autonomous Republic of Crimea and Sevastopol, from the world build's "
                     "working data, planet file of 2026-10-26, simplified to 0.002 degrees. Made by "
                     "tools/make_crimea_samples.py."),
           "licence": LICENCE, "box": [list(BOX)],
           "features": [
               feature({"id": UKRAINE, "name": "Ukraine", "local_name": "Україна", "layer": "countries",
                        "type": "country", "replaces": ["ne:UKR"]}, rounded(ukraine)),
               feature({"id": RUSSIA, "name": "Russia", "local_name": "Россия", "layer": "countries",
                        "type": "country", "replaces": ["ne:RUS"]}, rounded(russia)),
               feature({"id": CRIMEA, "name": "Autonomous Republic of Crimea", "layer": "regions", "type": "level 4",
                        "parent": UKRAINE}, rounded(regions[CRIMEA])),
               feature({"id": SEVASTOPOL, "name": "Sevastopol", "layer": "regions", "type": "level 4",
                        "parent": UKRAINE}, rounded(regions[SEVASTOPOL])),
           ]}
    (SAMPLES / "osm" / "crimea.geojson").write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8",
                                                    newline="\n")
    ne_path = folders.downloads / "naturalearth" / "ne_10m_admin_0_disputed_areas.geojson"
    ne = json.loads(ne_path.read_text(encoding="utf-8-sig"))
    keep = [f for f in ne["features"] if f["properties"].get("BRK_NAME") == "Crimea"]
    for f in keep:
        g = shapely.simplify(shapely.from_geojson(json.dumps(f["geometry"])), 0.01, preserve_topology=True)
        f["geometry"] = json.loads(shapely.to_geojson(rounded(g)))
        f["properties"] = {k: f["properties"][k] for k in ("BRK_NAME", "NOTE_BRK", "ADMIN", "SOVEREIGNT", "TYPE",
                                                          "WIKIDATAID")}
    (SAMPLES / "naturalearth-disputed-crimea.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "about": "Natural Earth's Crimea, from its breakaway and disputed areas at "
         "1:10 million, simplified to 0.01 degrees. Public domain. Made with Natural Earth.", "features": keep},
        ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote crimea.geojson (the land both hold: {held.area:.3f} square degrees) and Natural Earth's Crimea.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
