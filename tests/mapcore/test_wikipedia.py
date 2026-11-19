"""P3-T5b: the command that opens the Wikipedia article of the feature Details is about (INF-1, LOC-4).
Nothing is opened: the core only gives the address (rule 5)."""
import pytest

from mapcore.commands import registry
from mapcore.session import MapSession
from tests.mapcore.test_session import KENT


@pytest.fixture
def session(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    yield s
    s.store.close()


def test_the_article_of_the_feature_in_details_is_asked_for(session, monkeypatch):
    area = session.areas[0]
    monkeypatch.setitem(area.record, "wikipedia", "Kent (England)")
    r = session.press("W", "details")
    assert r.open_url == "https://en.wikipedia.org/wiki/Kent_(England)"
    assert r.announcements[0]["text"] == f"Opening the Wikipedia article for {area.name}."


def test_a_title_is_made_safe_for_an_address(session, monkeypatch):
    monkeypatch.setitem(session.areas[0].record, "wikipedia", "Zürich & Bern?")
    assert session.run("details.wikipedia").open_url == "https://en.wikipedia.org/wiki/Z%C3%BCrich_%26_Bern%3F"


def test_with_no_article_it_says_so_and_opens_nothing(session, monkeypatch):
    area = session.areas[0]
    monkeypatch.delitem(area.record, "wikipedia", raising=False)
    r = session.run("details.wikipedia")
    assert r.open_url is None
    assert r.announcements[0]["text"] == f"No Wikipedia article for {area.name}."


def test_a_selected_item_is_the_feature_asked_about(session, monkeypatch):
    session.world.step_index = 0
    session.run("panel.select", item=session.areas[-1].id)
    monkeypatch.setitem(session.areas[-1].record, "wikipedia", "United Kingdom")
    r = session.run("details.wikipedia")
    assert r.open_url == "https://en.wikipedia.org/wiki/United_Kingdom"
    assert "United Kingdom" in r.announcements[0]["text"]


def test_the_key_works_in_details_only_and_is_one_a_browser_keeps_nothing_on():
    assert registry.command_for_key("web", "W", "details").name == "details.wikipedia"
    assert registry.command_for_key("desktop", "W", "details").name == "details.wikipedia"
    assert registry.command_for_key("web", "W", "panel") is None


def test_enter_on_the_article_line_opens_it_and_on_another_line_does_nothing(session, monkeypatch):
    area = session.areas[0]
    monkeypatch.setitem(area.record, "wikipedia", "Kent (England)")
    lines = session.details().split(chr(10))
    n = next(i for i, line in enumerate(lines) if line.startswith("Wikipedia article: "))
    r = session.press("Enter", "details", line=n)
    assert r.open_url == "https://en.wikipedia.org/wiki/Kent_(England)"
    other = session.press("Enter", "details", line=0)
    assert other.open_url is None and not other.announcements
    assert registry.command_for_key("web", "Enter", "details").name == "details.open_line"


def test_details_says_location_and_the_openstreetmap_source(session):
    text = session.details()
    assert "Shape and name: OpenStreetMap, ODbL licence" in text
    assert "The location is" not in text


def test_the_location_line_is_worded_location(test_pack):
    s = MapSession(packs=[test_pack], saved_state=dict(KENT))
    s.start()
    s.run("panel.select", item=s.areas[-1].id)
    assert any(line.startswith("Location: ") for line in s.details().split(chr(10)))
    s.store.close()


def test_elevation_is_said_for_places_only(session, monkeypatch):
    area = session.areas[0]   # an area
    fact = {"value": 100.0, "source": "Wikidata", "fetched": "2026-01-01"}
    monkeypatch.setitem(area.record, "facts", {"elevation_m": fact})
    assert not any(line.startswith("Elevation") for line in session.details().split(chr(10)))
    assert any(line.startswith("Elevation") for line in session._fact_lines(area.record))


def test_ctrl_alt_w_opens_the_current_feature_from_anywhere_and_the_web_has_its_own_key(session, monkeypatch):
    area = session.current_feature
    monkeypatch.setitem(area.record, "wikipedia", "Kent (England)")
    session.run("panel.select", item=session.areas[-1].id)   # a selected item does not change the current feature
    r = session.press("Ctrl+Alt+W", "map")
    assert r.open_url == "https://en.wikipedia.org/wiki/Kent_(England)"
    assert r.announcements[0]["text"] == f"Opening the Wikipedia article for {area.name}."
    assert registry.command_for_key("desktop", "Ctrl+Alt+W", "panel").name == "wikipedia.open"
    assert registry.command_for_key("web", "Alt+Shift+W", "details").name == "wikipedia.open"
    assert registry.command_for_key("web", "Ctrl+Alt+W", "map") is None


def test_ctrl_alt_w_with_no_article_says_so(session, monkeypatch):
    area = session.current_feature
    monkeypatch.delitem(area.record, "wikipedia", raising=False)
    r = session.run("wikipedia.open")
    assert r.open_url is None
    assert r.announcements[0]["text"] == f"No Wikipedia article for {area.name}."
