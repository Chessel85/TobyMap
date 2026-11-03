"""The web bridge: the only Python the web shell has (architecture 4.3).

It runs in Pyodide inside the worker, holds one MapSession, and returns plain
JavaScript objects, never Python objects. It contains no map logic: it only
converts. Numeric arrays are returned as bytes with their type, so the worker
can turn them into typed arrays and pass them to the page without copying.

tools/stage_web.py copies this file to web/py/tobymap_bridge.py.
"""
from __future__ import annotations

import json

from js import Object
from pyodide.ffi import to_js

from mapcore.session import MapSession

_session: MapSession | None = None
_ARRAYS = {"coords": "f32", "rings": "i32", "shapes": "i32", "shape_style": "i32", "seam": "u8"}


def _js(value):
    return to_js(value, dict_converter=Object.fromEntries)


def _scene(width: int, height: int) -> dict:
    scene = _session.scene(width, height)
    for key, kind in _ARRAYS.items():
        scene[key] = {"type": kind, "bytes": scene[key].tobytes()}
    return scene


def start(width: int, height: int, startup_ms: float):
    global _session
    _session = MapSession(platform="web")
    _session.startup_took(startup_ms)
    response = _session.start()
    return _js({
        "registry": _session.registry(),
        "words": _session.words(),
        "response": response.to_dict(),
        "panel": _session.panel(),
        "details": _session.details(),
        "map_label": _session.map_label(),
        "scene": _scene(width, height),
    })


def run(commands_json: str, width: int, height: int):
    """commands_json is a list of [name, args]. More than one means keys came
    faster than the worker could answer; the core carries them all out and
    speaks only the last (ANN-3)."""
    commands = [(name, args) for name, args in json.loads(commands_json)]
    response = _session.run_many(commands)
    out = {"response": response.to_dict()}
    if response.panel_stale:
        out["panel"] = _session.panel()
        out["map_label"] = _session.map_label()
    if response.details_stale:
        out["details"] = _session.details()
    if response.redraw:
        out["scene"] = _scene(width, height)
    return _js(out)


def scene(width: int, height: int):
    return _js({"scene": _scene(width, height)})


def frame_painted(paint_ms: float) -> None:
    _session.frame_painted(paint_ms)


def pack_selfcheck():
    """The pack format's self-check in Pyodide (P1-T2): a list of problems, empty when all is well."""
    from mapcore.packs import selfcheck

    return _js(selfcheck.run())
