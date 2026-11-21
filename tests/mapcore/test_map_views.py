"""Map views and the drawing order (P3-T23, DP198; VIS-1, LOC-2, SCP-6, SCP-7, ACC-7).

The definition is "How TobyMap draws the map" in docs/design/Discussion points detail - responses.md.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from mapcore import views
from mapcore.render import scene as scene_mod
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}
LONGBRIDGE_LAKE = {"lat": 50.9566, "lon": -1.4882, "zoom_m": 1000, "step_m": 100}


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def _open(session):
    r = session.run("views.open")
    assert r.dialog["kind"] == "views" and r.dialog["words"]["cancel"] == "Cancel"   # Escape is never needed (ACC-7)
    assert [r.dialog["words"][k] for k in ("add", "save", "rename", "delete", "ok")] ==         ["Add", "Save changes", "Rename", "Delete", "OK"]
    return [i["label"] for i in r.dialog["views"]["items"]]


def _listing(session):
    return session.run("views.open").dialog["views"]


def _choose(session, label):
    return session.run("views.apply", index=_open(session).index(label))


# The views file ------------------------------------------------------------------------------------------

def test_the_drawing_order_is_the_definitions():
    assert views.drawing_order() == ["oceans", "seas", "territorial-waters", "countries", "regions", "counties", "physical-regions",
                                     "islands", "mountain-ranges", "lakes", "rivers", "outlines", "roads", "railways"]


def test_there_are_two_views_built_in_the_political_first():
    assert [(v["id"], v["name"]) for v in views.built_in()] == [("political", "Political"), ("physical", "Physical")]
    assert views.default_id() == "political"


def test_the_political_view_says_government_areas_then_natural_ones_and_the_physical_view_the_other_way(session):
    def area(name, layer, rank=1):
        return SimpleNamespace(id=name, name=name, layer=layer, rank=rank)

    # Smallest first within a layer, as the store gives them.
    atlas = [area("Lake", "lakes"), area("Cercle d'Asni", "counties"), area("Western High Atlas", "mountain-ranges"),
             area("High Atlas", "mountain-ranges"), area("Marrakech-Safi", "regions"),
             area("Atlas Mountains", "mountain-ranges"), area("Morocco", "countries"), area("Africa", "continents")]
    assert [a.name for a in session._said_order(atlas)] == [
        "Lake", "Cercle d'Asni", "Marrakech-Safi", "Morocco", "Western High Atlas", "High Atlas", "Atlas Mountains",
        "Africa"]
    session.settings.view = "physical"
    assert [a.name for a in session._said_order(atlas)] == [
        "Lake", "Western High Atlas", "High Atlas", "Atlas Mountains", "Cercle d'Asni", "Marrakech-Safi", "Morocco",
        "Africa"]


def test_the_current_feature_is_the_first_area_said_in_the_view(session):
    """P3-T28m (LOC-4): the current feature follows the order "where am I" says, in each view."""
    session.settings.view = "physical"
    session.areas = session._here()
    assert session.current_feature.name == "Kent" == session.areas[0].name


# Territorial waters (P4-T12b, DAT-15, DAT-3) --------------------------------------------------------------------

OFF_BRITTANY = {"lat": 48.2, "lon": -4.7, "zoom_m": 5000, "step_m": 1000}   # at sea, off the test pack's Brittany


@pytest.mark.parametrize("view", ["political", "physical"])
def test_at_sea_off_brittany_you_hear_the_sea_first_then_frances_territorial_waters(test_pack, view):
    s = MapSession(packs=[test_pack], saved_state=dict(OFF_BRITTANY))
    s.start()
    s.settings.view = view
    assert spoken(s.run("where.am_i"))[0].startswith("North Atlantic Ocean, Territorial waters of France")
    assert "France" not in [a.name for a in s._here()]   # at sea, not in France (DAT-3)
    s.store.close()


def test_territorial_waters_are_off_by_their_switch(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(OFF_BRITTANY))
    s.start()
    s.run("layers.set", layer="territorial-waters", field="on", value=False)
    assert "Territorial waters" not in spoken(s.run("where.am_i"))[0]
    s.store.close()


def test_territorial_waters_are_painted_a_lighter_blue_over_the_sea_under_the_land(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(OFF_BRITTANY))
    s.start()
    s.world.zoom_index = s.world.zoom_list.index(100000)
    frame = s.scene(800, 600)
    layer = [s.store.feature(a).layer for a in frame["shape_area"]]
    tw = layer.index("territorial-waters")
    style = frame["styles"][frame["shape_style"][tw]] if "styles" in frame else None
    light = scene_mod.KIND_STYLE + len(s.theme()["physical"])
    assert frame["shape_style"][tw] == light
    assert style is None or style["fill"] == s.theme()["light_water"]
    assert max(i for i, l in enumerate(layer) if l == "oceans") < tw < min(
        i for i, l in enumerate(layer) if l in ("countries", "regions", "counties"))
    assert tw not in frame["outline_shapes"].tolist()   # not outlined, as the seas are not
    s.store.close()


def test_every_theme_paints_territorial_waters_a_blue_apart_from_the_open_sea():
    from mapcore.render import themes

    for name in themes.names():
        t = themes.theme(name)
        assert themes.difference(t["light_water"], t["ocean"]) > 4, name
        if name != "high_contrast_light":   # its sea is white: the waters are a pale blue on it
            assert themes.luminance(t["light_water"]) > themes.luminance(t["ocean"]), name


# The drawing --------------------------------------------------------------------------------------------

def test_a_lake_is_painted_after_the_land_it_lies_on(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(LONGBRIDGE_LAKE))
    s.start()
    frame = s.scene(800, 600)
    layer = [s.store.feature(a).layer for a in frame["shape_area"]]
    assert "lakes" in layer
    assert max(i for i, l in enumerate(layer) if l in ("countries", "regions", "counties")) < layer.index("lakes")
    lake = layer.index("lakes")
    assert frame["shape_style"][lake] == scene_mod.OCEAN_STYLE   # water
    # Its outline, and the borders, are drawn over it.
    assert lake in frame["outline_shapes"].tolist()
    s.store.close()


def test_oceans_and_seas_are_not_outlined_and_the_countries_are(session):
    session.world.zoom_index = session.world.zoom_list.index(500000)
    frame = session.scene(800, 600)
    outlined = set(frame["outline_shapes"].tolist())
    layer = [session.store.feature(a).layer for a in frame["shape_area"]]
    assert not any(i in outlined for i, l in enumerate(layer) if l in ("oceans", "seas"))
    assert all(i in outlined for i, l in enumerate(layer) if l == "countries")


def test_the_current_feature_is_outlined_and_tinted(session):
    frame = session.scene(800, 600)
    style = frame["current_style"]
    assert frame["current"] and style["tint"] == style["stroke"] == "#b00020"
    assert 0 < style["tint_alpha"] < 1


def test_the_outline_setting_of_a_layer_is_followed(session):
    session.world.zoom_index = session.world.zoom_list.index(500000)
    session.run("layers.set", layer="regions", values={"outline": False})
    assert session.layers.get("regions").outline is False
    frame = session.scene(800, 600)
    outlined = set(frame["outline_shapes"].tolist())
    layer = [session.store.feature(a).layer for a in frame["shape_area"]]
    assert "regions" in layer and not any(i in outlined for i, l in enumerate(layer) if l == "regions")
    assert any(i in outlined for i, l in enumerate(layer) if l == "countries")


def test_a_river_is_drawn_under_the_outlines_and_a_station_over_them(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 50.91, "lon": -1.40, "zoom_m": 10000, "step_m": 1000})
    s.start()
    frame = s.scene(800, 600)
    under = frame["lines_under"]
    rivers = [k for k, a in enumerate(frame["line_area"]) if s.store.feature(a).layer == "rivers"]
    assert rivers and all(k < under for k in rivers)
    s.store.close()


def test_the_physical_view_paints_the_land_plain_and_outlines_the_countries(session):
    session.world.zoom_index = session.world.zoom_list.index(500000)
    _choose(session, "Physical")
    frame = session.scene(800, 600)
    layer = [session.store.feature(a).layer for a in frame["shape_area"]]
    countries = [frame["shape_style"][i] for i, l in enumerate(layer) if l == "countries"]
    assert countries and set(countries) <= {scene_mod.PLAIN_STYLE, scene_mod.HIGHLIGHT_STYLE}
    regions = [frame["shape_style"][i] for i, l in enumerate(layer) if l == "regions"]
    assert regions and set(regions) == {scene_mod.CLEAR_STYLE}
    outlined = set(frame["outline_shapes"].tolist())
    assert all(i in outlined for i, l in enumerate(layer) if l == "regions")


def test_an_island_is_named_on_the_map_though_not_filled():
    feats = [("i", 5, 1, "islands", 10.0, None, "Islay"), ("c", 1, 2, "countries", 100.0, None, "Scotland")]
    paint = {"islands": {"fill": "none", "outline": True, "names": True, "order": 6},
             "countries": {"fill": "colours", "outline": True, "names": None, "order": 2}}
    from mapcore.render import themes

    plan = scene_mod.paint_plan(feats, paint, None, themes.theme("standard"))
    assert plan["style"].tolist() == [scene_mod.CLEAR_STYLE, 1]
    assert plan["names"].tolist() == [True, True]


def test_the_physical_view_has_a_colour_for_each_kind():
    from mapcore.render import themes

    t = themes.theme("standard")
    feats = [("m", 3, 1, "mountain-ranges", 10.0, None, "Alps"), ("p", 3, 1, "physical-regions", 10.0, None, "Sahara")]
    paint = {k: {"fill": "kind", "order": 5} for k in ("mountain-ranges", "physical-regions")}
    plan = scene_mod.paint_plan(feats, paint, None, t)
    kinds = sorted(t["physical"])
    assert plan["style"].tolist() == [scene_mod.KIND_STYLE + kinds.index("mountain-ranges"),
                                      scene_mod.KIND_STYLE + kinds.index("physical-regions")]


def test_every_theme_keeps_its_contrast_with_the_views_colours():
    from mapcore.render import themes

    for name in themes.names():
        t = themes.theme(name)
        assert t["physical"] and t["plain_land"] and t["country_border_width"] > t["border_width"]
        if t.get("high_contrast"):
            assert themes.contrast_problems(t) == []


# The view manager -------------------------------------------------------------------------------------

def test_the_view_manager_lists_the_views_and_opens_on_the_one_in_use(session):
    assert _open(session) == ["Political, in use", "Physical"]
    assert _listing(session)["current"] == 0
    session.settings.view = "physical"
    assert _listing(session)["current"] == 1


def test_ok_uses_the_view_chosen_and_says_so(session):
    session.run("views.open")
    r = session.run("views.apply", index=1)
    assert spoken(r) == ["Physical view."] and r.redraw and r.settings_changed
    assert session.settings.view == "physical"
    assert session.layers.get("countries").fill == "plain"
    assert _open(session)[:2] == ["Political", "Physical, in use"]


def test_ok_with_nothing_changed_says_nothing(session):
    session.run("views.open")
    r = session.run("views.apply", index=0)
    assert spoken(r) == [] and not r.redraw


def test_cancel_runs_nothing_so_the_next_opening_starts_from_what_is_kept(session):
    session.run("views.open")
    session.run("views.add", text="Mine")
    session.run("views.open")   # Cancel ran nothing; opening again starts a new copy
    assert "Mine" not in session.settings.views and _open(session) == ["Political, in use", "Physical"]
    assert session.run("views.apply", index=0).announcements == []   # nothing left to keep


def test_a_change_to_a_layer_makes_the_view_custom_until_it_is_saved(session):
    session.run("layers.set", layer="regions", values={"outline": False})
    assert session.view_name() == "Custom"
    lines = _open(session)
    assert lines[0] == "Custom: your changes to the Political view, in use" and "Political" in lines
    assert _listing(session)["current"] == 0
    r = session.run("views.add", text="  Rivers   only ")
    assert spoken(r) == ["Added the Rivers only view. OK uses it."]
    assert r.views["items"][r.views["current"]]["label"] == "Rivers only"
    assert session.settings.layers and "Rivers only" not in session.settings.views   # nothing kept until OK
    r = session.run("views.apply", index=r.views["current"])
    assert spoken(r) == ["Rivers only view."]
    assert session.view_name() == "Rivers only" and not session.settings.layers
    assert session.layers.get("regions").outline is False   # kept in the view
    assert _open(session) == ["Political", "Physical", "Rivers only, in use"]


def test_ok_on_custom_keeps_your_changes_to_the_layers(session):
    session.run("layers.set", layer="regions", values={"outline": False})
    session.run("views.open")
    session.run("views.apply", index=0)
    assert session.view_name() == "Custom" and session.settings.layers


def test_a_view_name_must_be_new_and_not_empty(session):
    session.run("views.open")
    assert session.run("views.add", text="").error == "Type a name for the view."
    assert session.run("views.add", text="political").error == "There is already a view called political. Type another name."
    assert session.run("views.add", text="Custom").error.startswith("There is already a view called Custom.")
    session.run("views.add", text="Mine")
    assert session.run("views.add", text="MINE").error.startswith("There is already a view called MINE.")


def test_your_own_views_can_be_renamed_and_deleted_but_not_the_built_in_ones(session):
    session.run("views.open")
    session.run("views.add", text="Mine")
    session.run("views.apply", index=2)
    session.run("views.open")
    for r in (session.run("views.rename", index=0, text="X"), session.run("views.delete", index=1)):
        assert not r.error and spoken(r) == [] and r.views is None   # the buttons are unavailable there (P4-T14g)
    assert _listing(session)["items"][0]["label"] == "Political"
    session.run("views.open")
    assert spoken(session.run("views.rename", index=2, text="Ours")) == ["Mine is now called Ours."]
    assert session.settings.view == "Mine"   # kept only by OK
    r = session.run("views.delete", index=2)
    assert spoken(r) == ["The Ours view is deleted. Cancel brings it back."]
    assert [i["label"] for i in r.views["items"]] == ["Political, in use", "Physical"] and r.views["current"] == 1
    assert "Mine" in session.settings.views   # Cancel here leaves it
    session.run("views.open")
    session.run("views.rename", index=2, text="Ours")
    session.run("views.delete", index=2)
    r = session.run("views.apply", index=0)
    assert spoken(r) == ["Political view."] and not session.settings.views and session.view()["id"] == "political"


def test_your_views_and_the_one_in_use_are_kept_with_your_settings(test_pack, session):
    session.run("views.open")
    r = session.run("views.add", text="Mine")
    session.run("views.apply", index=r.views["current"])
    saved = session.save()
    again = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    assert again.settings.view == "Mine" and "Mine" in again.settings.views
    assert again.view_name() == "Mine"
    again.store.close()


def test_reset_all_settings_goes_back_to_the_political_view(session):
    session.run("views.open")
    session.run("views.apply", index=1)
    session.run("settings.reset_confirm")
    assert session.view()["id"] == "political" and not session.settings.views


def test_an_island_and_an_area_of_one_name_on_the_same_land_are_said_once(session, monkeypatch):
    """P3-T23, DP198: the build stores them as the same land (relationships "same"), so the second is left out."""
    def area(i, name, layer):
        return SimpleNamespace(id=i, name=name, layer=layer, rank=1)

    county, island, country = area("c", "Isle of Wight", "counties"), area("i", "Isle of Wight", "islands"),         area("k", "United Kingdom", "countries")
    same = {"i": {"same": ["c"]}, "c": {"same": ["i"]}}
    monkeypatch.setattr(session.store, "relationships", lambda identifier: same.get(identifier, {}))
    assert [a.id for a in session._said([county, country, island])] == ["c", "k"]
    other = area("o", "Wight", "islands")
    same["o"] = {"same": ["c"]}
    assert [a.id for a in session._said([county, other])] == ["c", "o"]   # another name: both said


def test_the_web_version_gets_the_list_back_after_each_change(session):
    # The web version runs every command through run_many, which must carry the list (P3-T28h).
    session.run("views.open")
    r = session.run_many([("views.add", {"text": "Mine"})])
    assert [i["label"] for i in r.to_dict()["views"]["items"]] == ["Political, in use", "Physical", "Mine"]
    r = session.run_many([("views.delete", {"index": 2})])
    assert [i["label"] for i in r.to_dict()["views"]["items"]] == ["Political, in use", "Physical"]


# Unavailable buttons and Save changes (P4-T14g) -------------------------------------------------------

def test_rename_is_unavailable_on_political_and_save_changes_saves_the_layers_into_a_view_of_your_own(session):
    session.run("views.open")
    session.run("views.add", text="Mine")
    session.run("views.apply", index=2)
    items = _listing(session)["items"]
    assert [(i["label"], i["own"], i["save"]) for i in items] ==         [("Political", False, False), ("Physical", False, False), ("Mine, in use", True, False)]
    r = session.run("views.rename", index=0, text="X")   # Political: unavailable, so nothing and no message
    assert not r.error and spoken(r) == [] and r.views is None
    assert session.run("views.save", index=0).views is None
    assert session.run("views.save", index=2).views is None   # Mine holds the layers as they are: nothing to save

    session.run("layers.set", layer="regions", values={"outline": False})
    assert session.view_name() == "Custom"
    items = _listing(session)["items"]
    assert items[0]["label"] == "Custom: your changes to the Mine view, in use"
    assert [(i["id"], i["save"]) for i in items] == [("custom", False), ("political", False), ("physical", False),
                                                     ("Mine", True)]
    r = session.run("views.save", index=3)
    assert spoken(r) == ["The layers are saved into the Mine view. OK keeps it."]
    assert [i["label"] for i in r.views["items"]] == ["Political", "Physical", "Mine, in use"]   # Custom is Mine now
    assert r.views["current"] == 2 and not r.views["items"][2]["save"]
    assert session.settings.views["Mine"]["layers"]["regions"]["outline"] is not False   # kept only by OK
    session.run("views.apply", index=r.views["current"])
    assert session.settings.views["Mine"]["layers"]["regions"]["outline"] is False
    assert session.view_name() == "Mine" and not session.settings.layers
    assert session.layers.get("regions").outline is False


def test_add_stores_the_layers_of_that_moment_and_save_changes_puts_later_ones_into_another_view(session):
    session.run("views.open")
    session.run("views.add", text="Mine")
    session.run("views.apply", index=0)   # Political stays in use; Mine is kept as it was added
    session.run("layers.set", layer="regions", values={"outline": False})
    assert session.settings.views["Mine"]["layers"]["regions"]["outline"] is True   # Add does not follow later changes
    items = _listing(session)["items"]
    assert [i["label"] for i in items] == ["Custom: your changes to the Political view, in use", "Political", "Physical", "Mine"]
    assert items[3]["save"]
    r = session.run("views.save", index=3)
    assert [i["label"] for i in r.views["items"]][0].startswith("Custom")   # not the view in use: Custom stays
    assert r.views["current"] == 3 and not r.views["items"][3]["save"]
    session.run("views.apply", index=0)   # OK on Custom keeps the saved view and your changes
    assert session.settings.views["Mine"]["layers"]["regions"]["outline"] is False and session.view_name() == "Custom"


def test_cancel_after_save_changes_leaves_the_view_as_it_was(session):
    session.run("views.open")
    session.run("views.add", text="Mine")
    session.run("views.apply", index=2)
    session.run("layers.set", layer="regions", values={"outline": False})
    session.run("views.open")
    session.run("views.save", index=3)
    session.run("views.open")   # Cancel ran nothing
    assert session.settings.views["Mine"]["layers"]["regions"]["outline"] is True
