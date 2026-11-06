"""P2-T10b: the graticule stage (DAT-13, SCP-7, AD-11)."""
import json

import numpy as np
import pytest
import shapely

from mapdata.paths import CONFIG_DIR
from mapdata.pipeline.errors import BuildStopped
from mapdata.pipeline.settings import load_layers, load_sources
from mapdata.stages import graticule
from mapdata.stages.write import drawing_shapes


def max_gap(line) -> float:
    worst = 0.0
    for part in shapely.get_parts(line):
        c = shapely.get_coordinates(part)
        worst = max(worst, float(np.abs(np.diff(c, axis=0)).max()))
    return worst


def test_every_whole_degree_is_a_line_with_the_intervals_it_belongs_to():
    records, geoms = graticule.graticule_lines("graticule")
    by_id = {r["id"]: r for r in records}
    assert by_id["graticule:lon30e"]["intervals"] == [1, 5, 10, 15, 30]
    assert by_id["graticule:lat45n"]["intervals"] == [1, 5, 15]
    assert by_id["graticule:lon7w"]["intervals"] == [1]
    assert by_id["graticule:lon7w"]["name"] == "7 degrees west"
    assert len(records) == len(geoms) == 358 + 178
    assert "graticule:lon0e" not in by_id and "graticule:lat0n" not in by_id


def test_no_two_points_of_a_line_are_more_than_one_degree_apart():
    _r, geoms = graticule.graticule_lines("graticule")
    assert all(max_gap(g) <= 1.0 + 1e-9 for g in geoms)
    _r, special = graticule.special_lines("special-lines", 2026)
    assert all(max_gap(g) <= 1.0 + 1e-9 for g in special)


def test_the_special_lines_are_each_named_and_the_tropics_follow_the_year():
    records, geoms = graticule.special_lines("special-lines", 2026)
    names = [r["name"] for r in records]
    assert names == ["Equator", "Prime meridian", "180 degree meridian", "Tropic of Cancer",
                     "Tropic of Capricorn", "Arctic Circle", "Antarctic Circle"]
    cancer = geoms[3].coords[0][1]
    assert cancer == pytest.approx(23.4355, abs=0.001)
    assert geoms[4].coords[0][1] == pytest.approx(-cancer)
    assert geoms[5].coords[0][1] == pytest.approx(90 - cancer)
    assert graticule.obliquity_degrees(2000) == pytest.approx(23.43928, abs=1e-4)
    assert graticule.obliquity_degrees(2126) < graticule.obliquity_degrees(2026)


def test_a_line_across_the_180_degree_line_is_stored_as_its_two_sides():
    parts = graticule.split_at_180([(170.0, 60.0), (179.0, 65.0), (-179.0, 67.0), (-170.0, 70.0)])
    assert len(parts) == 2
    assert parts[0][-1] == (180.0, pytest.approx(66.0)) and parts[1][0] == (-180.0, pytest.approx(66.0))
    assert parts[0][0] == (170.0, 60.0) and parts[1][-1] == (-170.0, 70.0)


def test_the_date_line_is_read_from_the_geographic_lines_and_the_rest_ignored(tmp_path):
    path = tmp_path / "lines.geojson"
    line = [[180, 70], [180, 65], [-172, 53], [-169, 50], [-180, -16], [-180, -90]]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"featurecla": "Date line", "name": "International Date Line"},
         "geometry": {"type": "LineString", "coordinates": line}},
        {"type": "Feature", "properties": {"featurecla": "Equator", "name": "Equator"},
         "geometry": {"type": "LineString", "coordinates": [[-180, 0], [180, 0]]}}]}), encoding="utf-8")
    got = graticule.date_line(path)
    assert max_gap(got) <= 1.0 + 1e-9
    c = shapely.get_coordinates(got)
    assert c[:, 1].max() == 70 and c[:, 1].min() == -90
    records, geoms = graticule.special_lines("special-lines", 2026, got)
    assert records[-1]["name"] == "International date line" and len(geoms) == 8


def test_a_file_with_no_date_line_stops_the_build(tmp_path):
    path = tmp_path / "none.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    with pytest.raises(BuildStopped, match="date line"):
        graticule.date_line(path)


def test_the_drawing_levels_keep_every_point_of_an_exact_line():
    records, geoms = graticule.graticule_lines("graticule")
    records, geoms = records[-1:], geoms[-1:]
    levels = [{"id": 0, "tolerance_m": 40000, "min_km2": 20000, "tile_level": 1, "view_km": 4000}]
    out = drawing_shapes(records, geoms, levels, lambda _line: None)
    assert out[0][0].equals(geoms[0])


def test_the_layers_are_lines_that_are_off_and_the_date_line_source_is_public_domain():
    layers = load_layers(["base", "graticule"], CONFIG_DIR)
    for key in ("graticule", "special-lines"):
        d = layers[key].definition()
        assert d["geometry"] == "line" and d["switched_on"] is False and d["group"] == "Graticule"
    source = load_sources(CONFIG_DIR)["naturalearth-geographic-lines"]
    assert source.licence == "Public domain"


def test_a_line_on_a_pack_tile_edge_is_not_lost_in_the_cutting():
    from mapdata.stages import pack_write

    assert not pack_write.cut_to_rect(graticule.parallel(0.0), (0.0, 0.0, 90.0, 45.0)).is_empty
    assert not pack_write.cut_to_rect(graticule.meridian(0.0), (0.0, 0.0, 90.0, 45.0)).is_empty
