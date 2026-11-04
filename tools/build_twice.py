"""Build a pack's write stage a second time from its kept results, and compare the two packs byte for byte (DMT-1).

Usage: python tools/build_twice.py world [--workers 8]

The pack must already be built. The write stage's folder is renamed with ".first"
on the end (inside the working folder only), the build is run again, which
writes the stage afresh from the stages before it, and the two packs are
compared. If they match, the ".first" folder is deleted; if not, both are
kept and the difference is reported.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    from mapdata.paths import resolve_data_folder
    from mapdata.pipeline.build import build, pack_file_name

    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--data")
    args = ap.parse_args()
    folders = resolve_data_folder(args.data)
    work = folders.working / args.pack
    writes = sorted(work.glob("*-write-*"))
    writes = [w for w in writes if w.is_dir() and not w.name.endswith(".first") and (w / "finished.json").is_file()]
    if not writes:
        print(f"No finished write stage in {work}. Build the pack first.")
        return 2
    # Older write stages stay in the working folder after a setting changes; the newest is the current one.
    first = max(writes, key=lambda w: (w / "finished.json").stat().st_mtime)
    name = pack_file_name(args.pack)
    before = sha(first / name)
    kept = first.with_name(first.name + ".first")
    first.rename(kept)
    print(f"The first pack, {kept / name}, has checksum {before}. Building the write stage again.", flush=True)
    code = build(args.pack, folders, args.workers)
    if code != 0:
        print("The second build failed.")
        return code
    after = sha(first / name)
    if before == after:
        print(f"IDENTICAL: the second pack has the same checksum, {after}. DMT-1 holds for {args.pack}.")
        shutil.rmtree(kept)
        return 0
    print(f"DIFFERENT: the first pack's checksum is {before} and the second's is {after}. Both are kept: "
          f"{kept} and {first}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
