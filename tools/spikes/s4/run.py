"""Spike S4: time the core in the browser, against the desktop (P0-T7, architecture 12.5).

Serves this repository (for the test page, Pyodide and the core's files) and
the pack's folder on this computer, then opens the page in Chromium and
Firefox without a window. The page starts Pyodide in a worker, copies the
pack into the browser's private storage, and times "where am I" and walks of
steps (s4_bench.py). The same timings are run here in desktop Python too.
Results go to docs/spikes/s4-results as plain text, and as JSON.

Run:
    .venv\\Scripts\\python.exe tools\\spikes\\s4\\run.py
    .venv\\Scripts\\python.exe tools\\spikes\\s4\\run.py --serve      (open the page in your own browser)

Options: --browsers chromium firefox, --pack <file> (default: spike S2 stage 2's
compact pack in the data folder's output), --fresh (copy the pack again).
Needs Pyodide with Shapely: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --web
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "spikes" / "s3"))

import yaml  # noqa: E402

import hosting  # noqa: E402  (spike S3's local server, which answers range requests)
import s4_bench  # noqa: E402

RESULTS = ROOT / "docs" / "spikes" / "s4-results"
PLACES = ROOT / "tests" / "acceptance" / "coastline_places_stage2.yaml"
PYODIDE = ROOT / "web" / "vendor" / "pyodide"
PACKAGES = ["numpy", "shapely"]
CORE_FILES = [
    {"from": "mapcore/__init__.py", "to": "mapcore/__init__.py"},
    {"from": "mapcore/packs/__init__.py", "to": "mapcore/packs/__init__.py"},
    {"from": "mapcore/packs/archive.py", "to": "mapcore/packs/archive.py"},
    {"from": "tools/spikes/s4/s4_bench.py", "to": "s4_bench.py"},
]


def default_pack() -> Path:
    from mapdata.paths import resolve_data_folder
    return resolve_data_folder(None).output / "s2-stage2" / "s2-stage2-compact.pack"


def check_pyodide() -> None:
    lock = json.loads((PYODIDE / "pyodide-lock.json").read_text(encoding="utf-8"))
    missing = [p for p in PACKAGES if not (PYODIDE / lock["packages"][p]["file_name"]).is_file()]
    if missing:
        raise SystemExit(f"Pyodide's {', '.join(missing)} not found in web/vendor/pyodide. "
                         "Run: .venv\\Scripts\\python.exe tools\\fetch_vendor.py --web")


def download_on_disk() -> list[tuple[str, int]]:
    """The files a first visit fetches for Pyodide and these packages, with their sizes."""
    lock = json.loads((PYODIDE / "pyodide-lock.json").read_text(encoding="utf-8"))
    names = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
    todo, seen = list(PACKAGES), set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        names.append(lock["packages"][p]["file_name"])
        todo.extend(lock["packages"][p].get("depends", []))
    return [(n, (PYODIDE / n).stat().st_size) for n in names if (PYODIDE / n).is_file()]


def start_servers(pack: Path, places: list, ports=(0, 0)):
    pack_server = hosting.LocalServer(pack.parent, allow_other_origins=True, port=ports[1]).start()
    config = {"packUrl": f"{pack_server.url}/{pack.name}", "packName": pack.name, "packSize": pack.stat().st_size,
              "places": places, "packages": PACKAGES, "coreFiles": CORE_FILES}
    page = hosting.LocalServer(ROOT, port=ports[0],
                               extra_files={"/tools/spikes/s4/web/config.json": json.dumps(config).encode()}).start()
    return page, [page, pack_server]


def desktop_run(pack: Path, places: list) -> tuple[list[str], dict]:
    from mapcore.packs.archive import Pack
    t0 = time.perf_counter()
    p = Pack(pack)
    open_ms = (time.perf_counter() - t0) * 1000
    try:
        result = s4_bench.run(p, places, s4_bench.WALKS)
    finally:
        p.close()
    lines = [f"Spike S4 on the desktop, Python {sys.version.split()[0]}, {dt.datetime.now().isoformat(timespec='seconds')}.",
             f"Pack: {pack.name}, {pack.stat().st_size / 2**20:.1f} MB. Opened in {open_ms:.0f} ms."]
    lines += s4_bench.report_lines(result, "On the desktop")
    return lines, {"open_ms": open_ms, "result": result}


def run_browser(playwright, browser: str, url: str, fresh: bool) -> dict:
    kind = playwright.firefox if browser == "firefox" else playwright.chromium
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        context = kind.launch_persistent_context(profile, headless=True)
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            first = page.evaluate(f"window.s4.run({'true' if fresh else 'false'})")
            # A second run in the same browser: the pack is already stored and
            # Pyodide's files may be cached, as on a later visit.
            second = page.evaluate("window.s4.run(false)")
            text = page.input_value("#results")
            if errors:
                text += "Errors on the page:\n" + "\n".join(errors) + "\n"
        finally:
            context.close()
    return {"text": text, "first": first, "second": second}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spike S4: the core in the browser.")
    parser.add_argument("--browsers", nargs="+", default=["chromium", "firefox"])
    parser.add_argument("--pack", type=Path, default=None)
    parser.add_argument("--fresh", action="store_true", help="copy the pack into private storage again")
    parser.add_argument("--serve", action="store_true", help="serve the page for your own browser")
    args = parser.parse_args(argv)

    check_pyodide()
    pack = args.pack or default_pack()
    if not pack.is_file():
        raise SystemExit(f"The pack was not found: {pack}")
    places = yaml.safe_load(PLACES.read_text(encoding="utf-8"))["places"]

    if args.serve:
        page, servers = start_servers(pack, places, ports=(8780, 8781))
        url = f"{page.url}/tools/spikes/s4/web/index.html"
        print(f"Spike S4 page: {url}")
        print("Press Ctrl+C in this window to stop.")
        webbrowser.open(url)
        try:
            page.thread.join()
        except KeyboardInterrupt:
            print("Stopped.")
        return 0

    from playwright.sync_api import sync_playwright

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    print("Running on the desktop.")
    lines, data = desktop_run(pack, places)
    disk = download_on_disk()
    lines.append(f"A first visit fetches {sum(s for _, s in disk) / 2**20:.1f} MB for Pyodide, NumPy and Shapely:")
    lines += [f"  {n}: {s / 2**20:.2f} MB" for n, s in disk]
    (RESULTS / f"{stamp}-desktop.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / f"{stamp}-desktop.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print("\n".join(lines))

    page, servers = start_servers(pack, places)
    try:
        with sync_playwright() as playwright:
            for browser in args.browsers:
                print(f"Running in {browser}.")
                out = run_browser(playwright, browser, f"{page.url}/tools/spikes/s4/web/index.html", args.fresh)
                (RESULTS / f"{stamp}-{browser}.txt").write_text(out["text"], encoding="utf-8")
                (RESULTS / f"{stamp}-{browser}.json").write_text(
                    json.dumps({"first": out["first"], "second": out["second"]}, indent=1), encoding="utf-8")
                print(out["text"])
    finally:
        for server in servers:
            server.stop()
    print(f"Results saved in {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
