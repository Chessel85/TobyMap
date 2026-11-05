"""The earcons: every event has a placeholder tone, short and distinct, and own files fall back (P1-T12; SON-6, SON-8)."""
import wave

from mapcore.describe import earcon_list
from mapcore.session import MapSession
from tools import make_placeholder_sounds as make


def test_every_earcon_gets_a_short_distinct_file(tmp_path):
    assert make.main(["--out", str(tmp_path)]) == 0
    sizes = {}
    for e in earcon_list():
        with wave.open(str(tmp_path / e["file"])) as w:
            assert w.getnframes() / w.getframerate() < 0.5   # short, so it never gets in the way of speech
            sizes[e["event"]] = (w.getnframes(), (tmp_path / e["file"]).read_bytes())
    assert len({b for _n, b in sizes.values()}) == len(sizes)   # no two are the same


def test_an_existing_file_is_never_overwritten(tmp_path):
    (tmp_path / "tick.wav").write_bytes(b"mine")
    make.main(["--out", str(tmp_path)])
    assert (tmp_path / "tick.wav").read_bytes() == b"mine"


def test_phase_1_uses_the_tick_and_blocked_sounds():
    assert {e["event"] for e in earcon_list() if e["phase"] == 1} == {"tick", "blocked"}


def test_an_own_sound_file_is_offered_and_a_failure_is_spoken(test_pack):
    s = MapSession(packs=[test_pack])
    assert s.earcon_file("tick") == {"event": "tick", "custom": None, "default": "click.wav"}
    s.run("settings.set", field="earcon_tick", value="C:/mine/tick.wav")
    assert s.earcon_file("tick")["custom"] == "C:/mine/tick.wav"
    r = s.earcon_failed("tick")
    assert "default sound is used" in r.announcements[0]["text"]
