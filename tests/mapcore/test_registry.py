"""The command registry is the one source of keys, menus and help (AD-3, SCP-2, ACC-4)."""
from collections import Counter

from mapcore.commands import registry
from mapcore.session import MapSession

REGIONS = {"map", "global"}
PLATFORMS = {"desktop", "web"}


def test_every_command_has_a_key_or_a_menu_entry():
    # Pointer commands come from a mouse click or a tree selection, which
    # always have a keyboard route of their own (moving, or the tree keys).
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
    banned = {"Insert", "Caps Lock", "Ctrl+Alt+N", "Ctrl+L", "Ctrl+T", "Ctrl+W", "Ctrl+N", "Ctrl+R", "F5",
              "F6", "F7", "F11", "F12", "Alt+F4", "Tab", "Shift+Tab", "Escape", "Ctrl+Tab"}
    for cmd in registry.load():
        assert cmd.key not in banned, cmd.name


def test_every_command_has_a_handler_in_the_session():
    session = MapSession()
    for cmd in registry.load():
        assert session.handles(cmd.name), cmd.name


def test_menu_access_letters_are_in_the_label_and_unique():
    # Alt+letter opens a desktop menu (PO feedback on spike S5: Alt+H for Help).
    menus = registry.menus("desktop")
    letters = [m["access"] for m in menus]
    assert letters == ["M", "S", "H"]
    assert len(set(letters)) == len(letters)
    for m in menus:
        assert m["access"].lower() in m["label"].lower()


def test_keymap_and_menus_for_a_platform():
    keymap = registry.keymap("web")
    assert keymap["map"]["Up"] == "globe.north"
    assert keymap["global"]["F1"] == "help.keys"
    menus = registry.menus("web")
    assert [m["label"] for m in menus] == ["Map", "Speech", "Help"]
    assert all(i["name"] != "app.exit" for m in menus for i in m["items"])
    desktop_items = [i["name"] for m in registry.menus("desktop") for i in m["items"]]
    assert "app.exit" in desktop_items
