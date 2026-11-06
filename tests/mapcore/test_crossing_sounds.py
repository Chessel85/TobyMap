"""Crossing sounds and the graticule interval (P2-T10e; DAT-13, SCP-7, AD-11).

A layer with a crossing sound plays it when a step crosses one of its lines. Nothing in the
core knows the graticule: a line that names the intervals it belongs to is used only at the
interval the setting gives, and the sound is the layer's own.
"""
import numpy as np
import pytest
import shapely

from mapcore.session import MapSession
from mapdata.stages import pack_write
from mapdata.stages.write import drawing_shapes

LAYERS = [{"id": "countries", "name": "Countries", "geometry": "area", "group": "Boundaries"},
          {"id": "graticule", "name": "Lines of latitude and longitude", "geometry": "line", "group": "Graticule",
           "switched_on": True, "crossing_earcon": "line_crossing"},
          {"id": "quiet", "name": "Quiet lines", "geometry": "line", "group": "Graticule", "switched_on": True},
          {"id": "special-lines", "name": "Special lines", "geometry": "line", "group": "Graticule", "switched_on": True,
           "crossing_earcon": "line_crossing",
           "crossing_earcons": {"prime-meridian": "meridian_crossed", "antimeridian": "meridian_crossed",
                                "equator": "equator_crossed", "tropic": "equator_crossed",
                                "polar-circle": "equator_crossed"}}]
LEVELS = [{"id": 0, "tolerance_m": 2000, "min_km2": 1, "tile_level": 3, "view_km": 10000}]


def meridian(lon):
    return shapely.LineString([(lon, lat) for lat in np.arange(40.0, 60.01, 0.5)])


def line(ident, layer, lon, intervals=None):
    r = {"id": ident, "layer": layer, "type": "meridian", "name": f"{lon} degrees east"}
    if intervals:
        r["intervals"] = intervals
    return r, meridian(lon)


FEATURES = [
    ({"id": "test:land", "layer": "countries", "type": "country", "name": "Squareland"}, shapely.box(0.0, 40.0, 20.0, 60.0)),
    line("grat:lon10e", "graticule", 10.0, [1, 5, 10]),    # in the 1, 5 and 10 degree sets
    line("grat:lon9e", "graticule", 9.9, [1]),             # only in the 1 degree set
    line("quiet:lon11e", "quiet", 11.0),
]
# Special lines, each of its own type. Only the type matters to the sound, so they are all
# drawn as meridians here, where a step east crosses them.
SPECIAL = {12.5: "prime-meridian", 13.0: "equator", 14.5: "date-line", 16.0: "tropic", 17.5: "polar-circle",
           18.5: "antimeridian"}
FEATURES += [({"id": f"special:{t}", "layer": "special-lines", "type": t, "name": t}, meridian(lon))
             for lon, t in SPECIAL.items()]


@pytest.fixture(scope="module")
def pack_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("crossing") / "crossing.pack"
    records = [dict(r) for r, _g in FEATURES]
    geoms = [g for _r, g in FEATURES]
    for r in records:
        r["area_km2"] = 1.0 if r["layer"] == "countries" else 0.0
    manifest = {"name": "crossing", "sources": [{"name": "made up", "licence": "CC0", "date": "2026-11-06"}],
                "drawing_levels": LEVELS}
    pack_write.write(path, manifest, records, geoms, 1, say=lambda _line: None, layers=LAYERS,
                     drawing_geoms=drawing_shapes(records, geoms, LEVELS, lambda _line: None))
    return path


def session(pack_path, lon, **settings):
    s = MapSession(packs=[pack_path], saved_state={"lat": 50.5, "lon": lon, "zoom_m": 1_000_000, "step_m": 100_000})
    s.start()
    for field, value in settings.items():
        s.run("settings.set", field=field, value=value)
    return s


def test_crossing_a_line_plays_its_layers_crossing_sound(pack_path):
    s = session(pack_path, 9.5, graticule_interval="10")
    assert s.run("move.east").earcons.count("line_crossing") == 1


def test_a_line_not_in_the_chosen_interval_is_not_crossed(pack_path):
    s = session(pack_path, 9.5, graticule_interval="10")
    # The 9.9 degree line is only in the 1 degree set: not crossed at 10, crossed at 1.
    s.world.lon = 9.8
    assert s.run("move.east").earcons.count("line_crossing") == 1       # the 10 degree line only
    s = session(pack_path, 9.8, graticule_interval="1")
    assert s.run("move.east").earcons.count("line_crossing") == 2


def test_a_layer_with_no_crossing_sound_plays_none(pack_path):
    s = session(pack_path, 10.5)
    assert s.run("move.east").earcons.count("line_crossing") == 0


def test_a_layer_that_is_off_plays_nothing(pack_path):
    s = session(pack_path, 9.5)
    s.run("layers.set", layer="graticule", field="on", value=False)
    assert "line_crossing" not in s.run("move.east").earcons


def test_a_layer_out_of_its_zoom_range_plays_nothing(pack_path):
    s = session(pack_path, 9.5)
    s.run("layers.set", layer="graticule", field="max_zoom_m", value=500_000)
    assert "line_crossing" not in s.run("move.east").earcons


def test_the_interval_is_a_setting_in_the_layers_tab_and_the_map_follows_it(pack_path):
    s = session(pack_path, 9.5)
    schema = s.settings_schema()
    tab = next(t for t in schema["tabs"] if t["label"] == "Layers")
    field = tab["fields"][0]
    assert field["id"] == "graticule_interval" and [c[0] for c in field["choices"]] == ["1", "5", "10", "15", "30"]
    s.run("settings.set", field="graticule_interval", value="10")
    ten = set(s.scene(800, 600)["line_area"])
    s.run("settings.set", field="graticule_interval", value="1")
    one = set(s.scene(800, 600)["line_area"])
    assert "grat:lon9e" not in ten and "grat:lon9e" in one and "grat:lon10e" in ten


def test_joined_held_moves_keep_every_crossing_sound(pack_path):
    # The web joins held moves that arrive while the worker is busy (ANN-3). The first
    # crosses the 10 degree line and the second crosses nothing, but clicks: the crossing
    # sound must not be lost to the second move's click.
    s = session(pack_path, 9.5, graticule_interval="10")
    r = s.run_many([("move.east", {"held": True, "repeat": True})] * 2)
    assert r.earcons.count("line_crossing") == 1
    assert "crossings" not in r.to_dict()


@pytest.mark.parametrize("lon, sounds", [
    (12.0, ["meridian_crossed", "equator_crossed"]),   # the prime meridian, then the equator, in the order crossed
    (14.0, ["line_crossing"]),                         # the date line keeps the layer's own sound
    (15.5, ["equator_crossed"]),                       # a tropic
    (17.0, ["equator_crossed"]),                       # a polar circle
    (18.0, ["meridian_crossed"]),                      # the 180 degree meridian
])
def test_special_lines_play_the_sound_their_type_has_in_the_layer_file(pack_path, lon, sounds):
    s = session(pack_path, lon)
    earcons = [e for e in s.run("move.east").earcons if e != "tick"]
    assert earcons == sounds


def test_switching_the_layers_crossing_sound_off_silences_every_special_line(pack_path):
    s = session(pack_path, 12.0)
    s.run("layers.set", layer="special-lines", field="crossing_earcon", value=None)
    assert [e for e in s.run("move.east").earcons if e != "tick"] == []


def test_each_crossing_earcon_has_its_own_switch(pack_path):
    s = session(pack_path, 12.0, earcon_on_meridian_crossed=False)
    assert [e for e in s.run("move.east").earcons if e != "tick"] == ["equator_crossed"]


def test_the_world_packs_special_lines_layer_names_the_product_owners_sounds():
    from mapdata.pipeline.settings import load_pack

    special = load_pack("world").layers["special-lines"].definition()
    assert special["crossing_earcons"] == {"prime-meridian": "meridian_crossed", "antimeridian": "meridian_crossed",
                                           "equator": "equator_crossed", "tropic": "equator_crossed",
                                           "polar-circle": "equator_crossed"}
    assert special["crossing_earcon"] == "line_crossing"
