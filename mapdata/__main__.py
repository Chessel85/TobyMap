"""The mapdata command line program (architecture section 8).

Phase 0 has only the status command. Output is plain lines, suited to a
screen reader (DMT-2).
"""
from __future__ import annotations

import argparse
import sys

from mapdata.paths import DataFolderNotSet, resolve_data_folder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mapdata", description="Build TobyMap data packs.")
    parser.add_argument("--data", help="the data folder; overrides MAPDATA_ROOT and paths.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="say where the data folder is and what it holds")
    return parser


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
    return 1


if __name__ == "__main__":
    sys.exit(main())
