"""P3-T5b on the desktop: W in Details asks the browser for the article through Qt. Nothing opens (rule 5):
the window's open_url is replaced."""
import pytest

from tests.desktop.test_window import make_window

FRANCE = {"lat": 47.0, "lon": 2.0, "zoom_m": 100000, "step_m": 1000}


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    return make_window(qtbot, test_pack, tmp_path, state=FRANCE)


def test_w_in_details_opens_the_article_asked_for(window):
    opened = []
    window.open_url = opened.append
    window.focus_region("details")
    assert window.dispatch_key("W", "details")
    assert opened == ["https://en.wikipedia.org/wiki/Metropolitan_France"]


def test_w_on_the_map_does_not_ask(window):
    opened = []
    window.open_url = opened.append
    window.dispatch_key("W", "map")
    assert opened == []
