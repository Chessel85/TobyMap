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
