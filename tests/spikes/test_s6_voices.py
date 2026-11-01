"""Spike S6 voices make audio in memory, without any sound device (P0-T9, SON-3)."""
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "tools" / "spikes"
sys.path.insert(0, str(HERE / "s6"))
sys.path.insert(0, str(HERE / "s1"))
sys.path.insert(0, str(HERE))

import voices  # noqa: E402


def test_espeak_speaks_into_memory():
    pytest.importorskip("espeakng_loader")
    v, _seconds = voices.load("espeak")
    audio = v.speak("Berlin")
    assert audio.dtype == np.float32
    assert 0.2 < len(audio) / voices.RATE < 2.0
    assert np.abs(audio).max() == pytest.approx(0.8, abs=0.01)
    assert len(v.speak("Bay of Biscay")) > len(audio)


@pytest.mark.slow
def test_piper_speaks_into_memory():
    pytest.importorskip("piper")
    if "cori" not in voices.available():
        pytest.skip("Piper voices not downloaded into voices/piper")
    v, _seconds = voices.load("cori")
    audio = v.speak("Llívia")
    assert 0.2 < len(audio) / voices.RATE < 2.0


@pytest.mark.skipif(not (HERE / "s1" / "downloads" / "mit_kemar_compact.zip").is_file(), reason="MIT KEMAR data not downloaded")
def test_demo_tour_with_espeak_and_a_stand_in_player(monkeypatch):
    pytest.importorskip("espeakng_loader")
    import importlib.util

    import spatial
    spec = importlib.util.spec_from_file_location("s6demo", HERE / "s6" / "demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    played = []
    monkeypatch.setattr(spatial, "play", lambda stereo: played.append(stereo.shape))
    answers = iter(["5", "2", "1"] + [""] * 8 + ["0"])  # stereo placing, then the tour, then quit
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert demo.main() == 0
    assert len(played) == 8
    assert all(shape[1] == 2 for shape in played)


def test_trim_removes_silence_at_both_ends():
    quiet = np.zeros(1000, np.float32)
    loud = np.ones(500, np.float32) * 0.5
    trimmed = voices._trim(np.concatenate([quiet, loud, quiet]))
    assert len(trimmed) < 1500
    assert trimmed.max() == 0.5


def test_resample_to_the_engine_rate():
    one_second = np.zeros(22050, np.float32)
    assert len(voices.to_rate(one_second, 22050)) == voices.RATE
