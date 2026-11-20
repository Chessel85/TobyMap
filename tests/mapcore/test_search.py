"""P3-T8a and P3-T8b: the search index and searching in the core (SRB-1, SRB-2, NAV-8, ACC-9, INF-8).

On the test pack, whose samples have two Parises, two Portlands, two Newports, and Sao Paulo the city and the
state (tests/samples/osm/shared-names.geojson). The test pack has no London and no Ile-de-France round Paris,
so "londn" is tried on Southampton, and Paris's region on the Western Europe trial (docs/plan/phase-3.md).
"""
import io

import pytest

from mapcore import search
from mapcore.packs.pack import Pack, PackWriteError, PackWriter
from mapcore.session import MapSession
from mapdata.stages import search_index, wikidata

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}
PARIS, PARIS_TEXAS = "osm:n17807753", "osm:n105715620"
SAO_PAULO_STATE, SAO_PAULO_CITY = "osm:r298204", "osm:n30674098"


def said(r) -> str:
    return " ".join(a["text"] for a in r.announcements)


@pytest.fixture
def s(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(HAMPSHIRE))
    s.start()
    yield s
    s.store.close()


# Making names plain (architecture 7.9) ---------------------------------------------------------------------

def test_names_are_made_plain_without_accents_or_case():
    assert search.normalise("São Paulo") == "sao paulo"
    assert search.normalise("  Île-de-France ") == "ile de france"
    assert search.normalise("Côtes-d'Armor") == search.normalise("Cotes d’Armor") == "cotes darmor"
    assert search.normalise("Straße") == "strasse" and search.normalise("Ørsted") == "orsted"
    assert search.normalise("Łódź") == "lodz" and search.normalise("ÆRØ") == "aero"
    assert search.normalise("Москва") == "москва"   # a script without accents is kept, in lower case


def test_a_name_is_filed_under_its_words_but_not_small_ones():
    assert search.filed_under("isle of wight") == ["isl", "wig"]
    assert search.filed_under("new york") == ["new", "yor"]
    assert search.filed_under("st albans") == ["st", "alb"]
    assert search.looked_up("isle of wight") == ["isl", "wig"]
    assert search.looked_up("st") == ["st"]


def test_matching_levels_best_first():
    q = search.Query("Paris")
    assert q.match("paris") == (search.SAME, 1.0)
    assert q.match("parisot") == (search.STARTS, 1.0)
    assert search.Query("york").match("new york") == (search.WORDS, 1.0)
    level, similar = search.Query("Pariss").match("paris")
    assert level == search.CLOSE and similar > 0.7
    assert search.Query("londn").match("london")[0] == search.CLOSE
    assert search.Query("paris").match("lyon") is None


# The index in the pack (P3-T8a) -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pack(test_pack):
    with Pack(test_pack, check_app=False) as p:
        yield p


def test_the_pack_has_search_records_and_a_search_never_reads_the_whole_index(pack, test_pack):
    info = pack.manifest["search"]
    assert info["buckets"] >= 1 and info["rows"] > 100
    keys = [k for k in pack.keys() if k.startswith("search/")]
    assert keys and len(keys) <= info["buckets"]
    from mapcore.store.store import Store

    store = Store([test_pack])
    store.search("Paris")
    read = store.packs[0].reads
    store.search("Pariss")   # the same prefix: its record is kept, so nothing more is read
    assert store.packs[0].reads == read
    store.close()


def test_rows_are_the_index_format(pack):
    rows = [r for b in range(pack.search_buckets) for r in pack.search_rows(b)]
    assert all(len(r) == len(search.ROW) for r in rows)
    paris = next(r for r in rows if r[search.ID] == PARIS)
    assert paris[search.KEY] == "paris" and paris[search.NAME] == "Paris" and paris[search.LAYER] == "towns"
    assert paris[search.LON] == pytest.approx(2.348, abs=1e-3) and paris[search.LAT] == pytest.approx(48.853, abs=1e-3)
    assert 0 <= paris[search.IMPORTANCE] <= 1000


def test_unnamed_features_are_not_in_the_index(pack):
    rows = [r for b in range(pack.search_buckets) for r in pack.search_rows(b)]
    assert not any(r[search.NAME].startswith("Unnamed ") for r in rows)


def test_importance_counts_population_sites_rank_and_size():
    w = search_index.SETTINGS["weights"]
    town = {"layer": "towns", "rank": 8}
    big = search_index.importance({**town, "population": 2_000_000}, 250, w)
    small = search_index.importance({**town, "population": 25_000}, 60, w)
    assert 0 < small < big <= 1000
    # Wikidata's population wins over OpenStreetMap's
    assert search_index.importance({**town, "population": 10, "facts": {"population": {"value": 2_000_000}}},
                                   250, w) == big
    country = search_index.importance({"layer": "countries", "rank": 2, "area_km2": 500_000}, None, w)
    assert country > search_index.importance({"layer": "counties", "rank": 6, "area_km2": 500}, None, w)


def test_one_feature_found_two_ways_is_listed_once():
    made = [
        {"id": "a", "layer": "counties", "rank": 6, "names": {"en": "Paris"}, "wikidata": "Q90", "area_km2": 105,
         "point": [2.35, 48.86]},
        {"id": "b", "layer": "towns", "rank": 8, "names": {"en": "Paris"}, "wikidata": "Q90", "point": [2.35, 48.85]},
        {"id": "c", "layer": "towns", "rank": 8, "names": {"en": "Paris"}, "wikidata": "Q830149", "point": [-95.5, 33.7]},
        {"id": "d", "layer": "countries", "rank": 2, "names": {"en": "Hawaii"}, "named_from": "e", "point": [-155, 20]},
        {"id": "e", "layer": "regions", "rank": 4, "names": {"en": "Hawaii"}, "point": [-155, 20]},
    ]
    ids = sorted(r[search.ID] for r in search_index.rows(made, {}, {}))
    assert ids == ["a", "c", "d"]


def test_an_administrative_area_wins_and_nearly_the_same_land_is_one():
    made = [
        {"id": "bzh", "layer": "regions", "rank": 4, "names": {"en": "Brittany"}, "wikidata": "Q12130",
         "area_km2": 27_208, "point": [-3, 48]},
        {"id": "ne", "layer": "physical-regions", "rank": 3, "names": {"en": "Brittany"}, "wikidata": "Q12130",
         "area_km2": 30_000, "point": [-3, 48]},
        {"id": "iow", "layer": "counties", "rank": 6, "names": {"en": "Isle of Wight"}, "area_km2": 381.7,
         "point": [-1.3, 50.7]},
        {"id": "isl", "layer": "islands", "rank": 5, "names": {"en": "Isle of Wight"}, "area_km2": 369.0,
         "point": [-1.3, 50.7]},
        {"id": "gva", "layer": "regions", "rank": 4, "names": {"en": "Geneva"}, "area_km2": 282, "point": [6.1, 46.2]},
        {"id": "city", "layer": "counties", "rank": 6, "names": {"en": "Geneva"}, "area_km2": 18, "point": [6.1, 46.2]},
    ]
    rel = {"isl": {"in": ["iow"]}, "city": {"in": ["gva"]}}
    ids = sorted(r[search.ID] for r in search_index.rows(made, rel, {}))
    assert ids == ["bzh", "city", "gva", "iow"]   # the canton and the city of Geneva are two


def test_german_letters_typed_as_two_are_found():
    made = [{"id": "m", "layer": "counties", "rank": 6, "names": {"en": "Munich", "local": "München"},
             "point": [11.6, 48.1]}]
    got = {r[search.KEY]: r[search.VIA] for r in search_index.rows(made, {}, {})}
    assert got == {"munich": "", "munchen": "München", "muenchen": "München"}


def test_rows_are_stored_smaller_and_read_back_whole():
    row = ["paris", "Paris", "p1", "towns", 500, 2.348, 48.853, "Paris, Île-de-France, France", ""]
    kept = search_index.stored(row)
    assert kept[search.KEY] == "" and kept[search.DESCRIPTION] == "Île-de-France, France"
    alone = search_index.stored(["sao paulo", "São Paulo", "s", "regions", 1, 0, 0, "São Paulo", ""])
    assert alone[search.KEY] == "" and alone[search.DESCRIPTION] == ""
    via = search_index.stored(["deutschland", "Germany", "de", "countries", 1, 0, 0, "Germany, Europe", "Deutschland"])
    assert via[search.KEY] == "deutschland"


def test_descriptions_tell_features_of_one_name_apart():
    made = [
        {"id": "fr", "layer": "countries", "rank": 2, "names": {"en": "France"}, "point": [2, 47]},
        {"id": "idf", "layer": "regions", "rank": 4, "names": {"en": "Île-de-France"}, "point": [2, 48]},
        {"id": "us", "layer": "countries", "rank": 2, "names": {"en": "United States"}, "point": [-95, 38]},
        {"id": "tx", "layer": "regions", "rank": 4, "names": {"en": "Texas"}, "point": [-99, 31]},
        {"id": "p1", "layer": "towns", "rank": 8, "names": {"en": "Paris"}, "point": [2.35, 48.85]},
        {"id": "p2", "layer": "towns", "rank": 8, "names": {"en": "Paris"}, "point": [-95.5, 33.7]},
        {"id": "hs", "layer": "roads", "rank": 8, "names": {"en": "High Street"}, "point": [0, 51]},
        {"id": "hs2", "layer": "roads", "rank": 8, "names": {"en": "High Street"}, "point": [1, 51]},
        {"id": "uk", "layer": "countries", "rank": 2, "names": {"en": "United Kingdom"}, "point": [0, 52]},
        {"id": "kent", "layer": "counties", "rank": 6, "names": {"en": "Kent"}, "point": [0.7, 51.2]},
        {"id": "sx", "layer": "counties", "rank": 6, "names": {"en": "East Sussex"}, "point": [0.2, 50.9]},
        {"id": "eng", "layer": "regions", "rank": 4, "names": {"en": "England"}, "point": [-1, 52]},
        {"id": "rhine", "layer": "rivers", "rank": 8, "names": {"en": "Rhine"}, "point": [8, 48]},
        {"id": "ch", "layer": "countries", "rank": 2, "names": {"en": "Switzerland"}, "point": [8, 47]},
        {"id": "de", "layer": "countries", "rank": 2, "names": {"en": "Germany"}, "point": [10, 51]},
    ]
    rel = {"p1": {"in": ["idf", "fr"]}, "p2": {"in": ["tx", "us"]}, "idf": {"in": ["fr"]},
           "hs": {"partly": [["kent", 1.0], ["eng", 1.0], ["uk", 1.0]], "in": ["kent", "eng", "uk"]},
           "hs2": {"in": ["sx", "eng", "uk"]},
           # a line in several countries: those holding most of it first, not the order of its stored crossings
           "rhine": {"crosses": ["fr", "ch", "de"], "partly": [["de", 0.6], ["ch", 0.3], ["fr", 0.1]]}}
    text = {r[search.ID]: r[search.DESCRIPTION] for r in search_index.rows(made, rel, {})}
    assert text["p1"] == "Paris, Île-de-France, France"
    assert text["p2"] == "Paris, Texas, United States"
    assert text["idf"] == "Île-de-France, France"
    # the same words for two High Streets, so the county is added to each
    assert text["hs"] == "High Street, Kent, England, United Kingdom"
    assert text["hs2"] == "High Street, East Sussex, England, United Kingdom"
    assert text["rhine"] == "Rhine, Germany, Switzerland, France"


def test_the_writer_refuses_a_search_row_for_a_feature_not_in_the_pack():
    w = PackWriter(io.BytesIO())
    w.add_features([selfcheck_record("x:1")])
    with pytest.raises(PackWriteError):
        w.add_search(1, {0: [["a", "A", "x:2", "countries", 1, 0, 0, "A", ""]]}, 1)


def selfcheck_record(identifier: str) -> dict:
    return {"id": identifier, "source": "test", "layer": "countries", "type": "country", "names": {"en": "A"},
            "rank": 2, "area_km2": 1.0, "bbox": [0, 0, 1, 1], "width_km": 1.0, "colour": None, "point": [0.5, 0.5],
            "parents": []}


def test_a_pack_without_a_search_index_finds_nothing():
    from mapcore.store.store import Store

    buf = io.BytesIO()
    w = PackWriter(buf)
    w.add_features([selfcheck_record("x:1")])
    w.finish({"name": "t", "version": "1", "coverage": {"kind": "world"}, "app_versions": {"from": "0.0.1"},
              "sources": [{"name": "s", "licence": "ODbL 1.0", "date": "2026-11-13"}], "drawing_levels": []},
             "credit", [{"id": "countries", "name": "Countries"}])
    from mapcore.packs.source import MemorySource

    p = Pack(MemorySource(buf.getvalue()), check_app=False)
    assert p.search_buckets == 0 and Store([p]).search("A") == []


# Site counts from Wikidata (P3-T8a) ---------------------------------------------------------------------------

def test_site_counts_are_fetched_in_batches_and_kept():
    asked = []

    def query(text):
        asked.append(text)
        return {"results": {"bindings": [
            {"item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q90"},
             "n": {"type": "literal", "value": "251"}}]}}

    got = wikidata.fetch_sites(["Q90", "Q830149"], query=query, batch=500, sleep=lambda s: None,
                               today="2026-11-14", say=lambda s: None)
    assert got["Q90"] == {"id": "Q90", "fetched": "2026-11-14", "sites": 251}
    assert got["Q830149"]["sites"] == 0
    assert len(asked) == 1 and "wikibase:sitelinks" in asked[0]


def test_a_site_count_answer_cut_off_is_asked_for_in_halves():
    asked = []

    def query(text):
        asked.append(text.count("wd:"))
        if text.count("wd:") > 1:
            raise wikidata.CutOff("cut off")
        q = text.split("wd:")[1].split()[0]
        return {"results": {"bindings": [{"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"},
                                          "n": {"type": "literal", "value": "7"}}]}}

    got = wikidata.fetch_sites(["Q1", "Q2"], query=query, sleep=lambda s: None, today="2026-11-13",
                               say=lambda s: None)
    assert asked == [2, 1, 1] and got["Q1"]["sites"] == got["Q2"]["sites"] == 7


# Searching in the core (P3-T8b) --------------------------------------------------------------------------------

def test_sao_paulo_finds_sao_paulo_and_enter_goes_there(s):
    found = s.search("Sao Paulo")
    assert {f["id"] for f in found[:2]} == {SAO_PAULO_STATE, SAO_PAULO_CITY}
    assert all(f["name"] == "São Paulo" for f in found[:2])
    city = next(f for f in found if f["id"] == SAO_PAULO_CITY)
    zoom = s.world.zoom_m
    r = s.search_go(city["id"])
    assert said(r).startswith("São Paulo, Brazil")
    assert (s.world.lat, s.world.lon) == pytest.approx((-23.5507, -46.6334), abs=1e-3)
    assert s.world.zoom_m == zoom   # a place keeps the zoom (NAV-8)
    assert s.current_feature.id == SAO_PAULO_CITY


def test_an_area_found_is_zoomed_to_fit_and_alt_comma_comes_back(s):
    before = (s.world.lat, s.world.lon, s.world.zoom_m)
    state = next(f for f in s.search("Sao Paulo") if f["id"] == SAO_PAULO_STATE)
    s.search_go(state["id"])
    assert s.world.zoom_m > before[2]   # the state is wider than 1 km
    s.press("Alt+,", "map")
    assert (s.world.lat, s.world.lon, s.world.zoom_m) == pytest.approx(before, abs=1e-6)


def test_paris_in_france_comes_before_paris_in_texas(s):
    found = s.search("Paris")
    ids = [f["id"] for f in found]
    assert ids.index(PARIS) < ids.index(PARIS_TEXAS)
    assert found[0]["label"] == "Paris, France, city or town"
    assert next(f for f in found if f["id"] == PARIS_TEXAS)["description"] == "Paris, United States"


def test_small_misspellings_are_found(s):
    assert s.search("Pariss")[0]["id"] == PARIS
    assert s.search("Southamton")[0]["name"] == "Southampton"
    assert s.search("hampshre")[0]["name"] == "Hampshire"


def test_a_name_in_another_language_is_found_and_said(s):
    found = s.search("Swiss Confederation")
    assert found and found[0]["name"] == "Switzerland"
    assert found[0]["label"].endswith("found as Swiss Confederation")


def test_a_later_word_of_a_name_finds_it(s):
    assert any(f["name"] == "New Forest National Park" for f in s.search("forest"))
    assert any(f["name"] == "Isle of Wight" for f in s.search("wight"))


def test_narrowing_by_layer_place_and_feature(s):
    assert {f["layer"] for f in s.search("Paris", layers={"towns"})} == {"towns"}
    near = [f["id"] for f in s.search("Paris", near_m=500_000)]   # Paris is about 400 km from Hampshire
    assert PARIS in near and PARIS_TEXAS not in near
    assert s.search("Paris", near_m=100_000) == []
    # Southampton is a county of its own beside Hampshire, so it is inside England but not Hampshire
    hampshire = next(a for a in s.areas if a.name == "Hampshire")
    england = next(a for a in s.areas if a.name == "England")
    inside = [f["name"] for f in s.search("Southampton", inside=england.id)]
    assert "Southampton" in inside and "Southampton Central" in inside
    assert [f["name"] for f in s.search("Southampton", inside=hampshire.id)] == []
    assert [f["name"] for f in s.search("Itchen", inside=hampshire.id)] == ["River Itchen"]   # a line partly in it
    assert s.search("Paris", inside=england.id) == []
    assert [f["name"] for f in s.search("England", inside=england.id)] == ["England"]   # the feature itself


def test_measuring_to_a_result_does_not_move_you(s):
    here = (s.world.lat, s.world.lon)
    found = s.search("Paris")
    r = s.search_measure(found[0]["id"])
    assert (s.world.lat, s.world.lon) == here
    assert said(r).startswith("Paris, nearest point ")


def test_nothing_found_and_nothing_typed(s):
    assert s.search("") == [] and s.search("   ") == []
    assert s.search("Xyzzyqqq") == []


# Ranking (P3-T32f, SRB-1): a word for the kind of feature, and nearness -----------------------------------------

def test_a_word_for_the_kind_of_feature_does_not_lower_the_match():
    q = search.Query("thames")
    assert q.match("river thames") == q.match("thames river") == q.match("thames") == (search.SAME, 1.0)
    assert search.Query("river thames").match("thames river") == (search.SAME, 1.0)
    assert q.match("thamesmead") == (search.STARTS, 1.0)
    assert q.match("thames ditton") == (search.STARTS, 1.0)
    assert search.Query("wight").match("isle of wight") == (search.SAME, 1.0)
    assert search.Query("michigan").match("lake michigan") == (search.SAME, 1.0)
    assert search.Query("river").match("river") == (search.SAME, 1.0)   # the kind word alone is still a name
    assert search.Query("river").match("river thames")[0] == search.STARTS
    assert search.Query("new forest").match("new") is None   # "forest" is not a kind word: a forest has its name


def test_nearness_counts_a_little_towards_importance():
    assert search.nearness(0) == search.NEAR_POINTS
    assert search.nearness(None) == 0
    near, far, farthest = search.nearness(20_000), search.nearness(6_000_000), search.nearness(20_000_000)
    assert search.NEAR_POINTS > near > far > farthest >= 0
    # A place nearby wins over a slightly better known one far away, but not over a far better known one
    assert search.rank_key(4, 1.0, 457, "Winchester", "a", near) < search.rank_key(4, 1.0, 491, "Winchester", "b", far)
    assert search.rank_key(4, 1.0, 681, "Paris", "a", far) < search.rank_key(4, 1.0, 430, "Paris", "b", near)


def _store_of(rows):
    from mapcore.packs.source import MemorySource
    from mapcore.store.store import Store

    buf = io.BytesIO()
    w = PackWriter(buf)
    w.add_features([selfcheck_record(r[search.ID]) for r in rows])
    n, records = search_index.buckets(rows)
    w.add_search(n, records, len(rows))
    w.finish({"name": "t", "version": "1", "coverage": {"kind": "world"}, "app_versions": {"from": "0.0.1"},
              "sources": [{"name": "s", "licence": "ODbL 1.0", "date": "2026-11-13"}], "drawing_levels": []},
             "credit", [{"id": "countries", "name": "Countries"}])
    return Store([Pack(MemorySource(buf.getvalue()), check_app=False)])


WINCHESTER_HERE = (51.06, -1.31)   # in Hampshire


def test_the_nearest_of_equals_comes_first_and_a_kind_word_is_no_worse():
    rows = [
        ["m3", "M3", "m:ir", "roads", 19, 48.876, 38.441, "M3, Iran", ""],
        ["m3", "M3", "m:mw", "roads", 19, 35.216, -15.057, "M3, Malawi", ""],
        ["m3", "M3", "m:ni", "roads", 19, -5.915, 54.601, "M3, Northern Ireland, United Kingdom", ""],
        ["m3", "M3", "m:en", "roads", 19, -0.935, 51.277, "M3, England, United Kingdom", ""],
        ["winchester", "Winchester", "w:va", "counties", 491, -78.173, 39.168, "Winchester, Virginia", ""],
        ["winchester", "Winchester", "w:en", "towns", 457, -1.313, 51.061, "Winchester, England", ""],
        ["thames river", "Thames River", "t:ca", "rivers", 197, -81.479, 42.784, "Thames River, Ontario", ""],
        ["river thames", "River Thames", "t:uk", "rivers", 330, -0.757, 51.565, "River Thames, United Kingdom", ""],
        ["paris", "Paris", "p:fr", "counties", 681, 2.32, 48.861, "Paris, France", ""],
        ["paris", "Paris", "p:tx", "towns", 430, -95.556, 33.662, "Paris, Texas", ""],
    ]
    store = _store_of(sorted(rows, key=lambda r: (r[0], r[2])))
    ids = lambda text, here: [f.id for f in store.search(text, here=here)]
    assert ids("m3", WINCHESTER_HERE)[:2] == ["m:en", "m:ni"]
    assert ids("winchester", WINCHESTER_HERE)[0] == "w:en"
    assert ids("winchester", None)[0] == "w:va"   # with nowhere to be near, importance alone
    assert ids("thames", WINCHESTER_HERE)[0] == "t:uk"
    assert ids("thames", (42.98, -81.25))[0] == "t:uk"   # from London, Ontario: still the better known
    assert ids("paris", (33.66, -95.55))[0] == "p:fr"   # from Paris, Texas: France's is far better known


def test_the_session_ranks_from_where_you_are(test_pack):
    oregon, maine = "osm:n1666626393", "osm:n158867610"
    for place, first in ((HAMPSHIRE, oregon), ({**HAMPSHIRE, "lat": 43.66, "lon": -70.26}, maine)):
        s = MapSession(packs=[test_pack], saved_state=dict(place))
        s.start()
        try:
            assert s.search("Portland", layers={"towns"})[0]["id"] == first
        finally:
            s.store.close()


def test_a_kind_word_lets_importance_choose():
    rows = [
        ["lake michigan", "Lake Michigan", "l:mi", "lakes", 386, -87.0, 44.0, "Lake Michigan", ""],
        ["michigan", "Michigan", "r:mi", "regions", 806, -85.0, 44.0, "Michigan, United States", ""],
        ["michigan", "Michigan", "i:mi", "islands", 75, 55.2, 25.1, "Michigan, Dubai", ""],
    ]
    store = _store_of(sorted(rows, key=lambda r: (r[0], r[2])))
    assert [f.id for f in store.search("michigan")] == ["r:mi", "l:mi", "i:mi"]


# Results said with the same words (P3-T32j, SRB-1, ACC-9) ----------------------------------------------------
# On the world pack "winchester" listed "Winchester Inlet, Hudson Bay" three times: three features of one inlet
# in OpenStreetMap, two points and a relation about 6 km apart. Two islands named "St. John Island" in one part of
# Newfoundland and Labrador, 350 km apart, were also said with the same words.

def _found_as(s, monkeypatch, rows):
    """Make the store's search give these results, each (id, description, lat, lon), all named "Paris"."""
    import dataclasses
    real = s.store.search("Paris", 50)
    by_id = {f.id: f for f in real}
    made = [dataclasses.replace(by_id[i], description=d, lat=lat, lon=lon, via="") for i, d, lat, lon in rows]
    asked = []

    def fake(text, limit=20, *a, **k):
        asked.append(limit)
        return made[:limit]
    monkeypatch.setattr(s.store, "search", fake)
    return asked


def test_results_said_with_the_same_words_far_apart_are_told_apart_by_distance_and_direction(s, monkeypatch):
    _found_as(s, monkeypatch, [(PARIS, "Paris", 48.86, 2.35), (PARIS_TEXAS, "Paris", 33.66, -95.55)])
    found = s.search("Paris")
    assert [f["id"] for f in found] == [PARIS, PARIS_TEXAS]
    labels = [f["label"] for f in found]
    assert labels[0].startswith("Paris, city or town, ") and labels[0].endswith(" kilometres south-east")
    assert labels[1].startswith("Paris, city or town, ") and " kilometres " in labels[1]
    assert len(set(labels)) == 2


def test_results_said_with_the_same_words_at_the_same_spot_are_listed_once(s, monkeypatch):
    # From Hampshire, two features 6 km apart and 400 km away are the same distance and direction in words.
    _found_as(s, monkeypatch, [(PARIS, "Paris", 48.86, 2.35), (PARIS_TEXAS, "Paris", 48.88, 2.40)])
    found = s.search("Paris")
    assert [f["id"] for f in found] == [PARIS]   # the better ranked is kept
    assert set(s.search_found) == {PARIS}


def test_results_said_differently_keep_their_own_words(s):
    labels = [f["label"] for f in s.search("Paris")]
    assert labels[0] == "Paris, France, city or town"   # no distance where none is needed
    assert len(labels) == len(set(labels))


def test_a_full_list_stays_full_when_results_are_listed_once(s, monkeypatch):
    asked = _found_as(s, monkeypatch, [(PARIS, "Paris", 48.86, 2.35), (PARIS_TEXAS, "Paris", 48.88, 2.40)])
    assert len(s.search("Paris", limit=1)) == 1
    assert asked[0] > 1   # more are asked of the store than are listed, so ones listed once leave no gap
