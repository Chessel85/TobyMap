"""The world sample store: which country is at a point, and the nearest countries (P0-T8)."""
import pytest

from mapcore.store.world_sample import WorldSample


@pytest.fixture(scope="module")
def world():
    return WorldSample.load()


def test_sample_has_all_countries(world):
    assert len(world.countries) == 177
    assert world.by_id("ne:FRA").name == "France"


@pytest.mark.parametrize("lat, lon, name", [
    (48.86, 2.35, "France"),
    (40.42, -3.70, "Spain"),
    (52.0, -1.0, "United Kingdom"),
    (-25.0, 134.0, "Australia"),
    (-17.8, 178.0, "Fiji"),          # near the antimeridian
    (66.0, 175.0, "Russia"),         # Chukotka, east of 180 is west longitude in the file
    (-29.5, 28.3, "Lesotho"),        # a hole in South Africa
    (-30.0, 24.0, "South Africa"),
])
def test_country_at(world, lat, lon, name):
    country = world.country_at(lat, lon)
    assert country is not None and country.name == name


@pytest.mark.parametrize("lat, lon", [(30.0, -40.0), (0.0, 0.0), (-50.0, -120.0)])
def test_sea_is_none(world, lat, lon):
    assert world.country_at(lat, lon) is None


def test_nearest_countries_are_sorted_and_skip_the_current(world):
    near = world.nearest(48.86, 2.35, count=5, exclude="ne:FRA")
    names = [c.name for c, _km, _b in near]
    assert "France" not in names
    kms = [km for _c, km, _b in near]
    assert kms == sorted(kms)
    assert {"Belgium", "Luxembourg", "Switzerland"} & set(names)
