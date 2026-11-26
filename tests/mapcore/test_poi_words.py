"""A point of interest is said with its type after its name (P4-T1f, design docs/plan/p4-t1-design.md 3.10).

A layer whose definition says say_type (the four layers of points of interest of a regional pack) has its items named
with their type wherever the core names them, in Within, Nearby and Contains alike, unless the name is already the
type's words: "Broadway (Stop E), bus stop", but "Bench". The approved wording is in tests/mapcore/test_session.py.
"""
import pytest

from mapcore import names
from mapcore.layers.catalogue import LayerCatalogue, from_definition

POI_LAYERS = ("stops", "shops-food", "services", "street-furniture")


@pytest.fixture(autouse=True)
def no_say_type_after():
    yield
    names.say_type_layers(())


def _record(name, layer="stops", kind="bus stop"):
    return {"id": "osm:n1", "layer": layer, "type": kind, "names": {"en": name}}


class _Pack:
    def __init__(self, layers):
        self.layers = layers


def test_the_catalogue_reads_say_type_from_the_layer_definition():
    assert from_definition({"id": "stops", "say_type": True}).say_type is True
    assert from_definition({"id": "countries"}).say_type is False


def test_a_bus_stop_is_said_with_its_type_after_its_name():
    LayerCatalogue([_Pack([{"id": "stops", "geometry": "point", "say_type": True}])], dict)
    assert names.Naming().name_of(_record("Broadway (Stop E)")) == "Broadway (Stop E), bus stop"


def test_an_unnamed_bench_is_bench_alone():
    LayerCatalogue([_Pack([{"id": "street-furniture", "geometry": "point", "say_type": True}])], dict)
    assert names.Naming().name_of(_record("Bench", "street-furniture", "bench")) == "Bench"


def test_a_layer_without_say_type_is_said_by_its_name_alone():
    LayerCatalogue([_Pack([{"id": "towns", "geometry": "point"}])], dict)
    assert names.Naming().name_of(_record("Winchester", "towns", "city")) == "Winchester"
    assert names.Naming().name_of(_record("Broadway (Stop E)")) == "Broadway (Stop E)"


def test_the_local_name_keeps_its_language_with_the_type():
    LayerCatalogue([_Pack([{"id": "shops-food", "geometry": "point", "say_type": True}])], dict)
    rec = {"id": "osm:n2", "layer": "shops-food", "type": "cafe", "names": {"en": "Café du Port"},
           "local_lang": "fr"}
    name = names.Naming().name_of(rec)
    assert name == "Café du Port, cafe" and name.lang == "fr"


def test_a_bus_stop_is_said_with_its_type_in_nearby(test_region_pack):
    """A bus stop on the Broadway, Winchester, in Nearby. Its layer's say_type is set here as P4-T1i sets it in
    mapdata/config/layers/regional.yaml."""
    from mapcore.packs.pack import Pack
    from mapcore.session import MapSession
    from mapcore.store import Store

    store = Store([Pack(test_region_pack, check_app=False)])
    for d in store.packs[0].layers:
        if d["id"] in POI_LAYERS:
            d["say_type"] = True
    s = MapSession(store=store, saved_state={"lat": 51.0614, "lon": -1.3094, "zoom_m": 250, "step_m": 10})
    try:
        s.start()
        s.settings.set("nearby_count", 30)
        _within, nearby, _crossed = s.panel()[:3]
        labels = [i["label"] for i in nearby["items"]]
        assert any(label.startswith("Broadway St Johns (Stand 8), bus stop, ") for label in labels), labels
        assert not any(label.startswith("Bench, bench") for label in labels)
    finally:
        store.close()
