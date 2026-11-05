"""Where the time goes when the web version draws the map (P2-T14b, DP140).

The same walk as tools/time_drawing.py, in the web version itself, in Chromium
and Firefox: the core in Pyodide works out each drawing and the page paints it
on its canvas. The times come from the trace, through Help, Copy diagnostics.

    .venv\\Scripts\\python.exe tools\\time_drawing_web.py [--pack PATH] [--steps 25] [--out FILE]

The pack is served from where it is. On the first visit each browser downloads
it into its private storage, which takes a minute or two for the world pack.
Needs Pyodide in web/vendor and the Playwright browsers.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import serve_web  # noqa: E402
import stage_web  # noqa: E402
import time_drawing  # noqa: E402

DRAW = re.compile(r"\sdraw\s.*choosing ([\d.]+) ms, projecting ([\d.]+) ms, painting ([\d.]+) ms, (\d+) points")


ONE_BY_ONE = """

# Added by tools/time_drawing_web.py --one-by-one: decode as before P2-T14c.
def _one_by_one(self, box):
    import numpy as np
    import shapely

    geoms = np.empty(len(self.entries), object)
    for i, e in enumerate(self.entries):
        geoms[i] = shapely.box(*box) if e.kind == tiles.COVERED else self.shape(i)
    return geoms, np.asarray([e.feature for e in self.entries], np.int64)


TileData.drawing_shapes = _one_by_one
"""


def serve(pack: Path, one_by_one: bool = False):
    stage_web.stage()
    if one_by_one:   # only the staged copy is changed; the next staging puts it back
        cache = serve_web.WEB / "py" / "mapcore" / "store" / "cache.py"
        cache.write_text(cache.read_text(encoding="utf-8") + ONE_BY_ONE, encoding="utf-8")
    serve_web.Handler.pack = pack.resolve()
    handler = functools.partial(serve_web.Handler, directory=str(serve_web.WEB))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def walk(context, url: str, lat: float, lon: float, zoom_m: int, step_m: int, steps: int) -> list[dict]:
    page = context.new_page()
    state = {"settings": {"values": {}, "keys": {}},
             "state": {"lat": lat, "lon": lon, "zoom_m": zoom_m, "step_m": step_m}}
    page.add_init_script(f"localStorage.setItem('tobymap', {json.dumps(json.dumps(state))});")
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{url}/index.html")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=900_000)
    if page.evaluate("window.tobymap.error"):
        raise RuntimeError(page.evaluate("window.tobymap.error"))
    for _ in range(steps):
        before = page.evaluate("window.tobymap.paints")
        page.keyboard.press("ArrowRight")
        page.wait_for_function(f"window.tobymap.paints > {before}", timeout=60_000)
    page.wait_for_timeout(300)   # the last "painted" message reaches the worker
    page.get_by_role("menuitem", name="Help").click()
    page.get_by_role("menuitem", name="Copy diagnostics").click()
    page.wait_for_function("document.getElementById('dialog').open && document.getElementById('dialog-text').value")
    text = page.input_value("#dialog-text")
    page.close()
    rows = []
    for m in DRAW.finditer(text):
        choose, project, paint, points = float(m[1]), float(m[2]), float(m[3]), int(m[4])
        rows.append({"choose": choose, "project": project, "paint": paint, "core": choose + project, "points": points})
    return rows   # a fresh page each walk, so every drawing in the trace is this walk's, the first included


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--browser", action="append", choices=["chromium", "firefox"])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--one-by-one", action="store_true", help="decode shapes one by one, as before P2-T14c")
    args = parser.parse_args(argv)
    pack = args.pack
    if pack is None:
        from desktop import storage

        found = storage.find_packs()
        if not found:
            print("No pack found. Give one with --pack.")
            return 1
        pack = found[0]
    from playwright.sync_api import sync_playwright

    server, url = serve(pack, args.one_by_one)
    texts = []
    try:
        with sync_playwright() as p:
            for name in args.browser or ["chromium", "firefox"]:
                browser = getattr(p, name).launch()
                context = browser.new_context()
                results = []
                for place, lat, lon in time_drawing.PLACES:
                    for zoom_m, step_m in time_drawing.ZOOMS:
                        results.append((place, zoom_m, walk(context, url, lat, lon, zoom_m, step_m, args.steps)))
                        print(f"{name}: {place}, {zoom_m // 1000} km done", flush=True)
                browser.close()
                texts.append(time_drawing.report(results, f"in {name.capitalize()}").replace(
                    f"{time_drawing.SIZE[0]} by {time_drawing.SIZE[1]} pixels", "a 1200 by 800 page"))
    finally:
        server.shutdown()
    text = "\n\n".join(texts)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
