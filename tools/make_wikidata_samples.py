"""Make the test pack's Wikidata samples (P3-T2a), in tests/samples/wikidata.

* links.yaml: each sample feature's Wikidata link, as the samples have none of their own: Natural
  Earth's countries from Natural Earth's own links, in its 1:110 million download; the OpenStreetMap
  areas from the world build's features, which keep OSM's wikidata tags.
* facts-sample.jsonl: the facts of those items, fetched from Wikidata's query service, in the same form
  as the build keeps them in the data folder, so the test pack reads them offline.
* names-sample.jsonl: the items with the names of the samples' oceans and seas, for matching by name
  and place.

    .venv\\Scripts\\python.exe tools\\make_wikidata_samples.py [--features <features.json>]

It needs the data folder and the internet, and takes under a minute. Without --features it reads the
newest world build's features from the working folder. Running it again on a later day gives the
facts as Wikidata has them then.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLES = ROOT / "tests" / "samples"
OUT = SAMPLES / "wikidata"
REFRESH = "sample"
MATCH_LAYERS = ("oceans", "seas")
# Areas the test pack's stages make, which are in no sample: Crimea, made by the disputes stage (P3-T2c).
EXTRA_LINKS = {"disputed:crimea": "Q7835"}


def sample_features() -> list[dict]:
    """Every feature's properties in the samples."""
    out = []
    for path in [SAMPLES / "world-naturalearth-110m.geojson", SAMPLES / "oceans-vliz-atlantic.geojson",
                 *sorted((SAMPLES / "osm").glob("*.geojson"))]:
        data = json.loads(path.read_text(encoding="utf-8"))
        out += [f["properties"] for f in data["features"]]
    return out


def newest_world_features(folders) -> Path:
    found = sorted((folders.working / "world").glob("*/features.json"), key=lambda p: p.stat().st_mtime)
    if not found:
        raise SystemExit("No world build in the working folder; give --features.")
    return found[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--features", type=Path, help="a build's features.json with OSM's Wikidata links")
    args = ap.parse_args()

    from mapdata.paths import resolve_data_folder
    from mapdata.stages import wikidata

    folders = resolve_data_folder()
    feats = sample_features()
    links: dict[str, str] = {}

    ne = json.loads((folders.downloads / "naturalearth" / "ne_110m_admin_0_countries.geojson")
                    .read_text(encoding="utf-8"))
    by_code = {f["properties"]["ADM0_A3"]: f["properties"].get("WIKIDATAID") for f in ne["features"]}
    for p in feats:
        if p["id"].startswith("ne:") and wikidata.valid_qid(by_code.get(p["id"][3:])):
            links[p["id"]] = by_code[p["id"][3:]]

    path = args.features or newest_world_features(folders)
    print(f"Reading OSM's Wikidata links from {path}.")
    world = json.loads(path.read_text(encoding="utf-8"))["records"]
    osm_links = {r["id"]: r["wikidata"] for r in world if r.get("wikidata")}
    from_tags = 0
    for p in feats:
        q = osm_links.get(p["id"])
        if q and wikidata.valid_qid(q):
            links[p["id"]] = q
            from_tags += 1
    links.update(EXTRA_LINKS)
    print(f"Links: {len(links)}, of which {from_tags} from OSM's tags; {len(feats)} sample features.")

    names = sorted({p["name"] for p in feats if p["layer"] in MATCH_LAYERS})
    named = wikidata.fetch_names(names)
    # The items found by name too, as the test pack's matches need their facts.
    found = {q for e in named.values() for q, _lon, _lat in e["items"]}
    qids = sorted(set(links.values()) | found, key=wikidata.qid_order)
    facts = wikidata.fetch(qids, today=None)

    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# Each test pack sample feature's Wikidata link, as the samples have none of their own.",
             "# Made by tools/make_wikidata_samples.py. Facts from Wikidata, CC0.", ""]
    lines += [f"{k}: {v}" for k, v in sorted(links.items())]
    (OUT / "links.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    for name, entries, key in ((f"facts-{REFRESH}.jsonl", facts, wikidata.qid_order),
                               (f"names-{REFRESH}.jsonl", named, str)):
        with open(OUT / name, "w", encoding="utf-8", newline="\n") as f:
            for k in sorted(entries, key=key):
                f.write(json.dumps(entries[k], ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Wrote {OUT}: {len(facts)} items' facts and {len(named)} names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
