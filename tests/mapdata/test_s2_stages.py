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
