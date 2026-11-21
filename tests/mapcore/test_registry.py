"""The command registry is the one source of keys, menus and help (AD-3, SCP-2, ACC-3, ACC-4)."""
from collections import Counter

import pytest
import yaml
from pathlib import Path

from mapcore.commands import keys as keymaps
from mapcore.commands import registry
from mapcore.session import MapSession

REGIONS = {"map", "panel", "details", "global"}
PLATFORMS = {"desktop", "web"}
FORBIDDEN = yaml.safe_load((Path(__file__).resolve().parents[1] / "data" / "forbidden_keys.yaml").read_text())


@pytest.fixture(scope="module")
def session(test_pack):
    return MapSession(packs=[test_pack])


def test_every_command_has_a_key_or_a_menu_entry():
    # Pointer commands come from the mouse, touch or a list, which have keyboard routes of their own.
    # Checked in every key map, for each system and version (P3-T31a).
    for name in keymaps.KEYMAPS:
        for system in keymaps.SYSTEMS:
            for platform in PLATFORMS:
                keys = keymaps.resolve(name, platform, system)
                for cmd in registry.for_platform(platform):
                    assert keys.get(cmd.name) or cmd.menu or cmd.pointer, (name, system, platform, cmd.name)


def test_the_command_list_holds_no_keys():
    """The keys are in the key maps; the command list keeps the commands, where each works and its menu."""
    raw = yaml.safe_load(registry.REGISTRY_FILE.read_text(encoding="utf-8"))
    assert not [c["name"] for c in raw["commands"] if "key" in c]


def test_every_command_has_a_label_region_and_platforms():
    for cmd in registry.load():
        assert cmd.label, cmd.name
        assert cmd.region in REGIONS, cmd.name
        assert set(cmd.platforms) <= PLATFORMS and cmd.platforms, cmd.name


def test_each_command_is_in_the_command_list_once():
    names = [c.name for c in registry.load()]
    assert len(names) == len(set(names))


def _all_keys():
    """Every key map's keys for each system and version: (key map, system, platform, {command: key})."""
    for name in keymaps.KEYMAPS:
        for system in keymaps.SYSTEMS:
            for platform in PLATFORMS:
                yield name, system, platform, keymaps.resolve(name, platform, system)


def test_no_key_is_used_twice_where_it_can_clash():
    for name, system, platform, keys in _all_keys():
        mine = [(c, keys[c.name]) for c in registry.for_platform(platform) if keys.get(c.name)]
        globals_ = {k for c, k in mine if c.region == "global"}
        for region in REGIONS:
            counts = Counter(k for c, k in mine if c.region == region)
            assert all(n == 1 for n in counts.values()), (name, system, platform, region, counts)
        for c, k in mine:
            if c.region != "global":
                assert k not in globals_, (name, system, platform, c.name)


def test_keys_use_the_shared_key_names():
    for name, system, platform, keys in _all_keys():
        for command, key in keys.items():
            if key:
                assert registry.valid_key(key), (name, command, key)
    for name in keymaps.KEYMAPS:   # as written in the files too, so a Mac key map's own keys are in order
        for command, key in keymaps.own_keys(name).items():
            assert not key or registry.valid_key(key), (name, command, key)


def test_every_command_in_a_key_map_is_in_the_command_list():
    names = {c.name for c in registry.load()}
    for name in keymaps.KEYMAPS:
        assert set(keymaps.own_keys(name)) <= names, (name, set(keymaps.own_keys(name)) - names)


def test_no_default_key_is_a_screen_reader_or_browser_key():
    """The Windows key maps, and Alternative on Windows: ACC-4's list, in each version."""
    for name in (keymaps.WINDOWS_DESKTOP, keymaps.WINDOWS_BROWSER, keymaps.ALTERNATIVE):
        for platform in PLATFORMS:
            keys = keymaps.resolve(name, platform, "windows")
            banned = set(FORBIDDEN["exact"]) | (set(FORBIDDEN["web_only"]) if platform == "web" else set())
            for cmd in registry.for_platform(platform):
                key = keys.get(cmd.name, "")
                assert key not in banned, (name, cmd.name)
                if key:
                    parts = key.split("+")
                    assert not set(parts) & set(FORBIDDEN["no_modifier_words"]), (name, cmd.name)
                    if FORBIDDEN["digits_with_ctrl"] and parts[0] == "Ctrl" and parts[-1].isdigit():
                        pytest.fail(f"{cmd.name} uses {key}, a browser tab key")


def test_no_mac_key_is_a_macos_voiceover_or_browser_key():
    """The Mac key maps, and Alternative on a Mac: macOS's and VoiceOver's keys, Option with a character, and
    in the browser the browser's keys (P3-T31a)."""
    mac = FORBIDDEN["mac"]
    for name in (keymaps.MAC_DESKTOP, keymaps.MAC_BROWSER, keymaps.ALTERNATIVE):
        for platform in PLATFORMS:
            keys = keymaps.resolve(name, platform, "mac")
            banned = set(mac["exact"]) | (set(mac["browser"]) if platform == "web" else set())
            for cmd in registry.for_platform(platform):
                key = keys.get(cmd.name, "")
                if not key:
                    continue
                mods, base = registry.split_key(key)
                assert key not in banned, (name, platform, cmd.name, key)
                assert not ("Ctrl" in mods and "Alt" in mods), (name, cmd.name, key)
                assert not ("Alt" in mods and len(base) == 1), (name, cmd.name, key)
                if platform == "web" and "Cmd" in mods and base.isdigit():
                    pytest.fail(f"{cmd.name} uses {key}, a browser tab key")


def test_every_command_has_a_handler_in_the_session(session):
    for cmd in registry.load():
        assert session.handles(cmd.name), cmd.name


def test_the_phase_1_keys_are_there():
    desktop = registry.keymap("desktop")
    expected = {"Up": "move.north", "Down": "move.south", "Left": "move.west", "Right": "move.east",
                "Page Up": "zoom.out", "Page Down": "zoom.in", "Shift+Page Up": "step.larger",
                "Shift+Page Down": "step.smaller", "Space": "where.am_i", "C": "where.coordinates",
                "H": "where.heading", "V": "where.visible"}
    for key, name in expected.items():
        assert desktop["map"][key] == name
    for key, name in {"F1": "help.keys", "Shift+F1": "help.describer", "F2": "focus.map", "F3": "focus.panel",
                      "F4": "focus.details", "Shift+Space": "speech.repeat", "Ctrl+Shift+Space": "history.list",
                      "Ctrl+M": "sound.mute", "Ctrl+,": "settings.open"}.items():
        assert desktop["global"][key] == name
    assert registry.keymap("web")["global"]["Ctrl+Alt+M"] == "focus.menu"
    assert "Ctrl+Alt+M" not in desktop["global"]


def test_the_dropped_keys_are_gone():
    # DP106: D, R and Ctrl+Alt+Space are dropped (Shift+Space was dropped as the Within key, and is now the repeat key); DP113: no copy of the coordinates.
    # DP219 brings Ctrl+C back for one thing only, copying the bookmark that is the current feature (P4-T8d), on the
    # map and in the Information panel: never global and never in Details, whose text it still copies.
    for platform in PLATFORMS:
        keymap = registry.keymap(platform)
        keys = {k for region in keymap.values() for k in region}
        assert not keys & {"D", "R", "Ctrl+Alt+Space"}
        assert {region: names.get("Ctrl+C") for region, names in keymap.items() if "Ctrl+C" in names} == {
            "map": "bookmark.copy", "panel": "panel.bookmark_copy"}


def test_menu_access_letters_are_in_the_label_and_unique():
    menus = registry.menus("desktop")
    letters = [m["access"] for m in menus]
    assert len(set(letters)) == len(letters)
    for m in menus:
        assert m["access"].lower() in m["label"].lower()


def test_keymap_and_menus_for_a_platform():
    menus = registry.menus("web")
    assert [m["label"] for m in menus] == ["Map", "Speech", "Settings", "Help"]
    assert all(i["name"] != "app.exit" for m in menus for i in m["items"])
    desktop_items = [i["name"] for m in registry.menus("desktop") for i in m["items"]]
    assert "app.exit" in desktop_items


def test_held_and_latest_only_commands_are_the_four_moves():
    assert sorted(registry.held_keys("desktop")) == ["move.east", "move.north", "move.south", "move.west"]
    assert sorted(registry.latest_only("web")) == sorted(registry.held_keys("web"))


def test_changed_keys_replace_the_default():
    overrides = {"where.heading": "G"}
    assert registry.keymap("desktop", overrides)["map"]["G"] == "where.heading"
    assert "H" not in registry.keymap("desktop", overrides)["map"]
    assert registry.command_for_key("desktop", "G", "map", overrides).name == "where.heading"
    assert registry.command_for_key("desktop", "G", "panel", overrides) is None  # map keys need the map
    assert registry.command_for_key("desktop", "F3", "panel").name == "focus.panel"


def test_a_clash_names_the_command_that_has_the_key():
    assert registry.clash("desktop", "where.heading", "C").name == "where.coordinates"
    assert registry.clash("desktop", "where.heading", "F2").name == "focus.map"
    assert registry.clash("desktop", "where.heading", "Ctrl+Q") is None
    assert registry.clash("desktop", "where.heading", "H") is None  # its own key
