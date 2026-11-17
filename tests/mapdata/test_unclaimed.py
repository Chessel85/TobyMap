"""P3-T26b (DP205): unclaimed land under 1 square kilometre left out, the rest named by a place near it."""
import shapely

from mapdata.stages import unclaimed


def square(lon, lat, deg):
    return shapely.box(lon, lat, lon + deg, lat + deg)


def test_small_unclaimed_land_is_left_out_and_the_rest_named_by_the_nearest_place():
    records = [
        {"id": "unclaimed:a", "layer": "countries", "type": "unclaimed land", "name": "Unclaimed"},   # about 150 km2
        {"id": "unclaimed:b", "layer": "countries", "type": "unclaimed land", "name": "Unclaimed"},   # under 1 km2
        {"id": "unclaimed:c", "layer": "countries", "type": "unclaimed land", "name": "Unclaimed",
         "dispute": {"name": "Doumera Island"}},                                                      # small, disputed
        {"id": "unclaimed:bir-tawil", "layer": "countries", "type": "unclaimed land", "name": "Bir Tawil"},
        {"id": "t:1", "layer": "towns", "type": "town", "name": "Tantéga"},
        {"id": "i:1", "layer": "islands", "type": "island", "name": "Unnamed island"},
        {"id": "i:2", "layer": "islands", "type": "island", "name": "Diaoyu Island;Uotsurijima Island"},
    ]
    geoms = [square(0.9, 11.0, 0.11), square(5.0, 5.0, 0.001), square(43.1, 12.7, 0.001), square(33.2, 21.8, 0.4),
             shapely.Point(1.2, 11.2), shapely.Point(0.95, 11.05), square(43.2, 12.8, 0.01)]
    lines = []
    out, shapes, left_out = unclaimed.tidy(records, geoms, None, lines.append)
    assert left_out == 1 and len(out) == len(shapes) == 6
    by_id = {r["id"]: r for r in out}
    assert "unclaimed:b" not in by_id
    assert by_id["unclaimed:a"]["name"] == "Unclaimed land near Tantéga, 11.1 N, 1.0 E"   # not the unnamed island
    assert by_id["unclaimed:c"]["name"] == "Unclaimed land near Diaoyu Island, 12.7 N, 43.1 E"
    assert by_id["unclaimed:bir-tawil"]["name"] == "Bir Tawil"
    assert any(line.startswith("Left out: unclaimed land of 0.012 km2") for line in lines)
