"""Disputed areas (P3-T2c; ANN-6, DAT-8, DP119, DP104, LOC-6).

Land two countries hold, such as Crimea, becomes a disputed area of its own with both as
claimants, with equal credit; Natural Earth's disputed areas mark the areas inside them, with its
view. The test pack's Crimea sample has Ukraine and Russia both holding Crimea, as their
OpenStreetMap outlines do, and Natural Earth's Crimea.
"""
import pytest
import shapely

from mapcore.packs.pack import Pack
from mapcore.session import MapSession
from mapdata.stages import disputes

SIMFEROPOL = {"lat": 44.95, "lon": 34.1, "zoom_m": 25000, "step_m": 25000}
KHERSON = {"lat": 46.6, "lon": 33.5, "zoom_m": 25000, "step_m": 25000}
CRIMEA, RUSSIA, UKRAINE, AR_CRIMEA = "disputed:crimea", "osm:r60189", "osm:r60199", "osm:r72639"


def spoken(response):
    return [a["text"] for a in response.announcements if a["channel"] == "speech"]


def session_at(test_pack, where):
    s = MapSession(packs=[test_pack], saved_state=dict(where))
    s.start()
    return s


@pytest.fixture(scope="module")
def records(test_pack):
    with Pack(test_pack, check_app=False) as p:
        return {r["id"]: r for r in (p.feature(n) for n in range(p.manifest["features"]["count"]))}


def test_in_crimea_where_am_i_says_crimea_disputed(test_pack):
    s = session_at(test_pack, SIMFEROPOL)
    assert spoken(s.press("Space")) == ["Autonomous Republic of Crimea, Crimea, disputed"]
    s.store.close()


def test_crimeas_details_name_russia_and_ukraine_as_claimants_and_natural_earths_view(test_pack):
    s = session_at(test_pack, SIMFEROPOL)
    s.run("panel.select", item=CRIMEA)
    lines = s.details().splitlines()
    s.store.close()
    assert lines[:5] == ["Crimea", "Type: disputed land", "This land is disputed.", "Claimed by: Russia, Ukraine",
                         "Natural Earth: Administered by Russia. Claimed by Ukraine."]
    assert any(line.startswith("Source: OpenStreetMap") for line in lines)


def test_the_land_is_in_neither_country_and_every_point_is_still_in_one(records, test_pack):
    rec = records[CRIMEA]
    assert rec["layer"] == "countries" and rec["disputed"] and rec["claimants"] == [RUSSIA, UKRAINE]
    assert 25_000 < rec["area_km2"] < 27_000
    s = session_at(test_pack, SIMFEROPOL)
    at = [a.id for a in s.areas]
    assert CRIMEA in at and RUSSIA not in at and UKRAINE not in at
    s.store.close()
    s = session_at(test_pack, KHERSON)                    # the mainland is still Ukraine's
    assert spoken(s.press("Space")) == ["Ukraine"]
    s.store.close()


def test_a_region_inside_natural_earths_area_is_marked_with_its_view(records):
    rec = records[AR_CRIMEA]
    assert rec["disputed"] and rec["dispute"] == {"name": "Crimea", "source": "Natural Earth",
                                                  "view": "Administered by Russia. Claimed by Ukraine."}


def test_natural_earths_notes_are_said_in_full_words():
    assert disputes.plain_note("Self admin.; Claimed by Azer.") == "Self-administered. Claimed by Azerbaijan."
    assert disputes.plain_note("Admin. By U.K.; Claimed by Spain") == ("Administered by the United Kingdom. "
                                                                       "Claimed by Spain.")


class Ctx:
    """Enough of a stage's context for make_held_twice and the held-twice-in-one-layer rule."""
    def __init__(self, settings):
        self.settings, self.earlier, self.lines = settings, {}, []

        class P:
            line = log = self.lines.append
        self.progress = P()


def test_a_held_twice_area_under_the_size_limit_is_left_as_it_is():
    a = shapely.box(0, 0, 1, 1)
    b = shapely.box(0.99999, 0, 2, 1)       # overlaps a by a strip about 1 metre wide
    records = [{"id": "x:a", "name": "A", "layer": "countries"}, {"id": "x:b", "name": "B", "layer": "countries"}]
    ctx = Ctx({"min_km2": 1})
    assert disputes.make_held_twice(ctx, records, [a, b]) == []
    assert len(records) == 2


def test_land_held_twice_gets_a_plain_name_when_none_is_given_and_is_cut_from_both():
    a, b = shapely.box(0, 0, 1, 1), shapely.box(0.5, 0, 2, 1)
    records = [{"id": "x:a", "name": "Aland", "layer": "countries", "colour": 1},
               {"id": "x:b", "name": "Bland", "layer": "countries", "colour": 2}]
    geoms = [a, b]
    made = disputes.make_held_twice(Ctx({}), records, geoms)
    assert made == ["disputed:a-b"]
    assert records[2]["name"] == "Land claimed by Aland and Bland" and records[2]["claimants"] == ["x:a", "x:b"]
    assert records[2]["colour"] not in (1, 2)
    assert geoms[0].intersection(geoms[2]).area == pytest.approx(0) and geoms[1].intersection(geoms[2]).area \
        == pytest.approx(0)
    assert geoms[0].area + geoms[1].area + geoms[2].area == pytest.approx(shapely.union(a, b).area)


def test_a_claimant_not_in_the_countries_layer_is_the_area_of_it_that_held_the_land(tmp_path):
    """France holds Mont Blanc's summit in its outline, but the Countries layer has metropolitan France."""
    import json

    import shapely as sh

    join, read = tmp_path / "join", tmp_path / "read"
    join.mkdir()
    read.mkdir()
    (join / "join.json").write_text(json.dumps({"overlaps": [["countries", ["x:france", "x:italy"], 1.0]]}))
    from mapdata.pipeline import features

    features.save(read, [{"id": "x:france"}, {"id": "x:italy"}], [sh.box(0, 0, 1.2, 1), sh.box(1, 0, 2, 1)])
    records = [{"id": "x:metro", "name": "France", "layer": "countries", "colour": 1},
               {"id": "x:italy", "name": "Italy", "layer": "countries", "colour": 2}]
    geoms = [sh.box(0, 0, 1.1, 1), sh.box(1.1, 0, 2, 1)]
    ctx = Ctx({})
    ctx.earlier = {"join": join, "osm-areas": read}
    made = disputes.make_held_twice(ctx, records, geoms)
    assert made and records[2]["claimants"] == ["x:metro", "x:italy"]
    assert records[2]["name"] == "Land claimed by France and Italy"
