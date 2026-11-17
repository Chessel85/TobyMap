"""P3-T26 (DP205): disputed areas grouped by dispute, and a condominium said with its owners."""
from mapcore import names as names_mod
from mapcore.store import contents


def row(i, name, layer="regions", parent=None, **extra):
    return {"id": i, "layer": layer, "names": {"en": name}, "parents": [parent] if parent else [], **extra}


ROWS = {r["id"]: r for r in (
    row("c:india", "India", "countries"),
    row("r:jk", "Jammu and Kashmir", parent="c:india", disputed=True, dispute={"name": "Jammu and Kashmir",
                                                                                  "view": "Claimed by Pakistan."}),
    row("k:anantnag", "Anantnag", "counties", parent="r:jk", disputed=True),   # its dispute is its region's
    row("k:baramulla", "Baramulla", "counties", parent="r:jk", disputed=True, dispute={"name": "Jammu and Kashmir"}),
    row("d:westbank", "West Bank", "countries", type="disputed land"),   # a dispute of one area
    row("u:birtawil", "Bir Tawil", "countries", type="unclaimed land"),
)}


def test_disputed_areas_has_one_item_for_each_dispute_which_opens_to_its_areas():
    tree = contents.build_tree(ROWS, lambda _i: {})
    assert tree["special:disputed"] == {"dispute:Jammu and Kashmir", "d:westbank"}
    assert tree["dispute:Jammu and Kashmir"] == {"r:jk", "k:anantnag", "k:baramulla"}
    assert tree["special:unclaimed"] == {"u:birtawil"}


def test_a_dispute_item_keeps_its_name_note_and_count():
    tree = contents.build_tree(ROWS, lambda _i: {})
    names = contents.tree_names(ROWS, tree)
    assert names["dispute:Jammu and Kashmir"] == {"id": "dispute:Jammu and Kashmir", "names": {"en": "Jammu and Kashmir"},
                                                  "claimants": [], "view": "Claimed by Pakistan.", "count": 3}


def test_a_condominium_is_said_with_its_owners():
    rec = {"names": {"en": "Moselle condominium"}, "type": "condominium", "sovereign": "Germany and Luxembourg"}
    assert names_mod.Naming().name_of(rec) == "Moselle condominium, shared by Germany and Luxembourg"
    assert names_mod.Naming().name_of({"names": {"en": "Germany"}, "type": "country"}) == "Germany"
