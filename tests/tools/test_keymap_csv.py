"""docs/design/keymap.csv is made from the key maps and the layout list, and is never out of date (P3-T31c)."""
from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def _tool():
    spec = importlib.util.spec_from_file_location("make_key_list", REPO / "tools" / "make_key_list.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_keymap_csv_is_up_to_date():
    tool = _tool()
    current = tool.OUT.read_bytes().decode("utf-8")
    assert current == tool.csv_text(), "docs/design/keymap.csv is out of date: run tools/make_key_list.py"


def test_keymap_csv_format_and_columns():
    data = (REPO / "docs" / "design" / "keymap.csv").read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in data.replace(b"\r\n", b"")
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
    assert rows[0] == ["Command", "Where it works", "Windows desktop", "Mac desktop", "Windows browser",
                       "Mac browser", "Variations", "Notes on the variations"]
    assert all(len(r) == 8 and all(c.strip() for c in r) for r in rows)


def test_every_command_has_a_row():
    tool = _tool()
    registry = yaml.safe_load(tool.REGISTRY.read_text(encoding="utf-8"))
    labels = {r[0] for r in tool.rows()}
    for c in registry["commands"]:
        if c["name"] != "panel.group":
            assert c["label"] in labels, c["name"]
    assert {"Go to Within", "Go to Passed over", "Go to Search"} <= labels


def test_layouts_file_has_the_agreed_layouts():
    names = " | ".join(l["name"] for l in _tool().layouts())
    for word in ("UK", "US International", "German", "French", "Spanish", "Italian", "Nordic", "Polish", "Czech", "Mac"):
        assert word in names, word


def test_a_known_altgr_clash_is_found():
    rows = {r[0]: r for r in _tool().rows()}
    wikipedia = rows["Open the current feature's Wikipedia article"]
    assert "Czech" in wikipedia[6]
    assert "Alt+Shift+W" in wikipedia[7]
