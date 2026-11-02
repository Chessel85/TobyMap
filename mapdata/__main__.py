"""The mapdata command line program (architecture section 8).

Phase 0 has the status command, and world-sample for the globe spike (S5). Output is plain lines, suited to a
screen reader (DMT-2).
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
    fe = sub.add_parser("fetch", help="download a source into the data folder's downloads folder")
    fe.add_argument("source", help="the source to download, or 'list' to list them")
    sub.add_parser("spike-s2-stage1", help="spike S2 stage 1: the UK, France and Spain, with its report")
    st = sub.add_parser("spike-s2", help="spike S2 stage 2 (Norway and Sweden), 3 (the 180 degree line) or 4 (Argentina)")
    st.add_argument("stage", type=int, choices=[2, 3, 4])
    st.add_argument("--workers", type=int, default=3,
                    help="processor cores to use for the slowest steps (default 3, which leaves the laptop usable)")
    st.add_argument("--away", action="store_true",
                    help="use 6 worker processes, for when nobody is using the laptop (DP103)")
    ex = sub.add_parser("spike-s2-extract", help="used by spike-s2: read the planet file in its own process")
    ex.add_argument("stage", type=int, choices=[2, 3, 4])
    ins = sub.add_parser("inspect", help="ask a pack what is at a point")
    ins.add_argument("pack", help="the pack file")
    ins.add_argument("lat", type=float)
    ins.add_argument("lon", type=float)
    ws = sub.add_parser("world-sample", help="write the Natural Earth world sample used by the globe spike")
    ws.add_argument("--scale", default="110m", choices=["110m", "50m", "10m"])
    ws.add_argument("--out", help="output file; default mapcore/data/world_<scale>.json in the repository")
    return parser


REPO = Path(__file__).resolve().parent.parent


def cmd_fetch(args: argparse.Namespace) -> int:
    from mapdata.stages import fetch

    if args.source == "list":
        for s in fetch.SOURCES.values():
            print(f"{s.key}: {s.note} Licence: {s.licence}.")
        return 0
    if args.source not in fetch.SOURCES:
        print(f"Unknown source {args.source}. Run: python -m mapdata fetch list")
        return 2
    try:
        folders = resolve_data_folder(args.data)
    except DataFolderNotSet as exc:
        print(exc)
        return 2
    fetch.fetch(fetch.SOURCES[args.source], folders.downloads)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """What is at a point, smallest area first, in plain lines (DMT-2, architecture 8.1)."""
    from mapcore.packs.archive import Pack

    pack = Pack(Path(args.pack))
    try:
        found = pack.at(args.lon, args.lat)
    finally:
        pack.close()
    if not found:
        print(f"At {args.lat} north, {args.lon} east: sea, no land area.")
        return 0
    print(f"At {args.lat} north, {args.lon} east, smallest first:")
    for f in found:
        extra = f", sovereign state {f['sovereign']}" if f.get("sovereign") and f["sovereign"] != f["name"] else ""
        print(f"{f['name']}: {f['layer']}, {f['type']}{extra}, {f['area_km2']:,.0f} km2.")
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
    if args.command == "fetch":
        return cmd_fetch(args)
    if args.command == "spike-s2-stage1":
        from mapdata.stages import s2_stage1
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        return s2_stage1.run(folders)
    if args.command in ("spike-s2", "spike-s2-extract"):
        from mapdata.stages import s2_stage
        try:
            folders = resolve_data_folder(args.data)
        except DataFolderNotSet as exc:
            print(exc)
            return 2
        if args.command == "spike-s2-extract":
            return s2_stage.run_extract(args.stage, folders)
        from mapdata import parallel
        workers = parallel.AWAY_WORKERS if args.away else args.workers
        return s2_stage.run(args.stage, folders, parallel.check_workers(workers))
    if args.command == "inspect":
        return cmd_inspect(args)
    if args.command == "world-sample":
        return cmd_world_sample(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
