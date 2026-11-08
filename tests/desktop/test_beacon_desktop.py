"""The orientation beacon on the desktop (P2-T9, P2-T16h; SON-10, SON-2): B hands the sound player
a beat, which the mixer repeats on the sound card's own clock (tests/desktop/test_spatial_player.py
checks the timing); a turn gives the beat its new place, and B or the pole stops it. No sound device
is opened."""
import pytest

from desktop.announcer import RecordingAnnouncer
from desktop.audio.player import RecordingSpatial
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state={"lat": 50.9, "lon": -1.45, "zoom_m": 5000, "step_m": 1000},
                         settings={"values": {"beacon_interval_s": 0.5}})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path,
                   spatial=RecordingSpatial())
    qtbot.addWidget(w)
    w.show()
    yield w
    w.close()


def beat(w):
    return w.spatial.beat_now


def test_b_starts_the_beat_at_its_interval(window):
    assert beat(window) is None
    window.dispatch("beacon.toggle")
    assert window.announcer.spoken[-1][0] == "Beacon on."
    placed, interval = beat(window)
    assert placed["sound"] == "beacon" and interval == 0.5
    assert window.actions_by_name["beacon.toggle"].isChecked()


def test_a_turn_moves_it_and_b_stops_it(window):
    window.dispatch("beacon.toggle")
    window.dispatch("orientation.cycle")
    window.dispatch("move.east")                     # facing east: the beacon is to the left
    placed, _interval = beat(window)
    assert placed["relative_deg"] == 270 and placed["pan"] == -1
    window.dispatch("beacon.toggle")
    assert beat(window) is None and not window.actions_by_name["beacon.toggle"].isChecked()


def test_silent_near_the_pole(window):
    window.dispatch("beacon.toggle")
    window.dispatch("goto.set", text="89.55, 0")
    assert any("Beacon off near the North Pole." in s[0] for s in window.announcer.spoken)
    assert beat(window) is None


def test_it_never_plays_as_a_sound_of_its_own(window):
    """The beat is the mixer's alone: nothing on the window's thread plays a beacon (P2-T16h)."""
    window.dispatch("beacon.toggle")
    window.dispatch("orientation.cycle")
    window.dispatch("move.east")
    assert not [p for p in window.spatial.played if p["sound"] == "beacon"]
