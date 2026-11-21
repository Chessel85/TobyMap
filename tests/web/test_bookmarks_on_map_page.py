"""Bookmarks on the web version's map (P4-T8f; DP219 point 5, SCP-6): each bookmark painted as a diamond where the
core put it, with its name, and none once the Bookmarks layer is switched off."""
import json

import pytest

pytest.importorskip("playwright")

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def bookmarks_text():
    from mapcore import bookmarks as bm

    b = bm.Bookmarks()
    b.add(0, "Wantsum", 51.2, 1.3)
    return b.to_text()


def open_with(page, site_url, layers=None):
    settings = json.dumps({"settings": {"values": {}, "keys": {}, "layers": layers or {}}, "state": KENT})
    script = (f"localStorage.setItem('tobymap', {json.dumps(settings)});"
              f"localStorage.setItem('tobymap-bookmarks', {json.dumps(bookmarks_text())});")
    page.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ {script} sessionStorage.setItem('seeded', '1'); }}")
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{site_url}/index.html")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert page.evaluate("window.tobymap.error") is None
    page.wait_for_function("window.tobymap.paints >= 1", timeout=60_000)
    return page


def test_a_bookmark_is_painted_in_its_own_colour_with_its_name(page, site_url):
    from mapcore.render import themes

    app = open_with(page, site_url)
    marks = app.evaluate("window.tobymap.bookmarkMarks")
    assert [m["text"] for m in marks] == ["Wantsum"]
    m = marks[0]
    colour = app.evaluate("""([x, y]) => {
        const c = document.getElementById('canvas');
        const dpr = window.devicePixelRatio || 1;
        const d = c.getContext('2d').getImageData(Math.round(x * dpr), Math.round(y * dpr), 1, 1).data;
        return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
    }""", [m["x"], m["y"]])
    assert colour == themes.theme("standard")["bookmark"]


def test_with_the_layer_off_no_bookmark_is_painted(page, site_url):
    app = open_with(page, site_url, layers={"bookmarks": {"on": False}})
    assert app.evaluate("window.tobymap.bookmarkMarks") == []
