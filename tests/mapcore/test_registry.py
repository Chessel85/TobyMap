"""The command registry is the one source of keys, menus and help (AD-3, SCP-2, ACC-3, ACC-4)."""
from collections import Counter

import pytest
import yaml
from pathlib import Path

from mapcore.commands import registry
from mapcore.session import MapSession

REGIONS = {"map", "global"}
PLATFORMS = {"desktop", "web"}
FORBIDDEN = yaml.safe_load((Path(__file__).resolve().parents[1] / "data" / "forbidden_keys.yaml").read_text())


@pytest.fixture(scope="module")
def session(test_pack):
    return MapSession(packs=[test_pack])


def test_every_command_has_a_key_or_a_menu_entry():
    # Pointer commands come from the mouse, touch or a list, which have keyboard routes of their own.
    for cmd in registry.load():
        assert cmd.key or cmd.menu or cmd.pointer, cmd.name


def test_every_command_has_a_label_region_and_platforms():
    for cmd in registry.load():
        assert cmd.label, cmd.name
        assert cmd.region in REGIONS, cmd.name
        assert set(cmd.platforms) <= PLATFORMS and cmd.platforms, cmd.name


def test_no_key_is_used_twice_where_it_can_clash():
    commands = registry.load()
    for platform in PLATFORMS:
        mine = [c for c in commands if platform in c.platforms and c.key]
        globals_ = {c.key for c in mine if c.region == "global"}
        for region in REGIONS:
            counts = Counter(c.key for c in mine if c.region == region)
            assert all(n == 1 for n in counts.values()), (platform, region, counts)
        for c in mine:
            if c.region != "global":
                assert c.key not in globals_, c.name


def test_keys_use_the_shared_key_names():
    for cmd in registry.load():
        if cmd.key:
            assert registry.valid_key(cmd.key), cmd.key


def test_no_default_key_is_a_screen_reader_or_browser_key():
    for cmd in registry.load():
        for platform in cmd.platforms:
            banned = set(FORBIDDEN["exact"]) | (set(FORBIDDEN["web_only"]) if platform == "web" else set())
            assert cmd.key not in banned, cmd.name
        if cmd.key:
            parts = cmd.key.split("+")
            assert not set(parts) & set(FORBIDDEN["no_modifier_words"]), cmd.name
            if FORBIDDEN["digits_with_ctrl"] and parts[0] == "Ctrl" and parts[-1].isdigit():
                pytest.fail(f"{cmd.name} uses {cmd.key}, a browser tab key")


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
                      "F4": "focus.details", "Ctrl+Space": "speech.repeat", "Ctrl+Shift+Space": "speech.history",
                      "Ctrl+M": "sound.mute", "Ctrl+,": "settings.open"}.items():
        assert desktop["global"][key] == name
    assert registry.keymap("web")["global"]["Ctrl+Alt+M"] == "focus.menu"
    assert "Ctrl+Alt+M" not in desktop["global"]


def test_the_dropped_keys_are_gone():
    # DP106: Shift+Space, D, R and Ctrl+Alt+Space are dropped; DP113: no copy of the coordinates.
    for platform in PLATFORMS:
        keys = {k for region in registry.keymap(platform).values() for k in region}
        assert not keys & {"Shift+Space", "D", "R", "Ctrl+Alt+Space", "Ctrl+C"}


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
