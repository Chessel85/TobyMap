"""The spatial voice on the desktop (P2-T7a, P2-T7c; SON-3, ANN-3, ANN-4, ACC-1, AD-10, NFR-1).

No sound device is opened: the player's mixer is run by hand, and the voice is a stand-in
that makes a tone, except in the timing test, which uses Piper if it is installed.
"""
import time

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.audio import voice as voice_mod
from desktop.audio.player import Mixer, RecordingSpatial, SpatialPlayer
from desktop.audio.spatial import RATE
from desktop.audio.voice import RecordingVoice, SpatialVoice
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession
from mapcore.sound.scene import VOICE_BEHIND_PITCH, place

STATION = (50.9074977, -1.4142289)


class ToneSpeaker:
    """A stand-in voice: each label is a tone a quarter of a second long, made at once."""

    def __init__(self, delay_s=0.0):
        self.delay_s = delay_s
        self.asked: list[str] = []

    def __call__(self, text, rate=1.0):
        self.asked.append(text)
        time.sleep(self.delay_s)
        n = int(RATE * 0.25 / rate)
        return (0.5 * np.sin(2 * np.pi * 440 * np.arange(n) / RATE)).astype(np.float32)


def label(text, bearing, ahead=0.0):
    placed = place("voice", bearing, 1000.0, ahead, 10_000.0).to_dict()
    pitch, placed["pitch"] = placed["pitch"], 1.0   # as the core gives it: the voice's own pitch
    return {"text": text, "placed": placed, "rate": 1.0, "pitch": pitch, "after": False}


@pytest.fixture
def player():
    return SpatialPlayer(open_stream=False)


def voice_for(player, speaker):
    v = SpatialVoice(player, speaker)
    assert v.wait()
    return v


def voice_samples(mixer):
    return [p[0] for p in mixer._playing if p[2] == "voice"]


def level(x):
    return float(np.sqrt((x ** 2).mean()))


def test_a_label_asked_for_at_90_degrees_is_placed_at_90_degrees(player):
    v = voice_for(player, ToneSpeaker())
    assert v.say(label("Berlin", 90.0)) == "ready"
    assert v.wait()
    (out,) = voice_samples(player.mixer)
    assert level(out[:, 1]) > 10 * level(out[:, 0]), "to the right"


def test_a_label_with_a_stretch_is_shorter_at_the_same_pitch(player):
    """Above what Piper can do, the core's time stretching makes up the speed (P2-T16g, SON-3)."""
    v = voice_for(player, ToneSpeaker())
    v.say(label("Normal", 0.0))
    v.wait()
    normal = voice_samples(player.mixer)[0][:, 0]
    fast = label("Fast", 0.0)
    fast["stretch"] = 2.5
    v.say(fast)
    v.wait()
    stretched = voice_samples(player.mixer)[0][:, 0]
    assert len(stretched) == pytest.approx(len(normal) / 2.5, rel=0.1)

    def crossings_per_sample(x):
        x = x[len(x) // 4: -len(x) // 4]
        return np.count_nonzero(np.diff(np.signbit(x))) / len(x)

    assert crossings_per_sample(stretched) == pytest.approx(crossings_per_sample(normal), rel=0.05)


def test_a_label_behind_is_lower_at_the_same_speed(player):
    """The PO chose sample 9 on 8 November 2026 (P2-T16g)."""
    v = voice_for(player, ToneSpeaker())
    v.say(label("Ahead", 0.0))
    v.wait()
    ahead = voice_samples(player.mixer)[0][:, 0]
    v.say(label("Behind", 180.0))
    v.wait()
    behind = voice_samples(player.mixer)[0][:, 0]
    assert len(behind) == pytest.approx(len(ahead), rel=0.05)

    def crossings_per_sample(x):
        x = x[len(x) // 4: -len(x) // 4]
        return np.count_nonzero(np.diff(np.signbit(x))) / len(x)

    assert crossings_per_sample(behind) == pytest.approx(VOICE_BEHIND_PITCH * crossings_per_sample(ahead), rel=0.03)


def test_a_second_label_stops_the_first(player):
    v = voice_for(player, ToneSpeaker())
    v.say(label("First", 90.0))
    v.wait()
    player.mixer.mix(256)   # the first is playing
    v.say(label("Second", 270.0))
    v.wait()
    (out,) = voice_samples(player.mixer)
    assert level(out[:, 0]) > level(out[:, 1]), "only the second, on the left, is left"


def test_a_label_asked_while_the_last_is_being_made_replaces_it(player):
    speaker = ToneSpeaker(delay_s=0.1)
    v = voice_for(player, speaker)
    v.say(label("One", 0.0))
    deadline = time.monotonic() + 5.0
    while "One" not in speaker.asked and time.monotonic() < deadline:
        time.sleep(0.001)   # "One" is being made before the others are asked
    for name in ("Two", "Three"):
        v.say(label(name, 0.0))
    assert v.wait()
    assert len(voice_samples(player.mixer)) == 1
    assert speaker.asked[-1] == "Three" and "Two" not in speaker.asked


def test_a_label_after_the_items_sound_starts_when_it_ends():
    mixer = Mixer()
    mixer.add(np.ones((1000, 2), np.float32) * 0.1)
    end = mixer.last_end
    mixer.add(np.ones((500, 2), np.float32) * 0.5, tag="voice", start_frame=end)
    out = np.concatenate([mixer.mix(256) for _ in range(8)])
    assert np.allclose(out[:1000], 0.1) and np.allclose(out[1000:1500], 0.5) and np.allclose(out[1500:], 0.0)


def test_a_voice_not_installed_says_so_and_plays_nothing(player, monkeypatch):
    monkeypatch.setattr(voice_mod, "available", lambda: False)
    v = SpatialVoice(player)
    assert v.wait()
    assert v.say(label("Berlin", 0.0)) == "missing"
    assert not voice_samples(player.mixer)


# The window -----------------------------------------------------------------

def make_window(qtbot, test_pack, tmp_path, voice, braille=True):
    session = MapSession(packs=[test_pack], saved_state={"lat": STATION[0], "lon": STATION[1] - 0.03,
                                                         "zoom_m": 5000, "step_m": 1000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(braille_works=braille), sounds=RecordingSounds(),
                   data_folder=tmp_path, spatial=RecordingSpatial(), voice=voice)
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    return w


def on_station(w, qtbot):
    w.focus_region("panel")
    nearby = w._group_item("nearby")
    nearby.setExpanded(True)
    item = next(nearby.child(i) for i in range(nearby.childCount())
                if nearby.child(i).text(0).startswith("Southampton Central"))
    w.tree.setCurrentItem(item)
    QApplication.processEvents()
    qtbot.keyClick(w.tree, Qt.Key.Key_Space)


def test_space_on_a_nearby_item_plays_its_sound_then_says_its_label_in_the_voice(qtbot, test_pack, tmp_path):
    v = RecordingVoice()
    w = make_window(qtbot, test_pack, tmp_path, v)
    on_station(w, qtbot)
    (said, start), = v.said
    assert said["text"].startswith("Southampton Central, ") and said["after"]
    assert w.spatial.played[-1]["sound"] == "item_direction"
    assert start == w.spatial.last_end
    assert w.announcer.brailled[-1] == said["text"], "the label goes to Braille"
    assert said["text"] not in w.announcer.texts, "but is not spoken by the screen reader"
    assert w.session.last_spoken == said["text"]   # Shift+Space repeats it


def test_a_key_that_runs_a_command_stops_the_voice_before_the_step_is_said(qtbot, test_pack, tmp_path):
    """P2-T17n, SON-3."""
    v = RecordingVoice()
    w = make_window(qtbot, test_pack, tmp_path, v)
    on_station(w, qtbot)
    assert v.events[-1] == "say"
    spoken_before = len(w.announcer.texts)
    w.focus_region("map")
    qtbot.keyClick(w.map, Qt.Key.Key_Down)
    assert v.events[-1] == "stop"
    assert len(w.announcer.texts) > spoken_before, "the step was said"


def test_with_also_speak_on_the_screen_reader_says_the_label_too(qtbot, test_pack, tmp_path):
    v = RecordingVoice()
    w = make_window(qtbot, test_pack, tmp_path, v)
    w.session.run("settings.set", field="voice_also_speak", value=True)
    on_station(w, qtbot)
    assert v.said[-1][0]["text"] in w.announcer.texts


def test_without_braille_nothing_is_spoken_instead(qtbot, test_pack, tmp_path):
    v = RecordingVoice()
    w = make_window(qtbot, test_pack, tmp_path, v, braille=False)
    before = list(w.announcer.texts)
    on_station(w, qtbot)
    assert w.announcer.texts == before


def test_a_voice_still_starting_says_so_each_time_and_a_missing_one_once(qtbot, test_pack, tmp_path):
    v = RecordingVoice(state="loading")
    w = make_window(qtbot, test_pack, tmp_path, v)
    on_station(w, qtbot)
    on_station(w, qtbot)
    assert w.announcer.texts.count("The spatial voice is still starting. Try again in a few seconds.") == 2
    v.state = "missing"
    on_station(w, qtbot)
    on_station(w, qtbot)
    assert sum(t.startswith("The spatial voice is not installed") for t in w.announcer.texts) == 1


# Time from asking to sound, with the real voice --------------------------------

@pytest.mark.skipif(not voice_mod.available(), reason="Piper or the Alba voice is not installed here")
def test_time_from_asking_to_sound_with_alba(player):
    v = SpatialVoice(player)
    assert v.wait(60) and v.state == "ready"
    for name in ("Berlin", "Bay of Biscay", "Isle of Skye", "River Thames", "Southampton Central, 2.1 kilometres"):
        v.say(label(name, 45.0))
        assert v.wait()
    times = sorted(t["ms"] for t in v.timings)
    print(f"\nAlba on the desktop, asking to sound: median {times[len(times) // 2]:.0f} ms, longest {times[-1]:.0f} ms")
    assert times[len(times) // 2] < 400
