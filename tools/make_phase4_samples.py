"""Make the Phase 4 street-level samples for the test pack from the planet file (P4-T0e).

Five files, each with the ODbL notice, so the Phase 4 tests run without the data folder:

* tests/samples/osm-raw/winchester.geojson, brockenhurst.geojson, lymington.geojson: every
  OpenStreetMap object that meets the box, whole, with all its tags (design 5.1). Building
  outlines are left out, as no stage reads building=*.
* tests/samples/osm/lymington-coast.geojson: the United Kingdom, England, Hampshire, the Isle of
  Wight where the box reaches it, and the named islands in the Lymington box, cut to the land
  polygons, simplified to 0.00001 degrees, shared borders kept (design 5.2).
* tests/samples/outlines/test-region.poly: the three boxes, each shrunk by 0.001 degrees.

    .venv\\Scripts\\python.exe tools\\make_phase4_samples.py

The planet file is the newest in the data folder, found as `mapdata check` finds it. It runs in
its own short-lived process and takes a few minutes. Nothing else should read the planet file
while it runs. Running it again makes the same files byte for byte. The tool reads the land
polygons from the download without writing anything; it writes only inside the repository.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW = ROOT / "tests" / "samples" / "osm-raw"
COOKED = ROOT / "tests" / "samples" / "osm"
OUTLINES = ROOT / "tests" / "samples" / "outlines"
LICENCE = ("Contains information from OpenStreetMap, which is made available under the Open Database "
           "License (ODbL): https://opendatacommons.org/licenses/odbl/1.0/. © OpenStreetMap contributors.")

# west, south, east, north: whole pack tiles at tile level 14 (design 5.1).
WINCHESTER = (-1.31836, 51.05347, -1.29639, 51.06445)
# Three pack tiles wide and two high, not the designed x 8119 to 8120, y 12817: a named pond (Mirror Pond) and a
# second neighbouring parish are not in the designed box. Whole pack tiles, x 8118 to 8120, y 12817 to 12818.
BROCKENHURST = (-1.62598, 50.81177, -1.56006, 50.83374)
LYMINGTON = (-1.56006, 50.73486, -1.51611, 50.75684)
BOXES = {"winchester": WINCHESTER, "brockenhurst": BROCKENHURST, "lymington": LYMINGTON}
SHRINK = 0.001

UK, ENGLAND, HAMPSHIRE, WIGHT = 62149, 58447, 172799, 154350
ADMIN_TOLERANCE = 0.0001        # administrative boundaries, in the raw samples
PARK_TOLERANCE = 0.0005         # national parks and other protected areas, in the raw samples
COAST_TOLERANCE = 0.00001
BIG_AREA = 0.5                  # an area wider than this, in degrees, and not a boundary read, is left out
# A building outline is left out unless it is also something a stage reads: a shop, a cathedral, a station.
PLACE_KEYS = ("amenity", "shop", "tourism", "historic", "leisure", "office", "craft", "healthcare", "railway",
              "public_transport", "man_made", "emergency")
SIZE_LIMIT = 11 * 512 * 1024       # 5.5 MB for the three raw files: the design said about 3 MB, but real streets need about 5


def has(tags: dict, key: str, *values: str) -> bool:
    return key in tags and (not values or tags[key] in values)


def named(tags: dict, *names: str) -> bool:
    return tags.get("name") in names


def contains(tags: dict, text: str) -> bool:
    return text.lower() in (tags.get("name") or "").lower()


# Each "must hold": (what, how many at least, test on the tags and the kind). Design 5.1.
MUST_HOLD = {
    "winchester": [
        ("the High Street", 1, lambda t, k: has(t, "highway") and named(t, "High Street")),
        ("the Broadway", 1, lambda t, k: has(t, "highway") and named(t, "The Broadway", "Broadway")),
        ("side streets", 3, lambda t, k: has(t, "highway", "residential", "service", "unclassified", "pedestrian",
                                             "tertiary", "living_street")),
        ("footpaths", 2, lambda t, k: has(t, "highway", "footway", "path", "pedestrian")),
        ("Abbey Gardens, a park", 1, lambda t, k: has(t, "leisure", "park", "garden") and contains(t, "Abbey")),
        ("a school ground", 1, lambda t, k: has(t, "amenity", "school", "college") and k == "area"),
        ("bus stops", 2, lambda t, k: has(t, "highway", "bus_stop")),
        ("crossings", 1, lambda t, k: has(t, "highway", "crossing")),
        ("post boxes", 1, lambda t, k: has(t, "amenity", "post_box")),
        ("benches", 1, lambda t, k: has(t, "amenity", "bench")),
        ("bins", 1, lambda t, k: has(t, "amenity", "waste_basket", "waste_disposal", "recycling")),
        ("shops", 3, lambda t, k: has(t, "shop")),
        ("cafes", 1, lambda t, k: has(t, "amenity", "cafe")),
        ("pubs", 1, lambda t, k: has(t, "amenity", "pub")),
        ("the Cathedral, a place of worship", 1, lambda t, k: has(t, "amenity", "place_of_worship")
         and contains(t, "Cathedral")),
        ("the River Itchen", 1, lambda t, k: has(t, "waterway", "river") and contains(t, "Itchen")),
        ("its side streams", 1, lambda t, k: has(t, "waterway", "stream", "river", "canal", "ditch")
         and not contains(t, "River Itchen")),
        ("land use", 1, lambda t, k: has(t, "landuse")),
        ("the City of Winchester district, level 8", 1, lambda t, k: has(t, "boundary", "administrative")
         and has(t, "admin_level", "8") and contains(t, "Winchester")),
        ("a level 10 area (none meets the box: OSM has no unparished area)", 0, lambda t, k: has(t, "boundary", "administrative")
         and has(t, "admin_level", "10")),
    ],
    "brockenhurst": [
        ("streets", 3, lambda t, k: has(t, "highway", "residential", "service", "unclassified", "tertiary",
                                        "secondary", "primary", "living_street")),
        ("tracks", 1, lambda t, k: has(t, "highway", "track")),
        ("bridleways", 1, lambda t, k: has(t, "highway", "bridleway")),
        ("heath", 1, lambda t, k: has(t, "natural", "heath")),
        ("woodland", 1, lambda t, k: has(t, "natural", "wood") or has(t, "landuse", "forest")),
        ("forest land use", 1, lambda t, k: has(t, "landuse", "forest")),
        ("named ponds", 1, lambda t, k: has(t, "water", "pond") and "name" in t),
        ("unnamed ponds", 1, lambda t, k: has(t, "water", "pond") and "name" not in t),
        ("streams", 1, lambda t, k: has(t, "waterway", "stream")),
        ("the New Forest National Park", 1, lambda t, k: has(t, "boundary", "national_park", "protected_area")
         and contains(t, "New Forest")),
        ("Brockenhurst station", 1, lambda t, k: has(t, "railway", "station") and contains(t, "Brockenhurst")),
        ("parishes", 2, lambda t, k: has(t, "boundary", "administrative") and has(t, "admin_level", "10")),
        ("the New Forest district", 1, lambda t, k: has(t, "boundary", "administrative")
         and has(t, "admin_level", "8") and contains(t, "New Forest")),
    ],
    "lymington": [
        ("streets", 3, lambda t, k: has(t, "highway", "residential", "service", "unclassified", "tertiary",
                                        "secondary", "primary", "living_street", "pedestrian")),
        ("the harbour", 1, lambda t, k: has(t, "harbour") or has(t, "leisure", "marina")
         or has(t, "seamark:type", "harbour")),
        ("the Lymington River", 1, lambda t, k: has(t, "waterway") and contains(t, "Lymington")),
        ("salt marsh", 1, lambda t, k: has(t, "wetland", "saltmarsh", "tidalflat", "salt_marsh")
         or has(t, "natural", "wetland")),
        ("small named islets (none in OSM near Lymington)", 0, lambda t, k: has(t, "place", "islet") and "name" in t),
        ("slipways", 1, lambda t, k: has(t, "leisure", "slipway") or has(t, "man_made", "slipway")
         or has(t, "waterway", "boatyard")),
        ("paths along the shore", 1, lambda t, k: has(t, "highway", "footway", "path", "bridleway", "track")),
        ("parishes", 1, lambda t, k: has(t, "boundary", "administrative") and has(t, "admin_level", "10")),
    ],
}


def planet() -> Path:
    """The newest planet file in the data folder's downloads."""
    from mapdata.paths import resolve_data_folder

    found = sorted(resolve_data_folder().downloads.glob("planet-*/planet-*.gol"))
    if not found:
        raise SystemExit("No planet file in the data folder's downloads. Run: python -m mapdata fetch planet")
    return found[-1]


def head(about: str, box) -> str:
    return json.dumps({"type": "FeatureCollection", "about": about, "licence": LICENCE, "box": box},
                      ensure_ascii=False)


def write(path: Path, about: str, box, features: list[dict]) -> None:
    """One sample, one feature to a line, as the other samples are."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = head(about, box)[:-1] + ', "features": [\n'
    text += ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in features) + "\n]}\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {path.relative_to(ROOT)}: {len(features)} features, {path.stat().st_size / 1024:.0f} KB.")


def order(f: dict) -> tuple:
    osm = f["properties"]["osm"]
    return "nwr".index(osm[0]), int(osm[1:])


def main() -> int:
    import geodesk
    import pyogrio
    import shapely

    from mapdata.paths import resolve_data_folder
    from mapdata.stages import land

    gol = planet()
    world = geodesk.Features(str(gol))
    when = gol.stem.removeprefix("planet-")
    source = f"the planet file of {when}, read with GeoDesk"

    def gbox(b):
        return geodesk.Box(west=b[0], south=b[1], east=b[2], north=b[3])

    def shape(f):
        return geodesk.from_mercator(f.shape)

    def geometry(g, digits=7):
        return json.loads(shapely.to_geojson(shapely.set_precision(g, 10 ** -digits, mode="pointwise")))

    def raw_features(box) -> list[dict]:
        clip = shapely.box(*box)
        out = []
        for f in world("*")(gbox(box)):
            tags = {k: str(v) for k, v in sorted(dict(f.tags).items())}
            if not tags:
                continue        # an untagged way or node that is only a member of a relation
            if "building" in tags and not any(k in tags for k in PLACE_KEYS):
                continue
            if f.is_node:
                kind, letter = "node", "n"
            elif f.is_way:
                kind, letter = ("area" if f.is_area else "way"), "w"
            elif f.is_area:
                kind, letter = "area", "r"
            else:
                continue        # a relation that is not an area (a route, say) has no shape
            g = shape(f)
            if not shapely.intersects(g, clip):
                continue
            boundary = tags.get("boundary")
            west, south, east, north = g.bounds
            if boundary == "administrative":
                g = shapely.simplify(g, ADMIN_TOLERANCE)
            elif boundary in ("national_park", "protected_area"):
                g = shapely.simplify(g, PARK_TOLERANCE)
            elif boundary or (kind == "area" and max(east - west, north - south) > BIG_AREA):
                continue        # time zones, police and fire areas, the island of Great Britain: no stage reads them
            out.append({"type": "Feature", "properties": {"osm": f"{letter}{f.id}", "kind": kind, "tags": tags},
                        "geometry": geometry(g)})
        out.sort(key=order)
        return out

    # The raw samples, with each "must hold" checked.
    problems = []
    total = 0
    for name, box in BOXES.items():
        features = raw_features(box)
        for what, least, test in MUST_HOLD[name]:
            n = sum(1 for f in features if test(f["properties"]["tags"], f["properties"]["kind"]))
            print(f"{name}: {what}: {n}")
            if n < least:
                problems.append(f"{name}: {what}: found {n}, needs {least}")
        path = RAW / f"{name}.geojson"
        write(path, f"Every OpenStreetMap object meeting the box, whole, with its tags, from {source}, without "
                    "building outlines. Administrative boundaries are simplified to 0.0001 degrees, national parks "
                    "and protected areas to 0.0005. A Point is a node, a LineString a way, a Polygon or MultiPolygon "
                    "an area.", list(box), features)
        total += path.stat().st_size
    print(f"The three raw files together: {total / 1024 / 1024:.2f} MB.")
    if total > SIZE_LIMIT:
        problems.append(f"the raw files are {total} bytes, over the limit {SIZE_LIMIT}")
    if problems:
        print("MISSING:\n" + "\n".join(problems))
        return 1

    # The cooked sample for the Lymington box.
    clip = shapely.box(*LYMINGTON)
    downloads = resolve_data_folder().downloads
    wkb = pyogrio.raw.read(land.vsi_path(land.source_path(downloads)), bbox=LYMINGTON, read_geometry=True)[2]
    shore = shapely.intersection(shapely.union_all(shapely.from_wkb(wkb)), clip)

    def one(query: str, want: int):
        for f in world(query)(gbox(LYMINGTON)):
            if f.id == want:
                return f
        return None

    counties = []
    for rel in (HAMPSHIRE, WIGHT):
        f = one("a[boundary=administrative][admin_level=6]", rel)
        if f is None:
            continue
        cut = shapely.make_valid(shapely.intersection(shapely.intersection(shape(f), clip), shore))
        if shapely.area(cut) > 1e-9:
            counties.append((f, cut))
    simple = [shapely.make_valid(g) for g in shapely.coverage_simplify([g for _, g in counties], COAST_TOLERANCE)]
    features = []
    for (f, _), g in zip(counties, simple):
        features.append(({"id": f"osm:r{f.id}", "name": str(f["name:en"] or f["name"]), "layer": "counties",
                         "type": "level 6", "parent": f"osm:r{ENGLAND}"}, g))
    land_union = shapely.union_all(simple)
    parts = [({"id": f"osm:r{UK}", "name": "United Kingdom", "layer": "countries", "type": "country",
               "replaces": ["ne:GBR"]}, land_union),
             ({"id": f"osm:r{ENGLAND}", "name": "England", "layer": "regions", "type": "level 4",
               "parent": f"osm:r{UK}"}, land_union)]
    parts += features
    islands = []
    for f in world("a[place=island],a[place=islet]")(gbox(LYMINGTON)):
        west, south, east, north = shape(f).bounds
        if not f["name"] or max(east - west, north - south) > BIG_AREA:
            continue        # the island of Great Britain is the land itself, not a small island
        g = shapely.make_valid(shapely.intersection(shapely.intersection(shape(f), clip), shore))
        if shapely.area(g) > 1e-10:
            islands.append((f"osm:{'w' if f.is_way else 'r'}{f.id}", f, g))
    islands.sort(key=lambda t: ("wr".index(t[0][4]), int(t[0][5:])))
    simple = [shapely.make_valid(g) for g in shapely.coverage_simplify([g for *_, g in islands], COAST_TOLERANCE)]
    for (oid, f, _), g in zip(islands, simple):
        if not g.is_empty:
            parts.append(({"id": oid, "name": str(f["name:en"] or f["name"]), "layer": "islands",
                           "type": str(f["place"]), "parent": f"osm:r{HAMPSHIRE}"}, g))
    cooked = [{"type": "Feature", "properties": p, "geometry": geometry(g, 7)} for p, g in parts]
    write(COOKED / "lymington-coast.geojson",
          f"The United Kingdom, England, Hampshire and the named islands in the Lymington box, from {source} and "
          "the OSM land polygons, cut to the land, simplified to 0.00001 degrees, keeping shared borders. "
          "England and the United Kingdom here are Hampshire's land in the box, as the samples stage takes the "
          "same ids from the coarser samples outside it.", [list(LYMINGTON)], cooked)

    # The outline: each box shrunk, as a .poly file.
    lines = ["test-region"]
    for n, box in enumerate(BOXES.values(), 1):
        w, s, e, nn = box[0] + SHRINK, box[1] + SHRINK, box[2] - SHRINK, box[3] - SHRINK
        lines.append(str(n))
        for lon, lat in ((w, s), (e, s), (e, nn), (w, nn), (w, s)):
            lines.append(f"   {lon:.5f}   {lat:.5f}")
        lines.append("END")
    lines.append("END")
    OUTLINES.mkdir(parents=True, exist_ok=True)
    (OUTLINES / "test-region.poly").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("Wrote tests/samples/outlines/test-region.poly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
