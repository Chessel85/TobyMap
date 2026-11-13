"""The Phase 3 samples in the test pack (P3-T0d; LOC-2, NAV-4, INF-5).

Made by tools/make_phase3_samples.py from the planet file. Hampshire and Wiltshire,
Switzerland and its neighbours, the Rhine, and the Bay of Biscay (P3-T1b) are in the
test pack now. The New Forest and the places with shared names wait for the work items
that add their layers: national parks and places.
"""
import json
from pathlib import Path

import pytest

from mapcore.geo import geodesy
from mapcore.store import Store

OSM = Path(__file__).resolve().parents[1] / "samples" / "osm"
FILES = {
    "hampshire-wiltshire.geojson": {"regions", "counties"},
    "new-forest.geojson": {"national_parks", "stations"},
    "switzerland-neighbours.geojson": {"countries"},
    "rhine.geojson": {"rivers"},
    "bay-of-biscay.geojson": {"seas"},
    "shared-names.geojson": {"places", "regions"},
}


@pytest.fixture(scope="module")
def store(test_pack):
    s = Store([test_pack])
    yield s
    s.close()


def names(areas):
    return [a.name for a in areas]


@pytest.mark.parametrize("name", sorted(FILES))
def test_each_sample_carries_the_odbl_notice_and_its_layers(name):
    data = json.loads((OSM / name).read_text(encoding="utf-8"))
    assert "Open Database License" in data["licence"] and "OpenStreetMap" in data["licence"]
    assert {f["properties"]["layer"] for f in data["features"]} == FILES[name]
    assert all(f["properties"]["id"].startswith("osm:") for f in data["features"])


def test_the_shared_names_are_shared():
    data = json.loads((OSM / "shared-names.geojson").read_text(encoding="utf-8"))
    count = {}
    for f in data["features"]:
        count[f["properties"]["name"]] = count.get(f["properties"]["name"], 0) + 1
    assert count == {"Paris": 2, "Portland": 2, "Newport": 2, "São Paulo": 2}


@pytest.mark.parametrize("lat, lon, expected", [
    (51.07, -1.80, ["Wiltshire", "England", "United Kingdom"]),    # Salisbury
    (51.27, -1.09, ["Hampshire", "England", "United Kingdom"]),    # Basingstoke
    (51.56, -1.78, ["Swindon", "England", "United Kingdom"]),      # north of the Channel sample's box
])
def test_hampshire_and_wiltshire_are_whole(store, lat, lon, expected):
    assert names(store.at(lat, lon)) == expected


@pytest.mark.parametrize("lat, lon, country", [
    (46.95, 7.45, "Switzerland"),      # Bern
    (47.14, 9.52, "Liechtenstein"),    # Vaduz
    (47.99, 7.85, "Germany"),          # Freiburg
    (45.46, 9.19, "Italy"),            # Milan
    (47.27, 11.39, "Austria"),         # Innsbruck
    (47.75, 7.34, "France"),           # Mulhouse
])
def test_switzerland_and_its_neighbours(store, lat, lon, country):
    assert names(store.at(lat, lon))[-1] == country


def test_france_stays_one_area_from_the_channel_to_the_alps(store):
    for lat, lon in ((50.5, 1.8), (48.85, 2.35), (47.75, 7.34)):
        assert [a.id for a in store.at(lat, lon) if a.layer == "countries"] == ["osm:r1403916"]


def test_a_step_north_across_the_rhine_at_rheinfelden_crosses_it(store):
    path = geodesy.step_meridian(47.545, 7.79, 2000).path      # from Switzerland into Germany
    assert [c.area.name for c in store.crossed_lines(path, layers={"rivers"})] == ["Rhine"]
    assert names(store.at(47.545, 7.79))[-1] == "Switzerland"
    assert names(store.at(47.563, 7.79))[-1] == "Germany"


def test_where_am_i_in_the_bay_of_biscay_says_the_bay_then_the_ocean(store):
    # P3-T1b, DAT-4, LOC-6: the Seas layer is below the ocean, so Within lists the bay, then the ocean.
    assert names(store.at(44.5, -3.5)) == ["Bay of Biscay", "North Atlantic Ocean"]
    bay = next(a for a in store.at(44.5, -3.5) if a.layer == "seas")
    assert bay.record["type"] == "bay"
    assert names(store.at(43.45, -2.95))[0] == "Bay of Biscay"     # off Bilbao, near the coast
    assert names(store.at(49.5, -12.0)) == ["North Atlantic Ocean"]   # open ocean has no sea
