"""The key maps and your keys (P3-T31a, AD-3, ACC-3, ACC-4): five key map files, your keys as changes on
top of the chosen one, key files, and the keys of earlier versions carried over."""
import json

import pytest

from mapcore.commands import keys as keymaps
from mapcore.commands import registry
from mapcore.session import MapSession


@pytest.fixture
def make(test_pack):
    made = []

    def _make(**kw):
        s = MapSession(packs=[test_pack], **kw)
        made.append(s)
        return s

    yield _make
    for s in made:
        s.store.close()


# The files -----------------------------------------------------------------------------------------

def test_there_are_five_key_maps_each_a_file():
    assert keymaps.KEYMAPS == ("windows-desktop", "mac-desktop", "windows-browser", "mac-browser", "alternative")
    for name in keymaps.KEYMAPS:
        assert (keymaps.KEYMAP_DIR / f"{name}.yaml").is_file()


def test_each_key_map_has_a_name_for_settings():
    from mapcore.describe import templates

    assert templates()["keymaps"] == {"windows-desktop": "Windows desktop", "mac-desktop": "Mac desktop",
                                      "windows-browser": "Windows browser", "mac-browser": "Mac browser",
                                      "alternative": "Alternative"}


def test_other_key_maps_list_only_the_keys_that_differ():
    """Keys are written once: the Windows browser and Mac key maps hold only their differences."""
    full = keymaps.own_keys("windows-desktop")
    assert len(full) > 60
    for name in ("windows-browser", "mac-desktop", "mac-browser", "alternative"):
        assert len(keymaps.own_keys(name)) <= 10, name


def test_the_windows_keys_are_as_they_were():
    desktop = keymaps.resolve("windows-desktop", "desktop", "windows")
    assert desktop["where.heading"] == "H" and desktop["wikipedia.open"] == "Ctrl+Alt+W"
    assert desktop["history.back"] == "Alt+," and desktop["settings.open"] == "Ctrl+,"
    assert desktop["panel.within"] == "Shift+1" and desktop["panel.search"] == "Shift+7"
    browser = keymaps.resolve("windows-browser", "web", "windows")
    assert browser["wikipedia.open"] == "Alt+Shift+W" and browser["focus.menu"] == "Ctrl+Alt+M"
    assert {c: k for c, k in browser.items() if c not in ("wikipedia.open", "focus.menu")} == \
        {c: k for c, k in desktop.items() if c != "wikipedia.open"}


def test_every_panel_group_has_its_shift_and_number_key():
    keys = keymaps.resolve(None, "desktop", "windows")
    for number, group in enumerate(registry.panel_groups(), start=1):
        assert keys[f"panel.{group}"] == f"Shift+{number}"


# How a key map is read --------------------------------------------------------------------------------

def test_a_mac_key_map_turns_ctrl_into_cmd():
    mac = keymaps.resolve("mac-desktop", "desktop", "mac")
    assert mac["search.open"] == "Cmd+F" and mac["browse.open"] == "Shift+Cmd+F"
    assert mac["settings.open"] == "Cmd+,"     # Apple's own key for Settings
    assert mac["where.heading"] == "H" and mac["panel.within"] == "Shift+1"
    assert keymaps.to_mac("Ctrl+Shift+Space") == "Shift+Cmd+Space" and keymaps.to_mac("Alt+Left") == "Alt+Left"


def test_the_mac_key_maps_keep_clear_of_macos_and_the_browser():
    desktop = keymaps.resolve("mac-desktop", "desktop", "mac")
    browser = keymaps.resolve("mac-browser", "web", "mac")
    for keys in (desktop, browser):
        assert keys["sound.mute"] == "Ctrl+M"                  # Cmd+M minimises the window
        assert keys["wikipedia.open"] == "Ctrl+Shift+W"        # Cmd+Option+W closes every window
        assert keys["history.back"] == "Shift+Cmd+Left"        # Option+Comma types a character
        assert keys["history.forward"] == "Shift+Cmd+Right"
        assert keys["turn.fine_left"] == "Alt+Left"            # Cmd+Left is Back in a browser
    assert browser["settings.open"] == "Ctrl+,"                # Cmd+Comma is the browser's settings
    assert browser["focus.menu"] == "Ctrl+Shift+M"


def test_alternative_replaces_only_ctrl_alt_with_a_letter_and_punctuation():
    for system in keymaps.SYSTEMS:
        for version in keymaps.VERSIONS:
            own = keymaps.resolve(None, version, system)
            alt = keymaps.resolve("alternative", version, system)
            for command, key in alt.items():
                assert not keymaps.needs_alternative(key), (system, version, command, key)
                if not keymaps.needs_alternative(own.get(command, "")):
                    assert key == own.get(command, ""), (system, version, command)
    windows = keymaps.resolve("alternative", "desktop", "windows")
    assert windows["wikipedia.open"] == "Alt+Shift+W" and windows["history.back"] == "Ctrl+Shift+Left"
    assert keymaps.resolve("alternative", "web", "windows")["focus.menu"] == "Ctrl+F2"
    assert keymaps.resolve("alternative", "desktop", "mac")["settings.open"] == "Shift+Cmd+X"


def test_every_alternative_key_is_used_somewhere():
    used = {c for s in keymaps.SYSTEMS for v in keymaps.VERSIONS
            for c, k in keymaps.resolve("alternative", v, s).items() if k != keymaps.resolve(None, v, s).get(c)}
    assert used == set(keymaps.own_keys("alternative"))


def test_needs_alternative():
    assert keymaps.needs_alternative("Ctrl+Alt+W") and keymaps.needs_alternative("Alt+,")
    assert keymaps.needs_alternative("Ctrl+Alt+5")
    assert not keymaps.needs_alternative("Shift+5") and not keymaps.needs_alternative("Ctrl+Shift+Left")
    assert not keymaps.needs_alternative("Alt+Shift+W") and not keymaps.needs_alternative("")


def test_the_key_map_for_each_system_and_version():
    assert keymaps.default_keymap("windows", "desktop") == "windows-desktop"
    assert keymaps.default_keymap("mac", "desktop") == "mac-desktop"
    assert keymaps.default_keymap("windows", "web") == "windows-browser"
    assert keymaps.default_keymap("mac", "web") == "mac-browser"
    assert keymaps.default_keymap("linux", "desktop") == "windows-desktop"
    assert keymaps.default_keymap("windows", "desktop", layout="de-DE") == "windows-desktop"   # not detected yet


def test_a_key_map_from_the_other_version_is_this_versions_for_the_same_system():
    assert keymaps.for_version("windows-desktop", "web", "windows") == "windows-browser"
    assert keymaps.for_version("mac-browser", "desktop", "windows") == "mac-desktop"
    assert keymaps.for_version("alternative", "web", "mac") == "alternative"
    assert keymaps.for_version(None, "web", "mac") == "mac-browser"
    assert keymaps.for_version("nonsense", "desktop", "windows") == "windows-desktop"


def test_the_choices_in_each_version():
    assert keymaps.choices("desktop") == ["windows-desktop", "mac-desktop", "alternative"]
    assert keymaps.choices("web") == ["windows-browser", "mac-browser", "alternative"]


# Your keys -------------------------------------------------------------------------------------------

def test_your_keys_are_changes_on_top_never_a_full_copy(make):
    s = make()
    assert s.settings.keymap == "windows-desktop" and s.settings.keys == {}
    s.run("keys.remap", command="where.heading", key="G")
    assert s.settings.keys == {"where.heading": "G"}
    assert s.save()["settings"]["keymap"] == "windows-desktop"
    assert s.keys()["where.heading"] == "G" and s.keys()["where.coordinates"] == "C"
    assert s.press("G") is not None and s.press("H") is None
    s.run("keys.remap", command="where.heading", key="H")   # back to the key map's own: not kept
    assert s.settings.keys == {}


def test_a_key_added_to_the_key_map_still_reaches_you(make, monkeypatch):
    s = make(settings={"keys": {"where.heading": "G"}, "keymap": "windows-desktop"})
    real = keymaps._resolved_for

    def with_a_new_key(name, version, system):
        return {**real(name, version, system), "help.about": "Ctrl+Shift+A"}

    monkeypatch.setattr(keymaps, "_resolved_for", with_a_new_key)
    assert s.keys()["help.about"] == "Ctrl+Shift+A" and s.keys()["where.heading"] == "G"


def test_keys_changed_before_key_maps_carry_over_on_windows(make):
    """Settings saved before key maps have "keys" and no "keymap": the key map for the system is picked,
    and every changed key stays, in both versions."""
    old = {"values": {}, "keys": {"where.heading": "G", "sound.mute": "", "search.open": "Ctrl+Shift+K"}}
    for platform in ("desktop", "web"):
        s = make(platform=platform, settings=json.loads(json.dumps(old)))
        assert s.settings.keymap == ("windows-desktop" if platform == "desktop" else "windows-browser")
        assert s.settings.keys == old["keys"]
        keys = s.keys()
        assert keys["where.heading"] == "G" and keys["sound.mute"] == "" and keys["search.open"] == "Ctrl+Shift+K"
        assert s.command_for_key("Ctrl+M") is None and s.command_for_key("G").name == "where.heading"


def test_keys_changed_before_key_maps_carry_over_on_a_mac(make):
    """The Mac desktop called Command "Ctrl" before key maps, so those keys become Cmd keys; the Mac
    browser called the Control key "Ctrl", as now, so they stay."""
    old = {"keys": {"where.heading": "Ctrl+J", "zoom.in": "Z"}}
    desktop = make(platform="desktop", system="mac", settings=json.loads(json.dumps(old)))
    assert desktop.settings.keymap == "mac-desktop"
    assert desktop.settings.keys == {"where.heading": "Cmd+J", "zoom.in": "Z"}
    web = make(platform="web", system="mac", settings=json.loads(json.dumps(old)))
    assert web.settings.keymap == "mac-browser" and web.settings.keys == old["keys"]
    # Once the key map is saved, they are never turned again.
    again = make(platform="desktop", system="mac", settings=desktop.save()["settings"])
    assert again.settings.keys == {"where.heading": "Cmd+J", "zoom.in": "Z"}


def test_a_mac_session_uses_the_mac_keys_and_says_them_the_mac_way(make):
    s = make(platform="desktop", system="mac")
    assert s.command_for_key("Cmd+F").name == "search.open" and s.command_for_key("Ctrl+F") is None
    reg = s.registry()
    assert reg["keymap"]["global"]["Shift+Cmd+F"] == "browse.open"
    items = {i["name"]: i for m in reg["menus"] for i in m["items"]}
    assert items["browse.open"]["key_text"] == "Shift+Command+F"
    assert items["turn.fine_left"]["key_text"] == "Option+Left"
    assert items["sound.mute"]["key_text"] == "Control+M"
    assert items["settings.open"]["key_text"] == "Command+Comma"
    assert "Search: Command+F" in s.press("F1", "map").dialog["text"]


def test_choose_a_key_map_keeps_your_keys_on_top(make):
    s = make()
    s.run("keys.remap", command="where.heading", key="G")
    assert [c["id"] for c in s.keymap_choices()] == ["windows-desktop", "mac-desktop", "alternative"]
    assert s.keymap_choices()[0] == {"id": "windows-desktop", "label": "Windows desktop", "chosen": True}
    assert s.choose_keymap("alternative")
    assert s.settings.keymap == "alternative" and s.settings.keys == {"where.heading": "G"}
    assert s.keys()["wikipedia.open"] == "Alt+Shift+W" and s.keys()["where.heading"] == "G"
    assert not s.choose_keymap("nonsense") and s.settings.keymap == "alternative"


def test_choosing_a_key_map_drops_your_keys_that_are_now_its_own(make):
    s = make(settings={"keys": {"wikipedia.open": "Alt+Shift+W"}})
    assert s.settings.keys == {"wikipedia.open": "Alt+Shift+W"}
    s.choose_keymap("alternative")
    assert s.settings.keys == {}


def test_reset_gives_back_the_key_maps_own_keys(make):
    s = make()
    s.choose_keymap("alternative")
    s.run("keys.remap", command="where.heading", key="G")
    s.reset_keys()
    assert s.settings.keys == {} and s.settings.keymap == "alternative"
    assert s.keys() == keymaps.resolve("alternative", "desktop", "windows")


def test_the_keys_tab_shows_the_key_maps_own_key_as_the_default(make):
    s = make(system="mac")
    s.run("keys.remap", command="search.open", key="Shift+Cmd+K")
    row = next(r for r in s.key_table() if r["name"] == "search.open")
    assert row["key"] == "Shift+Cmd+K" and row["default"] == "Cmd+F" and row["key_text"] == "Shift+Command+K"


def test_reset_all_settings_picks_the_key_map_for_the_system_again(make):
    s = make(system="mac")
    s.choose_keymap("alternative")
    s.run("settings.reset_confirm")
    assert s.system == "mac" and s.settings.keymap == "mac-desktop"


# Key files -------------------------------------------------------------------------------------------

def test_a_key_file_says_its_key_map_and_holds_only_your_keys(make):
    s = make()
    s.run("keys.remap", command="where.heading", key="G")
    data = json.loads(s.key_file())
    assert data == {"kind": "TobyMap key file", "format": 1, "based_on": "windows-desktop",
                    "keys": {"where.heading": "G"}}


def test_a_key_file_opens_in_the_other_version(make):
    desktop = make()
    desktop.choose_keymap("alternative")
    desktop.run("keys.remap", command="where.heading", key="G")
    web = make(platform="web")
    web.open_key_file(desktop.key_file())
    assert web.settings.keymap == "alternative" and web.settings.keys == {"where.heading": "G"}
    windows = make(platform="web")
    windows.open_key_file(keymaps.key_file_text("windows-desktop", {"zoom.in": "Z"}))
    assert windows.settings.keymap == "windows-browser" and windows.keys()["zoom.in"] == "Z"


@pytest.mark.parametrize("text", [
    "", "not json", "[]", json.dumps({"based_on": "windows-desktop", "keys": {}}),
    json.dumps({"kind": "TobyMap key file", "format": 1, "based_on": "nonsense", "keys": {}}),
    json.dumps({"kind": "TobyMap key file", "format": 1, "based_on": "windows-desktop", "keys": {"zoom.in": "Shift+Ctrl+Z"}}),
    json.dumps({"kind": "TobyMap key file", "format": 1, "based_on": "windows-desktop", "keys": {"zoom.in": 5}}),
])
def test_a_file_that_is_not_a_key_file_changes_nothing(make, text):
    s = make()
    s.run("keys.remap", command="where.heading", key="G")
    with pytest.raises(ValueError):
        s.open_key_file(text)
    assert s.settings.keymap == "windows-desktop" and s.settings.keys == {"where.heading": "G"}


def test_read_key_file_round_trip():
    text = keymaps.key_file_text("mac-browser", {"zoom.in": "Z", "where.heading": ""})
    assert keymaps.read_key_file(text) == ("mac-browser", {"where.heading": "", "zoom.in": "Z"})
