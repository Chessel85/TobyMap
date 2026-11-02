"""Spike S2 pipeline stages on tiny made-up shapes: no data folder, no network (P0-T5, AD-15, DAT-3)."""
import numpy as np
import pytest
import shapely

from mapdata.stages import clip, fetch
from mapdata.stages.geodesy import area_km2


def land_pieces():
    # Land: a big square split into four pieces (as the OSM land polygons are
    # split), plus a small island. The sea is everything else.
    big = [shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1), shapely.box(0, 1, 1, 2), shapely.box(1, 1, 2, 2)]
    island = shapely.box(3, 0.5, 3.2, 0.7)
    return np.array(big + [island], dtype=object)


def test_clip_removes_the_sea_and_keeps_islands():
    land = clip.Land(land_pieces())
    # A country whose boundary includes territorial waters around its land and the island.
    country = shapely.box(-0.5, -0.5, 3.5, 2.5)
    out = land.clip(country)
    assert out.area == pytest.approx(4 + 0.04)
    assert len(shapely.get_parts(out)) == 2


def test_clip_of_an_inland_area_is_unchanged():
    land = clip.Land(land_pieces())
    inland = shapely.box(0.5, 0.5, 1.5, 1.5)
    assert land.clip(inland).equals(inland)


def test_neighbours_still_fit_exactly_when_the_land_pieces_overlap():
    # The real OSM land pieces overlap by a thin band at each split line
    # (about 0.0005 degrees). Cutting two neighbours to them must not leave
    # extra points on one side of their shared border only.
    band = 0.0005
    pieces = np.array([shapely.box(0, 0, 1 + band, 2), shapely.box(1 - band, 0, 2, 2)], dtype=object)
    land = clip.Land(pieces)
    # A slanted shared border, crossing the overlap band, with sea beyond y = 2.
    north = shapely.Polygon([(-1, 3), (3, 3), (3, 1.2), (-1, 0.8)])
    south = shapely.Polygon([(-1, -1), (3, -1), (3, 1.2), (-1, 0.8)])
    assert shapely.coverage_is_valid(np.array([north, south], dtype=object))
    cut = np.array([land.clip(north), land.clip(south)], dtype=object)
    assert shapely.coverage_is_valid(cut)
    assert sum(g.area for g in cut) == pytest.approx(4)


def test_coverage_cleaning_fixes_neighbours_that_overlap():
    # OSM's own borders sometimes overlap (Burgos and Soria in spike S2).
    # Cleaning gives the overlap to one of them, so the layer can be simplified
    # as one coverage.
    west = shapely.box(0, 0, 1.01, 1)
    east = shapely.box(1, 0, 2, 1)
    layer = np.array([west, east], dtype=object)
    assert not shapely.coverage_is_valid(layer)
    cleaned = shapely.coverage_clean(layer)
    assert shapely.coverage_is_valid(cleaned)
    assert sum(g.area for g in cleaned) == pytest.approx(2)
    assert shapely.coverage_is_valid(shapely.coverage_simplify(cleaned, 0.01))


def test_clip_of_sea_is_empty():
    assert clip.Land(land_pieces()).clip(shapely.box(5, 5, 6, 6)).is_empty


def test_gaps_find_land_in_no_member_and_name_the_neighbour():
    land_square = shapely.box(0, 0, 2, 2)
    west = shapely.box(0, 0, 1, 2)
    east = shapely.box(1.01, 0, 2, 2)           # leaves a thin strip between them
    found = clip.gaps(land_square, [west, east], ["West", "East"])
    assert len(found) == 1
    assert found[0].area_km2 == pytest.approx(area_km2(shapely.box(1, 0, 1.01, 2)), rel=1e-6)
    assert found[0].near in ("West", "East")
    assert clip.gaps(land_square, [shapely.box(0, 0, 1, 2), shapely.box(1, 0, 2, 2)], ["W", "E"]) == []


def test_polygonal_keeps_only_the_areas():
    mixed = shapely.GeometryCollection([shapely.box(0, 0, 1, 1), shapely.LineString([(2, 2), (3, 3)]),
                                        shapely.MultiPolygon([shapely.box(5, 5, 6, 6), shapely.box(7, 7, 8, 8)]),
                                        shapely.Point(9, 9)])
    out = clip.polygonal(mixed)
    assert out.geom_type == "MultiPolygon"
    assert len(out.geoms) == 3 and out.area == pytest.approx(3)
    assert clip.polygonal(shapely.GeometryCollection([shapely.Point(0, 0)])).is_empty
    square = shapely.box(0, 0, 1, 1)
    assert clip.polygonal(square) is square
    # The coverage tools accept the result.
    shapely.coverage_simplify(np.array([out, shapely.box(10, 10, 11, 11)], dtype=object), 0.01)


def test_gaps_accept_a_member_that_is_a_geometry_collection():
    # make_valid can return a GeometryCollection, which has no boundary.
    land_square = shapely.box(0, 0, 2, 2)
    west = shapely.GeometryCollection([shapely.box(0, 0, 1, 2), shapely.LineString([(0, 0), (0, 3)])])
    east = shapely.box(1.2, 0, 2, 2)
    found = clip.gaps(land_square, [west, east, shapely.Polygon()], ["West", "East", "Empty"])
    assert len(found) == 1
    assert found[0].near in ("West", "East")


def test_area_on_the_earth():
    # One degree square at the equator is about 12,364 km2.
    assert area_km2(shapely.box(0, 0, 1, 1)) == pytest.approx(12364, rel=0.003)
    # At 60 degrees north it is about half that.
    assert area_km2(shapely.box(0, 59.5, 1, 60.5)) == pytest.approx(12364 * 0.5, rel=0.01)


def test_fetch_writes_only_into_the_downloads_folder(tmp_path):
    source_file = tmp_path / "source" / "data.zip"
    source_file.parent.mkdir()
    source_file.write_bytes(b"x" * 3000)
    src = fetch.Source("test", source_file.as_uri(), "test-folder", "Public domain", "A test.")
    downloads = tmp_path / "tobymap" / "downloads"
    lines = []
    out = fetch.fetch(src, downloads, say=lines.append)
    assert out == downloads / "test-folder" / "data.zip"
    assert out.read_bytes() == b"x" * 3000
    assert not list(downloads.rglob("*.part"))
    again = fetch.fetch(src, downloads, say=lines.append)
    assert again == out and "already downloaded" in lines[-1]
