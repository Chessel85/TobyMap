"""The orientation beacon on the desktop (P2-T9; SON-10, SON-2): B starts it at once, the window
repeats it on its own timer from where the core last placed it, a turn moves it, and B or the
pole stops it. No sound device is opened."""
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


def beacons(w):
    return [p for p in w.spatial.played if p["sound"] == "beacon"]


def test_b_starts_it_at_once_and_it_repeats(window, qtbot):
    assert not beacons(window)
    window.dispatch("beacon.toggle")
    assert len(beacons(window)) == 1 and window.announcer.spoken[-1][0] == "Beacon on."
    qtbot.waitUntil(lambda: len(beacons(window)) >= 3, timeout=3000)
    assert window.actions_by_name["beacon.toggle"].isChecked()


def test_a_turn_moves_it_and_b_stops_it(window, qtbot):
    window.dispatch("beacon.toggle")
    window.dispatch("orientation.cycle")
    window.dispatch("move.east")                     # facing east: the beacon is to the left
    count = len(beacons(window))
    qtbot.waitUntil(lambda: len(beacons(window)) > count, timeout=2000)
    assert beacons(window)[-1]["relative_deg"] == 270 and beacons(window)[-1]["pan"] == -1
    window.dispatch("beacon.toggle")
    count = len(beacons(window))
    qtbot.wait(1200)
    assert len(beacons(window)) == count and not window.actions_by_name["beacon.toggle"].isChecked()


def test_silent_near_the_pole(window, qtbot):
    window.dispatch("beacon.toggle")
    window.dispatch("goto.set", text="89.55, 0")
    assert any("Beacon off near the North Pole." in s[0] for s in window.announcer.spoken)
    count = len(beacons(window))
    qtbot.wait(1200)
    assert len(beacons(window)) == count
