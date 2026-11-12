"""Time the writing stage alone, on a pack's kept stages, and say whether it writes the same pack (P3-T1k, DMT-1).

The stage before "write" must have been built and kept. The writing stage runs
again into its own folder inside the data folder's tobymap folder,
working/<pack>-time-write/<label>, never into the build's folders, so a build
is never changed. Each progress line is printed with the time since the start.
At the end: the time taken, the pack's checksum, and whether it is the same,
byte for byte, as the pack in the output folder, the last build's, or the pack
named by --compare.

With --previous, the writing stage reads that folder instead, such as an older
world build's stage before "write", so it can be timed on data it was not tuned
on; the pack's settings still give the drawing levels and layers.

Run: .venv\\Scripts\\python.exe tools\\time_write.py trial-western-europe --workers 6 --label now
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None) -> int:
    from mapdata.paths import resolve_data_folder
    from mapdata.pipeline import ledger as ledgermod
    from mapdata.pipeline.build import (FINISHED, STAGES, StageContext, fingerprint, load_pack, pack_file_name,
                                        resolve_sources)
    from mapdata.pipeline.progress import Progress

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--label", default="run", help="the name of this run's folder")
    ap.add_argument("--data", default=None)
    ap.add_argument("--previous", default=None, help="the folder to read, in place of the stage before write")
    ap.add_argument("--compare", default=None, help="the pack to compare with (default: the output folder's)")
    args = ap.parse_args(argv)

    folders = resolve_data_folder(args.data)
    pack = load_pack(args.pack)
    sources = resolve_sources(pack, folders)
    prints = {k: pack.sources[k].fingerprint(p) for k, p in sources.items()}
    previous_print, previous_folder, write_stage = "", None, None
    for n, stage in enumerate(pack.stages, 1):
        fp = fingerprint(pack, stage, previous_print, prints)
        folder = folders.working / args.pack / f"{n:02d}-{stage['stage']}-{fp[:16]}"
        if stage["stage"] == "write":
            write_stage = (n, stage)
            break
        if not args.previous and not (folder / FINISHED).is_file():
            print(f"Stage {n}, {stage['stage']}, is not built with today's settings and code. Build the pack first.")
            return 2
        previous_print, previous_folder = fp, folder
    if write_stage is None:
        print("The pack has no write stage.")
        return 2
    if args.previous:
        previous_folder = Path(args.previous)
    out = folders.working / f"{args.pack}-time-write" / args.label
    started = time.perf_counter()
    progress = Progress(say=lambda t: print(f"{time.perf_counter() - started:7.1f} s  {t}", flush=True),
                        interval=0)
    ctx = StageContext(pack, write_stage[1], write_stage[0], previous_folder, out, folders, progress,
                       ledgermod.Ledger(folders.own), args.workers, sources, None)
    out.mkdir(parents=True, exist_ok=True)
    from importlib import import_module

    import_module(STAGES["write"].module).run(ctx)
    took = time.perf_counter() - started
    mine = out / pack_file_name(args.pack)
    digest = sha256(mine)
    print(f"Wrote the pack in {took:.1f} seconds with {args.workers} workers. Checksum {digest}.")
    built = Path(args.compare) if args.compare else folders.output / args.pack / pack_file_name(args.pack)
    if built.is_file():
        same = mine.read_bytes() == built.read_bytes()
        print(f"The same, byte for byte, as {built}." if same else
              f"Not the same as {built}, checksum {sha256(built)}.")
    else:
        print(f"{built} is not there to compare with.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
