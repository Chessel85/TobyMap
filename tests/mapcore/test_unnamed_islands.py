"""An unnamed island barely parted from bigger land is not said (P3-T32e, DP87, DP169, LOC-2).

On the world pack of 20 November, Ceuta's old town is land the Foso de San Felipe, a moat about 20 metres wide,
cuts off from the rest of Ceuta, so the build made it an island with no name, and the place was said as
"Unnamed island, Ceuta, ...". The Peloponnese, cut off by the Corinth Canal, and Cape Ann, cut off by the
Annisquam River, were the same. An unnamed island that land bigger than it, of its own country, comes within
PARTED_M of is not said; a real unnamed island, such as one 1 kilometre off the coast, still is (DP87).

The shapes are made here, as the test pack has no unnamed island.
"""
from types import SimpleNamespace

import pytest
import shapely

from mapcore.session import MapSession
from mapcore.store import store as store_mod

DEG_M = 111_320.0   # metres in a degree at the equator, where these shapes are


def area(i, name, layer, **record):
    return SimpleNamespace(id=i, name=name, layer=layer, rank=1, record={"id": i, "layer": layer, **record})


def island(i="island:unnamed:0.5:0.5", km2=12.0, bbox=(0.0, 0.0, 0.03, 0.03), name="Unnamed island"):
    return area(i, name, "islands", type="unnamed island" if name == "Unnamed island" else "island",
                area_km2=km2, bbox=list(bbox))


@pytest.fixture
def store(test_pack, monkeypatch):
    """A store whose features, relationships and shapes are the test's own."""
    s = store_mod.Store(test_pack)
    s.made = {"features": {}, "shapes": {}, "islands_at": []}
    monkeypatch.setattr(s, "feature", lambda i: s.made["features"].get(i))
    monkeypatch.setattr(s, "relationships", lambda i: {"in": ["country"]} if i.startswith("island") else {})
    monkeypatch.setattr(s, "_parts", lambda a, boxes: [s.made["shapes"][a.id]])
    monkeypatch.setattr(s, "_pieces_with_tiles", lambda a, boxes: [(s.made["shapes"][a.id], (-1.0, -1.0, 1.0, 1.0))])
    monkeypatch.setattr(s, "at", lambda lat, lon, layers=None: [
        a for a, g in s.made["islands_at"] if g.covers(shapely.Point(lon, lat))])
    yield s
    s.close()


def make(store, isl, land):
    """The island and its country, whose land is the island and `land`."""
    shape = shapely.box(*isl.record["bbox"])
    store.made["features"][isl.id] = isl
    store.made["features"]["country"] = area("country", "Spain", "countries", bbox=[-1, -1, 1, 1])
    store.made["shapes"][isl.id] = shape
    store.made["shapes"]["country"] = shapely.union_all([shape, *land])


def east_of_island(gap_m, width_deg=0.5, height=(0.0, 0.03)):
    w = 0.03 + gap_m / DEG_M
    return shapely.box(w, height[0], w + width_deg, height[1] + 0.2)


def test_an_unnamed_island_a_canal_parts_from_the_mainland_is_barely_parted(store):
    isl = island()
    make(store, isl, [east_of_island(20)])
    assert store.barely_parted(isl.id)


def test_the_mainland_cut_by_a_pack_tile_edge_is_still_the_mainland(store, monkeypatch):
    """The mainland's piece beside the gap is under 1 square kilometre in its pack tile, but it goes on into the
    next, so the land round the gap is measured whole."""
    isl = island()
    make(store, isl, [east_of_island(20)])
    edge = 0.0305
    country = store.made["shapes"]["country"]
    tiled = {isl.id: [(store.made["shapes"][isl.id], (-1.0, -1.0, edge, 1.0))],
             "country": [(shapely.clip_by_rect(country, -1.0, -1.0, edge, 1.0), (-1.0, -1.0, edge, 1.0)),
                         (shapely.clip_by_rect(country, edge, -1.0, 1.0, 1.0), (edge, -1.0, 1.0, 1.0))]}
    monkeypatch.setattr(store, "_pieces_with_tiles", lambda a, boxes: tiled[a.id])
    assert store.barely_parted(isl.id)


def test_an_unnamed_island_a_kilometre_off_the_coast_is_not(store):
    isl = island()
    make(store, isl, [east_of_island(1000)])
    assert not store.barely_parted(isl.id)


def test_a_rock_beside_an_unnamed_island_does_not_part_it(store):
    """Land under 1 square kilometre with no island of its own is a rock or an islet, not the mainland."""
    isl = island()
    rock = shapely.box(0.0302, 0.01, 0.0305, 0.0103)
    make(store, isl, [rock])
    assert not store.barely_parted(isl.id)


def test_a_bigger_island_across_a_narrow_channel_parts_it_and_a_smaller_one_does_not(store):
    isl = island()
    other = shapely.box(0.0302, 0.0, 0.07, 0.04)
    make(store, isl, [other])
    big = island("island:big", km2=20.0, bbox=other.bounds, name="Big Island")
    store.made["islands_at"] = [(big, other)]
    assert store.barely_parted(isl.id)
    store.made["islands_at"] = [(island("island:small", km2=5.0, bbox=other.bounds, name="Small Island"), other)]
    store._parted.clear()
    assert not store.barely_parted(isl.id)


def test_a_named_island_is_never_barely_parted(store):
    isl = island("osm:w1", name="Isla de Ceuta")
    make(store, isl, [east_of_island(20)])
    assert not store.barely_parted(isl.id)


@pytest.fixture
def session(test_pack, monkeypatch):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000})
    s.start()
    monkeypatch.setattr(s.store, "relationships", lambda i: {})
    yield s
    s.store.close()


def test_the_place_is_said_without_an_unnamed_island_barely_parted(session, monkeypatch):
    monkeypatch.setattr(session.store, "barely_parted", lambda i: i == "island:unnamed:35.8957:-5.2904")
    ceuta = [area("island:unnamed:35.8957:-5.2904", "Unnamed island", "islands", type="unnamed island"),
             area("ce", "Ceuta", "counties"), area("af", "Africa", "continents")]
    assert [str(a.name) for a in session._said(ceuta)] == ["Ceuta", "Africa"]
    skye = [area("island:unnamed:57.1:-6.4", "Unnamed island", "islands", type="unnamed island"),
            area("hi", "Highland", "counties")]
    assert [str(a.name) for a in session._said(skye)] == ["Unnamed island", "Highland"]
