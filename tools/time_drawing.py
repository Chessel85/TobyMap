"""Where the time goes when the map is drawn (P2-T14b, DP140).

A held key walk, as when an arrow key is held: from each starting place, at
each of three zooms, the location steps east again and again, and every place
is drawn. Each drawing is timed in three parts:

* choosing: finding the shapes in view and cutting them to it (the core);
* projecting: turning them into screen pixels (the core);
* painting: drawing them with Qt on an image the size of the map (the desktop).

Run on the desktop with a pack, normally the world pack:

    .venv\\Scripts\\python.exe tools\\time_drawing.py [--pack PATH] [--steps 25] [--out FILE]

The browser's figures come from tools/time_drawing_web.py, which runs the same
walk in Pyodide. Both write plain text for docs/plan/p2-t14-drawing-timing.md.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Where to walk: name, latitude, longitude. East from each.
PLACES = [("Europe", 48.0, -2.0), ("the Pacific near Fiji", -17.5, 176.0), ("Antarctica", -78.0, 0.0)]
# Zoom and step, in metres: a close view (exact pack tiles), a country view and a continent view.
ZOOMS = [(25_000, 5_000), (250_000, 100_000), (2_500_000, 1_000_000)]
SIZE = (900, 760)   # the map region of the desktop window at its usual size


def walk(session, steps: int, paint=None) -> list[dict]:
    """Step east `steps` times, drawing each place. Returns the timings of each drawing."""
    out = []
    for _ in range(steps + 1):
        frame = session.scene(*SIZE)
        paint_ms = paint(frame) if paint else None
        start = time.perf_counter()
        session.panel()   # before P2-T14 this was done after every held step, as well as the drawing
        panel_ms = (time.perf_counter() - start) * 1000
        out.append({"choose": frame["choose_ms"], "project": frame["projecting_ms"],
                    "core": frame["project_ms"], "paint": paint_ms, "points": frame["points"], "panel": panel_ms})
        session.run("move.east", held=True)
    return out


def summary(rows: list[dict], key: str) -> str:
    values = sorted(r[key] for r in rows if r[key] is not None)
    if not values:
        return "not measured"
    p95 = values[min(len(values) - 1, round(0.95 * (len(values) - 1)))]
    return f"median {statistics.median(values):.0f} ms, 95th percentile {p95:.0f} ms, slowest {values[-1]:.0f} ms"


def report(results: list[tuple[str, int, list[dict]]], where: str) -> str:
    lines = [f"Timings {where}, {SIZE[0]} by {SIZE[1]} pixels."]
    for place, zoom_m, rows in results:
        points = statistics.median(r["points"] for r in rows)
        lines.append("")
        lines.append(f"{place}, zoom {zoom_m // 1000:,} km, {len(rows)} drawings, about {points:,.0f} points each:")
        for key, label in (("choose", "Choosing the shapes"), ("project", "Projecting them"),
                           ("paint", "Painting them"), ("core", "The core's part in all")):
            lines.append(f"* {label}: {summary(rows, key)}")
        totals = [r["core"] + (r["paint"] or 0) for r in rows]
        lines.append(f"* The whole drawing: {summary([{'t': t} for t in totals], 't')}")
        if rows[0].get("panel") is not None:
            lines.append(f"* Bringing the Information panel up to date: {summary(rows, 'panel')}")
    return "\n".join(lines)


def run_desktop(pack: Path, steps: int) -> str:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from desktop.map_widget import paint_scene
    from mapcore.session import MapSession

    app = QApplication.instance() or QApplication([])

    def paint(frame) -> float:
        image = QImage(SIZE[0], SIZE[1], QImage.Format.Format_ARGB32_Premultiplied)
        start = time.perf_counter()
        painter = QPainter(image)
        paint_scene(painter, frame)
        painter.end()
        return (time.perf_counter() - start) * 1000

    results = []
    for place, lat, lon in PLACES:
        for zoom_m, step_m in ZOOMS:
            session = MapSession(packs=[pack], saved_state={"lat": lat, "lon": lon, "zoom_m": zoom_m, "step_m": step_m})
            session.start()
            results.append((place, zoom_m, walk(session, steps, paint)))
            session.store.close()
    del app
    return report(results, "on the desktop")


# The speed trial (P2-T14c, as for the build speed trials, DP107) ---------------

def _one_by_one(self, box):
    """Each pack tile's shapes decoded one at a time, as before P2-T14c."""
    import numpy as np
    import shapely

    from mapcore.packs import tiles

    geoms = np.empty(len(self.entries), object)
    for i, e in enumerate(self.entries):
        geoms[i] = shapely.box(*box) if e.kind == tiles.COVERED else self.shape(i)
    return geoms, np.asarray([e.feature for e in self.entries], np.int64)


def _warm_ahead(session) -> float:
    """Read and decode the pack tiles the next step east will need, as a background
    thread could while the key is held. Returns the time it took."""
    import copy
    import math

    from mapcore.render import globe, scene as scene_mod

    start = time.perf_counter()
    ahead = copy.copy(session.world)
    ahead.step("east")
    view = scene_mod.view_for(ahead, *SIZE)
    r = globe._radius(view, *SIZE)
    rho = math.asin(min(1.0, math.hypot(SIZE[0] / 2, SIZE[1] / 2) / r))
    session._scene._collect(ahead.lat, ahead.lon, rho, ahead.zoom_m / 1000.0)
    return (time.perf_counter() - start) * 1000


def trial(pack: Path, steps: int) -> str:
    """The core's part of each drawing in a held key walk, four ways."""
    from mapcore.session import MapSession
    from mapcore.store.cache import TileData

    batch = TileData.drawing_shapes
    ways = [("Decoded one by one, as before", _one_by_one, False),
            ("Approach 1: the shapes of each pack tile decoded together", batch, False),
            ("Approach 2: one by one, with the next pack tiles read ahead in the background", _one_by_one, True),
            ("Both together", batch, True)]
    lines = [f"The core's part of each drawing, in ms, over every walk ({len(PLACES) * len(ZOOMS)} walks of "
             f"{steps + 1} drawings), on the desktop."]
    for label, decode, ahead in ways:
        TileData.drawing_shapes = decode
        rows, cold, background = [], [], []
        for _place, lat, lon in PLACES:
            for zoom_m, step_m in ZOOMS:
                session = MapSession(packs=[pack], saved_state={"lat": lat, "lon": lon, "zoom_m": zoom_m,
                                                                "step_m": step_m})
                session.start()
                for i in range(steps + 1):
                    frame = session.scene(*SIZE)
                    (cold if i == 0 else rows).append({"t": frame["project_ms"]})
                    if ahead:
                        background.append({"t": _warm_ahead(session)})
                    session.run("move.east", held=True)
                session.store.close()
        lines.append("")
        lines.append(label + ":")
        lines.append(f"* The first drawing of each walk: {summary(cold, 't')}")
        lines.append(f"* Every drawing after it: {summary(rows, 't')}")
        if background:
            lines.append(f"* Reading ahead, in the background: {summary(background, 't')}")
    TileData.drawing_shapes = batch
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", type=Path, help="the pack file (default: the installed packs' first)")
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--trial", action="store_true", help="compare the ways of choosing the shapes (P2-T14c)")
    parser.add_argument("--one-by-one", action="store_true", help="decode shapes one by one, as before P2-T14c")
    args = parser.parse_args(argv)
    if args.one_by_one:
        from mapcore.store.cache import TileData

        TileData.drawing_shapes = _one_by_one
    pack = args.pack
    if pack is None:
        from desktop import storage

        found = storage.find_packs()
        if not found:
            print("No pack found. Give one with --pack.")
            return 1
        pack = found[0]
    text = trial(pack, args.steps) if args.trial else run_desktop(pack, args.steps)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
