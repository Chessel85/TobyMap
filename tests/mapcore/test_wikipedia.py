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
