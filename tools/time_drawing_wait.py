"""Does a key's answer ever wait for the map? (P3-T24a, DP202, rule 5 of "Drawing never silences TobyMap")

With every layer shown at every zoom, on the world pack, the map is drawn at each place and zoom
while keys are pressed. For each, it reports:

* the drawing: how long it took in all, its longest single step, and whether its limit left out
  small features;
* the answers: how long C (coordinates) took to be answered while the drawing was being made,
  against the same key with no drawing. The wait is the difference.

The rule is that no answer waits more than 100 milliseconds for a drawing.

    .venv\\Scripts\\python.exe tools\\time_drawing_wait.py desktop [--pack PATH] [--out FILE]
    .venv\\Scripts\\python.exe tools\\time_drawing_wait.py web [--pack PATH] [--browser chromium] [--out FILE]

On the desktop the drawing runs in a thread of its own, as in the application, while the main
thread answers C every 40 milliseconds. In the web version the page presses C every 40
milliseconds after a move, and the times are from the key to the words reaching the screen
reader. The first visit of each browser downloads the pack into its private storage, which takes
a few minutes for the world pack.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

PLACES = [("London", 51.5, -0.1), ("Switzerland", 46.8, 8.2), ("Delhi", 28.6, 77.2), ("the Pacific near Fiji", -17.5, 176.0)]
ZOOMS = [10_000, 50_000, 250_000, 1_000_000, 2_500_000, 10_000_000]
SIZE = (900, 760)
LIMIT_MS = 100.0
PRESS_EVERY_S = 0.04


def every_layer(session) -> None:
    """Every layer on, at every zoom."""
    for layer in session.layers.layers():
        session.layers.change_many(layer.id, {"on": True, "min_zoom_m": 0.0, "max_zoom_m": None})


def every_layer_saved(layer_ids) -> dict:
    return {i: {"on": True, "min_zoom_m": 0.0, "max_zoom_m": None} for i in layer_ids}


def _ms(values) -> str:
    if not values:
        return "none"
    return f"median {statistics.median(values):.0f} ms, slowest {max(values):.0f} ms"


def _line(place, zoom_m, drawing_ms, step_ms, trimmed, quiet, busy) -> tuple[str, float]:
    wait = max(busy) - statistics.median(quiet) if busy and quiet else 0.0
    verdict = "within" if wait <= LIMIT_MS else "OVER"
    text = (f"* {place}, zoom {zoom_m // 1000:,} km: drawing {drawing_ms:,.0f} ms, longest step {step_ms:.0f} ms"
            f"{', small features left out' if trimmed else ''}. C answered: {_ms(busy)} while drawing, "
            f"{_ms(quiet)} with no drawing. Longest wait {wait:.0f} ms, {verdict} the 100 ms.")
    return text, wait


def run_desktop(pack: Path) -> str:
    from mapcore.render.drawing import STEP_S
    from mapcore.session import MapSession

    lines = ["On the desktop, every layer at every zoom, a 900 by 760 map.", ""]
    worst = 0.0
    # One session throughout, as in TobyMap: a new session for each place kept every earlier one's records in
    # memory, as the store keeps them out of Python's clean-up (mapcore/memory.py), and the laptop ran short.
    session = MapSession(packs=[pack], saved_state={"lat": PLACES[0][1], "lon": PLACES[0][2], "zoom_m": ZOOMS[0]})
    session.start()
    every_layer(session)
    for place, lat, lon in PLACES:
        for zoom_m in ZOOMS:
            session.world.lat, session.world.lon = lat, lon
            session.world.zoom_index = min(range(len(session.world.zoom_list)),
                                           key=lambda i: abs(session.world.zoom_list[i] - zoom_m))
            session.areas = session._here()
            session.scene(*SIZE)   # what start-up reads, read once
            quiet = []
            for _ in range(10):
                t = time.perf_counter()
                session.run("where.coordinates")
                quiet.append((time.perf_counter() - t) * 1000)
                time.sleep(PRESS_EVERY_S)
            session.run("move.east")
            drawing = session.start_drawing(*SIZE)
            done = threading.Event()

            def draw():
                while drawing.advance(STEP_S) is None:
                    pass
                done.set()

            thread = threading.Thread(target=draw)
            thread.start()
            busy = []
            while not done.is_set():
                t = time.perf_counter()
                session.run("where.coordinates")
                busy.append((time.perf_counter() - t) * 1000)
                time.sleep(PRESS_EVERY_S)
            thread.join()
            text, wait = _line(place, zoom_m, drawing.age_s() * 1000, drawing.longest_step_s * 1000,
                               drawing.frame["trimmed"], quiet, busy)
            worst = max(worst, wait)
            lines.append(text)
            print(text, flush=True)
    session.store.close()
    lines += ["", f"Longest wait of all: {worst:.0f} ms."]
    return "\n".join(lines)


def run_web(pack: Path, browsers: list[str]) -> str:
    from playwright.sync_api import sync_playwright

    import time_drawing_web
    from mapcore.packs.pack import Pack

    layer_ids = [d["id"] for d in Pack(pack).layers]
    server, url = time_drawing_web.serve(pack)
    lines = []
    try:
        with sync_playwright() as p:
            for name in browsers:
                browser = getattr(p, name).launch()
                context = browser.new_context()
                lines += ["", f"In {name.capitalize()}, every layer at every zoom, a 1200 by 800 page.", ""]
                worst = 0.0
                for place, lat, lon in PLACES:
                    for zoom_m in ZOOMS:
                        text, wait = _web_place(context, url, layer_ids, place, lat, lon, zoom_m)
                        worst = max(worst, wait)
                        lines.append(text)
                        print(f"{name}: {text}", flush=True)
                lines += ["", f"Longest wait of all in {name.capitalize()}: {worst:.0f} ms."]
                browser.close()
    finally:
        server.shutdown()
    return "\n".join(lines).strip()


def _web_place(context, url, layer_ids, place, lat, lon, zoom_m):
    page = context.new_page()
    state = {"settings": {"values": {}, "keys": {}, "layers": every_layer_saved(layer_ids)},
             "state": {"lat": lat, "lon": lon, "zoom_m": zoom_m}}
    page.add_init_script(f"localStorage.setItem('tobymap', {json.dumps(json.dumps(state))});")
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{url}/index.html")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=1_800_000)
    if page.evaluate("window.tobymap.error"):
        raise RuntimeError(page.evaluate("window.tobymap.error"))
    page.wait_for_function("window.tobymap.drawings.length >= 1", timeout=600_000)
    page.locator("#map").focus()
    quiet = _presses(page, 10)
    drawn = page.evaluate("window.tobymap.drawings.length")
    page.keyboard.press("ArrowRight")
    busy = []
    while page.evaluate(f"window.tobymap.drawings.length") <= drawn:
        busy += _presses(page, 1)
    d = page.evaluate("window.tobymap.drawings.at(-1)")
    trimmed = "not drawn" in (page.text_content("#status") or "")
    page.close()
    return _line(place, zoom_m, d["drawMs"], d["stepMs"], trimmed, quiet, busy)


def _presses(page, n: int) -> list[float]:
    """Press C n times, PRESS_EVERY_S apart, and return how long each took to be answered, in ms."""
    out = []
    for _ in range(n):
        before = page.evaluate("window.tobymap.timings.length")
        page.keyboard.press("c")
        page.wait_for_function(f"window.tobymap.timings.length > {before}", timeout=120_000)
        out.append(page.evaluate("window.tobymap.timings.at(-1)"))
        page.wait_for_timeout(PRESS_EVERY_S * 1000)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("where", choices=["desktop", "web"])
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--browser", action="append", choices=["chromium", "firefox"])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    pack = args.pack
    if pack is None:
        from desktop import storage

        found = storage.find_packs()
        if not found:
            print("No pack found. Give one with --pack.")
            return 1
        pack = found[0]
    text = run_desktop(pack) if args.where == "desktop" else run_web(pack, args.browser or ["chromium", "firefox"])
    print()
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
