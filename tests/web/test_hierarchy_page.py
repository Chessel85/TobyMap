"""Hierarchy mode in the browser, in Chromium and Firefox (P3-T6b; NAV-4, ACC-7): M switches it on, Down
offers the kinds then a kind's features, in the location history's list with a Cancel button, and the
ambiguous up from Brockenhurst station plays its sound and offers both areas."""
import json

import pytest

from tests.web.test_shell_page import open_app, region, said, wait_said

pytest.importorskip("playwright")

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}


def lines(app):
    return app.evaluate("[...document.querySelectorAll('#history-list option')].map(o => o.textContent)")


def open_list(app, title):
    app.wait_for_function(f"document.getElementById('dialog').open && "
                          f"document.getElementById('dialog-title').textContent === {json.dumps(title)} && "
                          f"document.activeElement.id === 'history-list'")


def choose(app, starts):
    index = next(i for i, line in enumerate(lines(app)) if line.startswith(starts))
    app.evaluate(f"document.getElementById('history-list').selectedIndex = {index}")
    app.keyboard.press("Enter")


def test_down_then_up_in_hierarchy_mode(page, site_url):
    app = open_app(page, site_url, state=HAMPSHIRE)
    app.keyboard.press("m")
    wait_said(app, 1)
    assert said(app)[-1] == "Hierarchy mode. Hampshire."
    app.keyboard.press("ArrowDown")
    open_list(app, "Inside Hampshire")
    assert app.evaluate("document.getElementById('dialog-close').textContent") == "Cancel"
    choose(app, "Railway stations")
    open_list(app, "Railway stations in Hampshire")   # the kind's features, in the same box
    choose(app, "Brockenhurst")
    app.wait_for_function("!document.getElementById('dialog').open")
    app.wait_for_function("document.activeElement.id === 'map'")
    assert region(app) == "map"
    count = app.evaluate("window.tobymap.earcons.length")
    app.keyboard.press("ArrowUp")
    open_list(app, "Up from Brockenhurst")
    assert "ambiguous_up" in json.dumps(app.evaluate(f"window.tobymap.earcons.slice({count})"))
    assert lines(app) == ["New Forest National Park, national park", "Hampshire, county of England"]
    app.click("#dialog-close")
    app.wait_for_function("!document.getElementById('dialog').open && document.activeElement.id === 'map'")
    # Cancel stays: Brockenhurst is still the current feature, so Up offers the same list again.
    app.keyboard.press("ArrowUp")
    open_list(app, "Up from Brockenhurst")
    assert app.evaluate("document.getElementById('dialog-close').textContent") == "Cancel"
    app.click("#dialog-close")
    app.keyboard.press("Control+Shift+Space")   # the location history's button is Close again
    open_list(app, "Location history")
    assert app.evaluate("document.getElementById('dialog-close').textContent") == "Close"
