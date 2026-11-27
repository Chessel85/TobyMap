"""The pack manager and the world pack's offer at the first start (P4-T6d; PCK-2, PCK-4, PCK-5, ACC-7).
The catalogue's text is handed in, as a shell does: the core never touches the network."""
import json

import pytest

from mapcore.commands import keys as keymaps
from mapcore.commands import registry
from mapcore.session import MapSession

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 100000, "step_m": 1000}
SHA = "a" * 64


def entry(name, version="2026.11.1", size=552_000_000, **change):
    raw = {"name": name, "version": version, "date": "2026-11-20", "size": size, "sha256": SHA,
           "url_desktop": f"https://example.org/{name}.pack", "url_web": f"https://example.org/w/{name}.pack",
           "app_versions": {"from": "0.1.0"}}
    raw.update(change)
    return raw


def text(*entries):
    return json.dumps({"format": 1, "packs": list(entries)})


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


@pytest.fixture
def bare():
    s = MapSession(packs=[], saved_state=dict(HAMPSHIRE))
    s.start()
    return s


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


def test_p_opens_the_pack_manager_from_the_map_menu():
    assert registry.default_key("packs.manager_open") == "P"
    assert registry.by_name("packs.manager_open").menu == "Map"
    for version in ("desktop", "browser"):
        assert keymaps.resolve(None, version, "windows")["packs.manager_open"] == "P"
        assert keymaps.resolve(None, version, "mac")["packs.manager_open"] == "P"


def test_the_dialog_lists_installed_packs_until_the_catalogue_comes(s):
    d = s.run("packs.manager_open").dialog
    assert d["kind"] == "pack_manager" and d["title"] == "Pack manager"
    assert d["words"]["close"] == "Close"
    assert [w for w in ("install", "update", "remove") if w not in d["words"]] == []
    assert d["catalogue_urls"]["desktop"].startswith("https://github.com/Chessel85/TobyMap/releases/download/")
    (item,) = d["lines"]["items"]
    assert item["remove"] and not item["install"] and not item["update"]


def test_each_line_has_name_size_date_and_state_and_the_buttons_follow_the_state(s):
    version = s.store.packs[0].manifest["version"]
    name = s.store.packs[0].manifest["name"]
    s.run("packs.manager_open")
    r = s.run("packs.manager_listing", text=text(
        entry("world", title="World"), entry(name, version="9999.1.1", size=1_500_001, title="Local"),
        entry("extra", version="2026.11.1", size=2_000_000)))
    items = r.pack_manager["items"]
    by = {i["name"]: i for i in items}
    assert by["world"]["label"] == "World, 552 megabytes, 2026-11-20, not installed"
    assert by["world"]["install"] and not by["world"]["update"] and not by["world"]["remove"]
    assert by[name]["label"] == "Local, 2 megabytes, 2026-11-20, update available"
    assert by[name]["update"] and by[name]["remove"] and not by[name]["install"]
    assert version != "9999.1.1"


def test_an_installed_pack_that_is_current_can_only_be_removed(s):
    p = s.store.packs[0]
    s.run("packs.manager_open")
    r = s.run("packs.manager_listing", text=text(entry(p.manifest["name"], version=p.manifest["version"])))
    (item,) = r.pack_manager["items"]
    assert item["state"] == "installed" and item["label"].endswith("installed")
    assert item["remove"] and not item["install"] and not item["update"]


def test_a_pack_in_use_that_the_catalogue_does_not_list_is_still_shown_and_removable(s):
    s.run("packs.manager_open")
    r = s.run("packs.manager_listing", text=text(entry("world")))
    names = [i["name"] for i in r.pack_manager["items"]]
    assert names == ["world", s.store.packs[0].manifest["name"]]
    assert r.pack_manager["items"][1]["remove"]


def test_an_unreadable_catalogue_is_said_and_installed_packs_are_shown(s):
    s.run("packs.manager_open")
    r = s.run("packs.manager_listing", failed=True)
    assert "could not be read" in said(r) and "Only the packs you have installed" in said(r)
    assert len(r.pack_manager["items"]) == 1
    r = s.run("packs.manager_listing", text="not json")
    assert "could not be read" in said(r) and len(r.pack_manager["items"]) == 1
    r = s.run("packs.manager_listing", unset=True)
    assert "no list of packs for this version yet" in said(r)


def test_install_hands_the_entry_to_the_shell(bare):
    bare.run("packs.manager_open")
    r = bare.run("packs.manager_listing", text=text(entry("world", title="World")))
    r = bare.run("packs.manager_install", index=0)
    assert r.install["update"] is False and r.install["entry"]["name"] == "world"
    assert not r.announcements


def test_an_incompatible_pack_is_refused_with_a_clear_message(bare):
    bare.run("packs.manager_open")
    bare.run("packs.manager_listing", text=text(entry("old", title="Old map", app_versions={"from": "99.0.0"})))
    r = bare.run("packs.manager_install", index=0)
    assert r.install is None
    assert said(r).startswith("Old map needs TobyMap 99.0.0 or later") and "was not downloaded" in said(r)
    bare.run("packs.manager_listing", text=text(entry("gone", title="Gone", app_versions={"from": "0.1.0", "before": "0.1.1"})))
    r = bare.run("packs.manager_install", index=0)
    assert r.install is None and "was made for versions of TobyMap before 0.1.1" in said(r)


def test_buttons_that_cannot_act_say_why(s):
    p = s.store.packs[0]
    s.run("packs.manager_open")
    s.run("packs.manager_listing", text=text(entry(p.manifest["name"], version=p.manifest["version"]), entry("world")))
    assert "already installed" in said(s.run("packs.manager_install", index=0))
    assert "has no update" in said(s.run("packs.manager_update", index=0))
    assert "nothing to remove" in said(s.run("packs.manager_remove", index=1))
    assert "Choose a pack" in said(s.run("packs.manager_install", index=9))


def test_update_hands_the_entry_with_update_set(s):
    name = s.store.packs[0].manifest["name"]
    s.run("packs.manager_open")
    s.run("packs.manager_listing", text=text(entry(name, version="9999.1.1")))
    r = s.run("packs.manager_update", index=0)
    assert r.install == {"entry": r.install["entry"], "update": True}


def test_remove_asks_then_takes_the_pack_out_of_use_and_names_its_file(s):
    file = s.store.packs[0].name
    s.run("packs.manager_open")
    d = s.run("packs.manager_remove", index=0).dialog
    assert d["kind"] == "confirm" and d["cancel"] == "Cancel" and d["submit"] == "packs.manager_remove_confirm"
    assert s.store.packs   # nothing changes until it is answered
    r = s.run(d["submit"])
    assert r.remove_files == [file]
    assert not s.store.packs
    assert r.pack_manager["items"] == [] and r.pack_manager["none"].startswith("No packs are installed")
    assert said(r).endswith("is removed.")


def test_first_run_offers_the_world_pack_with_its_size(bare):
    assert bare.start().world_offer["catalogue_urls"]["desktop"].startswith("https:")
    r = bare.run("packs.first_run", text=text(entry("world", size=552_000_001)))
    d = r.dialog
    assert d["kind"] == "confirm" and d["ok"] == "Download" and d["cancel"] == "Not now"
    assert "553 megabytes" in d["text"] and "world pack" in d["text"]
    r = bare.run(d["submit"])
    assert r.install["entry"]["name"] == "world" and r.install["update"] is False


def test_first_run_with_the_world_pack_installed_offers_nothing(s, monkeypatch):
    monkeypatch.setattr("mapcore.pack_manager.WORLD", s.store.packs[0].manifest["name"])
    assert s.start().world_offer is None
    r = s.run("packs.first_run", text=text(entry("world")))
    assert r.dialog is None and not r.announcements


def test_a_session_with_a_pack_not_named_world_is_still_offered_the_world(s):
    assert s.start().world_offer


def test_first_run_without_a_readable_catalogue_says_how_to_get_one(bare):
    r = bare.run("packs.first_run", failed=True)
    assert r.dialog is None and "list of packs could not be read" in said(r) and "press P" in said(r)
    r = bare.run("packs.first_run", unset=True)
    assert "no list of packs for this version yet" in said(r)
    r = bare.run("packs.first_run", text=text(entry("other")))
    assert "does not include it" in said(r)


def test_first_run_does_not_offer_a_world_pack_this_version_cannot_use(bare):
    r = bare.run("packs.first_run", text=text(entry("world", title="World", app_versions={"from": "99.0.0"})))
    assert r.dialog is None and "needs TobyMap 99.0.0" in said(r)
