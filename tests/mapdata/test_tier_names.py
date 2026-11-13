"""Names for each country's tiers, from Wikidata's kinds, kept in the tiers record (DP181, P3-T17).

Kansas is a "state of the United States", Ontario a "province of Canada" and Yukon a "territory
of Canada", not a "region". mapdata tier-names works the names out once and writes them into the
tiers record, which the writing stage then reads.
"""
import textwrap

import yaml

from mapdata.stages import tier_names
from mapdata.stages.write import give_tiers, load_tiers

US, CANADA, UK = "osm:r148838", "osm:r1428125", "osm:r62149"


def area(fid, layer, parent, kinds, name=None, type_=None):
    r = {"id": fid, "name": name or fid, "layer": layer, "parent": parent, "kinds": kinds}
    if type_:
        r["type"] = type_
    return r


RECORDS = [
    {"id": US, "name": "United States", "layer": "countries"},
    {"id": CANADA, "name": "Canada", "layer": "countries"},
    {"id": UK, "name": "United Kingdom", "layer": "countries"},
    area("us:ks", "regions", US, ["U.S. state"], "Kansas"),
    area("us:ny", "regions", US, ["U.S. state"], "New York"),
    area("us:dc", "regions", US, ["federal district", "capital city"], "District of Columbia"),
    area("us:erie", "counties", "us:ny", ["county of New York"], "Erie County"),
    area("ca:on", "regions", CANADA, ["province of Canada"], "Ontario"),
    area("ca:qc", "regions", CANADA, ["province of Canada"], "Quebec"),
    area("ca:yt", "regions", CANADA, ["territory of Canada"], "Yukon"),
    area("ca:nt", "regions", CANADA, ["territory of Canada"], "Northwest Territories"),
    area("ca:nu", "regions", CANADA, ["territory of Canada"], "Nunavut"),
    area("ca:bc", "regions", CANADA, ["province of Canada"], "British Columbia"),
    area("ca:ab", "regions", CANADA, ["province of Canada"], "Alberta"),
    area("uk:en", "regions", UK, ["constituent country of the United Kingdom"], "England"),
]


def test_a_kind_is_cut_to_the_tiers_word():
    assert tier_names.word_of("state of the United States") == "state"
    assert tier_names.word_of("U.S. state") == "state"
    assert tier_names.word_of("department of France") == "department"
    assert tier_names.word_of("borough in the United Kingdom") == "borough"
    assert tier_names.word_of("administrative territorial entity of France") is None


def test_the_most_shared_word_names_the_layer_and_an_area_without_it_keeps_its_own():
    names = tier_names.work_out(RECORDS, skip={UK})
    # The District of Columbia's kind is one no other area shares, so it is taken as noise; Canada has three
    # territories, so each keeps its own.
    assert names[US] == {"name": "United States", "regions": "state", "counties": "county"}
    assert names[CANADA] == {"name": "Canada", "regions": "province",
                             "areas": {"ca:yt": "territory", "ca:nt": "territory", "ca:nu": "territory"}}
    assert UK not in names   # the tiers record gives the United Kingdom its own tiers


def record_text():
    return textwrap.dedent("""\
        # The tiers record.
        tiers: [country, constituent_country, region, county]
        layers: {countries: country, regions: region, counties: county}
        countries:
          osm:r62149: {name: United Kingdom, regions: constituent_country}
        areas: {}
        """)


def test_names_are_written_into_the_tiers_record_and_a_name_there_is_kept(tmp_path):
    path = tmp_path / "tiers.yaml"
    path.write_text(record_text() + "\nnames:\n  osm:r1428125: {name: Canada, regions: province}\n", encoding="utf-8")
    have, added = tier_names.write_names(path, tier_names.work_out(RECORDS, skip={UK}))
    assert added == [US]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["names"][CANADA] == {"regions": "province"}   # kept as it was, without Yukon; the name is a comment
    assert data["names"][US]["regions"] == "state" and data["tiers"][0] == "country"
    text = path.read_text(encoding="utf-8")
    assert '"territory": [ca:nt, ca:nu, ca:yt]' not in text   # Canada was there already, so kept as it was
    assert path.read_text(encoding="utf-8").startswith("# The tiers record.")
    tier_names.write_names(path, {})                                                  # written again: the same
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == data


def test_the_writing_stage_gives_each_area_its_tiers_name(tmp_path):
    path = tmp_path / "tiers.yaml"
    path.write_text(record_text(), encoding="utf-8")
    tier_names.write_names(path, tier_names.work_out(RECORDS, skip={UK}))
    records = [dict(r) for r in RECORDS]
    give_tiers(records, load_tiers(path))
    by = {r["id"]: r for r in records}
    assert by["us:ks"]["tier"] == "region" and by["us:ks"]["tier_name"] == "state"
    assert by["ca:yt"]["tier_name"] == "territory" and by["ca:on"]["tier_name"] == "province"
    assert by["us:erie"]["tier_name"] == "county"
    assert "tier_name" not in by["uk:en"] and by["uk:en"]["tier"] == "constituent_country"


def test_areas_named_on_their_own_are_grouped_by_name_a_name_to_a_line(tmp_path):
    path = tmp_path / "tiers.yaml"
    path.write_text(record_text(), encoding="utf-8")
    tier_names.write_names(path, tier_names.work_out(RECORDS, skip={UK}))
    text = path.read_text(encoding="utf-8")
    assert '      "territory": [ca:nt, ca:nu, ca:yt]' in text.splitlines()
    assert load_tiers(path)["names"][CANADA]["areas"] == {"ca:nt": "territory", "ca:nu": "territory",
                                                          "ca:yt": "territory"}
