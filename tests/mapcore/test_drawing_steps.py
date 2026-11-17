"""The drawing never holds up what is said (P3-T24a, DP202, VIS-1, NFR-1).

The map is drawn in steps, which the shells run between keys; a drawing has a limit on its
features, and a slow one says "Still drawing the map" once. The timings on the world pack, in
both versions, are in tools/time_drawing_wait.py: the test pack is too small to be slow.
"""
import numpy as np
import pytest

from mapcore.render import drawing as drawing_mod
from mapcore.render import scene as scene_mod
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 250000, "step_m": 25000}


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT), settings={"map_names": True})
    s.start()
    yield s
    s.store.close()


def _same(a: dict, b: dict) -> None:
    for key in ("coords", "seam", "rings", "shapes", "shape_style", "line_coords", "line_runs", "line_style",
                "marker_coords", "marker_style"):
        assert np.array_equal(np.asarray(a[key]), np.asarray(b[key])), key
    for key in ("shape_area", "current", "highlight", "line_area", "marker_area", "names", "points"):
        assert a[key] == b[key], key


def test_a_drawing_made_in_many_small_steps_is_the_same_as_one_made_at_once(session, monkeypatch):
    for zoom in (25000, 250000, 2500000):
        session.world.zoom_index = session.world.zoom_list.index(zoom)
        whole = session.scene(800, 600)
        session._scene = None   # the shapes decoded afresh, in chunks
        session.store.cache.clear()
        monkeypatch.setattr(scene_mod, "CLIP_CHUNK", 3)
        monkeypatch.setattr(scene_mod, "LINE_CHUNK", 2)
        monkeypatch.setattr(scene_mod, "FRAME_CHUNK_POINTS", 50)
        monkeypatch.setattr(scene_mod, "DECODE_CHUNK_BYTES", 40)
        monkeypatch.setattr(scene_mod, "NAMES_PER_STEP", 2)
        d = session.start_drawing(800, 600)
        steps = 0
        while d.advance(0.0) is None:   # one step at a time
            steps += 1
        assert steps > 10
        _same(whole, d.frame)
        monkeypatch.undo()


def test_a_drawing_gives_way_after_its_budget(session):
    clock = iter(range(0, 10_000))   # each reading of the clock is a second later
    d = drawing_mod.Drawing(session._drawing_steps(800, 600), 800, 600, clock=lambda: next(clock))
    assert d.advance(0.5) is None   # one step, then the budget is gone
    assert not d.done
    assert d.finish() is d.frame and d.done


def test_a_drawing_says_still_drawing_once_after_two_seconds():
    now = [0.0]

    def steps():
        for _ in range(100):
            now[0] += 0.5
            yield
        return {"done": True}

    d = drawing_mod.Drawing(steps(), 10, 10, clock=lambda: now[0])
    seen = []
    while d.advance(0.0) is None:
        seen.append(d.still_due())
    assert seen.count(True) == 1
    assert seen.index(True) == 3   # 2 seconds in: four steps of half a second
    assert not d.still_due()


def test_a_newer_drawing_replaces_a_young_one_but_not_one_half_a_second_old():
    now = [0.0]
    d = drawing_mod.Drawing(iter(()), 10, 10, clock=lambda: now[0])
    assert not d.keep_over_newer()
    now[0] = drawing_mod.KEEP_AFTER_S
    assert d.keep_over_newer()


def test_still_drawing_is_said_politely_in_the_cores_words(session):
    r = session.still_drawing()
    assert spoken(r) == ["Still drawing the map"]
    assert r.announcements[0]["priority"] == "polite"


def test_the_limit_draws_the_largest_and_the_status_line_says_some_are_left_out(session, monkeypatch):
    import mapcore.session as session_mod

    full = session.scene(800, 600)
    assert not full["trimmed"]
    assert "not drawn" not in session.controls()["status"]
    drawn = set(full["shape_area"]) | set(full["line_area"]) | set(full["marker_area"])
    monkeypatch.setattr(session_mod, "DRAW_LIMIT", 3)
    small = session.scene(800, 600)
    assert small["trimmed"]
    kept = set(small["shape_area"]) | set(small["line_area"]) | set(small["marker_area"])
    assert kept and len(kept) <= 3 < len(drawn)
    assert kept <= drawn
    # The largest are kept: the places, which have no size, go first.
    assert not small["marker_area"]
    assert session.controls()["status"].endswith("Some small areas are not drawn at this zoom.")
    monkeypatch.undo()
    session.scene(800, 600)
    assert "not drawn" not in session.controls()["status"]


def test_isolating_a_feature_is_never_limited(session, monkeypatch):
    import mapcore.session as session_mod

    session.run("isolate.toggle")
    monkeypatch.setattr(session_mod, "DRAW_LIMIT", 0)
    frame = session.scene(800, 600)
    assert not frame["trimmed"] and frame["shape_area"]
