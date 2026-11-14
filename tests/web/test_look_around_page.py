"""Look around in Chromium and Firefox (P3-T11a; SON-4, SON-3, INF-10).

L plays the Nearby group one item after another; any key stops it; Enter on the map while an item
plays goes to it. Works with or without the web voice: without it, each item is its sound alone.
"""
import pytest

pytest.importorskip("playwright")

from tests.web.test_shell_page import open_app  # noqa: E402

STATION_WEST = {"lat": 50.9074977, "lon": -1.4142289 - 0.03, "zoom_m": 5000, "step_m": 1000}
NOTHING = "Nothing to go to. Press Enter while look around plays an item to go to it."


def nearby_count(page):
    return page.evaluate("""() => document.querySelectorAll('[data-id="group:nearby"] [role=group] > [role=treeitem]').length""")


def look(page):
    page.focus("#map")
    before = page.evaluate("window.tobymap.scanStarted.length")
    page.keyboard.press("l")
    page.wait_for_function(f"window.tobymap.scanStarted.length > {before}", timeout=30_000)
    return before


def texts(page):
    return page.evaluate("window.tobymap.announcements.map(a => a.text)")


def test_l_plays_every_nearby_item_one_after_another_then_enter_goes_nowhere(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST)
    count = nearby_count(app)
    assert count >= 3
    placed = app.evaluate("window.tobymap.placed.length")
    before = look(app)
    app.wait_for_function("!window.tobymap.scanPlaying()", timeout=90_000)
    assert app.evaluate("window.tobymap.scanStarted.length") - before == count
    sounds = app.evaluate(f"window.tobymap.placed.slice({placed}).map(p => p.sound)")
    assert sum(s not in ("voice", "beacon") for s in sounds) >= count, "each item's own sound"
    app.keyboard.press("Enter")
    app.wait_for_function("t => window.tobymap.announcements.some(a => a.text === t)", arg=NOTHING)


def test_a_key_stops_the_scan(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST)
    before = look(app)
    app.keyboard.press("ArrowDown")
    app.wait_for_function("!window.tobymap.scanPlaying()", timeout=10_000)
    started = app.evaluate("window.tobymap.scanStarted.length")
    app.wait_for_timeout(3000)
    assert app.evaluate("window.tobymap.scanStarted.length") == started
    assert started - before <= 2, "stopped at the key, not at the end"


def test_enter_while_an_item_plays_goes_to_it(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST)
    look(app)
    said = len(texts(app))
    app.keyboard.press("Enter")
    app.wait_for_function(f"window.tobymap.announcements.length > {said}", timeout=10_000)
    app.wait_for_function("!window.tobymap.scanPlaying()", timeout=10_000)
    assert NOTHING not in texts(app)[said:], "the core knew the item playing, and went there"
