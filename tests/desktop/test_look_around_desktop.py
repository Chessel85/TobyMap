"""Look around in the desktop window (P3-T11a; SON-4, SON-3, INF-10).

No sound device is opened: the sound player and the voice are stand-ins, and the tests say when an
item is still sounding and move the scan's clock by hand.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.audio.player import RecordingSpatial
from desktop.audio.voice import RecordingVoice
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.session import MapSession, box_centre

STATION = (50.9074977, -1.4142289)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_window(qtbot, test_pack, tmp_path, voice=None):
    session = MapSession(packs=[test_pack], saved_state={"lat": STATION[0], "lon": STATION[1] - 0.03,
                                                         "zoom_m": 5000, "step_m": 1000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(braille_works=True), sounds=RecordingSounds(),
                   data_folder=tmp_path, spatial=RecordingSpatial(), voice=voice or RecordingVoice())
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    w.scan.timer.stop()   # the tests tick it themselves
    w.scan.clock = Clock()
    return w


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    return make_window(qtbot, test_pack, tmp_path)


def press_l(w, qtbot):
    qtbot.keyClick(w.map, Qt.Key.Key_L)
    w.scan.timer.stop()
    return w.scan.items


def finish_item(w):
    """The item's sound and label end, and the pause after them passes."""
    w.spatial.sounding.clear()
    w.voice.busy = False
    w.scan.tick()                       # the pause starts
    w.scan.clock.now += w.scan.gap_s
    w.scan.tick()                       # and ends: the next item


def test_l_plays_the_first_item_its_sound_then_its_label_and_brailles_it(window, qtbot):
    items = press_l(window, qtbot)
    assert window.scan.playing and len(items) >= 3
    assert window.spatial.played[-1] == items[0]["sound"] and window.spatial.tags[-1] == "scan"
    (said, start), = window.voice.said
    assert said == items[0]["voice"] and start == window.spatial.last_end, "the label waits for the sound"
    assert window.announcer.brailled[-1] == said["text"]
    assert said["text"] not in window.announcer.texts, "not spoken by the screen reader"
    assert window.session.last_spoken == said["text"]


def test_the_next_item_waits_for_the_sound_the_label_and_the_pause(window, qtbot):
    items = press_l(window, qtbot)
    window.spatial.sounding.add("scan")
    window.scan.tick()
    window.scan.clock.now += 5
    window.scan.tick()
    assert window.scan.started == [items[0]["id"]], "the sound is still playing"
    window.spatial.sounding.clear()
    window.voice.busy = True
    window.scan.tick()
    assert window.scan.started == [items[0]["id"]], "the label is still being said"
    window.voice.busy = False
    window.scan.tick()
    window.scan.clock.now += window.scan.gap_s / 2
    window.scan.tick()
    assert window.scan.started == [items[0]["id"]], "the pause"
    window.scan.clock.now += window.scan.gap_s / 2
    window.scan.tick()
    assert window.scan.started == [items[0]["id"], items[1]["id"]]
    assert window.voice.said[-1][0] == items[1]["voice"]


def test_an_item_that_never_ends_holds_the_scan_at_most_15_seconds(window, qtbot):
    items = press_l(window, qtbot)
    window.voice.busy = True   # a voice that never answers
    window.scan.clock.now += 16
    window.scan.tick()
    window.scan.clock.now += window.scan.gap_s
    window.scan.tick()
    assert window.scan.started == [items[0]["id"], items[1]["id"]]


def test_every_item_plays_in_order_and_then_enter_goes_nowhere(window, qtbot):
    items = press_l(window, qtbot)
    for _ in items:
        finish_item(window)
    assert window.scan.started == [i["id"] for i in items]
    assert not window.scan.playing
    place = (window.session.world.lat, window.session.world.lon)
    qtbot.keyClick(window.map, Qt.Key.Key_Return)
    assert (window.session.world.lat, window.session.world.lon) == place
    assert window.announcer.texts[-1].startswith("Nothing to go to.")


def test_a_key_stops_the_scan_and_its_sound(window, qtbot):
    press_l(window, qtbot)
    window.spatial.sounding.add("scan")
    qtbot.keyClick(window.map, Qt.Key.Key_Down)
    assert not window.scan.playing
    assert not window.spatial.playing("scan") and window.voice.events[-1] == "stop"
    window.scan.tick()
    window.scan.clock.now += 5
    window.scan.tick()
    assert len(window.scan.started) == 1, "nothing more plays"


def test_enter_while_an_item_plays_goes_to_it(window, qtbot):
    items = press_l(window, qtbot)
    finish_item(window)
    target = items[1]
    area = window.session.store.feature(target["id"])
    _area, lat, lon = window.session._spots[("nearby", target["id"])]
    if window.session._geometry(area) == "area":
        lat, lon = box_centre(area.record["bbox"])
    qtbot.keyClick(window.map, Qt.Key.Key_Return)
    assert (window.session.world.lat, window.session.world.lon) == pytest.approx((lat, lon))
    assert not window.scan.playing
    assert window.region_of(QApplication.focusWidget()) == "map"


def test_l_again_starts_again_from_the_first_item(window, qtbot):
    items = press_l(window, qtbot)
    finish_item(window)
    press_l(window, qtbot)
    assert window.scan.started == [items[0]["id"], items[1]["id"], items[0]["id"]]


def test_a_voice_still_starting_is_told_once_a_scan(qtbot, test_pack, tmp_path):
    w = make_window(qtbot, test_pack, tmp_path, RecordingVoice(state="loading"))
    items = press_l(w, qtbot)
    for _ in items:
        finish_item(w)
    assert w.announcer.texts.count("The spatial voice is still starting. Try again in a few seconds.") == 1
    assert len(w.spatial.played) >= len(items), "the sounds still play"
