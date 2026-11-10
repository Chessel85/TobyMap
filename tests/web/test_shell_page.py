"""The web shell in Chromium and Firefox (P1-T11; UX section 2, ACC-1, ACC-7, ANN-3, INF-10, PLT-5, SCP-1, NFR-1)."""
import json

import pytest

pytest.importorskip("playwright")

START_LABEL = "Kent, England, United Kingdom. Press F1 for keys."
KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def saved(state=None, values=None):
    return json.dumps({"settings": {"values": values or {}, "keys": {}}, "state": state or KENT})


def open_app(page, site_url, state=None, values=None, query=""):
    page.add_init_script(f"if (!localStorage.getItem('tobymap')) localStorage.setItem('tobymap', {json.dumps(saved(state, values))});")
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(f"{site_url}/index.html{query}")
    page.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert page.evaluate("window.tobymap.error") is None
    return page


@pytest.fixture
def app(page, site_url):
    return open_app(page, site_url)


MAP_DOWNLOAD = ("Downloading the map", "The map is downloaded")


def said(page):
    """What was announced, leaving out the map download's own messages (first visit only)."""
    return [t for t in page.evaluate("window.tobymap.announcements.map(a => a.text)") if not t.startswith(MAP_DOWNLOAD)]


def region(page):
    return page.evaluate("""() => {
        const a = document.activeElement;
        if (document.getElementById('map').contains(a)) return 'map';
        if (document.getElementById('tree').contains(a)) return 'panel';
        if (a.id === 'details') return 'details';
        if (document.getElementById('menubar').contains(a)) return 'menu';
        return a.tagName;
    }""")


def region_script():
    return """() => {
        const a = document.activeElement;
        if (document.getElementById('map').contains(a)) return 'map';
        if (document.getElementById('tree').contains(a)) return 'panel';
        if (a.id === 'details') return 'details';
        if (document.getElementById('menubar').contains(a)) return 'menu';
        return a.tagName;
    }"""


def wait_said(page, count):
    page.wait_for_function(f"window.tobymap.announcements.filter(a => !a.text.startsWith('Downloading the map') && !a.text.startsWith('The map is downloaded')).length >= {count}")


def go_to_menu_bar(app):
    app.keyboard.press("Control+Alt+M")
    app.wait_for_function("document.getElementById('menubar').contains(document.activeElement)")


def test_start_is_the_map_name_as_focus_arrives_and_the_map_has_focus(app):
    # Spoken, the start was cut off by the screen reader reading the map's name as the focus
    # arrived, so "Press F1 for keys" was never heard (P2-T17d, web checklist 1.2).
    assert said(app) == []
    assert region(app) == "map"
    assert app.title() == "TobyMap"
    assert app.get_attribute("#map", "role") == "application"
    assert app.get_attribute("#map", "aria-label") == START_LABEL
    app.keyboard.press("F3")
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)")
    assert app.get_attribute("#map", "aria-label") == "Kent, England, United Kingdom"
    assert app.get_attribute("#tree", "aria-label") == "Information panel"
    assert app.get_attribute("#details", "aria-label") == "Details"
    assert app.locator("#loading").count() == 0


def test_the_map_is_painted(app):
    assert app.evaluate("window.tobymap.paints") >= 1
    colour = app.evaluate("""() => {
        const c = document.getElementById('canvas');
        const d = c.getContext('2d').getImageData(Math.floor(c.width * 0.3), Math.floor(c.height / 2), 1, 1).data;
        return [d[0], d[1], d[2]];
    }""")
    assert colour != [0x1b, 0x1f, 0x24]


def test_tab_cycles_the_three_regions_and_wraps(app):
    seen = []
    for _ in range(3):
        app.keyboard.press("Tab")
        seen.append(region(app))
    assert seen == ["panel", "details", "map"]
    app.keyboard.press("Shift+Tab")
    assert region(app) == "details"


def test_arrow_keys_step_and_speak_and_tick(app):
    app.keyboard.press("ArrowDown")
    wait_said(app, 1)
    assert said(app)[-1] == "North Atlantic Ocean"
    app.keyboard.press("ArrowDown")
    app.wait_for_function("window.tobymap.earcons.length >= 1")
    assert app.evaluate("window.tobymap.earcons") == ["tick"]
    assert len(said(app)) == 1          # a step that changes nothing is only the tick
    app.keyboard.press("PageDown")
    wait_said(app, 2)
    assert said(app)[-1] == "Zoom 10 kilometres."      # only what changed (checklist 7, second pass)


def test_holding_an_arrow_key_speaks_only_the_final_place_after_release(app):
    """ANN-3: key repeats are made but not spoken; on release only the last place is."""
    app.keyboard.down("ArrowDown")                     # the first press speaks
    wait_said(app, 1)
    spoken = len(said(app))
    app.wait_for_timeout(600)                          # past the repeat delay (DP129)
    for _ in range(20):
        app.keyboard.down("ArrowDown")                 # a held key repeats, slower than the repeat rate
        app.wait_for_timeout(200)
    assert len(said(app)) == spoken, "nothing is spoken while the key is held"
    app.keyboard.up("ArrowDown")
    wait_said(app, spoken + 1)
    assert len(said(app)) == spoken + 1
    assert said(app)[-1] == "France"                   # 500 km south of Kent
    assert app.evaluate("window.tobymap.announcements.at(-1).priority") == "assertive"


def test_a_slow_drawing_never_delays_the_clicks_of_a_held_key(page, site_url):
    """DP140, P2-T14: every drawing takes 200 ms longer, yet a 3 second hold at 6
    steps a second has every click set to sound within 10 ms of its due time. The
    map is drawn at most 4 times a second while the key is held."""
    app = open_app(page, site_url, query="?slowdraw=200")
    paints = app.evaluate("window.tobymap.paints")
    app.keyboard.down("ArrowDown")                     # the press is spoken at once
    wait_said(app, 1)
    for _ in range(30):                                # 3 seconds of the system's key repeats
        app.wait_for_timeout(100)
        app.keyboard.down("ArrowDown")
    held_paints = app.evaluate("window.tobymap.paints") - paints
    app.keyboard.up("ArrowDown")
    wait_said(app, 2)
    assert said(app)[-1] == "France"
    clicks = app.evaluate("window.tobymap.clicks")
    assert len(clicks) >= 14                           # 2.5 seconds after the delay, 6 a second
    late = [round(c["at"] - c["due"], 1) for c in clicks]
    assert all(0 <= d <= 10 for d in late), late
    dues = [c["due"] for c in clicks]
    assert all(abs(b - a - 1000 / 6) < 0.5 for a, b in zip(dues, dues[1:]))   # an even beat
    assert held_paints <= 3 * 4 + 1, held_paints       # at most 4 a second, and the press's own


def test_letting_go_of_a_held_key_makes_no_second_click(page, site_url):
    """Phase 2 web checklist 2.10. Each click is set on the sound card 50 ms early. A key
    let go before then takes back the click and its step, unless the sound card has
    already started on the click, which works some way ahead of what is heard; then the
    step is made too, so every click heard has its step. The release adds no tick."""
    app = open_app(page, site_url, values={"coordinate_places": "fixed"})   # to count the steps
    app.evaluate("""() => document.addEventListener('keyup', () => {
        window.releasedAt = performance.now();
        window.playedAtRelease = window.tobymap.earcons.length;
    }, { capture: true, once: true })""")
    # Let go just after the third click is set, about 50 ms before it is due.
    app.evaluate("""() => { const c = window.tobymap.clicks, push = c.push.bind(c);
        c.push = (x) => { const n = push(x);
            if (n === 3) setTimeout(() => document.dispatchEvent(
                new KeyboardEvent('keyup', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true })), 0);
            return n; }; }""")
    app.keyboard.down("ArrowDown")                     # the press steps and is spoken at once
    wait_said(app, 1)
    app.wait_for_function("window.releasedAt !== undefined", timeout=10_000)
    app.keyboard.up("ArrowDown")                       # the real key, already let go as far as the page knows
    app.wait_for_timeout(600)                          # the release, and the time the click was due
    after = app.evaluate("window.tobymap.earcons.slice(window.playedAtRelease)")
    assert "tick" not in after, after
    assert len(said(app)) == 1                         # still at sea: nothing changed, so nothing said
    released = app.evaluate("window.releasedAt")
    ahead_ms = app.evaluate("""async () => {
        const s = await import(new URL('./js/sounds.js', location.href).href);
        const c = s.audio(), t = c.getOutputTimestamp();
        return (c.currentTime - t.contextTime) * 1000; }""")
    heard = [c for c in app.evaluate("window.tobymap.clicks") if not c["cancelled"]]
    assert all(c["due"] <= released + ahead_ms + 5 for c in heard), (released, ahead_ms, heard[-2:])
    app.keyboard.press("c")
    wait_said(app, 2)
    lat = float(said(app)[-1].split(" degrees north")[0])
    steps = round((51.2 - lat) / 0.22482)              # 25 km south each
    assert steps == 1 + len(heard), (lat, len(heard))  # the press, then one step for each click heard


def test_ten_rapid_taps_make_every_step_but_speech_keeps_up(page, site_url):
    app = open_app(page, site_url, values={"coordinate_places": "fixed"})   # every place, to see each step
    for _ in range(10):
        app.keyboard.press("ArrowDown")
    app.keyboard.press("c")
    app.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('degrees north'))")
    texts = said(app)
    assert texts[-1].startswith("48.9")         # ten steps of 25 km south: every step was made


def test_f2_f3_f4_and_ctrl_alt_m_go_where_they_should(app):
    for key, where in (("F4", "details"), ("F3", "panel"), ("F2", "map")):
        app.keyboard.press(key)
        app.wait_for_function(f"({region_script()})() === '{where}'")
    app.keyboard.press("F4")
    app.wait_for_function("document.activeElement.id === 'details'")
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    assert app.evaluate("document.activeElement.textContent") == "Kent"
    app.keyboard.press("F2")
    app.wait_for_function("document.activeElement.id === 'map'")
    go_to_menu_bar(app)
    app.keyboard.press("F2")
    app.wait_for_function("document.activeElement.id === 'map'")


def test_the_tree_has_levels_and_real_focus_on_its_items(app):
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    assert app.locator("[aria-activedescendant]").count() == 0
    assert app.evaluate("document.activeElement.getAttribute('aria-level')") == "2"
    assert app.evaluate("document.activeElement.parentElement.closest('[role=treeitem]').getAttribute('aria-level')") == "1"
    # Words directly inside each item, so the screen reader reads them in Firefox (spike S5).
    assert app.evaluate("document.activeElement.firstChild.nodeType") == 3
    assert app.locator("#tree [aria-labelledby]").count() == 0
    app.keyboard.press("ArrowLeft")
    assert app.evaluate("document.activeElement.getAttribute('aria-label')") == "Within"
    assert app.evaluate("document.activeElement.getAttribute('aria-level')") == "1"


def test_the_tree_keeps_its_items_when_refreshed(app):
    app.evaluate("window.__first = document.querySelector('#tree [role=treeitem] [role=treeitem]')")
    app.evaluate("window.tobymap.paints = 0")
    app.keyboard.press("ArrowUp")
    app.wait_for_function("window.tobymap.paints > 0")
    assert app.evaluate("window.__first === document.querySelector('#tree [role=treeitem] [role=treeitem]')")


def test_f3_goes_back_to_the_item_last_focused(app):
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    app.keyboard.press("ArrowDown")
    app.keyboard.press("ArrowDown")
    last = app.evaluate("document.activeElement.textContent")
    app.keyboard.press("F2")
    app.wait_for_function("document.activeElement.id === 'map'")
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    assert app.evaluate("document.activeElement.textContent") == last
    app.wait_for_function(f"document.getElementById('details').value.startsWith({json.dumps(last.split(',')[0])})")


def test_map_name_changes_only_while_it_does_not_have_focus(app):
    app.keyboard.press("ArrowDown")
    wait_said(app, 1)
    assert app.get_attribute("#map", "aria-label") == START_LABEL   # unchanged while focused
    app.keyboard.press("Tab")
    assert app.get_attribute("#map", "aria-label") == "North Atlantic Ocean"


def test_details_by_f4_starts_on_the_first_line(app):
    app.keyboard.press("F4")
    app.wait_for_function("document.activeElement.id === 'details'")
    assert app.input_value("#details").splitlines()[0] == "Kent"
    assert app.get_attribute("#details", "readonly") is not None
    assert app.evaluate("document.getElementById('details').selectionStart") == 0


def test_menu_bar_from_the_registry_with_toggles(app):
    go_to_menu_bar(app)
    tops = app.locator("#menubar > [role=menuitem]").all_text_contents()
    assert tops == ["Map", "Speech", "Settings", "Help"]
    assert app.evaluate("document.activeElement.textContent") == "Map"
    assert app.locator(".menu:not([hidden])").count() == 0
    app.keyboard.press("Enter")
    assert app.locator('.menu:not([hidden]) [role=menuitemcheckbox]').count() == 3   # Link step to zoom, the beacon, Isolate
    app.keyboard.press("Escape")
    assert app.locator(".menu:not([hidden])").count() == 0 and region(app) == "menu"
    app.keyboard.press("Escape")                       # Escape on the bar goes back to the map (web checklist 2.4)
    app.wait_for_function("document.activeElement.id === 'map'")
    go_to_menu_bar(app)
    app.keyboard.press("ArrowRight")
    for _ in range(5):                                 # past Next verbosity preset (P2-T11)
        app.keyboard.press("ArrowDown")
    assert app.evaluate("document.activeElement.textContent").startswith("Send a Braille-only message")
    app.keyboard.press("Enter")
    wait_said(app, 1)
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


def test_f1_dialog_for_the_focused_region_has_a_close_button(app):
    app.keyboard.press("F1")
    app.wait_for_function("document.getElementById('dialog').open")
    assert app.text_content("#dialog-title") == "Keys"
    text = app.input_value("#dialog-text")
    assert "Step north or forward: Up" in text and "Exit" not in text
    app.keyboard.press("Tab")
    assert app.evaluate("document.activeElement.id") == "dialog-close"
    app.keyboard.press("Enter")
    assert not app.evaluate("document.getElementById('dialog').open")
    assert region(app) == "map"


def test_history_repeat_and_the_key_describer(app):
    app.keyboard.press("Space")
    wait_said(app, 1)
    app.keyboard.press("Shift+Space")          # repeat (P2-T0c, your key)
    wait_said(app, 2)
    assert said(app)[-1] == "Kent, England, United Kingdom"
    app.keyboard.press("Control+Shift+Space")
    app.wait_for_function("document.getElementById('dialog').open")
    assert app.eval_on_selector("#history-list option", "o => o.textContent") == "Kent, England, United Kingdom"
    app.click("#dialog-close")
    app.keyboard.press("Shift+F1")
    wait_said(app, 3)
    app.keyboard.press("ArrowDown")
    wait_said(app, 4)
    assert said(app)[-1] == "Down: Step south or back"
    assert len(said(app)) == 4
    app.keyboard.press("Tab")             # caught: it does nothing (checklist 2.2)
    wait_said(app, 5)
    assert said(app)[-1] == "Tab: no command."
    app.keyboard.press("Shift+F1")
    wait_said(app, 6)
    assert said(app)[-1] == "Key describer off."


def test_settings_dialog_has_ok_and_cancel_and_the_settings_are_kept(app, page, site_url):
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    assert app.locator("#settings-ok").text_content() == "OK" and app.locator("#settings-cancel").text_content() == "Cancel"
    tabs = app.locator("#settings [role=tab]").all_text_contents()
    assert tabs == ["Units", "Movement", "Speech", "Layers", "Sound", "Earcons", "Display", "Keys"]   # pages, not one long dialog (web checklist 2)
    assert app.evaluate("document.activeElement.textContent") == "Units"
    assert app.locator("#settings [role=tabpanel]:not([hidden])").count() == 1
    app.keyboard.press("Tab")
    assert app.evaluate("document.activeElement.dataset.field") == "units"
    app.select_option("#settings select[data-field=units]", "imperial")
    app.keyboard.press("Enter")                        # Enter is OK (web checklist 5)
    app.wait_for_function("!document.getElementById('settings').open")
    app.keyboard.press("h")
    app.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('miles'))")
    assert "Zoom 15.5 miles" in said(app)[-1] or "miles" in said(app)[-1]
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))
    assert stored["settings"]["values"]["units"] == "imperial"
    app.reload()
    app.wait_for_function("window.tobymap && window.tobymap.ready", timeout=120_000)
    app.keyboard.press("h")
    app.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('miles'))")


def test_number_fields_are_chosen_on_arrival_and_tab_stays_on_the_page(app):
    """Web checklist 8: typing replaces the number. The hidden pages are not reached by Tab."""
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    app.keyboard.press("ArrowRight")
    assert app.evaluate("document.activeElement.textContent") == "Movement"
    app.keyboard.press("Tab")
    app.keyboard.press("Tab")
    assert app.evaluate("document.activeElement.dataset.field") == "repeat_delay_ms"
    app.keyboard.type("1000")
    assert app.input_value("#settings input[data-field=repeat_delay_ms]") == "1000"
    fields = app.evaluate("""[...document.querySelectorAll('#settings [data-field]')]
        .filter(el => !el.closest('[hidden]')).map(el => el.dataset.field)""")
    assert "units" not in fields and "repeat_rate" in fields
    app.click("#settings-cancel")
    app.wait_for_function("!document.getElementById('settings').open")


def test_changing_a_key_warns_when_it_is_taken(app):
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    app.click("#settings-tab-keys")
    labels = app.locator("#settings-keys option").all_text_contents()
    assert "Settings: Ctrl+Comma" in labels                       # symbols as words (checklist 2, second pass)
    app.select_option("#settings-keys", index=next(i for i, t in enumerate(labels) if t.startswith("Heading:")))
    app.click("#settings-change-key")
    app.wait_for_function("document.getElementById('keydialog').open")
    app.keyboard.press("c")
    app.click("#key-ok")
    app.wait_for_function("document.getElementById('key-message').textContent.length > 0")
    assert app.text_content("#key-message") == "C is already used by Coordinates. Choose another key."
    app.click("#key-cancel")
    app.click("#settings-cancel")
    app.wait_for_function("!document.getElementById('settings').open")


def test_the_sounds_in_help_can_be_played(app):
    """DP134: Help, The sounds is one list; Enter, Space or Play plays the chosen sound (web checklist 9)."""
    app.evaluate("window.tobymap.earcons.length = 0")
    app.evaluate("document.querySelector('[data-command=\"help.earcons\"]').click()")
    app.wait_for_function("document.activeElement.id === 'sounds-list'")
    app.keyboard.press("Enter")
    app.wait_for_function("window.tobymap.earcons.length >= 1")
    app.keyboard.press("ArrowDown")
    app.keyboard.press(" ")
    app.wait_for_function("window.tobymap.earcons.length >= 2")
    app.click("#sounds-play")
    app.wait_for_function("window.tobymap.earcons.length >= 3")
    assert app.evaluate("window.tobymap.earcons") == ["tick", "blocked", "blocked"]
    app.focus("#sounds-list")
    app.keyboard.press("Tab")                           # one stop for the list, then Play, then Close
    assert app.evaluate("document.activeElement.id") == "sounds-play"
    app.keyboard.press("Tab")
    assert app.evaluate("document.activeElement.id") == "dialog-close"
    app.click("#dialog-close")


def test_mute_stops_the_earcons(app):
    app.keyboard.press("Control+m")
    wait_said(app, 1)
    assert said(app)[-1] == "Sound muted."
    app.keyboard.press("ArrowUp")
    app.wait_for_timeout(500)
    assert app.evaluate("window.tobymap.earcons") == []


def test_click_describes_the_place(app):
    box = app.locator("#canvas").bounding_box()
    app.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 8)
    app.wait_for_function("window.tobymap.announcements.length > 1 || window.tobymap.earcons.length > 0")
    assert app.evaluate("window.tobymap.error") is None


def test_the_wheel_changes_the_zoom(app):
    box = app.locator("#canvas").bounding_box()
    app.mouse.move(box["x"] + 100, box["y"] + 100)
    app.mouse.wheel(0, -120)
    wait_said(app, 1)
    assert said(app)[-1].startswith("Zoom 10 kilometres")


def test_announcer_alternates_live_regions(page, site_url):
    open_app(page, site_url, values={"coordinate_places": "fixed"}, query="?announcer=live")
    page.keyboard.press("c")
    wait_said(page, 1)
    page.keyboard.press("c")
    wait_said(page, 2)
    texts = page.evaluate("[...document.querySelectorAll('[id^=live-assertive]')].map(e => e.textContent)")
    assert sorted(texts) == ["", "51.20000 degrees north, 1.20000 degrees east"]


def test_the_time_of_where_am_i_and_of_a_step_is_recorded(app):
    for key in ("Space", "ArrowDown", "ArrowUp", "ArrowDown"):
        app.keyboard.press(key)
        app.wait_for_timeout(300)
    times = app.evaluate("window.tobymap.timings")
    print(f"Key to speech in the browser: {[round(t) for t in times]} ms (for the web figure in the exit checks)")
    assert times and min(times) >= 0


def test_nothing_in_the_page_asks_for_the_location(app):
    assert app.evaluate("typeof navigator.geolocation") in ("object", "undefined")
    asked = app.evaluate("window.__asked === undefined")
    assert asked


def test_axe_finds_no_serious_accessibility_problems(app):
    """A first automatic check against WCAG 2.2 AA (ACC-7) with axe-core, a test tool only (MPL-2.0)."""
    from pathlib import Path

    axe = Path(__file__).resolve().parents[2] / "web" / "vendor" / "axe" / "axe.min.js"
    if not axe.is_file():
        pytest.skip("axe-core is not in web/vendor. Run: python tools/fetch_vendor.py --axe")
    app.add_script_tag(content=axe.read_text(encoding="utf-8"))
    result = app.evaluate("""() => axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } })
        .then(r => r.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target.join(' ')) })))""")
    serious = [v for v in result if v["impact"] in ("serious", "critical")]
    assert serious == [], serious


# Orientation, turning, typed bearings and coordinates, the place history (P2-T1d, P2-T2c, P2-T15) -------------

def test_the_orientation_and_turning_keys(app):
    app.keyboard.press("o")
    wait_said(app, 1)
    assert said(app)[-1] == "Cardinal facing, north."
    app.keyboard.press("ArrowRight")            # Shift turns do nothing in cardinal facing (P2-T16c)
    wait_said(app, 2)
    assert said(app)[-1] == "Facing east."
    app.keyboard.press("o")
    wait_said(app, 3)
    app.keyboard.press("Control+ArrowLeft")
    wait_said(app, 4)
    assert said(app)[-1] == "Facing 89 degrees."


def test_the_bearing_box_keeps_open_on_a_bad_answer_and_takes_a_good_one(app):
    app.keyboard.press("Control+b")
    app.wait_for_function("document.getElementById('inputdialog').open")
    assert app.eval_on_selector("#inputdialog h2", "e => e.textContent") == "Type a bearing"
    assert app.evaluate("document.activeElement.id") == "input-field"
    app.fill("#input-field", "sideways")
    app.click("#input-ok")
    app.wait_for_function("document.getElementById('input-message').textContent.startsWith('That is not a bearing')")
    assert app.evaluate("document.getElementById('inputdialog').open")
    app.fill("#input-field", "NE")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    assert app.get_attribute("#map", "aria-label") == "Free facing, 45 degrees."   # said as focus returns
    assert app.evaluate("document.activeElement.id") == "map"


def test_go_to_coordinates_and_back_through_the_places(app):
    app.keyboard.press("Control+g")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.fill("#input-field", "52.1 N 1.3 W")
    app.click("#input-ok")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    app.keyboard.press("Control+g")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.click("#input-cancel")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    app.keyboard.press("Alt+,")
    wait_said(app, 1)
    assert said(app)[-1] == "Kent, England, United Kingdom"


LABEL_ON_FOCUS = """() => {
  window.labelsOnFocus = [];
  document.getElementById('map').addEventListener('focus',
    (e) => window.labelsOnFocus.push(e.target.getAttribute('aria-label')));
}"""


def test_after_go_to_the_new_place_is_said_once_as_the_maps_name_when_focus_returns(app):
    # The screen reader reads the map's name as focus returns, so it must already be the new place,
    # and it is not spoken as well, or it is heard twice (P2-T17c, web checklist 5.2).
    app.evaluate(LABEL_ON_FOCUS)
    app.keyboard.press("Control+g")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.fill("#input-field", "48.8566, 2.3522")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    app.wait_for_function("window.labelsOnFocus.length > 0")
    (place,) = app.evaluate("window.labelsOnFocus")
    assert place and "Kent" not in place
    assert said(app) == []


def test_after_enter_in_the_history_the_map_has_that_place_as_its_name_when_focus_returns(app):
    app.keyboard.press("PageUp")
    wait_said(app, 1)
    app.keyboard.press("Control+g")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.fill("#input-field", "10, 10")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    app.evaluate(LABEL_ON_FOCUS)
    app.keyboard.press("Control+Shift+Space")
    app.wait_for_function("document.getElementById('dialog').open")
    app.keyboard.press("ArrowDown")          # the zoom entry, said at Kent
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('dialog').open")
    app.wait_for_function("window.labelsOnFocus.length > 0")
    assert app.evaluate("window.labelsOnFocus") == ["Kent, England, United Kingdom"]
    assert len(said(app)) == 1                # the zoom: the place is not spoken as well (P2-T17c)


def test_enter_in_the_announcement_history_goes_back_there(app):
    app.keyboard.press("PageUp")
    wait_said(app, 1)
    app.keyboard.press("Control+g")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.fill("#input-field", "10, 10")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    app.keyboard.press("Control+Shift+Space")
    app.wait_for_function("document.getElementById('dialog').open")
    app.keyboard.press("ArrowDown")          # the zoom entry, said at Kent
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('dialog').open")
    assert app.get_attribute("#map", "aria-label") == "Kent, England, United Kingdom"
    app.keyboard.press("Alt+,")
    wait_said(app, 2)
    assert said(app)[-1] != "Kent, England, United Kingdom"


def test_enter_on_an_entry_with_no_place_keeps_the_history_open(app):
    app.keyboard.press("Control+m")          # speaks, but has no place
    wait_said(app, 1)
    app.keyboard.press("Control+Shift+Space")
    app.wait_for_function("document.getElementById('dialog').open")
    app.keyboard.press("Enter")
    app.wait_for_function("document.getElementById('history-message').textContent === 'No place for this entry.'")
    assert app.evaluate("document.getElementById('dialog').open")


# The layers dialog (P2-T3c; SCP-6, SCP-7) -------------------------------------------------

def test_the_layers_dialog_lists_layers_in_groups_and_ok_switches_one(app):
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    assert app.eval_on_selector("#layersdialog h2", "e => e.textContent") == "Layers"
    assert app.eval_on_selector_all("#layersdialog legend", "els => els.map(e => e.textContent)")[:2] == \
        ["Boundaries", "Water"]
    assert app.evaluate("document.activeElement.dataset.layer") == "countries"
    app.uncheck("[data-layer=regions]")
    app.click("#layers-ok")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.keyboard.press("Space")
    wait_said(app, 1)
    assert said(app)[-1] == "Kent, United Kingdom"
    assert app.evaluate("document.activeElement.id") == "map"


def test_space_in_the_layers_dialog_ticks_and_enter_presses_ok(app):
    # PO feedback on web checklist 2.6: Space switches a layer, Enter always presses OK.
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    app.focus("[data-layer=regions]")
    app.keyboard.press("Space")
    assert not app.is_checked("[data-layer=regions]")
    app.focus("[data-layer=counties]")
    app.click("#layers-settings")
    app.focus("#layersdialog select >> nth=0")
    app.keyboard.press("Enter")                 # OK in the layer's settings: back to the list
    app.wait_for_function("document.activeElement.dataset.layer === 'counties'")
    assert app.evaluate("document.getElementById('layersdialog').open")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.keyboard.press("Space")
    wait_said(app, 1)
    assert said(app)[-1] == "Kent, United Kingdom"


def test_cancel_in_the_layers_dialog_changes_nothing_and_a_wrong_range_is_refused(app):
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    app.uncheck("[data-layer=regions]")
    app.focus("[data-layer=counties]")
    app.click("#layers-settings")
    app.select_option("#layersdialog select >> nth=0", label="250 kilometres")
    app.click("#layer-settings-ok")
    app.wait_for_function("document.querySelector('#layer-settings-message').textContent.startsWith('The minimum zoom')")
    app.click("#layer-settings-cancel")
    app.click("#layers-cancel")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.keyboard.press("Space")
    wait_said(app, 2)
    assert said(app)[-1] == "Kent, England, United Kingdom"


def test_crossed_and_passed_is_filled_between_key_presses_and_shift_3_goes_there(page, site_url):
    """P2-T5, ANN-2: a 1 km step across the River Itchen lists it in Crossed and passed, with the
    earcon and nothing more spoken. Shift+3 goes to the group, the third, whatever symbol the key makes (DP109)."""
    from pathlib import Path

    data = json.loads((Path(__file__).resolve().parents[1] / "samples" / "osm" / "southampton-itchen.geojson")
                      .read_text(encoding="utf-8"))
    river = next(f for f in data["features"] if f["properties"]["name"] == "River Itchen")
    line = max(river["geometry"]["coordinates"], key=len)
    lon, lat = line[len(line) // 2]
    import math
    west = lon - 300 / (6_371_000 * math.cos(math.radians(lat)) * math.pi / 180)
    app = open_app(page, site_url, state={"lat": lat, "lon": west, "zoom_m": 5000, "step_m": 1000})
    app.keyboard.press("ArrowRight")
    app.wait_for_function("window.tobymap.earcons.includes('crossed_added')", timeout=30_000)
    assert len(said(app)) == 0   # still Southampton: only the tick; the river is never spoken
    app.keyboard.press("Shift+Digit3")
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)")
    assert app.evaluate("document.activeElement.textContent").startswith("River Itchen, crossed")


def test_the_web_player_turns_the_scene_into_the_cores_pan_pitch_and_filter_values(app, test_pack):
    """P2-T6c, AD-10: the same placed sounds as the desktop's player gets, carried out by Web Audio."""
    import math

    from mapcore.session import MapSession

    s = MapSession(packs=[test_pack], saved_state={"lat": 0.0, "lon": 0.0, "zoom_m": 100000, "step_m": 1000})
    cases = []
    for mode in ("stereo", "hrtf"):
        s.settings.set("sound_mode", mode)
        for lat, lon in ((0.0, 0.3), (-0.3, 0.0), (0.0, -3.0)):   # right; behind; left, beyond the view
            cases.append(s.place_sound("ding", lat, lon))
    s.store.close()
    made = app.evaluate("""async (cases) => {
        const sounds = await import(new URL('./js/sounds.js', location.href).href);
        for (const p of cases) await sounds.playPlaced(p);
        return sounds.placed.slice(-cases.length);
    }""", cases)
    assert len(made) == len(cases)
    for p, m in zip(cases, made):
        assert m["pitch"] == pytest.approx(p["pitch"], abs=1e-6)
        assert m["gain"] == pytest.approx(p["gain"], abs=1e-6)
        assert m["cutoff_hz"] == pytest.approx(p["cutoff_hz"], rel=1e-5)
        if p["mode"] == "stereo":
            assert m["pan"] == pytest.approx(p["pan"], abs=1e-6)
        else:
            r = math.radians(p["relative_deg"])
            assert (m["x"], m["z"]) == (pytest.approx(math.sin(r), abs=1e-6), pytest.approx(-math.cos(r), abs=1e-6))
    assert made[1]["pitch"] < 1 and made[0]["pan"] == pytest.approx(1.0)


def test_a_preset_chosen_in_settings_keeps_its_switches_and_a_goes_to_the_next(app):
    """P2-T11 (ACC-5, DP144): OK sends only what was changed, so the preset's switches stay."""
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    app.click("#settings-tab-speech")
    app.select_option("#settings select[data-field=verbosity]", "terse")
    app.click("#settings-ok")
    app.wait_for_function("!document.getElementById('settings').open")
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))["settings"]["values"]
    assert stored["verbosity"] == "terse" and stored["say_area"] == "smallest" and stored["say_zoom_step"] is False
    count = len(said(app))
    app.keyboard.press("a")
    wait_said(app, count + 1)
    assert said(app)[-1] == "Normal. Every area that changed is said, and the zoom, the step and the heading."


@pytest.mark.parametrize("size", [(800, 600), (1200, 800), (1600, 1000)])
def test_the_focus_point_holds_the_map_centre_after_a_step_a_click_and_a_jump(app, size):
    """P2-T13b (ACC-8, DP146): the map's focused element is a small square at the map centre,
    so a magnifier that follows the keyboard focus keeps the location in view."""
    app.set_viewport_size({"width": size[0], "height": size[1]})

    def holds_centre():
        return app.evaluate("""() => {
            const f = document.getElementById('map').getBoundingClientRect();
            const c = document.getElementById('canvas').getBoundingClientRect();
            const x = c.left + c.width / 2, y = c.top + c.height / 2;
            return document.activeElement.id === 'map' && f.width <= 16 && f.height <= 16
                && f.left - 1 <= x && x <= f.right + 1 && f.top <= y && y <= f.bottom;
        }""")

    def paints():
        return app.evaluate("window.tobymap.paints")

    app.wait_for_function("() => { const s = document.getElementById('canvas').getBoundingClientRect(); "
                          f"return Math.abs(s.width + document.getElementById('side').getBoundingClientRect().width - {size[0]}) < 40; }}")
    app.wait_for_timeout(300)   # the drawing for the new size
    assert holds_centre()
    n = paints()
    app.keyboard.press("ArrowDown")                              # a step
    app.wait_for_function(f"window.tobymap.paints > {n}")
    assert holds_centre()
    n = paints()
    box = app.locator("#canvas").bounding_box()
    app.mouse.click(box["x"] + box["width"] / 3, box["y"] + box["height"] / 3)   # a click
    app.wait_for_function(f"window.tobymap.paints > {n}")
    assert holds_centre()
    n = paints()
    app.keyboard.press("Control+g")                              # a jump
    app.wait_for_function("document.querySelector('dialog[open] input')")
    app.keyboard.type("48.85, 2.35")
    app.keyboard.press("Enter")
    app.wait_for_function(f"window.tobymap.paints > {n} && document.activeElement.id === 'map'")
    assert holds_centre()


# Enter on a button presses that button, and Enter on a check box presses OK (P2-T17b; web checklist 8.6, 10.6; ACC-7)

def test_enter_on_a_layer_check_box_presses_ok_and_never_ticks_it(app):
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    # NVDA stays in focus mode here, so Enter reaches the page rather than clicking the box
    assert app.evaluate("!!document.querySelector('[data-layer=regions]').closest('[role=application]')")
    app.focus("[data-layer=regions]")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.keyboard.press("Space")
    wait_said(app, 1)
    assert said(app)[-1] == "Kent, England, United Kingdom"   # Regions is still on


def test_enter_on_each_button_in_the_layers_list_presses_that_button(app):
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    app.focus("[data-layer=counties]")
    app.focus("#layers-settings")
    app.keyboard.press("Enter")                         # opens that layer's settings
    app.wait_for_function("!!document.getElementById('layer-settings-cancel')")
    assert app.evaluate("!!document.activeElement.closest('[role=application]')")
    app.select_option("#layersdialog select >> nth=0", label="250 kilometres")
    app.focus("#layer-settings-cancel")
    app.keyboard.press("Enter")                         # back to the list, with nothing refused or kept
    app.wait_for_function("document.activeElement.dataset.layer === 'counties'")
    assert app.evaluate("!document.getElementById('layer-settings-message')")
    app.uncheck("[data-layer=regions]")
    app.focus("#layers-cancel")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.keyboard.press("Space")
    wait_said(app, 1)
    assert said(app)[-1] == "Kent, England, United Kingdom"   # Cancel kept nothing


def test_enter_on_a_settings_check_box_presses_ok_and_on_cancel_cancels(app):
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    assert app.evaluate("!!document.querySelector('#settings-ok').closest('[role=application]')")
    app.click("#settings-tab-movement")
    app.focus("#settings [data-field=link]")
    app.keyboard.press("Enter")                         # OK, and the box is not ticked
    app.wait_for_function("!document.getElementById('settings').open")
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))
    assert not stored["settings"]["values"].get("link")
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    app.click("#settings-tab-movement")
    app.check("#settings [data-field=link]")
    app.focus("#settings-cancel")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('settings').open")
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))
    assert not stored["settings"]["values"].get("link")


def test_enter_on_cancel_closes_the_bearing_box_without_reading_it(app):
    app.keyboard.press("Control+b")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.keyboard.type("hello")
    app.focus("#input-cancel")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    assert not any(t.startswith("That is not a bearing") for t in said(app))


# The place said once as a dialog closes (P2-T17c; web checklist 5.2, 8.6) ------------------------

def test_closing_the_layers_list_names_the_map_after_the_changes(app):
    # Web checklist 8.6: with Countries and Regions off, "United Kingdom" was still said as the list
    # closed, because the map's name was changed only after the focus had come back.
    app.evaluate(LABEL_ON_FOCUS)
    app.keyboard.press("Control+Shift+L")
    app.wait_for_function("document.getElementById('layersdialog').open")
    for layer in ("countries", "regions", "counties"):
        app.uncheck(f"[data-layer={layer}]")
    app.click("#layers-ok")
    app.wait_for_function("!document.getElementById('layersdialog').open")
    app.wait_for_function("window.labelsOnFocus.length > 0")
    (name,) = app.evaluate("window.labelsOnFocus")
    assert "United Kingdom" not in name
    app.keyboard.press("Space")
    wait_said(app, 1)
    assert said(app)[-1] == name              # the same words as Space says, after the change
    assert said(app)[:-1] == []          # and nothing spoken as the list closed


def test_after_a_bearing_leaving_the_map_names_it_after_the_place_again(app):
    app.keyboard.press("Control+b")
    app.wait_for_function("document.getElementById('inputdialog').open")
    app.fill("#input-field", "90")
    app.keyboard.press("Enter")
    app.wait_for_function("!document.getElementById('inputdialog').open")
    assert app.get_attribute("#map", "aria-label") == "Free facing, 90 degrees."
    assert said(app) == []
    app.keyboard.press("F3")
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)")
    assert app.get_attribute("#map", "aria-label") == "Kent, England, United Kingdom"
