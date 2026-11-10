"""Make the Phase 3 samples for the test pack from the planet file (P3-T0d).

Six files in tests/samples/osm, each with the ODbL notice, so every Phase 3 test runs on the
test pack without the data folder:

* hampshire-wiltshire.geojson: England and every county in a box round Hampshire and
  Wiltshire, simplified to 0.001 degrees (about 100 metres), keeping shared borders.
* new-forest.geojson: the New Forest National Park, which overlaps Hampshire and Wiltshire,
  in the layer national_parks. Only for INF-5 and the ambiguous up of NAV-4: national
  parks come to the real packs in Phase 4.
* switzerland-neighbours.geojson: Switzerland, Liechtenstein, and France, Germany, Italy
  and Austria cut to a box round them, simplified to 0.002 degrees, keeping shared borders.
* rhine.geojson: the Rhine from Basel to Schaffhausen, where it is the border of
  Switzerland and Germany, in the layer rivers.
* bay-of-biscay.geojson: the Bay of Biscay as OpenStreetMap has it, in the layer seas.
* shared-names.geojson: places that share a name, in the layer places: Paris in France and
  in Texas, Portland in Oregon and in Maine, Newport in Wales and on the Isle of Wight, and
  Sao Paulo the city, with Sao Paulo the state in the layer regions.

    .venv\\Scripts\\python.exe tools\\make_phase3_samples.py

The planet file is the newest in the data folder, found as `mapdata check` finds it. It runs
in its own short-lived process, as the GeoDesk notes ask, and takes a few minutes. Nothing
else should read the planet file while it runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "tests" / "samples" / "osm"
LICENCE = ("Contains information from OpenStreetMap, which is made available under the Open Database "
           "License (ODbL): https://opendatacommons.org/licenses/odbl/1.0/. © OpenStreetMap contributors.")

ENGLAND, UK = 58447, 62149
HANTS_WILTS_BOX = (-2.40, 50.70, -0.70, 51.72)        # west, south, east, north
NEW_FOREST = 2678988
ALPS_BOX = (5.0, 45.0, 11.5, 48.5)
COUNTRIES = [  # relation, English name, Natural Earth id it replaces, or None
    (51701, "Switzerland", "ne:CHE"),
    (1155955, "Liechtenstein", None),
    (1403916, "France", "ne:FRA"),       # metropolitan France, as in england-france-channel.geojson
    (51477, "Germany", "ne:DEU"),
    (365331, "Italy", "ne:ITA"),
    (16239, "Austria", "ne:AUT"),
]
RHINE = 123924
RHINE_BOX = (7.55, 47.50, 8.70, 47.72)                 # Basel to Schaffhausen
BISCAY = 7156290
PLACES = [  # node, English name, type, where it is, and roughly where to look: longitude, latitude
    (17807753, "Paris", "city", "France", (2.35, 48.85)),
    (105715620, "Paris", "town", "Texas, USA", (-95.56, 33.66)),
    (1666626393, "Portland", "city", "Oregon, USA", (-122.67, 45.52)),
    (158867610, "Portland", "city", "Maine, USA", (-70.26, 43.66)),
    (26700977, "Newport", "city", "Wales", (-3.00, 51.59)),
    (2386521, "Newport", "town", "the Isle of Wight, England", (-1.30, 50.70)),
    (30674098, "São Paulo", "city", "Brazil", (-46.63, -23.55)),
]
SAO_PAULO_STATE, SAO_PAULO_BOX = 298204, (-53.2, -25.4, -44.1, -19.7)


def planet() -> Path:
    """The newest planet file in the data folder's downloads."""
    from mapdata.paths import resolve_data_folder

    found = sorted(resolve_data_folder().downloads.glob("planet-*/planet-*.gol"))
    if not found:
        raise SystemExit("No planet file in the data folder's downloads. Run: python -m mapdata fetch planet")
    return found[-1]


def write(name: str, about: str, features: list[dict], box=None) -> None:
    """One sample, one feature to a line, as the other samples are."""
    path = OUT / name
    head = {"type": "FeatureCollection", "about": about, "licence": LICENCE}
    if box:
        head["box"] = [list(box)]
    path.write_text("\n".join(["{" + ", ".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}"
                                              for k, v in head.items()) + ", \"features\": [",
                              ",\n".join(json.dumps(f, ensure_ascii=False, separators=(",", ":")) for f in features),
                              "]}"]) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {path.relative_to(ROOT)}: {len(features)} features, {path.stat().st_size // 1024} KB.")


def main() -> int:
    import geodesk
    import shapely

    gol = planet()
    world = geodesk.Features(str(gol))
    when = gol.stem.removeprefix("planet-")
    source = f"the planet file of {when}, read with GeoDesk"

    def gbox(b):
        return geodesk.Box(west=b[0], south=b[1], east=b[2], north=b[3])

    def shape(f):
        return geodesk.from_mercator(f.shape)

    def one(query: str, b, want: int):
        for f in world(query)(gbox(b)):
            if f.id == want:
                return f
        raise SystemExit(f"Not found in the planet file: {query} with the id {want}.")

    def geometry(g, digits=7):
        return json.loads(shapely.to_geojson(shapely.set_precision(g, 10 ** -digits)))

    def feature(props, g):
        return {"type": "Feature", "properties": props, "geometry": geometry(g)}

    def local(f, english):
        name = str(f["name"] or "")
        return {"local_name": name} if name and name != english else {}

    def coverage(geoms, tolerance):
        """Simplify areas that share borders, keeping the borders shared."""
        parts = [shapely.make_valid(g) for g in geoms]
        out = shapely.coverage_simplify(parts, tolerance)
        return [shapely.make_valid(g) for g in out]

    # Hampshire and Wiltshire, with England and every county round them.
    clip = shapely.box(*HANTS_WILTS_BOX)
    counties = []
    for f in world("a[boundary=administrative][admin_level=6]")(gbox(HANTS_WILTS_BOX)):
        if f.id in [c.id for c, _ in counties]:
            continue
        cut = shapely.intersection(shape(f), clip)
        if shapely.area(cut) > 1e-6:
            counties.append((f, cut))
    england = shapely.intersection(shape(one("a[boundary=administrative][admin_level=4][name=England]",
                                             HANTS_WILTS_BOX, ENGLAND)), clip)
    counties = [(f, g) for f, g in counties if shapely.area(shapely.intersection(g, england)) > 0.9 * shapely.area(g)]
    counties.sort(key=lambda fg: fg[0].id)
    simple = coverage([g for _, g in counties], 0.001)
    features = [feature({"id": f"osm:r{f.id}", "name": str(f["name:en"] or f["name"]), "layer": "counties",
                         "type": "level 6", "parent": f"osm:r{ENGLAND}"}, g) for (f, _), g in zip(counties, simple)]
    features.insert(0, feature({"id": f"osm:r{ENGLAND}", "name": "England", "layer": "regions", "type": "level 4",
                                "parent": f"osm:r{UK}"}, shapely.union_all(simple)))
    names = ", ".join(str(f["name"]) for f, _ in counties)
    write("hampshire-wiltshire.geojson",
          f"England and its counties cut to a box round Hampshire and Wiltshire, from {source}, simplified to "
          f"0.001 degrees, keeping shared borders. England here is the counties joined, so it holds each of them. "
          f"The counties: {names}.", features, HANTS_WILTS_BOX)

    # The New Forest National Park.
    park = one("a[boundary=protected_area]", HANTS_WILTS_BOX, NEW_FOREST)
    write("new-forest.geojson",
          f"The New Forest National Park from {source}, simplified to 0.0005 degrees. It overlaps Hampshire and "
          "Wiltshire. Only for the tests of INF-5 and the ambiguous up of NAV-4: national parks come to the "
          "real packs in Phase 4.",
          [feature({"id": f"osm:r{NEW_FOREST}", "name": "New Forest National Park", "layer": "national_parks",
                    "type": "national park"}, shapely.simplify(shape(park), 0.0005))])

    # Switzerland and its five neighbours.
    clip = shapely.box(*ALPS_BOX)
    found = []
    for rel, english, replaces in COUNTRIES:
        f = one("a[boundary]", ALPS_BOX, rel)
        found.append((f, english, replaces, shapely.intersection(shape(f), clip)))
    simple = coverage([g for *_, g in found], 0.002)
    features = []
    for (f, english, replaces, _), g in zip(found, simple):
        props = {"id": f"osm:r{f.id}", "name": english, **local(f, english), "layer": "countries",
                 "type": "metropolitan France" if f.id == 1403916 else "country"}
        if replaces:
            props["replaces"] = [replaces]
        features.append(feature(props, g))
    write("switzerland-neighbours.geojson",
          f"Switzerland, Liechtenstein, and France, Germany, Italy and Austria cut to the box, from {source}, "
          "simplified to 0.002 degrees, keeping shared borders.", features, ALPS_BOX)

    # The Rhine from Basel to Schaffhausen.
    clip = shapely.box(*RHINE_BOX)
    rhine = one("r[waterway=river]", RHINE_BOX, RHINE)
    lines = []
    for m in rhine.members:
        if m.is_way and str(m["waterway"]) == "river":
            part = shapely.intersection(shapely.LineString(shape(m).coords), clip)
            lines.extend(g for g in shapely.get_parts(part) if g.geom_type == "LineString" and not g.is_empty)
    merged = shapely.simplify(shapely.line_merge(shapely.MultiLineString(lines)), 0.0002)
    write("rhine.geojson",
          f"The Rhine from Basel to Schaffhausen, where it is the border of Switzerland and Germany, from "
          f"{source}, simplified to 0.0002 degrees. Its river ways in the box, in several parts where it splits round islands.",
          [feature({"id": f"osm:r{RHINE}", "name": "Rhine", "local_name": "Rhein", "layer": "rivers",
                    "type": "river"}, merged)])

    # The Bay of Biscay.
    bay = one("*[name:en=\"Bay of Biscay\"]", (-10.0, 43.0, -1.0, 48.5), BISCAY)
    natural = str(bay["natural"] or "bay")
    g = shapely.simplify(shape(bay), 0.005) if bay.is_area else shapely.Point(bay.lon, bay.lat)
    write("bay-of-biscay.geojson",
          f"The Bay of Biscay from {source}, as OpenStreetMap has it ({'an area' if bay.is_area else 'a point'}, "
          f"natural={natural}), {'simplified to 0.005 degrees' if bay.is_area else 'unchanged'}.",
          [feature({"id": f"osm:r{BISCAY}", "name": "Bay of Biscay", **local(bay, "Bay of Biscay"),
                    "layer": "seas", "type": natural}, g)])

    # Places that share a name.
    features = []
    for node, english, kind, where, (lon, lat) in PLACES:
        f = one(f"n[place={kind}]", (lon - 0.1, lat - 0.1, lon + 0.1, lat + 0.1), node)
        props = {"id": f"osm:n{node}", "name": english, **local(f, english), "layer": "places", "type": kind,
                 "where": where}
        if f["population"]:
            props["population"] = int(str(f["population"]).replace(",", ""))
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Point", "coordinates": [round(f.lon, 7), round(f.lat, 7)]}})
    state = one("a[boundary=administrative][admin_level=4]", SAO_PAULO_BOX, SAO_PAULO_STATE)
    features.append(feature({"id": f"osm:r{SAO_PAULO_STATE}", "name": "São Paulo", "layer": "regions",
                             "type": "level 4", "parent": "ne:BRA", "where": "Brazil"},
                            shapely.simplify(shape(state), 0.01)))
    write("shared-names.geojson",
          f"Places that share a name, from {source}: two Parises, two Portlands, two Newports, and São Paulo "
          "the city and the state. The places are points; the state is an area simplified to 0.01 degrees. "
          "\"where\" says which is which, for the tests of search.", features)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
