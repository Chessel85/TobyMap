"""What a larger pack means for you: start-up, the first place said, memory and storage (P3-T1a).

    .venv\\Scripts\\python.exe tools\\time_pack_start.py pad <pack> --mb 300 --out <padded.pack>
    .venv\\Scripts\\python.exe tools\\time_pack_start.py desktop <pack> [<pack> ...] [--runs 3] [--json FILE]
    .venv\\Scripts\\python.exe tools\\time_pack_start.py web <pack> [<pack> ...] [--browser chromium] [--json FILE]

pad: a copy of a pack made larger with padding records, which the
application never reads, of the same average size as the pack's own pack
tiles, so the copy has as many records as a real pack of that size would.
The padding is random, so it does not compress, as map shapes hardly do.
Its manifest and every real record are the pack's own, so it opens and
works as the pack does. Used to stand in for the world pack at the size the
trial estimates, before it is built.

desktop: starts the desktop application with each pack, with no window on
the screen and no sound (QT_QPA_PLATFORM=offscreen, stand-in announcer and
sounds), each run in a new process. Measures the time from starting the
process to the window being made, and to the first place being said (the
start, which names the map with the place, read as the window appears); the
memory then; and the memory
after a held key walk of 30 steps, each drawn.

web: serves the web version with each pack and opens it in Chromium and
Firefox, each with a new, empty profile, so the first visit downloads the
pack into the browser's private storage as it would from the internet (here
from this computer, so far faster). Measures the first visit (download
included), the storage used, and a second visit, when the pack is read from
storage: the time until the map is ready and names the place, and the memory
of the browser's processes.

The download time at 10 and 50 megabits a second is worked out from the
pack's size, not measured.

Every result is plain lines for a screen reader (DMT-2).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

START_AT = "51.06,-1.31"   # Winchester, in Hampshire: inside the trial pack and the world pack


# Padding ------------------------------------------------------------------------

def pad(source: Path, target_mb: float, out: Path) -> dict:
    """A copy of the pack padded to about target_mb megabytes (see the notes above)."""
    from mapcore.packs import pack as packmod

    with packmod.Pack(source, check_app=False) as p:
        directory = dict(p.directory)
        tile_sizes = [v[1] for k, v in directory.items() if k.startswith("tile/")]
        average = max(1024, sum(tile_sizes) // max(1, len(tile_sizes)))
        records = {k: bytes(p.source.read(v[0], v[1])) for k, v in sorted(directory.items(), key=lambda kv: kv[1][0])}
    have = sum(len(b) for b in records.values())
    want = int(target_mb * 1e6) - have
    rng = random.Random(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_dir = {}
    with open(out, "wb") as f:
        f.write(bytes(packmod.HEADER_SIZE))
        for k, b in records.items():
            new_dir[k] = [f.tell(), len(b), packmod.check_number(b)]
            f.write(b)
        n = 0
        while want > 0:
            size = min(want, max(256, int(rng.expovariate(1 / average))))
            b = rng.randbytes(size)
            new_dir[f"pad/{n}"] = [f.tell(), size, packmod.check_number(b)]
            f.write(b)
            want -= size
            n += 1
        import zlib

        directory_bytes = zlib.compress(packmod._json({"records": new_dir}), 9)
        offset = f.tell()
        f.write(directory_bytes)
        head = packmod._HEADER.pack(packmod.MAGIC, packmod.FORMAT, 0, 0, offset, len(directory_bytes),
                                    packmod.check_number(directory_bytes), 0)
        head = head[:-4] + struct.pack("<I", packmod.check_number(head[:-4]))
        f.seek(0)
        f.write(head)
    packmod.write_checksum(out)
    with packmod.Pack(out, check_app=False) as p:   # it opens as a pack
        assert p.manifest["name"]
    return {"file": str(out), "bytes": out.stat().st_size, "padding_records": n, "records": len(new_dir)}


# Memory, from Windows ----------------------------------------------------------

def own_memory_mb() -> dict:
    """This process's memory: working set, its peak, and private bytes, in MB (Windows only)."""
    if sys.platform != "win32":
        return {}
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t)]

    c = Counters()
    c.cb = ctypes.sizeof(c)
    psapi = ctypes.WinDLL("psapi")
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return {"working_mb": c.WorkingSetSize / 1e6, "peak_working_mb": c.PeakWorkingSetSize / 1e6,
            "private_mb": c.PrivateUsage / 1e6}


def browser_memory_mb() -> float:
    """The working set of every process of Playwright's own browsers, in MB: never your own browsers."""
    cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '*ms-playwright*' } | "
           "Measure-Object -Property WorkingSetSize -Sum | ForEach-Object { $_.Sum }")
    done = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    try:
        return float(done.stdout.strip() or 0) / 1e6
    except ValueError:
        return 0.0


# The desktop ---------------------------------------------------------------------

def desktop_child(pack: str, started: float) -> None:
    """One start of the desktop application, in its own process. Prints one line of JSON."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["TOBYMAP_PACKS"] = pack
    from PySide6.QtWidgets import QApplication

    from desktop.announcer import RecordingAnnouncer
    from desktop.sounds import RecordingSounds
    from desktop.window import MainWindow

    said: list[tuple[float, str]] = []

    class Stamped(RecordingAnnouncer):
        def speak(self, text, priority="polite"):
            said.append((time.time(), text))
            super().speak(text, priority)

    app = QApplication.instance() or QApplication([sys.argv[0]])
    with tempfile.TemporaryDirectory() as folder:
        window = MainWindow(announcer=Stamped(), sounds=RecordingSounds(), data_folder=Path(folder),
                            start_at=START_AT)
        made = time.time()
        app.processEvents()
        window.show()
        app.processEvents()
        # The start is not spoken: the map is named with it, and the screen reader reads that name as
        # the window appears (P2-T17d). So the first place is said when the window is shown.
        first = (time.time(), window.map.accessibleName())
        at_first = own_memory_mb()
        session = window.session
        walk_ms = []
        for _ in range(30):
            t = time.perf_counter()
            session.run("move.east", held=True)
            session.scene(900, 760)
            walk_ms.append((time.perf_counter() - t) * 1000)
        after_walk = own_memory_mb()
        window.close()
    print(json.dumps({"window_s": made - started, "first_place_s": (first[0] - started) if first[0] else None,
                      "first_said": first[1], "memory_at_first": at_first, "memory_after_walk": after_walk,
                      "walk_ms_median": sorted(walk_ms)[len(walk_ms) // 2]}))


def run_desktop(packs: list[Path], runs: int) -> list[dict]:
    out = []
    for pack in packs:
        for n in range(runs):
            started = time.time()
            done = subprocess.run([sys.executable, __file__, "desktop-child", str(pack), repr(started)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
            line = (done.stdout or "").strip().splitlines()[-1:] or [""]
            try:
                r = json.loads(line[0])
            except ValueError:
                raise SystemExit(f"The desktop run failed: {(done.stderr or done.stdout)[-2000:]}")
            r.update(pack=str(pack), bytes=pack.stat().st_size, run=n + 1)
            out.append(r)
            print(f"Desktop, {pack.name}, run {n + 1}: window in {r['window_s']:.2f} s, first place said in "
                  f"{r['first_place_s']:.2f} s, memory {r['memory_at_first'].get('private_mb', 0):,.0f} MB private, "
                  f"{r['memory_after_walk'].get('private_mb', 0):,.0f} MB after the walk.", flush=True)
    return out


# The web version ------------------------------------------------------------------

def run_web(packs: list[Path], browsers: list[str]) -> list[dict]:
    import functools
    import http.server
    import threading

    sys.path.insert(0, str(ROOT / "tools"))
    import serve_web
    import stage_web
    from playwright.sync_api import sync_playwright

    stage_web.stage()
    out = []
    with sync_playwright() as p:
        for pack in packs:
            serve_web.Handler.pack = pack.resolve()
            handler = functools.partial(serve_web.Handler, directory=str(serve_web.WEB))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_address[1]}/index.html?at={START_AT}"
            try:
                for name in browsers:
                    with tempfile.TemporaryDirectory() as profile:
                        context = getattr(p, name).launch_persistent_context(profile, viewport={"width": 1200, "height": 800})
                        r = {"pack": str(pack), "bytes": pack.stat().st_size, "browser": name}
                        for visit in ("first", "second"):
                            page = context.new_page()
                            t = time.perf_counter()
                            page.goto(url)
                            page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)",
                                                   timeout=1_800_000, polling=100)
                            took = time.perf_counter() - t
                            if page.evaluate("window.tobymap.error"):
                                raise SystemExit(f"{name}: {page.evaluate('window.tobymap.error')}")
                            label = page.evaluate("document.getElementById('map').getAttribute('aria-label')")
                            page.wait_for_timeout(3000)   # the spatial voice and sounds load after the start
                            r[visit] = {"ready_s": took, "named": label, "memory_mb": browser_memory_mb(),
                                        "storage_mb": page.evaluate(
                                            "navigator.storage.estimate().then(e => e.usage)") / 1e6}
                            page.close()
                        context.close()
                        out.append(r)
                        print(f"{name.capitalize()}, {pack.name}: first visit ready in {r['first']['ready_s']:.1f} s, "
                              f"second visit in {r['second']['ready_s']:.1f} s, storage "
                              f"{r['first']['storage_mb']:,.0f} MB, memory {r['second']['memory_mb']:,.0f} MB.",
                              flush=True)
            finally:
                server.shutdown()
    return out


def download_lines(size_bytes: int) -> list[str]:
    return [f"At {rate} megabits a second: {size_bytes * 8 / (rate * 1e6) / 60:.1f} minutes."
            for rate in (10, 50)]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "desktop-child":
        desktop_child(argv[1], float(argv[2]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="what", required=True)
    pa = sub.add_parser("pad")
    pa.add_argument("pack", type=Path)
    pa.add_argument("--mb", type=float, required=True)
    pa.add_argument("--out", type=Path, required=True)
    de = sub.add_parser("desktop")
    de.add_argument("packs", type=Path, nargs="+")
    de.add_argument("--runs", type=int, default=3)
    de.add_argument("--json", type=Path)
    we = sub.add_parser("web")
    we.add_argument("packs", type=Path, nargs="+")
    we.add_argument("--browser", action="append", choices=["chromium", "firefox"])
    we.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    if args.what == "pad":
        r = pad(args.pack, args.mb, args.out)
        print(f"Padded copy {r['file']}: {r['bytes'] / 1e6:,.1f} MB, {r['records']:,} records, of which "
              f"{r['padding_records']:,} are padding.")
        return 0
    results = run_desktop(args.packs, args.runs) if args.what == "desktop" else \
        run_web(args.packs, args.browser or ["chromium", "firefox"])
    for pack in args.packs:
        print(f"Download of {pack.name}, {pack.stat().st_size / 1e6:,.0f} MB, worked out from its size:")
        for line in download_lines(pack.stat().st_size):
            print(f"* {line}")
    if args.json:
        args.json.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
