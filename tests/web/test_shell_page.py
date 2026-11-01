"""The spike S5 web shell in Chromium and Firefox (P0-T8, UX section 2, ACC-1, ACC-7, AD-9)."""
import pytest

pytest.importorskip("playwright")

START = "TobyMap globe. United Kingdom. Press F1 for keys."


@pytest.fixture
def app(page, site_url):
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{site_url}/index.html")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert page.evaluate("window.tobymap.error") is None
    return page


def said(page):
    return page.evaluate("window.tobymap.announcements.map(a => a.text)")


def region(page):
    return page.evaluate("""() => {
        const a = document.activeElement;
        if (document.getElementById('map').contains(a)) return 'map';
        if (document.getElementById('tree').contains(a)) return 'panel';
        if (a.id === 'details') return 'details';
        if (document.getElementById('menubar').contains(a)) return 'menu';
        return a.tagName;
    }""")


def test_start_is_announced_and_the_map_has_focus(app):
    assert said(app) == [START]
    assert region(app) == "map"
    assert app.title() == "TobyMap"
    assert app.get_attribute("#map", "role") == "application"
    assert app.get_attribute("#map", "aria-label") == "United Kingdom"  # the place, as the PO asked
    assert app.get_attribute("#tree", "aria-label") == "Information panel"
    assert app.get_attribute("#details", "aria-label") == "Details"
    assert app.locator("#loading").count() == 0


def test_the_globe_is_painted(app):
    assert app.evaluate("window.tobymap.paints") >= 1
    # A pixel on the ocean part of the globe is not the dark background.
    colour = app.evaluate("""() => {
        const c = document.getElementById('canvas');
        const d = c.getContext('2d').getImageData(Math.floor(c.width * 0.3), Math.floor(c.height / 2), 1, 1).data;
        return [d[0], d[1], d[2]];
    }""")
    assert colour != [0x1b, 0x1f, 0x24]


def test_tab_cycles_the_three_regions_and_wraps(app):
    # The menu bar is reached with Ctrl+Alt+M, not Tab (DP93).
    seen = []
    for _ in range(3):
        app.keyboard.press("Tab")
        seen.append(region(app))
    assert seen == ["panel", "details", "map"]
    app.keyboard.press("Shift+Tab")
    assert region(app) == "details"


def go_to_menu_bar(app):
    app.keyboard.press("Control+Alt+M")
    app.wait_for_function("document.getElementById('menubar').contains(document.activeElement)")


def test_arrow_keys_turn_the_globe_and_speak(app):
    paints = app.evaluate("window.tobymap.paints")
    app.keyboard.press("ArrowDown")
    app.wait_for_function(f"window.tobymap.announcements.length > 1")
    assert said(app)[-1] == "Spain"
    app.wait_for_function(f"window.tobymap.paints > {paints}")
    app.keyboard.press("PageDown")
    app.wait_for_function("window.tobymap.announcements.length > 2")
    assert said(app)[-1] == "Zoom 2 of 5, step 5 degrees."


def test_rapid_keys_move_every_step_but_speech_keeps_up(app):
    # ANN-3: after 10 rapid moves, every move is made and the final position is spoken.
    for _ in range(10):
        app.keyboard.press("ArrowRight")
    app.keyboard.press("Space")
    app.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('degrees north'))")
    texts = said(app)
    assert texts[-1] == "Russia. 52 degrees north, 99 degrees east. Zoom 1 of 5, step 10 degrees."
    assert len(texts) <= 12


def test_tree_items_take_real_focus(app):
    app.keyboard.press("Shift+Space")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    active = app.evaluate("document.activeElement.textContent")
    assert active == "United Kingdom"
    assert app.locator("[aria-activedescendant]").count() == 0
    app.keyboard.press("ArrowDown")
    assert app.evaluate("document.activeElement.textContent") == "Earth"
    app.keyboard.press("ArrowLeft")
    assert app.evaluate("document.activeElement.querySelector('.label').textContent") == "Within"
    assert app.evaluate("document.activeElement.getAttribute('aria-expanded')") == "true"
    app.keyboard.press("ArrowDown")  # Within's first item again
    app.keyboard.press("ArrowDown")
    app.keyboard.press("ArrowDown")  # Nearby group
    app.keyboard.press("ArrowRight")
    app.keyboard.press("ArrowRight")
    first_nearby = app.evaluate("document.activeElement.textContent")
    assert first_nearby == "Belgium, 420 kilometres east"
    app.wait_for_function("document.getElementById('details').value.startsWith('Belgium')")


def test_map_name_changes_only_while_it_does_not_have_focus(app):
    app.keyboard.press("ArrowDown")
    app.wait_for_function("window.tobymap.announcements.length > 1")
    assert app.get_attribute("#map", "aria-label") == "United Kingdom"  # unchanged while focused
    app.keyboard.press("Tab")
    assert app.get_attribute("#map", "aria-label") == "Spain"           # updated on leaving


def test_details_with_d_starts_on_the_first_line(app):
    app.keyboard.press("d")
    app.wait_for_function("document.activeElement.id === 'details'")
    assert "Sovereign state: United Kingdom" in app.input_value("#details")
    assert app.get_attribute("#details", "readonly") is not None
    assert app.evaluate("document.getElementById('details').selectionStart") == 0


def test_details_by_tab_starts_on_the_first_line_after_a_move(app):
    app.keyboard.press("ArrowDown")
    app.wait_for_function("document.getElementById('details').value.startsWith('Spain')")
    app.keyboard.press("Tab")
    app.keyboard.press("Tab")
    assert region(app) == "details"
    assert app.evaluate("document.getElementById('details').selectionStart") == 0


def test_menu_bar_from_the_registry(app):
    go_to_menu_bar(app)
    tops = app.locator("#menubar > [role=menuitem]").all_text_contents()
    assert tops == ["Map", "Speech", "Help"]
    # Ctrl+Alt+M goes to Map without opening it (DP93).
    assert app.evaluate("document.activeElement.textContent") == "Map"
    assert app.locator(".menu:not([hidden])").count() == 0
    app.keyboard.press("ArrowRight")  # Speech
    app.keyboard.press("ArrowDown")   # opens it, on its first item, Repeat
    app.keyboard.press("ArrowDown")
    assert app.evaluate("document.activeElement.textContent") == "Send a Braille-only message"
    app.keyboard.press("Enter")
    app.wait_for_function("window.tobymap.announcements.length > 1")
    assert said(app)[-1].startswith("Braille-only messages are not possible in a web browser.")
    assert region(app) == "map"


def test_tab_leaves_the_menu_bar_and_an_open_menu(app):
    go_to_menu_bar(app)
    app.keyboard.press("Tab")
    assert region(app) == "map"
    go_to_menu_bar(app)
    app.keyboard.press("Shift+Tab")
    assert region(app) == "details"
    go_to_menu_bar(app)
    app.keyboard.press("Enter")
    assert app.locator(".menu:not([hidden])").count() == 1
    app.keyboard.press("Tab")
    assert region(app) == "map"
    assert app.locator(".menu:not([hidden])").count() == 0


def test_f1_dialog_has_a_close_button(app):
    app.keyboard.press("F1")
    app.wait_for_function("document.getElementById('dialog').open")
    assert app.text_content("#dialog-title") == "Keys"
    assert "Turn the globe north: Up" in app.input_value("#dialog-text")
    assert "Exit" not in app.input_value("#dialog-text")
    app.keyboard.press("Tab")
    assert app.evaluate("document.activeElement.id") == "dialog-close"
    app.keyboard.press("Enter")
    assert not app.evaluate("document.getElementById('dialog').open")
    assert region(app) == "map"


def test_click_centres_the_globe(app):
    box = app.locator("#canvas").bounding_box()
    app.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    app.wait_for_function("window.tobymap.announcements.length > 1")
    assert said(app)[-1] == "United Kingdom"


def test_announcer_alternates_live_regions(page, site_url):
    # ?announcer=live forces the live regions even where ariaNotify exists.
    app = page
    app.goto(f"{site_url}/index.html?announcer=live")
    app.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    app.keyboard.press("c")
    app.wait_for_function("window.tobymap.announcements.length > 1")
    app.keyboard.press("c")
    app.wait_for_function("window.tobymap.announcements.length > 2")
    texts = app.evaluate("[...document.querySelectorAll('[id^=live-assertive]')].map(e => e.textContent)")
    assert sorted(texts) == ["", "52 degrees north, 1 degree west"]
