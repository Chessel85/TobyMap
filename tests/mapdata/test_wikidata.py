"""Facts from Wikidata (P3-T2a, P3-T2b; DAT-7, INF-1, DMT-1).

The wikidata stage gives each feature with a Wikidata link its facts, each with its source and
date. The tests never use the network: the test pack reads its facts offline from
tests/samples/wikidata, made by tools/make_wikidata_samples.py, and the fetching is tested with
a query function that answers as Wikidata's query service does.
"""
import json

import pytest

from mapcore.packs.pack import Pack
from mapcore.session import MapSession
from mapdata.stages import wikidata

FRANCE, HAMPSHIRE, RHINE, ATLANTIC = "osm:r1403916", "osm:r172799", "osm:r123924", "vliz:goas:north-atlantic-ocean"


@pytest.fixture(scope="module")
def records(test_pack):
    with Pack(test_pack, check_app=False) as p:
        return {r["id"]: r for r in (p.feature(n) for n in range(p.manifest["features"]["count"]))}


def test_frances_facts_include_area_population_and_capital_each_with_source_and_date(records):
    facts = records[FRANCE]["facts"]
    assert {"area_km2", "population", "capital"} <= set(facts)
    for fact in facts.values():
        assert fact["source"] == "Wikidata" and fact["fetched"] == "2026-11-13"
    assert facts["population"]["date"] == "2020-01-01" and facts["population"]["value"] > 60_000_000
    assert facts["capital"]["value"] == ["Paris"] and facts["capital"]["wikidata"] == ["Q90"]
    assert records[FRANCE]["wikipedia"] == "Metropolitan France"


def test_a_river_has_its_length_and_a_feature_without_facts_has_none(records):
    assert records[RHINE]["facts"]["length_km"]["value"] == pytest.approx(1232.7)
    assert "facts" not in records["osm:n638908005"]   # Southampton Central: no link in the samples


def test_an_ocean_with_no_link_is_matched_by_name_and_place(records):
    assert records[ATLANTIC]["wikidata"] == "Q350134"
    assert "wikidata_matched" not in records[ATLANTIC] and "kinds" not in records[FRANCE]   # for the build only


def test_wikidata_is_credited_in_the_manifest(test_pack):
    with Pack(test_pack, check_app=False) as p:
        assert any(s["licence"] == "CC0 1.0" and "Wikidata" in s["name"] for s in p.manifest["sources"])
        assert "Facts from Wikidata" in p.attribution


def test_details_say_each_fact_with_its_source_and_date(test_pack):
    s = MapSession(packs=[test_pack], saved_state={"lat": 47.0, "lon": 2.5, "zoom_m": 250000, "step_m": 25000})
    s.start()
    s.run("panel.select", item=FRANCE)
    lines = s.details().splitlines()
    s.store.close()
    assert "Population: 64,897,954, from Wikidata, 1 January 2020" in lines
    assert "Capital: Paris, from Wikidata, as fetched on 13 November 2026" in lines
    assert "Area, as published: 544,000 square kilometres, from Wikidata, as fetched on 13 November 2026" in lines
    assert "Wikipedia article: Metropolitan France" in lines


# The rules for choosing a fact ------------------------------------------------------------------------

def entry(*rows):
    return {"id": "Q1", "fetched": "2026-11-13", "rows": [list(r) for r in rows]}


def test_the_latest_population_of_the_preferred_statements_is_chosen():
    got = wikidata.choose_facts(entry(("population", 900, "2024", "normal", None),
                                      ("population", 800, "2020", "preferred", None),
                                      ("population", 850, "2021", "preferred", None)))
    assert got["facts"]["population"] == {"value": 850, "date": "2021", "source": "Wikidata", "fetched": "2026-11-13"}


def test_an_area_is_in_square_kilometres_and_a_length_in_kilometres():
    got = wikidata.choose_facts(entry(("area", 2.5e9, None, "normal", None), ("length", 1232700, None, "normal", None),
                                      ("elevation", 4808.7, None, "normal", None)))
    assert got["facts"]["area_km2"]["value"] == 2500.0 and "date" not in got["facts"]["area_km2"]
    assert got["facts"]["length_km"]["value"] == 1232.7 and got["facts"]["elevation_m"]["value"] == 4808.7


def test_the_english_official_name_is_preferred_and_kinds_are_kept_for_the_build():
    got = wikidata.choose_facts(entry(("official_name", "République française", None, "normal", "fr"),
                                      ("official_name", "French Republic", None, "normal", "en"),
                                      ("kind", "Q6256", None, "normal", "country"),
                                      ("wikipedia", "France", None, "normal", None)))
    assert got["facts"]["official_name"]["value"] == "French Republic"
    assert got["kinds"] == ["country"] and got["wikipedia"] == "France"


def test_a_date_is_cut_to_its_precision():
    assert wikidata.date_at("2020-01-01", 9) == "2020"
    assert wikidata.date_at("2020-03-01", 10) == "2020-03"
    assert wikidata.date_at("2020-03-07", 11) == "2020-03-07"


# Fetching, with a query function standing in for the service --------------------------------------

def answer(rows):
    """An answer as the query service gives it, for rows of (item, what, value)."""
    def uri(q):
        return {"type": "uri", "value": f"http://www.wikidata.org/entity/{q}"}
    return {"results": {"bindings": [
        {"item": uri(q), "what": {"type": "literal", "value": what},
         "value": {"type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#decimal", "value": str(v)},
         "rank": {"type": "uri", "value": "http://wikiba.se/ontology#NormalRank"}} for q, what, v in rows]}}


def test_items_are_fetched_in_batches_and_kept_as_they_come(tmp_path):
    asked, kept = [], tmp_path / "facts-x.jsonl"

    def query(text):
        qs = [w[3:] for w in text.split() if w.startswith("wd:Q")]
        asked.append(qs)
        return answer([(q, "population", 10) for q in qs])

    got = wikidata.fetch(["Q1", "Q2", "Q3"], query=query, batch=2, say=lambda s: None, sleep=lambda s: None,
                         today="2026-11-13", keep=lambda e: wikidata.append_file(kept, e))
    assert asked == [["Q1", "Q2"], ["Q3"]]
    assert got["Q3"] == {"id": "Q3", "fetched": "2026-11-13", "rows": [["population", 10, None, "normal", None]]}
    assert set(wikidata.read_file(kept)) == {"Q1", "Q2", "Q3"}


def test_an_item_wikidata_knows_nothing_of_is_kept_as_empty_so_it_is_not_fetched_again():
    got = wikidata.fetch(["Q9"], query=lambda text: answer([]), say=lambda s: None, today="2026-11-13")
    assert got["Q9"]["rows"] == [] and wikidata.choose_facts(got["Q9"]) == {"facts": {}}


def test_a_match_by_name_needs_exactly_one_item_near_the_feature():
    named = {"Lake A": {"items": [["Q1", 5.0, 46.0], ["Q2", 120.0, 30.0]]},
             "Lake B": {"items": [["Q3", 5.0, 46.0], ["Q4", 5.1, 46.1]]}}
    recs = [{"name": "Lake A"}, {"name": "Lake B"}, {"name": "Lake C"}]
    boxes = [(4.9, 45.9, 5.2, 46.2)] * 3
    assert wikidata.match_by_name(recs, boxes, named, 50) == [(0, "Q1")]


def test_a_box_across_the_180_degree_line_finds_a_point_on_either_side():
    fiji = (177.0, -19.5, -178.0, -15.5)
    assert wikidata.near_box(179.5, -17.0, fiji, 10) and wikidata.near_box(-179.5, -17.0, fiji, 10)
    assert not wikidata.near_box(0.0, -17.0, fiji, 10)


def test_the_samples_facts_file_is_sorted_so_it_is_made_the_same_each_time():
    from pathlib import Path

    path = Path(__file__).parents[1] / "samples" / "wikidata" / "facts-sample.jsonl"
    ids = [json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert ids == sorted(ids, key=wikidata.qid_order)


def test_a_batch_whose_answer_is_cut_off_is_asked_for_in_halves():
    """The query service cuts an answer off when a query runs out of time; one heavy item must not stop the fetch."""
    def query(text):
        qs = [w[3:] for w in text.split() if w.startswith("wd:Q")]
        if "Q2" in qs:
            raise wikidata.CutOff("cut off")
        return answer([(q, "population", 1) for q in qs])

    said = []
    got = wikidata.fetch(["Q1", "Q2", "Q3", "Q4"], query=query, batch=4, say=said.append, today="2026-11-13")
    assert got["Q1"]["rows"] and got["Q3"]["rows"] and got["Q4"]["rows"] and got["Q2"]["rows"] == []
    assert any("cut off every time" in s for s in said)
