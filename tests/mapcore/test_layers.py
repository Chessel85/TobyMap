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
    assert [layer.id for layer in layers] == ["countries", "oceans", "seas", "regions", "counties", "rivers", "lakes",
                                                   "stations"]
    countries = session.layers.get("countries")
    assert countries.name == "Countries" and countries.group == "Boundaries" and countries.geometry == "area"
    assert countries.on and countries.in_zoom(5000) and countries.in_zoom(10_000_000)
    assert [g for g, _ in session.layers.groups()] == ["Boundaries", "Water", "Transport"]


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
    assert all(layer.crossing_earcon is None for layer in session.layers.layers() if layer.id not in ("regions", "rivers"))   # the sample river has its own


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
    session.world.zoom_index = session.world.zoom_list.index(100000)   # Nearby searches within the zoom (NAV-13)

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
        ("Boundaries", ["countries", "regions", "counties"]), ("Water", ["oceans", "seas", "rivers", "lakes"]),
        ("Transport", ["stations"])]
    oceans = data["groups"][1]["layers"][0]
    assert oceans["name"] == "Oceans and seas" and oceans["on"] is False and oceans["changed"] == ["on"]


def test_a_bad_layer_change_says_the_value_cannot_be_used(session):
    assert spoken(session.run("layers.set", layer="nowhere", field="on", value=False)) == [
        "That value cannot be used for this setting."]


# Using the visible rule (P2-T4b; NAV-13, SCP-7, ANN-7) --------------------------------

def _nearby(session):
    return [i["label"] for g in session.panel() if g["id"] == "nearby" for i in g["items"]]


def test_nearby_searches_within_the_zoom_not_a_separate_radius(session):
    session.world.zoom_index = session.world.zoom_list.index(5000)
    assert not any(label.startswith("France") for label in _nearby(session))   # France is 35 km off
    session.world.zoom_index = session.world.zoom_list.index(100000)
    assert any(label.startswith("France") for label in _nearby(session))
    assert "nearby_radius_km" not in session.settings.values


def test_nearby_leaves_out_a_layer_whose_zoom_range_is_passed(session):
    session.world.zoom_index = session.world.zoom_list.index(100000)
    session.run("layers.set", layer="countries", field="max_zoom_m", value=50000)
    assert not any(label.startswith("France") for label in _nearby(session))
    session.run("layers.set", layer="countries", field="max_zoom_m", value=None)
    assert any(label.startswith("France") for label in _nearby(session))


def test_the_map_draws_only_layers_in_their_zoom_range(session):
    ids = regions(session)
    session.world.zoom_index = session.world.zoom_list.index(250000)
    assert ids & set(session.scene(800, 600)["shape_area"])
    session.run("layers.set", layer="regions", field="max_zoom_m", value=100000)
    assert not ids & set(session.scene(800, 600)["shape_area"])


# What is said follows the zoom range, as what is drawn does (P2-T17i, DP160; ANN-7, NAV-13)

def _zoom(session, zoom_m):
    session.world.zoom_index = session.world.zoom_list.index(zoom_m)


def test_where_am_i_leaves_out_a_layer_outside_its_zoom_range(session):
    # Counties go to 100 kilometres in the layer file; Regions are given 50 here.
    session.run("layers.set", layer="regions", field="max_zoom_m", value=50000)
    _zoom(session, 100000)
    assert spoken(session.press("Space")) == ["Kent, United Kingdom"]
    within = [i["label"].split(",")[0] for g in session.panel() if g["id"] == "within" for i in g["items"]]
    assert within == ["Kent", "United Kingdom"]
    _zoom(session, 50000)
    assert spoken(session.press("Space")) == ["Kent, England, United Kingdom"]
    _zoom(session, 250000)
    assert spoken(session.press("Space")) == ["United Kingdom"]   # Counties too are out of their range


def test_with_every_layer_here_outside_its_zoom_range_there_is_no_data_at_this_zoom(session):
    for layer in session.layers.layers():
        session.run("layers.set", layer=layer.id, field="max_zoom_m", value=100000)
    _zoom(session, 250000)
    assert spoken(session.press("Space")) == ["No data at this zoom level"]
    assert session.map_label().startswith("No data at this zoom level")


def test_a_layer_that_is_off_is_still_said_to_be_off_not_out_of_zoom(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT, lat=ATLANTIC[0], lon=ATLANTIC[1], zoom_m=250000))
    s.start()
    s.run("layers.set", layer="oceans", field="on", value=False)
    assert spoken(s.press("Space")) == ["Every layer here is switched off"]
    s.store.close()


def test_zooming_out_of_a_layers_range_changes_the_place_the_map_is_named_after(session):
    session.run("layers.set", layer="regions", field="max_zoom_m", value=50000)
    _zoom(session, 50000)
    session.press("Space")
    assert "England" in session.map_label()
    session.run("zoom.out")
    assert session.world.zoom_m > 50000 and "England" not in session.map_label()
    session.run("zoom.in")
    assert "England" in session.map_label()


def test_a_step_leaves_out_a_layer_outside_its_zoom_range(session):
    session.run("layers.set", layer="regions", field="max_zoom_m", value=50000)
    _zoom(session, 100000)
    session.press("Space")
    session.world.lat, session.world.lon = CALAIS
    assert spoken(session._arrived(session._moved())) == ["Pas-de-Calais, France"]


def test_the_map_leaves_out_an_area_too_small_to_see_at_this_zoom(session):
    session.world.lat, session.world.lon = CALAIS
    session.world.zoom_index = session.world.zoom_list.index(250000)
    drawn = set(session.scene(800, 600)["shape_area"])
    session.run("layers.set", layer="counties", field="on", value=True)
    assert drawn <= set(session.scene(800, 600)["shape_area"])
    widths = session.visible.min_widths(250000)
    assert widths["countries"] == 0.02 * 250000 / 1000.0


def test_the_panel_follows_the_zoom(session):
    session.world.zoom_index = session.world.zoom_list.index(100000)
    far = _nearby(session)
    session.world.zoom_index = session.world.zoom_list.index(5000)
    assert _nearby(session) != far or not far


# The layers dialog's data (P2-T3b, P2-T3c; SCP-6, SCP-7) ---------------------------------

def test_the_layers_command_has_its_key_and_gives_the_dialog_its_words_and_choices(session):
    assert session.press("Ctrl+Shift+L").dialog["kind"] == "layers"
    d = session.run("layers.open").dialog
    assert d["title"] == "Layers" and [g["name"] for g in d["groups"]] == ["Boundaries", "Water", "Transport"]
    assert d["every_zoom"] == "No limit" and {"value": 1000.0, "label": "1 kilometre"} in d["zooms"]
    assert "line_crossing" in {e["event"] for e in d["earcons"]}
    # The closest zoom, the smaller distance, is the maximum zoom (P2-T18c, the PO swapped them).
    assert d["words"]["min_zoom"] == "Maximum zoom" and d["words"]["max_zoom"] == "Minimum zoom"
    assert d["words"]["crossing"] == "Sound when a line or border of this layer is crossed"
    assert d["words"]["settings_button"] and d["words"]["ok"] == "OK" and d["words"]["cancel"] == "Cancel"
    assert "Countries, on" in d["text"].split("\n")


def test_a_layers_own_zoom_outside_the_list_comes_with_its_words_from_the_core(session):
    # The shells add no words of their own (3.4), so the core lists a zoom such as one a pack chose.
    session.run("layers.set", layer="counties", field="max_zoom_m", value=1234.0)
    zooms = session.run("layers.open").dialog["zooms"]
    assert [z for z in zooms if z["value"] == 1234.0] == [{"value": 1234.0, "label": "1.2 kilometres"}]
    assert [z["value"] for z in zooms] == sorted(z["value"] for z in zooms)


def test_a_range_check_says_what_is_wrong(session):
    assert not session.run("layers.check", low=0, high=None).error
    assert not session.run("layers.check", low=1000, high=5000).error
    assert session.run("layers.check", low=5000, high=1000).error == \
        "The maximum zoom must not be a larger distance than the minimum zoom."


def test_several_changes_to_a_layer_are_judged_together(session):
    session.run("layers.set", layer="counties", values={"min_zoom_m": 250000, "max_zoom_m": None})
    counties = session.layers.get("counties")
    assert (counties.min_zoom_m, counties.max_zoom_m) == (250000, None)
    r = session.run("layers.set", layer="counties", values={"min_zoom_m": 900000, "max_zoom_m": 500000})
    assert spoken(r) == ["That value cannot be used for this setting."]
    assert session.layers.get("counties").min_zoom_m == 250000   # all or none
