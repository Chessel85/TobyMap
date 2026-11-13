"""P3-T5b in the browser, in Chromium and Firefox: W in Details asks for the article, to open in a new tab.
The page records the address and opens nothing (window.tobymap.noOpen)."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

FRANCE = {"lat": 47.0, "lon": 2.0, "zoom_m": 100000, "step_m": 1000}


def test_w_in_details_asks_for_the_article(page, site_url):
    app = open_app(page, site_url, state=FRANCE)
    app.evaluate("window.tobymap.noOpen = true")
    app.keyboard.press("F4")
    app.wait_for_function("document.activeElement.id === 'details'")
    app.keyboard.press("w")
    app.wait_for_function("(window.tobymap.opened || []).length === 1")
    assert app.evaluate("window.tobymap.opened[0]") == "https://en.wikipedia.org/wiki/Metropolitan_France"


def test_w_on_the_map_asks_for_nothing(page, site_url):
    app = open_app(page, site_url, state=FRANCE)
    app.evaluate("window.tobymap.noOpen = true")
    app.keyboard.press("w")
    assert app.evaluate("(window.tobymap.opened || []).length") == 0
