"""The map for sighted users (P2-T17v; VIS-1, VIS-2, DAT-13, SCP-7).

* A line layer whose line_style is special, such as the special lines, is drawn thicker and in
  the theme's colour for special lines, on top of the plain lines. Nothing in the core knows
  the special lines layer: the style comes from the layer definition in the pack.
* The setting "Outline the current area" chooses when the current area is outlined: always,
  not for the oceans, never for oceans and seas, or never.
"""
import numpy as np
import pytest
import shapely

from mapcore.layers.catalogue import from_definition
from mapcore.render import themes
from mapcore.session import MapSession, outlined
from mapdata.stages import pack_write
from mapdata.stages.write import drawing_shapes

LAYERS = [{"id": "countries", "name": "Countries", "geometry": "area", "group": "Boundaries", "rank": 2},
          {"id": "oceans", "name": "Oceans and seas", "geometry": "area", "group": "Water", "rank": 2},
          {"id": "graticule", "name": "Lines of latitude and longitude", "geometry": "line", "group": "Graticule",
           "switched_on": True},
          {"id": "bold", "name": "Bold lines", "geometry": "line", "group": "Graticule", "switched_on": True,
           "line_style": "special"}]
LEVELS = [{"id": 0, "tolerance_m": 2000, "min_km2": 1, "tile_level": 3, "view_km": 10000}]


def meridian(lon):
    return shapely.LineString([(lon, lat) for lat in np.arange(40.0, 60.01, 0.5)])


FEATURES = [
    ({"id": "test:land", "layer": "countries", "type": "country", "name": "Squareland"}, shapely.box(0.0, 40.0, 20.0, 60.0)),
    ({"id": "test:ocean", "layer": "oceans", "type": "ocean", "name": "Square Ocean"}, shapely.box(-20.0, 40.0, 0.0, 60.0)),
    ({"id": "grat:lon5e", "layer": "graticule", "type": "meridian", "name": "5 degrees east"}, meridian(5.0)),
    ({"id": "bold:lon6e", "layer": "bold", "type": "prime-meridian", "name": "Bold meridian"}, meridian(6.0)),
]


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("sighted") / "sighted.pack"
    records = [dict(r) for r, _g in FEATURES]
    geoms = [g for _r, g in FEATURES]
    for r in records:
        r["area_km2"] = 1.0 if r["layer"] in ("countries", "oceans") else 0.0
    manifest = {"name": "sighted", "sources": [{"name": "made up", "licence": "CC0", "date": "2026-11-10"}],
                "drawing_levels": LEVELS}
    pack_write.write(path, manifest, records, geoms, 1, say=lambda _line: None, layers=LAYERS,
                     drawing_geoms=drawing_shapes(records, geoms, LEVELS, lambda _line: None))
    return path


def session(pack_path, lon, **settings):
    s = MapSession(packs=[pack_path], saved_state={"lat": 50.0, "lon": lon, "zoom_m": 1_000_000, "step_m": 100_000})
    s.start()
    for field, value in settings.items():
        s.run("settings.set", field=field, value=value)
    return s


def runs_by_area(frame):
    return {a: int(st) for a, st in zip(frame["line_area"], frame["line_style"])}


# The special line style ---------------------------------------------------------------

@pytest.mark.parametrize("theme", themes.names())
def test_a_special_layers_lines_are_drawn_thicker_in_their_own_colour(pack_path, theme):
    s = session(pack_path, 5.5, theme=theme)
    f = s.scene(800, 600)
    styles = runs_by_area(f)
    assert styles["grat:lon5e"] != styles["bold:lon6e"]
    plain, special = f["line_styles"][styles["grat:lon5e"]], f["line_styles"][styles["bold:lon6e"]]
    t = s.theme()
    assert special == {"stroke": t["special_line"], "width": t["special_line_width"]}
    assert special["width"] > plain["width"]
    assert special["stroke"] not in (plain["stroke"], t["current_outline"], t["border"])


def test_the_special_lines_are_drawn_on_top_of_the_plain_lines(pack_path):
    f = session(pack_path, 5.5).scene(800, 600)
    order = [int(x) for x in f["line_style"]]
    assert order == sorted(order, key=lambda st: {0: 0, 2: 1, 1: 2}[st])
    # The runs still hold their own points after the reordering.
    xy = np.asarray(f["line_coords"]).reshape(-1, 2)
    runs = f["line_runs"]
    for k in range(len(runs) - 1):
        seg = xy[runs[k]:runs[k + 1]]
        assert np.ptp(seg[:, 0]) < np.ptp(seg[:, 1])   # each run is a meridian: tall, not wide


def test_a_selected_special_line_is_drawn_highlighted(pack_path):
    s = session(pack_path, 5.5)
    s.selected = "bold:lon6e"
    styles = runs_by_area(s.scene(800, 600))
    assert styles["bold:lon6e"] == 1


@pytest.mark.parametrize("theme", [n for n in themes.names() if themes.theme(n).get("high_contrast")])
def test_the_special_line_keeps_7_to_1_in_the_high_contrast_themes(theme):
    t = themes.theme(theme)
    assert all(themes.contrast(t["special_line"], f) >= 7.0 for f in t["land"] + [t["ocean"]])
    assert not themes.contrast_problems(t)


def test_a_layer_without_a_line_style_or_with_an_unknown_one_is_plain():
    assert from_definition({"id": "x", "geometry": "line"}).line_style == "plain"
    assert from_definition({"id": "x", "geometry": "line", "line_style": "dotted"}).line_style == "plain"
    assert from_definition({"id": "x", "geometry": "line", "line_style": "special"}).line_style == "special"


def test_the_world_packs_special_lines_layer_is_drawn_special_and_the_graticule_plain():
    from mapdata.pipeline.settings import load_pack

    layers = load_pack("world").layers
    assert layers["special-lines"].definition()["line_style"] == "special"
    assert layers["graticule"].definition().get("line_style", "plain") == "plain"


def test_a_layer_file_with_an_unknown_line_style_stops_the_build(tmp_path):
    from mapdata.pipeline.errors import BuildStopped
    from mapdata.pipeline.settings import load_layers

    (tmp_path / "layers").mkdir()
    (tmp_path / "layers" / "odd.yaml").write_text(
        "layers:\n  - {id: odd, name: Odd, rank: 8, kind: land, geometry: line, line_style: wavy}\n", encoding="utf-8")
    with pytest.raises(BuildStopped, match="line_style"):
        load_layers(["odd"], config_dir=tmp_path)


# Outline the current area -------------------------------------------------------------

@pytest.mark.parametrize("setting, on_land, at_sea", [
    ("always", True, True),
    ("not_oceans", True, False),
    ("not_water", True, False),
    ("never", False, False),
])
def test_the_setting_chooses_when_the_current_area_is_outlined(pack_path, setting, on_land, at_sea):
    land = session(pack_path, 10.0, outline_current=setting).scene(800, 600)
    sea = session(pack_path, -10.0, outline_current=setting).scene(800, 600)
    assert bool(land["current"]) is on_land
    assert bool(sea["current"]) is at_sea


def test_the_outline_is_always_drawn_at_first(pack_path):
    s = session(pack_path, -10.0)
    assert s.settings["outline_current"] == "always"
    assert s.scene(800, 600)["current"]


def test_a_sea_is_outlined_unless_oceans_and_seas_are_left_out():
    sea = {"type": "sea"}
    assert outlined(sea, "always") and outlined(sea, "not_oceans")
    assert not outlined(sea, "not_water") and not outlined(sea, "never")
    assert outlined({"type": "lake"}, "not_water")


def test_changing_the_setting_redraws_the_map(pack_path):
    s = session(pack_path, -10.0)
    assert s.run("settings.set", field="outline_current", value="never").redraw
