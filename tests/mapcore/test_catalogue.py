"""The catalogue of published packs (P4-T6a, PCK-2, PCK-4, PCK-5, architecture 6.10)."""
import json
from pathlib import Path

import pytest

from mapcore.packs.catalogue import (Catalogue, CatalogueError, INSTALLED, NOT_INSTALLED, UPDATE, parse)

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "catalogue.json"


def sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_parse_sample():
    cat = parse(SAMPLE.read_text(encoding="utf-8"))
    assert isinstance(cat, Catalogue)
    assert [e.name for e in cat.entries] == ["world", "england"]
    w = cat.get("world")
    assert (w.version, w.size, w.title) == ("2026.11.1", 552000000, "World")
    assert w.url_desktop.endswith("world.pack") and "huggingface" in w.url_web
    assert cat.get("england").app_versions == {"from": "0.1.0", "before": "0.2.0"}
    assert cat.get("england").depends == ["world"]
    assert cat.get("nothing") is None


@pytest.mark.parametrize("change", [
    lambda d: d.update(format=2),
    lambda d: d.pop("packs"),
    lambda d: d["packs"][0].pop("sha256"),
    lambda d: d["packs"][0].update(size="big"),
    lambda d: d["packs"][0].update(size=-1),
    lambda d: d["packs"][0].update(size=True),
    lambda d: d["packs"][0].update(sha256="xyz"),
    lambda d: d["packs"][0].update(app_versions={"from": "soon"}),
    lambda d: d["packs"][0].update(app_versions={}),
    lambda d: d["packs"][0].update(url_web=""),
    lambda d: d["packs"][1].update(name="world"),
    lambda d: d["packs"][0].update(version=""),
])
def test_bad_catalogue(change):
    data = sample()
    change(data)
    with pytest.raises(CatalogueError) as e:
        parse(json.dumps(data))
    assert str(e.value) and "{" not in str(e.value)


@pytest.mark.parametrize("text", ["", "not json", "[]", "null"])
def test_not_json_object(text):
    with pytest.raises(CatalogueError):
        parse(text)


def test_compatible():
    cat = parse(SAMPLE.read_text(encoding="utf-8"))
    e = cat.get("england")
    assert e.compatible("0.1.1")
    assert not e.compatible("0.0.9")
    assert not e.compatible("0.2.0")
    assert not e.compatible("unknown")


def test_states():
    cat = parse(SAMPLE.read_text(encoding="utf-8"))
    w, e = cat.get("world"), cat.get("england")
    assert cat.state(w, {}, "0.1.1") == NOT_INSTALLED
    assert cat.state(w, {"world": "2026.11.1"}, "0.1.1") == INSTALLED
    assert cat.state(w, {"world": "2026.10.2"}, "0.1.1") == UPDATE
    assert cat.state(w, {"world": "2026.11.2"}, "0.1.1") == INSTALLED  # installed is newer: nothing to offer
    assert cat.state(w, {"world": "unknown"}, "0.1.1") == UPDATE
    # An incompatible update is not offered.
    assert cat.state(e, {"england": "2026.10.1"}, "0.2.0") == INSTALLED
    assert cat.state(e, {}, "0.2.0") == NOT_INSTALLED


def test_dates_as_versions():
    data = sample()
    data["packs"][0]["version"] = "2026-11-20"
    cat = parse(json.dumps(data))
    assert cat.state(cat.get("world"), {"world": "2026-10-01"}, "0.1.1") == UPDATE
    assert cat.state(cat.get("world"), {"world": "2026-11-20"}, "0.1.1") == INSTALLED
