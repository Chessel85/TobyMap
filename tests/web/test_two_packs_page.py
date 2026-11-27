"""The web version with two packs (P4-T3d; PLT-4, PCK-2, AD-14), in Chromium and Firefox.

The site lists the regional test pack, test-region, and the test pack (a world pack). The worker downloads both
into the browser's private storage on the first visit and opens both; the second visit reads both from there.
Inside the regional pack's covered pack tiles the map names what only the regional pack holds, outside it says
what the world pack alone says, and a search lists a feature both packs hold once. Each answer is compared with
the core's own, given the same two packs outside the browser, so the web says what the desktop says.
"""
import json

import pytest

from tests.web.test_shell_page import open_app, said

pytest.importorskip("playwright")

WINCHESTER = {"lat": 51.0590, "lon": -1.3074, "zoom_m": 1000, "step_m": 10}   # in a covered pack tile
OUTSIDE = {"lat": 51.2000, "lon": -1.4000, "zoom_m": 5000, "step_m": 100}      # Hampshire, in no covered tile
HAMPSHIRE = "osm:r172799"
WORDS = ("Winchester", "Hampshire", "Lymington", "New Forest")


def _core(packs, state, ask):
    """The core's own answer with these packs, outside the browser. Each session is made just before it is asked,
    as the layers said with their type are kept for the whole process (mapcore.names), set by the newest session."""
    from mapcore.packs.pack import Pack
    from mapcore.session import MapSession

    s = MapSession(platform="web", packs=[Pack(p) for p in packs], saved_state=state)
    try:
        s.start()
        return ask(s)
    finally:
        s.store.close()


@pytest.fixture(scope="module")
def core(test_pack, test_region_pack):
    both, world = [test_pack, test_region_pack], [test_pack]
    return lambda which, state, ask: _core(both if which == "both" else world, state, ask)


def test_both_packs_are_downloaded_then_read_from_storage(page, two_packs_site_url):
    app = open_app(page, two_packs_site_url, state=WINCHESTER)
    texts = app.evaluate("window.tobymap.announcements.map(a => a.text)")
    assert sum(t.startswith("The map is downloaded") for t in texts) == 2, texts
    app.reload()
    app.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert app.evaluate("window.tobymap.error") is None
    texts = app.evaluate("window.tobymap.announcements.map(a => a.text)")
    assert not [t for t in texts if t.startswith(("Downloading the map", "The map is downloaded"))], texts


def test_inside_the_coverage_the_regional_pack_answers(page, two_packs_site_url, core):
    app = open_app(page, two_packs_site_url, state=WINCHESTER)
    label = app.get_attribute("#map", "aria-label")
    assert label == core("both", WINCHESTER, lambda s: s.start_label())
    assert "Winchester" in label and label.count("Hampshire") == 1, label   # the district only the regional holds
    assert not [t for t in said(app) if "detail" in t.lower()]
    app.wait_for_function("window.tobymap.paints > 0", timeout=60_000)


def test_outside_the_coverage_the_world_pack_answers_and_nothing_is_said_of_detail(page, two_packs_site_url, core):
    app = open_app(page, two_packs_site_url, state=OUTSIDE)
    label = app.get_attribute("#map", "aria-label")
    assert label == core("both", OUTSIDE, lambda s: s.start_label()) == core("world", OUTSIDE, lambda s: s.start_label())
    assert "Hampshire" in label
    assert not [t for t in said(app) if "detail" in t.lower()]


def test_a_search_lists_a_feature_both_packs_hold_once(page, two_packs_site_url, core):
    app = open_app(page, two_packs_site_url, state=WINCHESTER)
    for text in WORDS:
        got = app.evaluate(f"window.tobymap.search({json.dumps(text)})")["results"]
        ids = [r["id"] for r in got]
        assert len(ids) == len(set(ids)), text
        expected = core("both", WINCHESTER, lambda s: s.search(text))
        assert [(r["id"], r["label"]) for r in got] == [(r["id"], r["label"]) for r in expected], text
    hampshire = app.evaluate("window.tobymap.search('Hampshire')")["results"]
    assert [r["id"] for r in hampshire].count(HAMPSHIRE) == 1
