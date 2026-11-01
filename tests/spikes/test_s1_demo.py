"""Spike S1 demo menus and quiz, driven by typed answers, with a stand-in player (no audio device)."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s1"))
import demo  # noqa: E402
import spatial  # noqa: E402


@pytest.fixture
def scripted(monkeypatch, tmp_path):
    played = []
    monkeypatch.setattr(spatial, "play", lambda stereo: played.append(stereo.shape))
    monkeypatch.setattr(demo, "RESULTS", tmp_path)
    monkeypatch.setattr(demo, "fetch", lambda: None)

    def run(answers):
        it = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(it))
        return demo.main([])
    return run, played, tmp_path


def test_tour_plays_eight_directions(scripted):
    run, played, _ = scripted
    # Use the stereo engine so the test does not need the KEMAR download.
    stereo = str(list(spatial.ENGINES).index("stereo") + 1)  # needs no downloaded data
    assert run(["5", stereo, "1"] + [""] * 8 + ["0"]) == 0
    assert len(played) == 8


def test_quiz_saves_played_and_heard(scripted):
    run, played, results = scripted
    stereo = str(list(spatial.ENGINES).index("stereo") + 1)  # its number in the engine menu
    answers = ["5", stereo, "4"]
    for _ in range(8):
        answers += ["", "r", "1"]  # play, replay once, answer "ahead"
    assert run(answers + ["0"]) == 0
    assert len(played) == 16
    (saved,) = results.glob("*.csv")
    rows = list(csv.DictReader(open(saved, encoding="utf-8")))
    assert len(rows) == 8
    assert {r["heard_degrees"] for r in rows} == {"0"}
    assert all(r["engine"] == "stereo" for r in rows)
    for r in rows:
        played_deg = int(r["played_degrees"])
        assert int(r["error_degrees"]) == min(played_deg, 360 - played_deg)
