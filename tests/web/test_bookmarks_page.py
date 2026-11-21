"""The bookmarks file in the web version (P4-T8a; USR-1, USR-5, DP209, DP219, architecture 6.11): in the
browser's private storage under a key of its own, read at start, set aside when damaged, and left alone
by Reset all settings."""
import json

import pytest

pytest.importorskip("playwright")

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}
SETTINGS = json.dumps({"settings": {"values": {}, "keys": {}}, "state": KENT})
DAMAGED = '{"type": "FeatureCollection", "feat'


def bookmarks_text():
    from mapcore import bookmarks as bm

    b = bm.Bookmarks()
    b.add(0, "Rome", 41.9, 12.5, feature="Rome", note="Visited 2019")
    b.add(b.new_list("Castles"), "Bodiam", 51.0023, 0.5436, feature="Bodiam Castle")
    return b.to_text()


def open_with(page, site_url, bookmarks):
    script = f"localStorage.setItem('tobymap', {json.dumps(SETTINGS)});"
    if bookmarks is not None:
        script += f"localStorage.setItem('tobymap-bookmarks', {json.dumps(bookmarks)});"
    page.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ {script} sessionStorage.setItem('seeded', '1'); }}")
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{site_url}/index.html")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert page.evaluate("window.tobymap.error") is None
    return page


def stored(page, key):
    return page.evaluate(f"localStorage.getItem({json.dumps(key)})")


def test_the_bookmarks_are_read_at_start_and_not_written_again(page, site_url):
    text = bookmarks_text()
    app = open_with(page, site_url, text)
    assert stored(app, "tobymap-bookmarks") == text
    assert stored(app, "tobymap-bookmarks-damaged") is None
    assert "could not be read" not in app.get_attribute("#map", "aria-label")


def test_with_no_bookmarks_nothing_is_written(page, site_url):
    app = open_with(page, site_url, None)
    assert stored(app, "tobymap-bookmarks") is None


def test_a_damaged_bookmarks_file_is_kept_aside_and_said(page, site_url):
    from mapcore.describe import say

    app = open_with(page, site_url, DAMAGED)
    assert stored(app, "tobymap-bookmarks-damaged") == DAMAGED
    assert stored(app, "tobymap-bookmarks") is None
    assert app.get_attribute("#map", "aria-label").endswith(say("bookmarks.damaged"))


def test_reset_all_settings_leaves_the_bookmarks(page, site_url):
    text = bookmarks_text()
    app = open_with(page, site_url, text)
    app.keyboard.press("Shift+A")   # a setting changed, so the reset has something to put back
    app.keyboard.press("Control+Alt+M")   # to the menu bar, as in test_shell_page.go_to_menu_bar
    app.wait_for_function("document.getElementById('menubar').contains(document.activeElement)")
    app.keyboard.press("Enter")
    app.locator(".menu:not([hidden]) [role=menuitem]", has_text="Reset all settings").click()
    app.wait_for_function("document.getElementById('messagebox').open")
    app.focus("#messagebox-ok")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('messagebox').open")
    app.wait_for_function("document.getElementById('map').getAttribute('aria-label').startsWith('All settings are reset')")
    assert stored(app, "tobymap-bookmarks") == text
