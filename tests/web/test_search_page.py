"""P3-T8b in the browser, in Chromium and Firefox: search in the core, run in the web worker on the test pack. The
search dialog itself comes with P3-T8c; this calls the core through window.tobymap.search."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


def test_search_in_the_worker_finds_sao_paulo_and_ranks_paris(page, site_url):
    app = open_app(page, site_url, state=HAMPSHIRE)
    got = app.evaluate("window.tobymap.search('Sao Paulo')")
    assert [r["name"] for r in got["results"][:2]] == ["São Paulo", "São Paulo"]
    paris = app.evaluate("window.tobymap.search('Pariss')")["results"]
    assert paris[0]["description"] == "Paris, France"
    assert paris[1]["description"] == "Paris, United States"
    near = app.evaluate("window.tobymap.search('Paris', {near_m: 100000})")["results"]
    assert near == []
    assert got["ms"] < 1000


def test_ctrl_f_opens_the_search_dialog_and_enter_goes_there(page, site_url):
    app = open_app(page, site_url, state=HAMPSHIRE)
    page.keyboard.press("Control+f")
    field = page.locator("#search-field")
    field.wait_for(state="visible")
    assert page.evaluate("document.activeElement.id") == "search-field"   # not the browser's own find
    assert page.locator("#search-cancel").inner_text() == "Cancel"
    field.type("Sao Paulo")
    page.locator("#search-list option").first.wait_for(timeout=15000)
    assert "São Paulo" in page.locator("#search-list option").first.inner_text()
    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.id") == "search-list"
    page.keyboard.press("Enter")
    page.locator("#searchdialog").wait_for(state="hidden")
    assert "São Paulo" in page.locator("#map").get_attribute("aria-label")   # the answer is the map's name as focus returns


def test_search_says_when_nothing_is_found_and_cancel_closes(page, site_url):
    open_app(page, site_url, state=HAMPSHIRE)
    page.keyboard.press("Control+f")
    page.locator("#search-field").type("qqzzxx")
    page.locator("#search-message").filter(has_text="Nothing found for qqzzxx.").wait_for(timeout=15000)
    page.locator("#search-cancel").click()
    page.locator("#searchdialog").wait_for(state="hidden")
