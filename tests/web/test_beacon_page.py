"""The orientation beacon in the web version (P2-T9; SON-10, SON-2), in Chromium and Firefox.

B starts it at once, the page repeats it on its own timer from where the core last placed it,
with the core's pan and pitch, a turn moves it, and B or the North Pole stops it.
"""
import pytest

from tests.web.test_shell_page import open_app, said

pytest.importorskip("playwright")

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def beacons(app):
    return app.evaluate("window.tobymap.placed.filter((p) => p.sound === 'beacon')")


def test_b_starts_it_it_repeats_and_a_turn_moves_it(page, site_url):
    app = open_app(page, site_url, state=KENT, values={"beacon_interval_s": 0.5})
    app.keyboard.press("b")
    app.wait_for_function("window.tobymap.placed.filter((p) => p.sound === 'beacon').length >= 3", timeout=5000)
    assert "Beacon on." in said(app)
    first = beacons(app)[0]
    assert first["pan"] == 0 and first["pitch"] == 1          # north-fixed: straight ahead
    app.keyboard.press("o")                                   # cardinal facing, north
    app.keyboard.press("Shift+ArrowRight")                    # facing east: the beacon to the left
    app.keyboard.press("Shift+ArrowRight")                    # facing south: behind, lower
    app.wait_for_function("(() => { const b = window.tobymap.placed.filter((p) => p.sound === 'beacon');"
                          " return b[b.length - 1].pitch < 1; })()", timeout=5000)
    assert beacons(app)[-1]["pitch"] == pytest.approx(0.84, abs=0.001)
    app.keyboard.press("b")
    app.wait_for_function("window.tobymap.announcements.some((a) => a.text === 'Beacon off.')")
    count = len(beacons(app))
    app.wait_for_timeout(1200)
    assert len(beacons(app)) == count


def test_silent_near_the_north_pole_and_told(page, site_url):
    app = open_app(page, site_url, state={"lat": 89.55, "lon": 0.0, "zoom_m": 25000, "step_m": 25000},
                   values={"beacon_interval_s": 0.5})
    app.keyboard.press("b")
    app.wait_for_function("window.tobymap.announcements.some((a) => a.text.startsWith('Beacon on'))")
    assert "Beacon on, but silent near the North Pole." in said(app)
    app.wait_for_timeout(1200)
    assert beacons(app) == []
