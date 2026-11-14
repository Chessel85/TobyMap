"""Each base layer has its own placeholder sound, so items can be told apart (P3-T11b, SCP-7, SON-4)."""
from pathlib import Path

import yaml

from mapcore.describe import earcon_list
from tests.mapcore.test_layers import session  # noqa: F401
from tools import make_placeholder_sounds as make

ROOT = Path(__file__).resolve().parents[2]


def _base_layers():
    return yaml.safe_load((ROOT / "mapdata/config/layers/base.yaml").read_text(encoding="utf-8"))["layers"]


def test_every_base_layer_has_a_sound_that_exists():
    events = {e["event"] for e in earcon_list()}
    for layer in _base_layers():
        assert layer.get("sound") in events, layer["id"]


def test_layer_sounds_differ_and_have_a_tone():
    used = {l["sound"] for l in _base_layers()}
    tones = {e: tuple(make.TONES[e]) for e in used if e != "layer_region"}
    assert all(tones.values())
    assert len(set(tones.values())) == len(tones)
    assert "layer_region" in used and make.TONES["layer_region"]


def test_the_layers_dialog_offers_the_layer_sound_and_a_change_is_kept(session):
    d = session.run("layers.open").dialog
    assert d["words"]["layer_sound"] and "layer_water" in {e["event"] for e in d["earcons"]}
    assert all("sound" in layer for g in d["groups"] for layer in g["layers"])
    session.run("layers.set", layer="regions", field="sound", value="layer_peak")
    assert session.layers.get("regions").sound == "layer_peak"
    session.run("layers.set", layer="regions", field="sound", value=None)
    assert session.layers.get("regions").sound is None
