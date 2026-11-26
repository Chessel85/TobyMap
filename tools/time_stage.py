"""Run one stage of a pack alone, timed, with its peak memory, and say whether it makes the same files (P4-T1l, DMT-1).

The stage reads the kept folder of the stage before it, as a build would, and
writes into its own folder inside the data folder's tobymap folder,
working/<pack>-time-stage/<stage>-<label>, never into the build's folders, so
a build is never changed. The stage before is the one built with today's code
and settings if there is one, otherwise the newest finished one of that stage
(said, as it may be from older code), or the folder named by --previous.

Each progress line starts with the time and the stage's own process's memory then. At the end: the time taken; the peak memory of the stage's own process, of its
largest worker and of all together; and, for each file the stage wrote, whether
it is the same, byte for byte, as the same file in the build's newest finished
folder for this stage, or in the folder named by --compare.

Run: .venv\\Scripts\\python.exe tools\\time_stage.py hampshire-isle-of-wight relationships --workers 3 --label now
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


def newest(base: Path, n: int, kind: str, exclude: Path | None = None) -> Path | None:
    from mapdata.pipeline.build import FINISHED

    found = [p for p in base.glob(f"{n:02d}-{kind}-*") if (p / FINISHED).is_file() and p != exclude]
    return max(found, key=lambda p: (p / FINISHED).stat().st_mtime) if found else None


def same_files(mine: Path, theirs: Path) -> list[str]:
    from mapdata.pipeline.build import FINISHED

    out = []
    for p in sorted(mine.rglob("*")):
        if not p.is_file() or p.name == FINISHED:
            continue
        other = theirs / p.relative_to(mine)
        if not other.is_file():
            out.append(f"{p.relative_to(mine)}: not in {theirs.name}.")
        elif p.stat().st_size == other.stat().st_size and sha256(p) == sha256(other):
            out.append(f"{p.relative_to(mine)}: the same, byte for byte.")
        else:
            out.append(f"{p.relative_to(mine)}: different ({p.stat().st_size:,} bytes, against "
                       f"{other.stat().st_size:,}).")
    return out


def main(argv=None) -> int:
    from mapdata.paths import resolve_data_folder
    from mapdata.pipeline import ledger as ledgermod
    from mapdata.pipeline.build import FINISHED, STAGES, StageContext, fingerprint, load_pack, resolve_sources
    from mapdata.pipeline.peak import PeakWatch
    from mapdata.pipeline.progress import Progress

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack")
    ap.add_argument("stage", help="the stage's kind, such as relationships, or its number in the pack")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--label", default="run", help="the name of this run's folder")
    ap.add_argument("--data", default=None)
    ap.add_argument("--previous", default=None, help="the folder to read, in place of the stage before")
    ap.add_argument("--compare", default=None, help="the folder to compare with (default: the build's newest)")
    args = ap.parse_args(argv)

    folders = resolve_data_folder(args.data)
    pack = load_pack(args.pack)
    sources = resolve_sources(pack, folders)
    prints = {k: pack.sources[k].fingerprint(p) for k, p in sources.items()}
    base = folders.working / args.pack
    previous_print, previous_folder, target, earlier = "", None, None, {}
    for n, stage in enumerate(pack.stages, 1):
        if stage["stage"] == args.stage or str(n) == args.stage:
            target = (n, stage)
            break
        fp = fingerprint(pack, stage, previous_print, prints)
        folder = base / f"{n:02d}-{stage['stage']}-{fp[:16]}"
        if not (folder / FINISHED).is_file():
            folder = newest(base, n, stage["stage"])
            if folder is None and not args.previous:
                print(f"Stage {n}, {stage['stage']}, has never finished. Build the pack first.")
                return 2
        previous_print, previous_folder = fp, folder
        if folder is not None:
            earlier[stage["stage"]] = folder
    if target is None:
        print(f"The pack has no stage {args.stage}.")
        return 2
    if args.previous:
        previous_folder = Path(args.previous)
    print(f"Stage {target[0]}, {target[1]['stage']}, reading {previous_folder}.")
    out = folders.working / f"{args.pack}-time-stage" / f"{target[1]['stage']}-{args.label}"
    started = time.perf_counter()
    from mapdata.parallel import memory_mb

    def say(text):   # each line with this process's memory then, to see which step holds the most
        print(f"{time.perf_counter() - started:7.1f} s  {memory_mb()[0]:6,.0f} MB  {text}", flush=True)
    progress = Progress(say=say, interval=0)
    ctx = StageContext(pack, target[1], target[0], previous_folder, out, folders, progress,
                       ledgermod.Ledger(folders.own), args.workers, sources, None, earlier)
    out.mkdir(parents=True, exist_ok=True)
    from importlib import import_module

    with PeakWatch() as watch:
        import_module(STAGES[target[1]["stage"]].module).run(ctx)
    took = time.perf_counter() - started
    print(f"The stage took {took:.1f} seconds with {args.workers} workers.")
    print(watch.sentence() or "Peak memory: not measured on this system.")
    theirs = Path(args.compare) if args.compare else newest(base, target[0], target[1]["stage"])
    if theirs is None:
        print("No finished folder of this stage to compare with.")
    else:
        print(f"Compared with {theirs}:")
        for text in same_files(out, theirs):
            print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
