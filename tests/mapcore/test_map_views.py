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
    assert r.dialog["kind"] == "choose" and r.dialog["cancel"] == "Cancel"   # Escape is never needed (ACC-7)
    return r.dialog["lines"]


def _choose(session, line):
    return session.run("views.choose", index=_open(session).index(line))


# The views file ------------------------------------------------------------------------------------------

def test_the_drawing_order_is_the_definitions():
    assert views.drawing_order() == ["oceans", "seas", "countries", "regions", "counties", "physical-regions",
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


def test_the_current_feature_is_still_the_smallest_area_whatever_the_order_said(session):
    session.settings.view = "physical"
    session.areas = session._here()
    assert session.current_feature.name == "Kent"


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

def test_the_view_manager_lists_the_views_and_what_you_can_do(session):
    assert _open(session) == ["Political, in use", "Physical", "Save the layers as a view"]


def test_choosing_a_view_uses_it_and_says_so(session):
    r = _choose(session, "Physical")
    assert spoken(r) == ["Physical view."] and r.redraw and r.settings_changed
    assert session.settings.view == "physical"
    assert session.layers.get("countries").fill == "plain"
    assert _open(session)[:2] == ["Political", "Physical, in use"]


def test_a_change_to_a_layer_makes_the_view_custom_until_it_is_saved(session):
    session.run("layers.set", layer="regions", values={"outline": False})
    assert session.view_name() == "Custom"
    lines = _open(session)
    assert lines[0] == "Custom: your changes to the Political view, in use" and "Political" in lines
    r = _choose(session, "Save the layers as a view")
    assert r.dialog["kind"] == "input" and r.dialog["submit"] == "views.save" and r.dialog["cancel"] == "Cancel"
    r = session.run("views.save", text="  Rivers   only ")
    assert spoken(r) == ["Saved as the Rivers only view, now in use."]
    assert session.view_name() == "Rivers only" and not session.settings.layers
    assert session.layers.get("regions").outline is False   # kept in the view
    assert _open(session) == ["Political", "Physical", "Rivers only, in use", "Save the layers as a view",
                              "Rename one of your views", "Delete one of your views"]


def test_a_view_name_must_be_new_and_not_empty(session):
    assert session.run("views.save", text="").error == "Type a name for the view."
    assert session.run("views.save", text="political").error == "There is already a view called political. Type another name."
    assert session.run("views.save", text="Custom").error.startswith("There is already a view called Custom.")
    session.run("views.save", text="Mine")
    assert session.run("views.save", text="MINE").error.startswith("There is already a view called MINE.")


def test_your_own_views_can_be_renamed_and_deleted_but_not_the_built_in_ones(session):
    session.run("views.save", text="Mine")
    r = _choose(session, "Rename one of your views")
    assert r.dialog["lines"] == ["Mine"]
    r = session.run("views.choose", index=0)
    assert r.dialog["kind"] == "input" and r.dialog["title"] == "Rename Mine"
    assert spoken(session.run("views.rename", text="Ours")) == ["Mine is now called Ours."]
    assert session.settings.view == "Ours"
    r = _choose(session, "Delete one of your views")
    assert r.dialog["lines"] == ["Ours"]
    r = session.run("views.choose", index=0)
    assert r.dialog["kind"] == "confirm" and r.dialog["text"] == "Delete your view Ours? This cannot be undone."
    assert r.dialog["cancel"] == "Cancel"
    assert spoken(session.run("views.delete")) == ["The Ours view is deleted. The Political view is in use."]
    assert _open(session) == ["Political, in use", "Physical", "Save the layers as a view"]


def test_your_views_and_the_one_in_use_are_kept_with_your_settings(test_pack, session):
    session.run("views.save", text="Mine")
    saved = session.save()
    again = MapSession(packs=[test_pack], settings=saved["settings"], saved_state=saved["state"])
    assert again.settings.view == "Mine" and "Mine" in again.settings.views
    assert again.view_name() == "Mine"
    again.store.close()


def test_reset_all_settings_goes_back_to_the_political_view(session):
    _choose(session, "Physical")
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
