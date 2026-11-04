"""The listening test tool: trials, flow, results file and analysis (P1-T13, SON-1, SON-9). No sound, no window."""
import csv

import numpy as np
import pytest

from tools.listening_test import analyse, model
from tools.listening_test.run import ListeningTest, render_trial


def test_trials_cover_the_hours_and_distances_and_repeat_for_a_seed():
    block = model.BLOCKS[0]
    trials = model.make_trials(block, 1)
    assert {t.hour for t in trials} == set(range(1, 13))
    assert {t.level for t in trials} <= {1, 2, 3, 4}
    assert [(t.hour, t.level) for t in trials] == [(t.hour, t.level) for t in model.make_trials(block, 1)]
    assert [t.hour for t in trials] != [t.hour for t in model.make_trials(block, 2)]


def test_the_beyond_block_has_quiet_and_tone_beyond_sounds():
    trials = model.make_trials(model.BLOCKS[2], 1)
    beyond = [t for t in trials if t.level == 5]
    assert len(beyond) == 5 and {t.style for t in beyond} == {"muffled", "tone"}


def test_a_moving_sound_starts_elsewhere_and_ends_where_it_says():
    for t in model.make_trials(model.BLOCKS[3], 1):
        assert t.start_bearing is not None and t.start_bearing != t.bearing


def test_typed_answers():
    assert model.parse_hour("12") == 12 and model.parse_hour(" 0 ") == 0
    assert model.parse_hour("13") is None and model.parse_hour("x") is None
    assert model.parse_level("5") == 5 and model.parse_level("0") is None


def test_the_flow_runs_a_block_and_writes_every_answer(tmp_path):
    test = ListeningTest("tester", tmp_path, hrtf=False)
    said = test.start()
    assert "stereo" in said[0] and "Block 1 of 5" in said[0]
    block = test.block
    for i in range(block["trials"]):
        assert test.state == "ready"
        trial, samples = test.play()
        assert samples.ndim == 2 and samples.shape[1] == 2 and len(samples) > 1000
        assert test.submit("abc")[0].startswith("Type an hour")
        assert "distance" in test.submit(str(trial.hour))[0]
        assert test.submit("9")[0].startswith("Type a distance")
        out = test.submit(str(trial.level))
    assert "end of the block" in out[0]
    assert "head-related" in " ".join(out)          # block 2 is skipped without the HRTF files
    rows = list(csv.DictReader(open(test.results.path, newline="", encoding="utf-8")))
    assert len(rows) == block["trials"] and rows[0]["block_name"] == "stereo"
    assert rows[0]["played_hour"] == rows[0]["heard_hour"]
    assert test.state == "ready" and test.block["id"] == 3     # on to block 3, skipping the unusable 2


def test_replaying_is_counted_and_cant_tell_is_zero(tmp_path):
    test = ListeningTest("t", tmp_path, hrtf=False)
    test.start()
    test.play()
    test.play()
    test.play()
    test.submit("0")
    test.submit("3")
    rows = list(csv.DictReader(open(test.results.path, newline="", encoding="utf-8")))
    assert rows[0]["plays"] == "3" and rows[0]["heard_hour"] == "0" and rows[0]["heard_bearing"] == ""


def test_the_end_of_the_test_points_to_the_results_file(tmp_path):
    test = ListeningTest("t", tmp_path, hrtf=False)
    test.start()
    test.block_index = len(model.BLOCKS) - 1
    out = test.next_block()
    assert "finished" in out[-1] and str(test.results.path) in out[-1] and test.state == "done"


def test_the_beyond_tone_and_moving_sounds_render(tmp_path):
    for block in (model.BLOCKS[2], model.BLOCKS[3]):
        for t in model.make_trials(block, 1)[:4]:
            assert np.abs(render_trial(t, "stereo")).max() > 0


def rows_for(played_heard, name="stereo"):
    out = []
    for i, (played, heard, level, heard_level) in enumerate(played_heard):
        out.append({"block_name": name, "played_bearing": str(played), "heard_bearing": "" if heard is None else str(heard),
                    "heard_hour": "" if heard is None else ("0" if heard == "x" else "1"), "played_level": str(level),
                    "played_fraction": str(model.LEVEL_FRACTION[level]), "heard_level": str(heard_level), "style": ""})
    return out


def test_analysis_counts_within_45_degrees_and_front_back_confusions():
    rows = rows_for([(30, 30, 1, 1), (90, 120, 2, 2), (150, 30, 3, 3), (270, 240, 4, 4), (0, 180, 1, 1)])
    r = analyse.analyse(rows)["stereo"]
    assert r["within_45"] == pytest.approx(3 / 5)
    assert r["front_back"] == pytest.approx(1 / 4)       # of the four that can be judged, only 150 to 30 is a confusion; 0 and 180 are on the line between front and back
    assert r["distance_rho"] is not None and r["distance_rho"] > 0.5


def test_analysis_recognises_beyond_and_writes_findings(tmp_path):
    rows = rows_for([(30, 30, 5, 5), (60, 60, 5, 4), (90, 90, 1, 1), (120, 120, 2, 5)])
    r = analyse.analyse(rows)["stereo"]
    assert r["beyond_recognised"] == 0.5 and r["false_beyond"] == 0.5
    text = analyse.findings({"stereo": r})
    assert "## stereo" in text and "50 percent" in text and "Settings I propose" in text
    assert "|" not in text           # no tables, for a screen reader


def test_findings_say_when_there_are_too_few_results():
    assert "not enough results yet" in analyse.findings({})


def test_the_label_block_renders_all_three_styles_with_the_piper_voice():
    from desktop.audio import voice

    if not voice.available():
        pytest.skip("the Piper voice is not in voices/piper")
    lengths = {}
    for style in model.LABEL_STYLES:
        trial = model.Trial(5, 1, "labels", 180.0, 2, style=style)
        out = render_trial(trial, "stereo")
        assert out.ndim == 2 and np.abs(out).max() > 0
        lengths[style] = len(out)
    assert lengths["lower"] > lengths["plain"] and lengths["tone"] > lengths["plain"]


def test_the_label_block_is_skipped_with_a_message_when_there_is_no_voice(tmp_path):
    test = ListeningTest("t", tmp_path, hrtf=False, voice=False)
    ok, why = test.usable(model.BLOCKS[4])
    assert not ok and "Piper" in why
