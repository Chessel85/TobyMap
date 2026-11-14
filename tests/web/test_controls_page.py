"""The status line and the move and zoom buttons in Chromium and Firefox (P3-T18; VIS-1, SCP-2, ACC-2)."""
import pytest

pytest.importorskip("playwright")

from tests.web.test_shell_page import open_app  # noqa: E402

STATE = {"lat": 51.2, "lon": -1.0, "zoom_m": 5000, "step_m": 1000}


def announced(page, key):
    before = page.evaluate("window.tobymap.announcements.length")
    page.keyboard.press(key)
    page.wait_for_function(f"window.tobymap.announcements.length > {before}", timeout=30_000)
    return page.evaluate("window.tobymap.announcements.at(-1).text")


def test_the_line_says_the_same_as_c_and_h_after_a_step(page, site_url):
    app = open_app(page, site_url, state=STATE)
    app.focus("#map")
    app.keyboard.press("ArrowUp")
    c = announced(app, "c")
    h = announced(app, "h")
    assert app.inner_text("#status") == f"{c}. {h}"


def test_a_button_sends_its_command_and_the_focus_stays_on_the_map(page, site_url):
    app = open_app(page, site_url, state=STATE)
    app.focus("#map")
    before = app.inner_text("#status")
    app.click("[id='control-move.north']")
    app.wait_for_function("b => document.getElementById('status').textContent !== b", arg=before, timeout=30_000)
    assert app.evaluate("document.activeElement.id") == "map"


def test_neither_is_reached_by_tab_or_is_a_live_region(page, site_url):
    app = open_app(page, site_url, state=STATE)
    assert app.evaluate("[...document.querySelectorAll('#control-buttons button')].every(b => b.tabIndex === -1)")
    assert app.evaluate("document.querySelectorAll('#controls [aria-live]').length") == 0
    app.focus("#map")
    for _ in range(6):
        app.keyboard.press("Tab")
        assert app.evaluate("!document.activeElement.closest('#controls')")


def test_the_buttons_are_renamed_when_the_orientation_changes(page, site_url):
    app = open_app(page, site_url, state=STATE)
    app.focus("#map")
    assert app.inner_text("[id='control-move.north']") == "North"
    app.keyboard.press("o")
    app.wait_for_function("document.getElementById('control-move.north').textContent === 'Forward'", timeout=30_000)
    assert app.inner_text("[id='control-move.west']") == "Turn left"
