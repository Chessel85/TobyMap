"""The listening test for sound in space and the voice (P2-T17u; SON-1, SON-2, SON-3, SON-9; DP164).

No sound device and no Piper: a stand-in voice and player (rule 5)."""
import csv

import numpy as np
import pytest

from desktop.audio import spatial
from mapcore.sound import scene
from tools.listening_test import compass


def fake_speaker(text, rate=1.0):
    return spatial.noise_bursts(count=2, seed=len(text))


ITEM = spatial.noise_bursts(count=1)


def rows_of(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("typed, point", [("n", 0), ("NE", 1), ("north east", 1), ("North-East", 1), ("northeast", 1),
                                          ("e", 2), ("south west", 5), ("W", 6), ("nw", 7), ("0", -1), ("?", -1),
                                          ("up", None), ("", None), ("9", None)])
def test_a_compass_point_typed_in_any_common_way(typed, point):
    assert compass.parse_point(typed) == point


def test_each_block_has_all_eight_points_and_names_mixed_afresh():
    a, b = compass.make_trials(1, "now", 1), compass.make_trials(2, "hrtf", 1)
    for trials in (a, b):
        assert sorted(t.point for t in trials) == list(range(8))
        assert sorted(t.name for t in trials) == sorted(compass.NAMES)
    assert [(t.point, t.name) for t in a] != [(t.point, t.name) for t in b]
    assert [(t.point, t.name) for t in a] == [(t.point, t.name) for t in compass.make_trials(1, "now", 1)]


def test_now_is_the_core_placing_unchanged():
    for point in range(8):
        b = compass.bearing_of(point)
        for sound in ("item_direction", "voice"):
            assert compass.placed_for("now", sound, b) == scene.place(
                sound, b, compass.DISTANCE_M, 0.0, compass.RANGE_M).to_dict()


def test_the_models_differ_only_behind():
    north, east = 0.0, 90.0
    for b in (north, east):
        now = compass.placed_for("now", "item_direction", b)
        assert compass.placed_for("lower", "item_direction", b) == now
        assert compass.placed_for("muffled", "item_direction", b) == now
        assert compass.placed_for("hrtf", "item_direction", b) == {**now, "mode": "hrtf"}


def test_lower_is_twice_as_many_semitones_down_behind():
    south = compass.placed_for("lower", "item_direction", 180.0)
    voice = compass.placed_for("lower", "voice", 225.0)
    assert south["pitch"] == pytest.approx(2 ** (-6 / 12), abs=0.005)
    assert voice["pitch"] == pytest.approx(2 ** (-3 / 12), abs=0.005)
    assert compass.placed_for("now", "voice", 225.0)["pitch"] == scene.VOICE_BEHIND_PITCH


def test_muffled_has_a_lower_cut_off_behind():
    now = compass.placed_for("now", "item_direction", 135.0)
    more = compass.placed_for("muffled", "item_direction", 135.0)
    assert more["cutoff_hz"] == pytest.approx(now["cutoff_hz"] * 0.3 / 0.7)
    assert more["pitch"] == now["pitch"]


def test_the_sound_then_the_voice_from_the_same_side():
    trial = compass.Trial(1, "now", 1, 2, "Berlin")       # east
    out = compass.render(trial, fake_speaker, ITEM)
    assert out.ndim == 2 and out.shape[1] == 2
    sound_len = len(spatial.placed(ITEM, compass.placed_for("now", "item_direction", 90.0)))
    assert len(out) > sound_len
    for part in (out[:sound_len], out[sound_len:]):
        left, right = np.abs(part[:, 0]).sum(), np.abs(part[:, 1]).sum()
        assert right > 10 * left


def test_the_voice_behind_keeps_its_length_but_not_its_pitch():
    ahead = compass.render(compass.Trial(1, "now", 1, 0, "Berlin"), fake_speaker, ITEM)
    behind = compass.render(compass.Trial(1, "now", 1, 4, "Berlin"), fake_speaker, ITEM)
    item_ahead = len(spatial.placed(ITEM, compass.placed_for("now", "item_direction", 0.0)))
    item_behind = len(spatial.placed(ITEM, compass.placed_for("now", "item_direction", 180.0)))
    assert item_behind > item_ahead                       # the sound behind is played slower, so lower
    assert abs((len(behind) - item_behind) - (len(ahead) - item_ahead)) < 0.02 * (len(ahead) - item_ahead)


def run(tmp_path, answers, hrtf=False):
    played, told = [], []
    typed = iter(answers)

    def ask(prompt):
        told.append(prompt)
        try:
            return next(typed)
        except StopIteration:
            raise EOFError from None

    results = compass.Results("tester", tmp_path, 100)
    test = compass.CompassTest(results, fake_speaker, ITEM, ask, told.append, played.append, hrtf=hrtf)
    return test.run(), played, told


def block_answers(model, block, right=True):
    out = []
    for t in compass.make_trials(block, model, 1):
        out += ["", compass.SHORT[t.point] if right else compass.SHORT[(t.point + 4) % 8]]
    return out + ["4", "3"]


def test_the_whole_test_writes_every_answer_and_rating(tmp_path):
    answers = [""] + block_answers("now", 1) + block_answers("lower", 2) + block_answers("muffled", 3)
    path, played, told = run(tmp_path, answers)
    rows = rows_of(path)
    directions = [r for r in rows if r["kind"] == "direction"]
    assert len(directions) == 24 and len(played) == 24
    assert [r["model"] for r in directions[::8]] == ["now", "lower", "muffled"]   # HRTF left out without its files
    assert all(r["played_point"] == r["heard_point"] for r in directions)
    assert [(r["kind"], r["rating"]) for r in rows if r["kind"] != "direction"] == [("ease", "4"), ("voice", "3")] * 3
    assert any("HRTF block is left out" in t for t in told) and "finished" in told[-1]


def test_with_the_hrtf_files_there_are_four_blocks(tmp_path):
    answers = [""] + block_answers("now", 1) + block_answers("hrtf", 2)
    path, _, told = run(tmp_path, answers, hrtf=True)
    assert [r["model"] for r in rows_of(path) if r["kind"] == "direction"][8] == "hrtf"
    assert "Stopped" in told[-1]


def test_hear_again_cant_tell_a_wrong_answer_and_stopping(tmp_path):
    path, played, told = run(tmp_path, ["", "", "r", "r", "sideways", "0", "q"])
    rows = rows_of(path)
    assert len(rows) == 1 and rows[0]["plays"] == "3" and rows[0]["heard_point"] == "can't tell"
    assert rows[0]["heard_bearing"] == "" and len(played) == 3
    assert any(t.startswith("Type a compass point") for t in told)
    assert "Stopped" in told[-1] and str(path) in told[-1]


def test_the_demonstration_plays_all_eight_points_in_order(tmp_path):
    _, played, told = run(tmp_path, ["d"] + [""] * 8)
    assert len(played) == 8
    assert [t for t in told if t in compass.POINTS] == compass.POINTS


def test_the_findings_compare_the_models(tmp_path):
    answers = ([""] + block_answers("now", 1, right=False) + block_answers("lower", 2)
               + block_answers("muffled", 3, right=False))
    path, _, _ = run(tmp_path, answers)
    results = compass.analyse(compass.read_rows([path]))
    assert results["lower"]["right"] == 1 and results["lower"]["front_back"] == 0
    assert results["now"]["within_one"] == 0 and results["now"]["front_back"] == 1
    assert results["now"]["behind_heard_behind"] == 0 and results["lower"]["behind_heard_behind"] == 1
    assert results["lower"]["ease"] == [4]
    text = compass.findings(results, [path.name])
    assert "## lower: stereo with twice the lower pitch behind" in text
    assert "lower did best" in text and "6 semitones" in text
    assert "|" not in text                                 # lists, not tables, for the screen reader


def test_analyse_on_the_command_line(tmp_path):
    path, _, _ = run(tmp_path, [""] + block_answers("now", 1))
    assert compass.main(["--analyse", str(path)]) == 0
    text = (tmp_path / "compass-findings.md").read_text(encoding="utf-8")
    assert "Keep the sound as it is now" in text
