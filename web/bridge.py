"""The web bridge: the only Python the web shell has (architecture 4.3).

It runs in Pyodide inside the worker, holds one MapSession, and returns plain
JavaScript objects, never Python objects. It contains no map logic: it only
converts. Numeric arrays are returned as bytes with their type, so the worker
can turn them into typed arrays and pass them to the page without copying.

The packs are read through JavaScript handles the worker gives it: the
browser's private storage (a synchronous access handle), or bytes in memory
where that is not available.

tools/stage_web.py copies this file to web/py/tobymap_bridge.py.
"""
from __future__ import annotations

import json

from js import Object, Uint8Array
from pyodide.ffi import to_js

from mapcore.describe import say
from mapcore.session import MapSession

_session: MapSession | None = None
_slow_ms = 0.0   # a stand-in for a slow drawing, for the held key test only (?slowdraw= in the address)
_ARRAYS = {"coords": "f32", "rings": "i32", "shapes": "i32", "shape_style": "i32", "seam": "u8",
           "line_coords": "f32", "line_runs": "i32", "line_style": "i32", "marker_coords": "f32", "marker_style": "i32"}


class HandleSource:
    """A pack's bytes from a JavaScript object with getSize() and read(buffer, {at})."""

    def __init__(self, handle, name: str):
        self.handle = handle
        self.name = name
        self.size = int(handle.getSize())

    def read(self, offset: int, length: int) -> bytes:
        buffer = Uint8Array.new(length)
        got = int(self.handle.read(buffer, to_js({"at": offset}, dict_converter=Object.fromEntries)))
        return bytes(buffer.to_py())[:got]

    def close(self) -> None:
        pass


def _js(value):
    return to_js(value, dict_converter=Object.fromEntries)


def _scene(width: int, height: int) -> dict:
    if _slow_ms:
        import time

        until = time.perf_counter() + _slow_ms / 1000
        while time.perf_counter() < until:
            pass
    scene = _session.scene(width, height)
    for key, kind in _ARRAYS.items():
        scene[key] = {"type": kind, "bytes": scene[key].tobytes()}
    return scene


def progress_text(percent: int) -> str:
    return say("packs.downloading", percent=str(percent))


def words_text(key: str) -> str:
    """A template from the core by its dotted name, for the few messages the worker itself triggers."""
    return say(key)


def _extras(response, out: dict, width: int, height: int) -> dict:
    out["response"] = response.to_dict()
    out["describing"] = _session.describing
    out["earcons"] = [_session.earcon_file(e) for e in response.earcons]
    if response.panel_stale:
        out["panel"] = _session.panel()
        out["map_label"] = _session.map_label()
    if response.details_stale:
        out["details"] = _session.details()
    if response.redraw:
        out["scene"] = _scene(width, height)
    if response.settings_changed:
        out["registry"] = _session.registry()
    out["hold"] = _session.hold_info()   # the held key's timing, for the page's clicks (DP140)
    out["toggles"] = _session.toggles()   # the ticks of the menu items
    out["save"] = json.dumps(_session.save())
    return out


def start(width: int, height: int, startup_ms: float, packs, saved_json: str, start_at: str = "",
          slow_ms: float = 0.0):
    global _session, _slow_ms
    _slow_ms = float(slow_ms or 0)
    saved = json.loads(saved_json) if saved_json else {}
    sources = [HandleSource(p.handle, str(p.name)) for p in packs]
    _session = MapSession(platform="web", packs=[_pack(s) for s in sources],
                          settings=saved.get("settings"), saved_state=saved.get("state"), start_at=start_at or None)
    _session.startup_took(startup_ms)
    response = _session.start()
    out = {"registry": _session.registry(), "words": _session.words()}
    out["map_label"] = _session.map_label()
    out["start_label"] = _session.start_label()   # the map's name as the focus first arrives (P2-T17d)
    out["details"] = _session.details()
    out["panel"] = _session.panel()
    out["scene"] = _scene(width, height)
    return _js(_extras_start(response, out))


def _pack(source):
    from mapcore.packs.pack import Pack

    return Pack(source)


def _extras_start(response, out: dict) -> dict:
    out["response"] = response.to_dict()
    out["describing"] = False
    out["earcons"] = []
    from mapcore.describe import earcon_list

    out["preload"] = [_session.earcon_file(e["event"]) for e in earcon_list()]   # every earcon, ready (P2-T8)
    out["toggles"] = _session.toggles()
    out["save"] = json.dumps(_session.save())
    return out


def run(commands_json: str, width: int, height: int):
    """commands_json is a list of [name, args]. More than one means keys came
    faster than the worker could answer; the core carries them all out and
    speaks only the last (ANN-3)."""
    commands = [(name, args) for name, args in json.loads(commands_json)]
    response = _session.run_many(commands)
    return _js(_extras(response, {}, width, height))


def press(key: str, region: str, width: int, height: int):
    """A key while the key describer is on: described, never carried out."""
    response = _session.press(key, region)
    return _js(_extras(response, {}, width, height)) if response is not None else None


def release(width: int, height: int):
    """The held movement key was let go: only the final place is spoken (ANN-3)."""
    return _js(_extras(_session.release(), {}, width, height))


def crossed(width: int, height: int):
    """The Crossed and passed search (P2-T5), which the page asks for when nothing else is
    waiting, so it never delays a key press. A newer move has already made an old one empty."""
    return _js(_extras(_session.crossed_now(), {}, width, height))


def panel_open(open_json: str):
    """The groups the page has open in the Information panel (P3-T4a): the core fills those, and keeps
    the list for the panels it makes after each command, so a group not open is never filled by a step."""
    return _js({"panel": _session.panel(open=json.loads(open_json))})


def hold():
    """The held key's timing, when the press's own answer was joined to a later one."""
    return _js({"hold": _session.hold_info()})


def scene(width: int, height: int):
    return _js({"scene": _scene(width, height)})


def settings_schema():
    return _js(_session.settings_schema())


def key_text(key: str) -> str:
    """A key as it is said and shown, such as "Ctrl+Comma", for the key dialog."""
    from mapcore.commands.registry import key_text as text

    return text(key)


def voice_problem(problem: str, width: int, height: int):
    """The page's spatial voice is "loading", "missing" or "failed" (P2-T7b)."""
    return _js(_extras(_session.voice_problem(problem), {}, width, height))


def scan_item(index: int, width: int, height: int):
    """Look around (P3-T11a): the page has started playing item index of the scan, or -1 at its end."""
    index = int(index)
    return _js(_extras(_session.scan_item(index if index >= 0 else None), {}, width, height))


def stretch(samples, rate: int, factor: float, pitch: float):
    """A spatial voice label made factor times as fast, and at pitch times the pitch without
    slowing, by the core (P2-T16g, SON-3): float32 samples in, as bytes, and out, as bytes
    with their type."""
    import numpy as np

    from mapcore.sound.stretch import shape_voice

    mono = np.frombuffer(bytes(samples.to_py()), dtype=np.float32)
    return _js({"type": "f32", "bytes": shape_voice(mono, int(rate), float(factor), float(pitch)).tobytes()})


def earcon_failed(event: str, width: int, height: int):
    return _js(_extras(_session.earcon_failed(event), {}, width, height))


def frame_painted(paint_ms: float) -> None:
    _session.frame_painted(paint_ms)


def shell_times(key_ms: float, handed_ms: float) -> None:
    """The page reports when the key was pressed and when the text was handed to the screen reader (P1-T15)."""
    from mapcore import diagnostics
    import time

    now = time.time()
    diagnostics.add_shell(_session, key_pressed_at=now - key_ms / 1000 if key_ms is not None else None,
                          handed_over_at=now - handed_ms / 1000 if handed_ms is not None else None)


def search(text: str, scope_json: str = "{}"):
    """A search in the core (P3-T8b, SRB-1): the results as MapSession.search gives them, and how long the
    search took in Pyodide, in milliseconds. scope_json may give layers, near_m and inside (SRB-2). For the
    search dialog (P3-T8c), the browser tests and the timing of search on the web."""
    import json
    import time

    scope = json.loads(scope_json or "{}")
    t = time.perf_counter()
    results = _session.search(text, layers=scope.get("layers"), near_m=scope.get("near_m"),
                              inside=scope.get("inside"))
    return _js({"results": results, "ms": (time.perf_counter() - t) * 1000})


def pack_selfcheck():
    """The pack format's self-check in Pyodide (P1-T2): a list of problems, empty when all is well."""
    from mapcore.packs import selfcheck

    return _js(selfcheck.run())


def store_selfcheck():
    """The store's self-check in Pyodide (P1-T5): a list of problems, empty when all is well."""
    from mapcore.store import selfcheck

    return _js(selfcheck.run())
