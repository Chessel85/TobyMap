"""The desktop's player for placed sounds (P2-T6b; AD-10, SON-1, SON-7, NFR-1). No sound device is opened."""
import math
import sys
import time

import numpy as np
import pytest

from desktop.audio import spatial
from desktop.audio.player import Mixer, RecordingSpatial, SpatialPlayer, read_mono
from desktop.sounds import SOUNDS
from mapcore.sound.scene import place


def loop_lowpass(x, cutoff_hz):
    """The original filter, one sample at a time, to check the quick one against."""
    a = math.exp(-2 * math.pi * cutoff_hz / spatial.RATE)
    y = x.astype(np.float64)
    for _ in range(2):
        out = np.empty_like(y)
        state = 0.0
        for i, v in enumerate(y):
            state = (1 - a) * v + a * state
            out[i] = state
        y = out
    return y


@pytest.mark.parametrize("cutoff", [600.0, 1500.0, 9000.0])
def test_the_quick_muffling_filter_gives_the_same_samples(cutoff):
    x = np.random.default_rng(3).standard_normal(3000).astype(np.float32)
    assert np.allclose(spatial.lowpass(x, cutoff), loop_lowpass(x, cutoff), atol=1e-5)


def level(x):
    return float(np.sqrt((x ** 2).mean()))


def info(sound="ding"):
    return {"event": sound, "custom": None, "default": f"{sound.replace('_', '-')}.wav"}


def scene(bearing, distance, mode="stereo"):
    p = place("ding", bearing, distance, 0.0, 1000.0, mode=mode).to_dict()
    p["file"] = info()
    return p


@pytest.fixture(scope="module")
def mono():
    return spatial.noise_bursts(count=1)


def test_the_pan_is_the_cores_equal_power_pan_as_web_audios_stereo_panner(mono):
    p = scene(60, 10)
    out = spatial.placed(mono, p)
    x = (p["pan"] + 1) / 2   # Web Audio: left gain cos(x pi / 2), right gain sin(x pi / 2)
    ratio = level(out[:, 1]) / level(out[:, 0])
    assert ratio == pytest.approx(math.sin(x * math.pi / 2) / math.cos(x * math.pi / 2), rel=1e-3)


@pytest.mark.parametrize("mode", ["stereo", "hrtf"])
def test_right_is_right_left_is_left_and_behind_is_lower(mono, mode):
    if mode == "hrtf" and not spatial.hrtf_available():
        pytest.skip("the KEMAR responses are not fetched")
    right, left = spatial.placed(mono, scene(90, 10, mode)), spatial.placed(mono, scene(270, 10, mode))
    assert level(right[:, 1]) > 2 * level(right[:, 0]) and level(left[:, 0]) > 2 * level(left[:, 1])
    assert len(spatial.placed(mono, scene(180, 10, mode))) > len(spatial.placed(mono, scene(0, 10, mode)))


def test_loudness_is_the_cores_gain(mono):
    near, far = spatial.placed(mono, scene(0, 10)), spatial.placed(mono, scene(0, 900))
    assert level(far) / level(near) < 0.5


@pytest.mark.parametrize("mode", ["stereo", "hrtf"])
def test_an_earcon_is_ready_to_play_well_within_50_ms(mode):
    if mode == "hrtf" and not spatial.hrtf_available():
        pytest.skip("the KEMAR responses are not fetched")
    player = SpatialPlayer(folder=SOUNDS, open_stream=False)
    path = SOUNDS / "bump.wav"
    p = scene(135, 500, mode)
    p["file"] = {"event": "blocked", "custom": None, "default": str(path)}
    player.render(p)   # the file read once, as the window does at the first sound
    times = []
    for _ in range(5):
        started = time.perf_counter()
        samples, failed = player.render(p)
        times.append((time.perf_counter() - started) * 1000)
    assert samples is not None and not failed
    assert sorted(times)[2] < 25, times


def test_several_sounds_play_at_once_each_at_its_own_loudness():
    mixer = Mixer()
    a = np.full((600, 2), 0.1, np.float32)
    b = np.full((300, 2), 0.3, np.float32)
    mixer.add(a)
    mixer.add(b)
    first = mixer.mix(256)
    assert np.allclose(first, 0.4)
    second = mixer.mix(256)
    assert np.allclose(second[:44], 0.4) and np.allclose(second[44:], 0.1)
    mixer.mix(256)
    assert not mixer.busy
    assert len(mixer.block_ms) == 3


def test_mixing_eight_sounds_takes_a_small_part_of_each_block():
    mixer = Mixer()
    for k in range(8):
        mixer.add(np.random.default_rng(k).standard_normal((44100, 2)).astype(np.float32) * 0.05)
    for _ in range(100):
        mixer.mix(256)
    assert sorted(mixer.block_ms)[50] < 1.0   # a block lasts 5.8 ms


def test_with_no_sound_device_the_player_is_silent_and_says_so(monkeypatch):
    monkeypatch.setitem(sys.modules, "sounddevice", None)   # importing it now fails, as with no PortAudio
    player = SpatialPlayer(folder=SOUNDS)
    assert player.missing and player.stream is None
    p = scene(0, 10)
    p["file"] = {"event": "blocked", "custom": None, "default": "bump.wav"}
    assert player.play(p) == (False, False)


def test_a_wav_file_is_read_as_mono_at_the_players_rate():
    mono = read_mono(SOUNDS / "bump.wav")
    assert mono.ndim == 1 and np.abs(mono).max() <= 1.0


def test_the_window_plays_placed_sounds_and_says_once_if_there_is_no_device(qtbot, test_pack, tmp_path):
    from desktop.announcer import RecordingAnnouncer
    from desktop.sounds import RecordingSounds
    from desktop.window import MainWindow
    from mapcore.session import MapSession, Response

    spatial_player = RecordingSpatial()
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path,
                   spatial=spatial_player)
    qtbot.addWidget(w)
    placed = session.place_sound("ding", 51.3, 1.2)
    w.handle(Response(sounds=[placed]))
    assert spatial_player.played == [placed]
    spatial_player.missing = True
    w.handle(Response(sounds=[placed]))
    w.handle(Response(sounds=[placed]))
    told = [t for t in w.announcer.texts if t.startswith("No sound device")]
    assert len(told) == 1


# The beacon's beat and the earcons, in the mixer (P2-T16h) ------------------------------------

def run_blocks(mixer, blocks, frames=256):
    return np.concatenate([mixer.mix(frames) for _ in range(blocks)])


def onsets(out, threshold=0.05):
    """The frames where a sound starts after silence."""
    loud = np.abs(out[:, 0]) > threshold
    return [i for i in range(len(loud)) if loud[i] and (i == 0 or not loud[max(0, i - 50):i].any())]


def test_the_beat_starts_at_the_next_block_and_keeps_exact_time():
    m = Mixer()
    m.mix(256)                                         # some time has passed
    m.set_beat(np.ones((100, 2), np.float32) * 0.5, 1000)
    out = run_blocks(m, 20)
    assert m.beats == [256, 1256, 2256, 3256, 4256, 5256]
    assert onsets(out) == [0, 1000, 2000, 3000, 4000, 5000]  # out starts at frame 256


def test_a_new_place_keeps_the_beat_and_is_heard_at_the_next_one():
    m = Mixer()
    m.set_beat(np.ones((100, 2), np.float32) * 0.5, 1000)
    run_blocks(m, 2)                                   # the first beat, at 0
    m.set_beat(np.ones((100, 2), np.float32) * -0.5, 1000)
    out = run_blocks(m, 6)                             # frames 512 to 2048
    assert m.beats == [0, 1000, 2000]
    assert out[1000 - 512, 0] == pytest.approx(-0.5)


def test_a_slow_window_never_delays_a_beat():
    """The beats are set by the frames mixed, not by any timer on the window's thread."""
    m = Mixer()
    m.set_beat(np.ones((10, 2), np.float32), 441)
    run_blocks(m, 100, frames=441)
    assert np.diff(m.beats).tolist() == [441] * 99


def test_stopping_the_beat_lets_the_last_one_finish():
    m = Mixer()
    m.set_beat(np.ones((600, 2), np.float32) * 0.5, 2000)
    m.mix(256)
    m.stop_beat()
    out = run_blocks(m, 10)
    assert m.beats == [0] and np.abs(out[:600 - 256, 0]).min() > 0.4 and not np.abs(out[600:, 0]).any()


def test_a_beat_replaces_the_last_still_sounding():
    m = Mixer()
    m.set_beat(np.ones((3000, 2), np.float32) * 0.5, 1000)
    out = run_blocks(m, 12)
    assert out[:, 0].max() == pytest.approx(0.5)       # never two at once


def test_an_earcon_plays_in_both_ears_at_its_volume_through_the_mixer():
    player = SpatialPlayer(folder=SOUNDS, open_stream=False)
    player.stream = object()                           # as if a device were open; none is
    played, failed = player.play_earcon({"event": "tick", "custom": None, "default": "click.wav", "gain": 0.5})
    assert played and not failed
    out = run_blocks(player.mixer, 40)
    mono = read_mono(SOUNDS / "click.wav")
    assert np.allclose(out[:, 0], out[:, 1])
    assert np.allclose(out[:len(mono), 0], np.clip(mono * 0.5, -1, 1), atol=1e-6)


def test_an_own_earcon_file_that_cannot_be_played_falls_back_and_says_so(tmp_path):
    bad = tmp_path / "mine.wav"
    bad.write_text("not a sound")
    player = SpatialPlayer(folder=SOUNDS, open_stream=False)
    player.stream = object()
    info = {"event": "tick", "custom": str(bad), "default": "click.wav"}
    assert player.play_earcon(info) == (True, True)
    assert player.play_earcon(info) == (True, True)    # its failure is kept, not read again


def test_ticks_close_together_each_play_whole():
    """A tick started again before the last has ended: both play in full, added together (15, 14.4)."""
    player = SpatialPlayer(folder=SOUNDS, open_stream=False)
    player.stream = object()
    info = {"event": "tick", "custom": None, "default": "click.wav"}
    player.play_earcon(info)
    player.mixer.mix(256)
    player.play_earcon(info)
    mono = read_mono(SOUNDS / "click.wav")
    out = run_blocks(player.mixer, 40)
    expected = np.zeros(len(out), np.float32)
    expected[:len(mono) - 256] += mono[256:]
    expected[:len(mono)] += mono
    assert np.allclose(out[:, 0], np.clip(expected, -1, 1), atol=1e-6)
