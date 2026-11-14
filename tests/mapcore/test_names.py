"""P3-T12: languages of names (ACC-9, DP172). The setting "Names" chooses the English name where there is one,
or always the local name, everywhere a name is said or shown (P3-T12a); names in another language are handed to
the shell with their language, for the web page to mark (P3-T12b)."""
import pytest

from mapcore import names
from mapcore.describe import say
from mapcore.session import MapSession
from mapcore.store.store import Area

GERMANY = {"lat": 48.0, "lon": 8.5, "zoom_m": 100000, "step_m": 10000}   # the Black Forest, in the Alps sample


@pytest.fixture
def s(test_pack):
    names.take()
    s = MapSession(packs=[test_pack], saved_state=dict(GERMANY))
    s.start()
    yield s
    s.store.close()


def where(s):
    return s.run("where.am_i").announcements[0]["text"]


# The rule, on records ----------------------------------------------------------------------------------

def rec(**kw):
    return {"id": "osm:r1", **kw}


def test_english_where_there_is_one_else_the_local_name():
    germany = rec(names={"en": "Germany", "local": "Deutschland"}, local_lang="de")
    assert names.name_of(germany) == "Germany" and names.name_of(germany).lang is None
    assert names.name_of(germany, "local") == "Deutschland" and names.name_of(germany, "local").lang == "de"


def test_a_place_with_no_english_name_is_said_by_its_local_name_in_its_language():
    # With no English name in OpenStreetMap, the pack's "en" holds the local name and there is no "local".
    kreis = rec(names={"en": "Kreis Pinneberg"}, local_lang="de")
    for choice in ("english", "local"):
        assert names.name_of(kreis, choice) == "Kreis Pinneberg" and names.name_of(kreis, choice).lang == "de"


def test_an_english_name_or_an_unknown_language_is_not_marked():
    assert names.name_of(rec(names={"en": "Hampshire"})).lang is None
    assert names.name_of(rec(names={"en": "Switzerland", "local": "Schweiz/Suisse"}), "local").lang is None
    assert names.name_of(rec(names={"en": "England"}, local_lang="en")).lang is None
    assert names.name_of(rec(names={})) == "osm:r1"


def test_the_language_of_an_osm_name():
    assert names.language_of_name({"name": "Deutschland", "name:de": "Deutschland", "name:fr": "Allemagne"}) == "de"
    assert names.language_of_name({"name": "England", "name:en": "England"}) == "en"
    # Italia is also Spanish, Romanian and more: the country's own default language decides.
    italia = {"name": "Italia", "name:it": "Italia", "name:es": "Italia", "name:ro": "Italia", "default_language": "it"}
    assert names.language_of_name(italia) == "it"
    # Or the language of its Wikipedia article, when the article has the same title.
    osterreich = {"name": "Österreich", "name:de": "Österreich", "name:als": "Österreich", "wikipedia": "de:Österreich"}
    assert names.language_of_name(osterreich) == "de"
    # Several languages and nothing to choose between them, or a name in four languages: not known.
    assert names.language_of_name({"name": "Italia", "name:it": "Italia", "name:es": "Italia"}) is None
    swiss = {"name": "Schweiz/Suisse/Svizzera/Svizra", "name:de": "Schweiz", "default_language": "de",
             "wikipedia": "de:Schweiz"}
    assert names.language_of_name(swiss) is None
    assert names.language_of_name({"name:de": "Bern"}) is None


def test_an_area_made_without_a_store_says_english():
    assert Area(0, 0, rec(names={"en": "Germany", "local": "Deutschland"})).name == "Germany"


# The setting, in the application --------------------------------------------------------------------------

def test_the_setting_is_in_the_speech_tab_english_at_first(s):
    speech = next(t for t in s.settings_schema()["tabs"] if t["id"] == "speech")
    field = next(f for f in speech["fields"] if f["id"] == "names")
    assert field["label"] == "Names" and field["default"] == "english"
    assert [c[0] for c in field["choices"]] == ["english", "local"]
    assert s.settings["names"] == "english"


def test_with_english_germany_is_germany_and_with_the_local_name_deutschland(s):
    assert "Germany" in where(s) and "Deutschland" not in where(s)
    r = s.run("settings.set", field="names", value="local")
    assert r.settings_changed and r.panel_stale and r.redraw
    assert "Deutschland" in where(s) and "Germany" not in where(s)
    s.run("settings.set", field="names", value="english")
    assert "Germany" in where(s)


def test_every_name_follows_the_setting_the_panel_and_the_map(s):
    s.run("settings.set", field="names", value="local")
    panel = s.panel()
    words = [i["label"] for g in panel for i in g["items"]]
    assert any("Deutschland" in w for w in words) and not any("Germany" in w for w in words), words
    shown = [n["text"] for n in s.scene(800, 600)["names"]]
    assert "Germany" not in shown


def test_the_world_tree_follows_the_setting(continents_pack):
    s = MapSession(packs=[continents_pack], saved_state=dict(GERMANY), settings={"values": {"names": "local"}})
    s.start()
    europe = next(i for i, n in s.store.tree_children("world") if n == "Europe")
    countries = [n for _i, n in s.store.tree_children(europe)]
    assert "Deutschland" in countries and "Germany" not in countries
    assert countries == sorted(countries, key=str.casefold)
    s.run("settings.set", field="names", value="english")
    assert "Germany" in [n for _i, n in s.store.tree_children(europe)]
    s.store.close()


def test_the_setting_is_kept_between_runs(s, test_pack):
    s.run("settings.set", field="names", value="local")
    saved = s.save()
    again = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    again.start()
    assert "Deutschland" in where(again)


def test_search_shows_the_local_name_with_the_local_setting(s):
    s.run("settings.set", field="names", value="local")
    found = s.search("germany")
    assert found and found[0]["label"].startswith("Deutschland"), found[:2]
    found = s.search("deutschland")
    assert found and found[0]["label"].startswith("Deutschland")


# Marking the language (P3-T12b) ---------------------------------------------------------------------------

def test_names_in_another_language_are_handed_to_the_shell_with_their_language(s):
    s.name_languages()
    s.run("settings.set", field="names", value="local")
    s.run("where.am_i")
    assert s.name_languages().get("Deutschland") == "de"
    assert s.name_languages() == {}   # each asking takes them


def test_english_names_are_not_handed_over(s):
    s.name_languages()
    s.run("where.am_i")
    assert "Germany" not in s.name_languages()


def test_say_notes_a_name_given_to_a_template():
    names.take()
    say("tree.leaf", name=names.Name("Österreich", "de"))
    assert names.take() == {"Österreich": "de"}
