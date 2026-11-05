"""The layer catalogue (P2-T3a; SCP-6, SCP-7, LOC-6).

A layer that is off is gone from "where am I", the announcements after a move,
Nearby and the map, and the choice is kept by layer id, through a restart and
a pack rebuild.
"""
import pytest

from mapcore.layers import LayerCatalogue
from mapcore.layers.catalogue import from_definition
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}
CALAIS = (50.6, 2.2)          # Pas-de-Calais, Hauts-de-France, France
ATLANTIC = (45.0, -30.0)


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def regions(session) -> set:
    return {a.id for a in session.store.at(*CALAIS) if a.layer == "regions"} | \
           {a.id for a in session.store.at(KENT["lat"], KENT["lon"]) if a.layer == "regions"}


# The catalogue ---------------------------------------------------------------

class _Pack:
    def __init__(self, layers):
        self.layers = layers


def test_the_catalogue_comes_from_the_packs_layer_definitions(session):
    layers = session.layers.layers()
    assert [layer.id for layer in layers] == ["countries", "oceans", "regions", "counties"]
    countries = session.layers.get("countries")
    assert countries.name == "Countries" and countries.group == "Boundaries" and countries.geometry == "area"
    assert countries.on and countries.in_zoom(5000) and countries.in_zoom(10_000_000)
    assert [g for g, _ in session.layers.groups()] == ["Boundaries", "Water"]


def test_an_old_pack_with_only_ids_and_names_gets_the_defaults():
    layer = from_definition({"id": "regions", "name": "Regions"})
    assert layer.on and layer.geometry == "area" and layer.min_size == 0.02
    assert layer.min_zoom_m == 0 and layer.max_zoom_m is None and layer.crossing_earcon is None


def test_the_first_packs_definition_wins_and_off_by_default_is_kept():
    changes = {}
    cat = LayerCatalogue([_Pack([{"id": "graticule", "name": "Lines", "switched_on": False}]),
                          _Pack([{"id": "graticule", "name": "Other", "switched_on": True}])], lambda: changes)
    assert cat.get("graticule").name == "Lines" and not cat.get("graticule").on
    assert cat.active() == frozenset()


def test_a_change_back_to_the_packs_value_is_forgotten():
    changes = {}
    cat = LayerCatalogue([_Pack([{"id": "regions", "name": "Regions"}])], lambda: changes)
    cat.change("regions", "on", False)
    assert changes == {"regions": {"on": False}} and cat.get("regions").changed == ("on",)
    cat.change("regions", "on", True)
    assert changes == {}


def test_bad_changes_are_refused():
    changes = {}
    cat = LayerCatalogue([_Pack([{"id": "regions", "name": "Regions"}])], lambda: changes)
    for layer, field, value in [("nowhere", "on", False), ("regions", "on", "no"), ("regions", "name", "X"),
                                ("regions", "min_zoom_m", -1), ("regions", "crossing_earcon", "trumpet")]:
        with pytest.raises(ValueError):
            cat.change(layer, field, value)
    cat.change("regions", "max_zoom_m", 1000)
    with pytest.raises(ValueError):
        cat.change("regions", "min_zoom_m", 5000)   # closer than the farthest zoom
    assert changes == {"regions": {"max_zoom_m": 1000.0}}


def test_a_damaged_saved_change_is_left_out():
    changes = {"regions": {"on": "perhaps", "crossing_earcon": "line_crossing"}}
    cat = LayerCatalogue([_Pack([{"id": "regions", "name": "Regions"}])], lambda: changes)
    assert cat.get("regions").on and cat.get("regions").crossing_earcon == "line_crossing"


def test_changing_one_layers_crossing_earcon_changes_that_layer_only(session):
    assert spoken(session.run("layers.set", layer="regions", field="crossing_earcon", value="line_crossing")) == []
    assert session.layers.get("regions").crossing_earcon == "line_crossing"
    assert all(layer.crossing_earcon is None for layer in session.layers.layers() if layer.id != "regions")


# A layer that is off is gone (SCP-6) -----------------------------------------------

def test_with_regions_off_where_am_i_leaves_the_region_out(session):
    assert spoken(session.press("Space")) == ["Kent, England, United Kingdom"]
    r = session.run("layers.set", layer="regions", field="on", value=False)
    assert r.redraw and r.panel_stale and r.settings_changed and spoken(r) == []
    assert spoken(session.press("Space")) == ["Kent, United Kingdom"]
    session.run("layers.set", layer="regions", field="on", value=True)
    assert spoken(session.press("Space")) == ["Kent, England, United Kingdom"]


def test_with_regions_off_crossing_to_france_says_nothing_about_the_region(session):
    session.run("layers.set", layer="regions", field="on", value=False)
    session.world.lat, session.world.lon = CALAIS
    r = session._arrived(session._moved())
    assert spoken(r) == ["Pas-de-Calais, France"]


def test_with_regions_off_the_map_draws_no_region(session):
    ids = regions(session)
    assert ids, "the test pack has regions here"
    session.world.zoom_index = session.world.zoom_list.index(250000)
    assert ids & set(session.scene(800, 600)["shape_area"])
    session.run("layers.set", layer="regions", field="on", value=False)
    assert not ids & set(session.scene(800, 600)["shape_area"])
    session.run("layers.set", layer="regions", field="on", value=True)
    assert ids & set(session.scene(800, 600)["shape_area"])


def test_with_countries_off_nearby_leaves_france_out(session):
    def nearby():
        return [i["label"] for g in session.panel() if g["id"] == "nearby" for i in g["items"]]
    assert any(label.startswith("France") for label in nearby())
    session.run("layers.set", layer="countries", field="on", value=False)
    assert not any(label.startswith("France") for label in nearby())
    assert any(label.startswith("Pas-de-Calais") for label in nearby())


def test_with_oceans_off_a_point_in_the_atlantic_says_every_layer_is_off(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT, lat=ATLANTIC[0], lon=ATLANTIC[1]))
    assert spoken(s.start()) == ["TobyMap. North Atlantic Ocean. Press F1 for keys."]
    s.run("layers.set", layer="oceans", field="on", value=False)
    assert spoken(s.press("Space")) == ["Every layer here is switched off"]
    s.run("layers.set", layer="oceans", field="on", value=True)
    assert spoken(s.press("Space")) == ["North Atlantic Ocean"]
    s.store.close()


def test_stepping_into_a_place_where_every_layer_is_off_says_so(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT, lat=ATLANTIC[0], lon=ATLANTIC[1] - 0.3))
    s.start()
    s.run("layers.set", layer="oceans", field="on", value=False)
    s.areas = [s.store.at(*ATLANTIC)[0]]   # as if the last place had the ocean
    s.world.lat, s.world.lon = ATLANTIC
    assert spoken(s._arrived(s._moved())) == ["Every layer here is switched off"]
    s.store.close()


def test_a_layer_switched_off_stays_off_after_a_restart(test_pack, session):
    session.run("layers.set", layer="regions", field="on", value=False)
    saved = session.save()
    assert saved["settings"]["layers"] == {"regions": {"on": False}}
    again = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    assert spoken(again.start()) == ["TobyMap. Kent, United Kingdom. Press F1 for keys."]
    again.store.close()


def test_a_layer_switched_off_stays_off_with_a_rebuilt_pack(test_pack, tmp_path):
    """The choice is kept by layer id, so a pack built again, with new feature numbers, follows it."""
    import shutil

    from mapcore.packs.pack import checksum_path

    copy = tmp_path / "rebuilt.pack"
    shutil.copyfile(test_pack, copy)
    if checksum_path(test_pack).exists():
        shutil.copyfile(checksum_path(test_pack), checksum_path(copy))
    s = MapSession(packs=[copy], settings={"layers": {"regions": {"on": False}}}, saved_state=dict(KENT))
    assert spoken(s.start()) == ["TobyMap. Kent, United Kingdom. Press F1 for keys."]
    s.store.close()


def test_the_layers_list_for_the_shells(session):
    session.run("layers.set", layer="oceans", field="on", value=False)
    data = session.layer_list()
    assert data["title"] == "Layers"
    assert [(g["name"], [layer["id"] for layer in g["layers"]]) for g in data["groups"]] == [
        ("Boundaries", ["countries", "regions", "counties"]), ("Water", ["oceans"])]
    oceans = data["groups"][1]["layers"][0]
    assert oceans["name"] == "Oceans and seas" and oceans["on"] is False and oceans["changed"] == ["on"]


def test_a_bad_layer_change_says_the_value_cannot_be_used(session):
    assert spoken(session.run("layers.set", layer="nowhere", field="on", value=False)) == [
        "That value cannot be used for this setting."]
