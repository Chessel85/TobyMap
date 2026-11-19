"""What is said and shown for territories (P3-T24d, DP199) and enclaves and exclaves (P3-T24g, DP207).

The records are made here, as the test pack's distant parts have no Wikidata links for the territories list; the
build's side is in tests/mapdata/test_territories_and_enclaves.py.
"""
from types import SimpleNamespace

import pytest

from mapcore.session import MapSession


def area(i, name, layer, **record):
    return SimpleNamespace(id=i, name=name, layer=layer, rank=1, record={"id": i, "layer": layer, **record})


@pytest.fixture
def session(test_pack, monkeypatch):
    s = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000})
    s.start()
    known = {}
    monkeypatch.setattr(s.store, "relationships", lambda i: {})
    real = s.store.feature
    monkeypatch.setattr(s.store, "feature", lambda i: known.get(i) or real(i))
    s.known = known
    yield s
    s.store.close()


def names(session, areas):
    return [str(a.name) for a in session._said(areas)]


def test_the_sovereign_state_is_said_after_an_integral_part(session):
    tenerife = [area("c", "Santa Cruz de Tenerife", "counties"),
                area("k", "Canary Islands", "countries", sovereign="Spain", say_sovereign=True, status="integral part"),
                area("a", "Africa", "continents")]
    assert names(session, tenerife) == ["Santa Cruz de Tenerife", "Canary Islands", "Spain", "Africa"]


def test_the_sovereign_state_is_not_said_after_a_dependent_territory(session):
    jersey = [area("p", "Saint Lawrence", "regions"),
              area("j", "Jersey", "countries", sovereign="the British Crown", say_sovereign=False,
                   status="Crown Dependency"),
              area("e", "Europe", "continents")]
    assert names(session, jersey) == ["Saint Lawrence", "Jersey", "Europe"]


def test_the_sovereign_state_is_said_once_when_it_is_there_already(session):
    places = [area("k", "Hawaii", "countries", sovereign="United States", say_sovereign=True),
              area("u", "United States", "countries")]
    assert names(session, places) == ["Hawaii", "United States"]


def test_an_exclave_is_said_after_its_country(session):
    session.known["fr"] = area("fr", "France", "countries")
    llivia = [area("g", "Girona", "counties"), area("es", "Spain", "countries"),
              area("x", "Exclave of Spain", "exclaves",
                   exclave={"sovereign": "Spain", "beside": ["fr"], "coast": False, "enclave": True}),
              area("eu", "Europe", "continents")]
    assert names(session, llivia) == ["Girona", "Spain", "exclave in France", "Europe"]


def test_an_exclave_with_a_name_of_its_own_is_said_by_it(session):
    """The test pack has no exclave, so the record is made here (P3-T28j, LOC-6)."""
    session.known["fr"] = area("fr", "France", "countries")
    session.known["ma"] = area("ma", "Morocco", "countries")
    llivia = [area("g", "Girona", "counties"), area("es", "Spain", "countries"),
              area("x", "Llívia", "exclaves",
                   exclave={"sovereign": "Spain", "beside": ["fr"], "coast": False, "enclave": True}),
              area("eu", "Europe", "continents")]
    assert names(session, llivia) == ["Girona", "Spain", "Llívia, exclave of Spain in France", "Europe"]
    assert session._exclave_words({"sovereign": "Spain", "beside": ["ma"], "coast": True}, "Perejil")         == "Perejil, exclave of Spain on the coast of Morocco"
    assert session._exclave_words({"sovereign": "Spain", "beside": ["fr"]}, "Llívia") \
        =="Llívia, exclave of Spain beside France"


def test_an_exclave_that_is_an_area_of_its_own_is_said_after_its_sovereign(session):
    session.known["ma"] = area("ma", "Morocco", "countries")
    ceuta = [area("ce", "Ceuta", "countries", sovereign="Spain", say_sovereign=True,
                  exclave={"beside": ["ma"], "coast": True, "enclave": False}),
             area("af", "Africa", "continents")]
    assert names(session, ceuta) == ["Ceuta", "Spain", "exclave on the coast of Morocco", "Africa"]


def test_an_exclave_beside_several_countries(session):
    session.known.update({"lt": area("lt", "Lithuania", "countries"), "pl": area("pl", "Poland", "countries")})
    words = session._exclave_words({"beside": ["lt", "pl"], "coast": False, "enclave": False})
    assert words == "exclave beside Lithuania and Poland"


def _details_of(session, monkeypatch, a):
    monkeypatch.setattr(session, "_details_feature", lambda: a)
    return session.details().split("\n")


def test_details_gives_the_status_and_any_claim(session, monkeypatch):
    falklands = area("f", "Falkland Islands", "countries", sovereign="United Kingdom", status="overseas territory",
                     claimed_by="Argentina", area_km2=12000.0, names={"en": "Falkland Islands"})
    falklands.area_km2 = 12000.0
    lines = _details_of(session, monkeypatch, falklands)
    assert "Type: overseas territory of the United Kingdom" in lines
    assert "Status: territory of the United Kingdom, not part of it." in lines
    assert "Claimed by Argentina." in lines


def test_details_lists_exclaves_and_enclaves(session, monkeypatch):
    session.known["x"] = area("x", "Llivia", "exclaves", exclave={"sovereign": "Spain", "beside": ["fr"]})
    france = area("fr", "France", "countries", enclaves=["x"])
    france.area_km2 = 550000.0
    lines = _details_of(session, monkeypatch, france)
    assert "Contains enclaves: Llivia, Spain" in lines
    spain = area("es", "Spain", "countries", exclaves=["x"])
    spain.area_km2 = 500000.0
    assert "Exclaves: Llivia" in _details_of(session, monkeypatch, spain)
