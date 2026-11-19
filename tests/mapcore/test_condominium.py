"""P3-T28f (R1, option B): a condominium is not a country of its own, but land its owners hold together.

It is listed under each owner in the world tree, not among its continent's countries, and is inside each owner in
the stored relationships, so Up from it offers both and Down from each lists it.
"""
from mapcore.store import contents


def row(i, name, layer, **extra):
    return {"id": i, "layer": layer, "names": {"en": name}, "parents": [], **extra}


RECORDS = [
    row("ne:europe", "Europe", "continents"),
    row("osm:r51477", "Germany", "countries"),
    row("osm:r2171347", "Luxembourg", "countries"),
    row("condominium:de-lu", "Moselle condominium", "countries", type="condominium",
        sovereign="Germany and Luxembourg", owners=["osm:r51477", "osm:r2171347"]),
]


def relationships():
    return {
        "osm:r51477": {"in": ["ne:europe"], "next": [["condominium:de-lu", 73.0]], "counts": {"rivers": 4}},
        "osm:r2171347": {"in": ["ne:europe"], "next": [["condominium:de-lu", 70.0]]},
        "condominium:de-lu": {"in": ["ne:europe"], "next": [["osm:r51477", 73.0], ["osm:r2171347", 70.0]]},
        "ne:europe": {"counts": {"countries": 3}},
    }


def test_a_condominium_is_put_inside_each_owner():
    rel = relationships()
    assert contents.share_condominiums(RECORDS, rel) == 1
    assert rel["condominium:de-lu"]["in"] == ["osm:r51477", "osm:r2171347", "ne:europe"]
    assert rel["osm:r51477"]["counts"] == {"countries": 1, "rivers": 4}
    assert rel["osm:r2171347"]["counts"] == {"countries": 1}
    # It stays a neighbour of each (INF-2), and done twice changes nothing more.
    assert rel["osm:r51477"]["next"] == [["condominium:de-lu", 73.0]]
    assert contents.share_condominiums(RECORDS, rel) == 0
    assert rel["osm:r51477"]["counts"]["countries"] == 1


def test_the_world_tree_lists_it_under_both_owners_not_under_its_continent():
    rel = relationships()
    contents.share_condominiums(RECORDS, rel)
    rows = {r["id"]: r for r in RECORDS}
    tree = contents.build_tree(rows, lambda i: rel.get(i) or {})
    assert tree["world"] == {"ne:europe"}
    assert tree["ne:europe"] == {"osm:r51477", "osm:r2171347"}
    assert tree["osm:r51477"] == {"condominium:de-lu"}
    assert tree["osm:r2171347"] == {"condominium:de-lu"}
    names = contents.tree_names(rows, tree)
    assert names["condominium:de-lu"]["sovereign"] == "Germany and Luxembourg"


def test_each_owner_holds_it_so_down_and_browse_list_it():
    rel = relationships()
    contents.share_condominiums(RECORDS, rel)
    numbers = {r["id"]: n for n, r in enumerate(RECORDS, 1)}
    holds = contents.contents(RECORDS, lambda i: rel.get(i) or {}, numbers)
    assert holds["osm:r51477"]["countries"] == ([4], [])
    assert holds["osm:r2171347"]["countries"] == ([4], [])


def test_a_condominium_without_owners_stays_under_its_continent():
    records = [r if r["id"] != "condominium:de-lu" else {**r, "owners": []} for r in RECORDS]
    rel = relationships()
    assert contents.share_condominiums(records, rel) == 0
    tree = contents.build_tree({r["id"]: r for r in records}, lambda i: rel.get(i) or {})
    assert "condominium:de-lu" in tree["ne:europe"]
