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


# The bookmark dialog (P4-T8b; USR-1, DP219, ACC-7). Written, not yet run: a world build was using the memory.

def open_dialog(app):
    app.focus("#map")
    app.keyboard.press("Control+Enter")
    app.wait_for_function("document.getElementById('bookmarkdialog').open "
                          "&& document.activeElement.id === 'bookmark-name'")


def test_ctrl_enter_on_the_map_opens_the_bookmark_dialog_in_tab_order(page, site_url):
    app = open_with(page, site_url, None)
    open_dialog(app)
    assert app.input_value("#bookmark-name")
    assert app.get_attribute("#bookmark-feature", "readonly") is not None
    assert app.get_attribute("#bookmark-coordinates", "readonly") is not None
    order = []
    for _ in range(7):
        order.append(app.evaluate("document.activeElement.id"))
        app.keyboard.press("Tab")
    assert order == ["bookmark-name", "bookmark-feature", "bookmark-coordinates", "bookmark-list",
                     "bookmark-new-list", "bookmark-ok", "bookmark-cancel"]
    app.click("#bookmark-cancel")
    assert stored(app, "tobymap-bookmarks") is None


def test_ok_keeps_a_bookmark_and_a_second_is_numbered(page, site_url):
    app = open_with(page, site_url, None)
    open_dialog(app)
    name = app.input_value("#bookmark-name")
    app.click("#bookmark-ok")
    app.wait_for_function("!document.getElementById('bookmarkdialog').open")
    first = json.loads(stored(app, "tobymap-bookmarks"))
    assert [f["properties"]["name"] for f in first["features"]] == [name]
    open_dialog(app)
    assert app.input_value("#bookmark-name") == f"{name}_1"
    app.click("#bookmark-cancel")


def test_new_list_is_chosen_and_ok_bookmarks_into_it(page, site_url):
    app = open_with(page, site_url, None)
    open_dialog(app)
    app.click("#bookmark-new-list")
    app.fill("#bookmark-new-name", "Castles")
    app.click("#bookmark-new-ok")
    app.wait_for_function("document.activeElement.id === 'bookmark-list'")
    assert app.evaluate("document.getElementById('bookmark-list').selectedIndex") == 1
    app.click("#bookmark-ok")
    app.wait_for_function("!document.getElementById('bookmarkdialog').open")
    file = json.loads(stored(app, "tobymap-bookmarks"))
    assert [l["name"] for l in file["tobymap"]["lists"]] == ["Bookmarks", "Castles"]
    assert file["features"][0]["properties"]["list"] == "Castles"


# A bookmark as the current feature (P4-T8d; USR-1, DP219 point 6, ACC-7). Written, not yet run: a world build was
# using the memory. Delete asks in the message box, and Cancel keeps it; a text box and Details keep Ctrl+C and Delete.

def castles_text():
    from mapcore import bookmarks as bm

    b = bm.Bookmarks()
    b.lists[0].name = "Castles"
    b.add(0, "Alpha", 51.2, 1.3, feature="Kent")
    return b.to_text()


def make_current(app):
    """Shift+8, open the Castles list, down to Alpha, and Enter: Alpha is the current feature."""
    app.keyboard.press("Shift+Digit8")
    app.wait_for_function("document.activeElement.dataset.id === 'group:bookmarks'"
                          " && document.activeElement.getAttribute('aria-expanded') === 'true'")
    app.evaluate("document.querySelector('[data-id=\"heading:bookmarks:0\"]').focus()")
    app.keyboard.press("ArrowRight")
    app.keyboard.press("ArrowDown")
    app.wait_for_function("document.activeElement.dataset.id === 'bookmark:0:0'")
    app.keyboard.press("Enter")
    app.wait_for_function("document.activeElement.dataset.id === 'group:bookmarks'")


def watch_keys(app):
    """A listener after the page's own: whether the page took the last key from the browser."""
    app.evaluate("document.addEventListener('keydown', (e) => { window.lastKeyTaken = e.defaultPrevented; })")


def test_delete_asks_and_cancel_keeps_it(page, site_url):
    text = castles_text()
    app = open_with(page, site_url, text)
    make_current(app)
    app.keyboard.press("Delete")
    app.wait_for_function("document.getElementById('messagebox').open")
    assert app.text_content("#messagebox-text") == "Delete the bookmark Alpha from Castles?"
    assert app.text_content("#messagebox-ok") == "Delete"
    assert app.evaluate("document.activeElement.id") == "messagebox-cancel"   # Cancel first
    app.click("#messagebox-cancel")
    app.wait_for_function("!document.getElementById('messagebox').open")
    assert stored(app, "tobymap-bookmarks") == text


def test_delete_after_asking_writes_the_file(page, site_url):
    app = open_with(page, site_url, castles_text())
    make_current(app)
    app.keyboard.press("Delete")
    app.wait_for_function("document.getElementById('messagebox').open")
    app.click("#messagebox-ok")
    app.wait_for_function("!document.getElementById('messagebox').open")
    app.wait_for_function("!localStorage.getItem('tobymap-bookmarks').includes('Alpha')")


def test_ctrl_c_in_the_search_box_and_in_details_is_left_to_the_browser(page, site_url):
    app = open_with(page, site_url, castles_text())
    make_current(app)
    watch_keys(app)
    app.keyboard.press("Control+f")
    app.wait_for_function("document.activeElement.id === 'search-field'")
    app.keyboard.type("Kent")
    app.keyboard.press("Control+a")
    app.keyboard.press("Control+c")
    assert app.evaluate("window.lastKeyTaken") is False
    app.keyboard.press("Delete")   # Delete edits the text, and asks nothing
    assert app.evaluate("window.lastKeyTaken") is False
    assert app.input_value("#search-field") == ""
    assert not app.evaluate("document.getElementById('messagebox').open")
    app.click("#search-cancel")
    app.wait_for_function("!document.getElementById('searchdialog').open")
    app.focus("#details")
    app.keyboard.press("Control+c")
    assert app.evaluate("window.lastKeyTaken") is False
    app.focus("#map")
    app.keyboard.press("Control+c")
    assert app.evaluate("window.lastKeyTaken") is True   # on the map, Ctrl+C copies the bookmark
