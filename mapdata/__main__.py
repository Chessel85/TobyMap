"""The mapdata command line program (architecture section 8).

check, fetch, build and inspect (P1-T3), status, world-sample for the globe spike (S5), and the spike S2
commands, which stay until P1-T16 is finished. Output is plain lines, suited to a screen reader (DMT-2). The data
manager's guide is docs/data-manager/guide.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mapdata.paths import DataFolderNotSet, resolve_data_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mapdata", description="Build TobyMap data packs.")
    parser.add_argument("--data", help="the data folder; overrides MAPDATA_ROOT and paths.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="say where the data folder is and what it holds")
    ck = sub.add_parser("check", help="say whether the data folder is ready: free space, planet file, land polygons")
    ck.add_argument("--pack", help="also say whether this pack's build fits in the free space")
    fe = sub.add_parser("fetch", help="download sources into the data folder, or find their local copies")
    fe.add_argument("source", nargs="?", help="the source to fetch, 'list' to list them, or 'all'")
    fe.add_argument("--pack", help="fetch every source this pack uses")
    bu = sub.add_parser("build", help="build a pack from its settings file in mapdata/config/packs")
    bu.add_argument("pack", help="the pack's name, such as test")
    bu.add_argument("--workers", type=int, default=1,
                    help="processor cores to use for the slowest steps (default 1; 3 leaves the laptop usable)")
    bu.add_argument("--away", action="store_true",
                    help="use 6 worker processes, for when nobody is using the laptop (DP103)")
    bu.add_argument("--wait-for-yes", action="store_true",
                    help="if continue.txt says no, wait until it says yes, then carry on (otherwise stop)")
    sub.add_parser("spike-s2-stage1", help="spike S2 stage 1: the UK, France and Spain, with its report")
    st = sub.add_parser("spike-s2", help="spike S2 stage 1 again (the UK, France and Spain, with the faster "
                                         "methods), 2 (Norway and Sweden), 3 (the 180 degree line), 4 (Argentina), "
                                         "or belgium (the build speed trials)")
    st.add_argument("stage", choices=["1", "2", "3", "4", "belgium"])
    st.add_argument("--workers", type=int, default=3,
                    help="processor cores to use for the slowest steps (default 3, which leaves the laptop usable)")
    st.add_argument("--away", action="store_true",
                    help="use 6 worker processes, for when nobody is using the laptop (DP103)")
    ct = sub.add_parser("spike-s2-counties", help="build speed trials (P1-T16): the counties step of one stage, "
                                                  "timed with each method, from the stage's caches")
    ct.add_argument("stage", choices=["1", "2", "3", "4", "belgium"])
    ct.add_argument("--method", action="append", choices=["whole-gap", "nearby-gap", "covered-first", "gap-land"],
                    help="a method to try; give it more than once to compare them (default: all of them)")
    ct.add_argument("--country", help="only this country, by its identifier, such as osm:r2202162")
    ct.add_argument("--within", type=float, nargs=4, metavar=("WEST", "SOUTH", "EAST", "NORTH"),
                    help="only the land in this rectangle, in degrees, such as mainland France's")
    ct.add_argument("--give-up", type=float, metavar="MINUTES", help="stop a method after this many minutes")
    ct.add_argument("--workers", type=int, default=3, help="processor cores for cutting regions not yet cached")
    cmp_ = sub.add_parser("spike-s2-compare", help="compare stage 1 built again with the build of 1 November")
    cmp_.add_argument("--workers", type=int, default=3, help="processor cores to use (default 3)")
    ex = sub.add_parser("spike-s2-extract", help="used by spike-s2: read the planet file in its own process")
    ex.add_argument("stage", choices=["1", "2", "3", "4", "belgium"])
    rp = sub.add_parser("read-planet", help="used by build: read the planet file in its own process (osm-areas)")
    rp.add_argument("folder", help="the osm-areas stage's folder, holding its request")
    wx = sub.add_parser("spike-s2-water", help="used by spike-s2: read the inland water in its own process")
    wx.add_argument("stage", choices=["1", "2", "3", "4", "belgium"])
    ins = sub.add_parser("inspect", help="ask a pack about itself: its manifest, one feature, or what is at a point",
                         description="Examples: inspect test manifest; inspect test feature osm:r62149; "
                                     "inspect test at 50.7 -1.3; inspect test 50.7 -1.3.")
    ins.add_argument("pack", help="the pack file, or the name of a pack in the output folder")
    ins.add_argument("question", nargs="+", help="manifest, feature <identifier>, at <lat> <lon>, or <lat> <lon>")
    ws = sub.add_parser("world-sample", help="write the Natural Earth world sample used by the globe spike")
    ws.add_argument("--scale", default="110m", choices=["110m", "50m", "10m"])
    ws.add_argument("--out", help="output file; default mapcore/data/world_<scale>.json in the repository")
    return parser


REPO = Path(__file__).resolve().parent.parent


def _folders(args: argparse.Namespace):
    try:
        return resolve_data_folder(args.data)
    except DataFolderNotSet as exc:
        print(exc)
        return None


def cmd_check(args: argparse.Namespace) -> int:
    from mapdata.pipeline.check import check

    folders = _folders(args)
    return 2 if folders is None else check(folders, args.pack)


def cmd_fetch(args: argparse.Namespace) -> int:
    from mapdata.pipeline.settings import load_pack, load_sources
    from mapdata.stages import fetch

    sources = load_sources()
    if args.source == "list":
        for s in sources.values():
            where = "in the repository" if s.repo else ("downloaded" if s.file else "a local copy")
            print(f"{s.key}: {s.name}, {where}. Licence: {s.licence}.")
        return 0
    if args.pack:
        keys = list(load_pack(args.pack).sources)
    elif args.source == "all":
        keys = list(sources)
    elif args.source in sources:
        keys = [args.source]
    else:
        print(f"Unknown source {args.source}. Run: python -m mapdata fetch list" if args.source
              else "Name a source, or give --pack. Run: python -m mapdata fetch list")
        return 2
    folders = _folders(args)
    if folders is None:
        return 2
    if not folders.root.is_dir():
        print(f"The data folder, {folders.root}, cannot be reached. Connect its drive, then run fetch again.")
        return 2
    return 1 if fetch.fetch_sources(keys, sources, folders) else 0


def cmd_build(args: argparse.Namespace) -> int:
    from mapdata import parallel
    from mapdata.pipeline.build import build

    folders = _folders(args)
    if folders is None:
        return 2
    workers = parallel.check_workers(parallel.AWAY_WORKERS if args.away else args.workers)
    if args.wait_for_yes:
        from mapdata.pipeline.build import build_waiting

        return build_waiting(["--data", str(folders.root), "build", args.pack, "--workers", str(workers)])
    return build(args.pack, folders, workers)


def place_words(lat: float, lon: float) -> str:
    """A point as people say it: "68.234 north, 14.568 east", "90.0 south, 0.0 east"."""
    ns = "south" if lat < 0 else "north"
    ew = "west" if lon < 0 else "east"
    return f"{abs(lat)} {ns}, {abs(lon)} {ew}"


def _name(feature: dict) -> str:
    names = feature["names"]
    return names.get("en") or next(iter(names.values()), feature["id"])


def _pack_path(args: argparse.Namespace) -> Path | None:
    path = Path(args.pack)
    if path.is_file():
        return path
    folders = _folders(args)
    if folders is None:
        return None
    named = folders.output / args.pack / f"{args.pack}.pack"
    if named.is_file():
        return named
    print(f"There is no pack file {args.pack}, and no pack called {args.pack} in {folders.output}.")
    return None


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


INSPECT_HELP = "Ask: manifest, feature <identifier>, at <lat> <lon>, or <lat> <lon>."


def cmd_inspect(args: argparse.Namespace) -> int:
    """A pack's manifest, one feature, or what is at a point, in plain lines (DMT-2, architecture 8.1)."""
    from mapcore.packs.pack import PackError
    from mapdata.stages.lookup import open_pack

    q = list(args.question)
    if q and q[0] == "at":
        q = q[1:]
    point = [_number(v) for v in q] if len(q) == 2 else None
    asks_manifest = q == ["manifest"]
    asks_feature = len(q) == 2 and q[0] == "feature"
    asks_point = point is not None and None not in point and not asks_feature
    if not (asks_manifest or asks_feature or asks_point):
        print(INSPECT_HELP)
        return 2
    path = _pack_path(args)
    if path is None:
        return 1
    try:
        with open_pack(path) as pack:
            if asks_manifest:
                return inspect_manifest(pack)
            if asks_feature:
                return inspect_feature(pack, q[1])
            return inspect_point(pack, point[0], point[1])
    except PackError as exc:
        print(exc.message)
        return 1


def inspect_manifest(pack) -> int:
    m = pack.manifest
    print(f"Pack {m['name']}, version {m['version']}, format {m['format']}, built from sources dated up to "
          f"{m['built']}.")
    if m.get("title"):
        print(m["title"])
    apps = m["app_versions"]
    upto = f" up to but not including {apps['before']}." if apps.get("before") else " on."
    print(f"Works with application versions from {apps['from']}{upto}")
    print(f"Coverage: {m['coverage'].get('kind', 'not given')}.")
    print(f"Layers: {', '.join(layer['name'] for layer in pack.layers)}.")
    print(f"{m['features']['count']} feature records. Tile levels: {', '.join(map(str, m['tile_levels']))}.")
    print(f"Drawing levels: {len(m['drawing_levels']) or 'none'}.")
    print("Sources:")
    for s in m["sources"]:
        print(f"{s['name']}: {s['licence']}, dated {s['date']}.")
    print("Attribution:")
    for line in pack.attribution.splitlines():
        if line.strip():
            print(line)
    return 0


def inspect_feature(pack, identifier: str) -> int:
    f = pack.feature_by_id(identifier)
    if f is None:
        print(f"There is no feature {identifier} in this pack.")
        return 1
    print(f"{_name(f)}: {f['id']}.")
    for key in sorted(f):
        if key == "id":
            continue
        value = f[key]
        if isinstance(value, dict):
            value = ", ".join(f"{k} {v}" for k, v in value.items())
        elif isinstance(value, list):
            value = ", ".join(str(v) for v in value) or "none"
        elif value is None:
            value = "not set"
        print(f"{key}: {value}.")
    return 0


def inspect_point(pack, lat: float, lon: float) -> int:
    from mapdata.stages.lookup import Lookup

    found = Lookup(pack).at(lon, lat)
    if not found:
        print(f"At {place_words(lat, lon)}: no area.")
        return 0
    print(f"At {place_words(lat, lon)}, smallest first:")
    for f in found:
        name = _name(f)
        extra = f", sovereign state {f['sovereign']}" if f.get("sovereign") and f["sovereign"] != name else ""
        print(f"{name}: {f['layer']}, {f['type']}{extra}, {f['area_km2']:,.0f} km2, {f['id']}.")
    return 0


def cmd_world_sample(args: argparse.Namespace) -> int:
    from mapdata.stages import world_sample

    try:
        folders = resolve_data_folder(args.data)
    except DataFolderNotSet as exc:
        print(exc)
        return 2
    name = f"ne_{args.scale}_admin_0_countries.geojson"
    source = folders.downloads / "naturalearth" / name
    if not source.is_file():
        print(f"Natural Earth file not found: {source}")
        print("Download it from https://github.com/nvkelso/natural-earth-vector, geojson folder, into that folder.")
        return 1
    out = Path(args.out) if args.out else REPO / "mapcore" / "data" / f"world_{args.scale}.json"
    sample = world_sample.convert(json.loads(source.read_text(encoding="utf-8")),
                                  source_name=f"Natural Earth 1:{args.scale[:-1]} million admin 0 countries")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(world_sample.dumps(sample), encoding="utf-8", newline="\n")
    print(f"Wrote {len(sample['countries'])} countries to {out}, {out.stat().st_size // 1024} KB.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        folders = resolve_data_folder(args.data)
    except DataFolderNotSet as exc:
        print(exc)
        return 2
    print(f"Data folder: {folders.root}, from {folders.where_from}.")
    if not folders.root.is_dir():
        print("That folder does not exist yet.")
        return 1
    for name, path in (("Downloads", folders.downloads), ("Working", folders.working), ("Output", folders.output)):
        state = "present" if path.is_dir() else "not created yet"
        print(f"{name} folder: {path}, {state}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "fetch":
        return cmd_fetch(args)
    if args.command == "build":
        return cmd_build(args)
    if args.command == "spike-s2-stage1":
        from mapdata.stages import s2_stage1
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        return s2_stage1.run(folders)
    if args.command == "spike-s2-compare":
        from mapdata import parallel
        from mapdata.stages import s2_compare
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        return s2_compare.run(folders, parallel.check_workers(args.workers))
    if args.command == "spike-s2-counties":
        from mapdata import parallel
        from mapdata.stages import county_trials
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        methods = args.method or ["whole-gap", "nearby-gap", "covered-first", "gap-land"]
        return county_trials.run(args.stage, folders, methods, args.country, args.within, args.give_up,
                                 parallel.check_workers(args.workers))
    if args.command in ("spike-s2", "spike-s2-extract", "spike-s2-water"):
        from mapdata.stages import s2_stage
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        if args.command == "spike-s2-extract":
            return s2_stage.run_extract(args.stage, folders)
        if args.command == "spike-s2-water":
            return s2_stage.run_water_extract(args.stage, folders)
        from mapdata import parallel
        workers = parallel.AWAY_WORKERS if args.away else args.workers
        return s2_stage.run(args.stage, folders, parallel.check_workers(workers))
    if args.command == "read-planet":
        from mapdata.stages import osm_areas
        return osm_areas.main(Path(args.folder))
    if args.command == "inspect":
        return cmd_inspect(args)
    if args.command == "world-sample":
        return cmd_world_sample(args)
    return 1


if __name__ == "__main__":
    # Names such as Russia's are printed as written in OSM. Sent to a file,
    # Windows would otherwise use its old character set and stop the build.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
