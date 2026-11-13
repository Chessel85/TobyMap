"""The tiers record and the writing stage's tiers (P3-T17, DP165)."""
import pytest

from mapdata.stages import write

UK, FRANCE = "osm:r62149", "osm:r1403916"


def records():
    return [
        {"id": UK, "layer": "countries", "type": "country"},
        {"id": FRANCE, "layer": "countries", "type": "metropolitan France"},
        {"id": "england", "layer": "regions", "type": "region", "parent": UK},
        {"id": "brittany", "layer": "regions", "type": "region", "parent": FRANCE},
        {"id": "hampshire", "layer": "counties", "type": "county", "parent": "england"},
        {"id": "england#county", "layer": "counties", "type": "region used as county", "parent": "england"},
        {"id": "morbihan", "layer": "counties", "type": "county", "parent": "brittany"},
        {"id": "a county with no region", "layer": "counties", "type": "county", "parent": FRANCE},
        {"id": "a lake", "layer": "lakes", "type": "lake"},
    ]


def test_the_record_in_the_repository_makes_the_uks_regions_constituent_countries():
    tiers = write.load_tiers()
    assert tiers["tiers"] == ["country", "constituent_country", "region", "county"]
    assert tiers["countries"][UK]["regions"] == "constituent_country"


def test_each_area_gets_its_countrys_tier_or_its_layers():
    rs = records()
    counts = write.give_tiers(rs, write.load_tiers())
    tier = {r["id"]: r.get("tier") for r in rs}
    assert tier == {UK: "country", FRANCE: "country", "england": "constituent_country", "brittany": "region",
                    "hampshire": "county", "england#county": "constituent_country", "morbihan": "county",
                    "a county with no region": "county", "a lake": None}
    assert counts == {"country": 2, "constituent_country": 2, "region": 1, "county": 3}


def test_an_area_listed_on_its_own_takes_its_own_tier():
    tiers = write.load_tiers()
    tiers["areas"] = {"morbihan": {"name": "Morbihan", "tier": "region"}}
    rs = records()
    write.give_tiers(rs, tiers)
    assert next(r for r in rs if r["id"] == "morbihan")["tier"] == "region"


def test_a_tier_not_in_the_list_is_refused(tmp_path):
    path = tmp_path / "tiers.yaml"
    path.write_text("tiers: [country, region]\nlayers: {countries: country, regions: state}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="state"):
        write.load_tiers(path)


def test_the_tiers_record_is_in_the_writing_stages_fingerprint():
    assert "constituent_country" in write.fingerprint_extra({})["tiers"]


def test_the_regions_layers_new_name_builds_no_area_again():
    # The name is in every stage's fingerprint; shown_name is only in the writing stage's.
    from mapdata.pipeline.settings import load_layers

    regions = load_layers(["base"])["regions"]
    assert regions.build_fields() == {"id": "regions", "name": "Regions", "rank": 4, "kind": "land"}
    definition = regions.definition()
    assert definition["name"] == "Regions and constituent countries" and "shown_name" not in definition


def test_the_test_pack_has_the_tiers_in_its_manifest_and_records(test_pack):
    from mapcore.packs.pack import Pack

    p = Pack(test_pack)
    try:
        assert p.manifest["tiers"] == ["country", "constituent_country", "region", "county"]
        tier = {i: p.feature(p.feature_number(i))["tier"] for i in (UK, "osm:r58447", "osm:r102740")}
        assert tier == {UK: "country", "osm:r58447": "constituent_country", "osm:r102740": "region"}
    finally:
        p.close()
