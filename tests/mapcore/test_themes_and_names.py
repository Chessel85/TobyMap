"""Themes, the map display setting, isolate, names on the map and heading-up
(P2-T12; VIS-1, VIS-2, VIS-3, VIS-5, SCP-2, AD-17, AD-19, DP108)."""
import itertools

import numpy as np
import pytest

from mapcore import settings as settings_mod
from mapcore.commands import registry
from mapcore.render import globe, scene as scene_mod, themes
from mapcore.session import MapSession

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 100000, "step_m": 25000}
FIJI = {"lat": -16.5, "lon": 179.99, "zoom_m": 1000000, "step_m": 1000}
COLOUR_CHOICES = [c[0] for c in settings_mod.fields()["border_colour"]["choices"]]
W, H = 800, 600


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


# P2-T12a The themes -------------------------------------------------------------------

def test_the_four_themes_in_order_with_the_settings_choices():
    assert themes.names() == ["standard", "high_contrast_dark", "high_contrast_light", "colour_blind_safe"]
    assert [c[0] for c in settings_mod.fields()["theme"]["choices"]] == themes.names()
    for name in themes.names():
        assert [c[1] for c in settings_mod.fields()["theme"]["choices"] if c[0] == name] == [themes.theme(name)["label"]]


@pytest.mark.parametrize("name", themes.names())
def test_neighbours_never_share_a_colour_in_any_theme(name):
    """Seven land colours, all clearly different, and different from the sea (AD-19)."""
    t = themes.theme(name)
    assert len(t["land"]) == 7
    assert themes.least_difference(t["land"] + [t["ocean"]]) >= 5


@pytest.mark.parametrize("name", ["high_contrast_dark", "high_contrast_light"])
def test_the_high_contrast_themes_reach_7_to_1(name):
    assert themes.theme(name)["high_contrast"]
    assert themes.contrast_problems(themes.theme(name)) == []


def test_the_contrast_ratio_is_the_wcag_one():
    assert themes.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert themes.contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize("kind", sorted(themes.SIMULATIONS))
def test_the_colour_blind_safe_colours_still_differ_with_each_kind_of_colour_blindness(kind):
    t = themes.theme("colour_blind_safe")
    assert themes.least_difference(t["land"] + [t["ocean"]], kind) >= 10
    # The standard theme does not: that is why the colour-blind safe theme is needed.
    s = themes.theme("standard")
    assert themes.least_difference(s["land"] + [s["ocean"]], "protanopia") < 10


def test_the_simulation_keeps_grey_grey():
    for kind in themes.SIMULATIONS:
        assert themes.difference("#808080", "#808080", kind) == pytest.approx(0, abs=1e-9)
        assert themes.difference("#000000", "#ffffff", kind) > 90


# P2-T12b The map display setting (DP108) ---------------------------------------------------

@pytest.mark.parametrize("name", ["high_contrast_dark", "high_contrast_light"])
def test_high_contrast_keeps_7_to_1_with_every_choice(name):
    for fill, borders in itertools.product(["neighbours", "one", "none"], [True, False]):
        for setting, colour in itertools.product(themes.COLOUR_SETTINGS, COLOUR_CHOICES):
            t, _refused = themes.effective(name, fill, borders, **{setting: colour})
            assert themes.contrast_problems(t) == [], (fill, borders, setting, colour)


def test_one_colour_for_all_and_no_fill_and_no_borders():
    t, _ = themes.effective("standard", "one", True, fill_colour="light_grey")
    assert set(t["land"]) == {"#d3d3d3"}
    t, _ = themes.effective("standard", "none", True)
    assert set(t["land"]) == {themes.TRANSPARENT}
    t, _ = themes.effective("standard", "neighbours", False)
    assert t["border"] == themes.TRANSPARENT and t["border_width"] == 0
    assert t["current_outline"] == themes.theme("standard")["current_outline"]   # always drawn (VIS-1)


def test_a_colour_below_7_to_1_is_refused_in_high_contrast_and_used_in_standard():
    t, refused = themes.effective("high_contrast_dark", border_colour="black")
    assert refused == ["border_colour"] and t["border"] == "#ffffff"
    t, refused = themes.effective("high_contrast_dark", border_colour="yellow")
    assert refused == [] and t["border"] == "#ffff00"
    t, refused = themes.effective("standard", border_colour="black")
    assert refused == [] and t["border"] == "#000000"


def test_the_fill_colour_counts_only_for_one_colour_for_all():
    t, refused = themes.effective("high_contrast_dark", "neighbours", fill_colour="white")
    assert refused == [] and t["land"] == themes.theme("high_contrast_dark")["land"]


def test_the_frame_uses_the_theme_and_the_display_setting(session):
    session.run("settings.set", field="theme", value="high_contrast_dark")
    frame = session.scene(W, H)
    assert frame["background"] == "#000000" and frame["current_style"]["stroke"] == "#ffff00"
    assert frame["styles"][0]["stroke"] == "#ffffff" and frame["styles"][0]["width"] == 1.5
    session.run("settings.set", field="map_borders", value=False)
    session.run("settings.set", field="map_fill", value="none")
    frame = session.scene(W, H)
    assert frame["styles"][0] == {"fill": themes.TRANSPARENT, "stroke": themes.TRANSPARENT, "width": 0}
    assert frame["current"] and frame["current_style"]["stroke"] == "#ffff00"
    assert session.scene_background() == "#000000"


def test_t_and_shift_t_go_through_the_themes_and_say_them(session):
    assert registry.by_name("theme.next").key == "T" and registry.by_name("theme.previous").key == "Shift+T"
    r = session.press("T")
    assert spoken(r) == ["High contrast dark theme."] and r.redraw and r.settings_changed
    assert spoken(session.press("T")) == ["High contrast light theme."]
    assert spoken(session.press("Shift+T")) == ["High contrast dark theme."]
    session.press("Shift+T")
    assert spoken(session.press("Shift+T")) == ["Colour-blind safe theme."]


def test_a_refused_colour_is_said(session):
    session.run("settings.set", field="theme", value="high_contrast_dark")
    r = session.run("settings.set", field="border_colour", value="black")
    assert spoken(r) == ["Colour of the borders: that colour is too close to the colours around it for the 7 to 1 "
                         "contrast of a high contrast theme, so the theme's own colour is used."]


# P2-T12c Isolate --------------------------------------------------------------------

def test_isolating_fiji_shows_one_compact_shape_across_the_180_degree_line(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(FIJI))
    s.start()
    everything = s.scene(W, H)
    r = s.press("Ctrl+I")
    fiji = s.areas[0]
    assert spoken(r) == [f"Isolated: {fiji.name}. Only it is on the map. Press Ctrl+I again to show everything."]
    assert s.toggles()["isolate.toggle"]
    frame = s.scene(W, H)
    assert frame["shape_area"] and set(frame["shape_area"]) == {fiji.id}
    assert len(set(everything["shape_area"])) > 1
    xy = frame["coords"].reshape(-1, 2)
    # Both sides of the line are drawn, next to each other, not at opposite edges of the map.
    assert xy[:, 0].min() < W / 2 < xy[:, 0].max()
    assert xy[:, 0].max() - xy[:, 0].min() < W / 2
    assert frame["current"]   # its outline
    r = s.press("Ctrl+I")
    assert spoken(r) == ["Showing everything."] and not s.toggles()["isolate.toggle"]
    assert len(set(s.scene(W, H)["shape_area"])) > 1
    s.store.close()


def test_isolate_with_no_area_says_so(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 0.0, "lon": -150.0, "zoom_m": 1000, "step_m": 1000})
    s.start()
    if s.areas:
        pytest.skip("the test pack has an area here")
    assert spoken(s.press("Ctrl+I")) == ["No area here to isolate."]
    s.store.close()


# P2-T12d Names on the map --------------------------------------------------------------

def boxes(frame):
    return [scene_mod.name_box(n["x"], n["y"], n["text"], n["size"]) for n in frame["names"]]


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize("zoom_m", [100_000, 1_000_000, 5_000_000])
def test_no_two_names_overlap_in_europe(session, zoom_m):
    session.world.zoom_index = min(range(len(session.world.zoom_list)),
                                   key=lambda i: abs(session.world.zoom_list[i] - zoom_m))
    frame = session.scene(W, H)
    assert frame["names"], "some names are drawn"
    for a, b in itertools.combinations(boxes(frame), 2):
        assert not overlap(a, b)
    for box in boxes(frame):
        assert box[0] >= 0 and box[1] >= 0 and box[2] <= W and box[3] <= H


def test_every_name_is_one_where_am_i_can_say(session):
    """SCP-2: each name is drawn inside its own area, so that point is in it."""
    frame = session.scene(W, H)
    view = scene_mod.view_for(session.world, W, H)
    for n in frame["names"]:
        lat, lon = globe.from_screen(view, W, H, n["x"], n["y"])
        assert n["text"] in [a.name for a in session.store.at(lat, lon)], n


def test_larger_areas_get_larger_names_and_200_percent_doubles_them(session):
    assert scene_mod.name_size(100) < scene_mod.name_size(250_000)
    assert scene_mod.name_size(250_000, 2.0) == 2 * scene_mod.name_size(250_000)
    assert settings_mod.fields()["label_size"]["max"] >= 200   # VIS-3
    session.world.zoom_index = min(range(len(session.world.zoom_list)),
                                   key=lambda i: abs(session.world.zoom_list[i] - 1_000_000))
    normal = {n["text"]: n["size"] for n in session.scene(W, H)["names"]}
    session.run("settings.set", field="label_size", value=200)
    big = session.scene(W, H)
    assert big["names"]
    for n in big["names"]:
        if n["text"] in normal:
            assert n["size"] == 2 * normal[n["text"]]
    for a, b in itertools.combinations(boxes(big), 2):
        assert not overlap(a, b)


def test_names_wait_while_a_key_is_held_and_can_be_switched_off(session):
    assert session.scene(W, H)["names"]
    session.holding = "move.north"
    assert session.scene(W, H)["names"] == []
    session.holding = None
    session.run("settings.set", field="map_names", value=False)
    frame = session.scene(W, H)
    assert frame["names"] == [] and frame["name_style"]["colour"]


def test_no_name_covers_the_centre_cross(session):
    frame = session.scene(W, H)
    c = scene_mod.CENTRE_CLEAR_PX
    centre = (W / 2 - c, H / 2 - c, W / 2 + c, H / 2 + c)
    assert not any(overlap(b, centre) for b in boxes(frame))


# P2-T12e Heading-up (VIS-5) ---------------------------------------------------------------

def test_heading_up_turns_the_map_so_the_way_you_face_is_up(session):
    session.world.orientation = "free"
    session.world.heading = 90.0
    session.run("settings.set", field="heading_up", value=True)
    view = scene_mod.view_for(session.world, W, H, True)
    x, y = globe.to_screen(view, W, H, session.world.lat, session.world.lon + 1.0)   # east
    assert abs(x - W / 2) < 3 and y < H / 2 - 10   # straight up, as near as a line of latitude goes
    x, y = globe.to_screen(view, W, H, session.world.lat + 1.0, session.world.lon)   # north
    assert x < W / 2 - 10 and abs(y - H / 2) < 3   # to the left
    assert session.scene(W, H)["heading"]["degrees"] == pytest.approx(0.0)
    # A click above the centre is east of you.
    session.run("map.click", x=W / 2, y=H / 2 - 50, width=W, height=H)
    assert session.world.lon > KENT["lon"] and abs(session.world.lat - KENT["lat"]) < 0.05


def test_heading_up_is_north_up_in_north_fixed_and_off_by_default(session):
    assert not session.settings["heading_up"]
    session.world.heading = 90.0
    assert scene_mod.view_for(session.world, W, H, True).up == 0.0
    session.world.orientation = "cardinal"
    assert scene_mod.view_for(session.world, W, H, False).up == 0.0
    assert scene_mod.view_for(session.world, W, H, True).up == 90.0
