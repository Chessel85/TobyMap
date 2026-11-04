"""The listening test window, offscreen, with a recording announcer and no sound (P1-T13, ACC-7)."""
import numpy as np
import pytest
from PySide6.QtCore import Qt

from desktop.announcer import RecordingAnnouncer
from tools.listening_test.app import Window
from tools.listening_test.run import ListeningTest


class FakePlayer:
    def __init__(self):
        self.played = []

    def play(self, samples):
        self.played.append(np.asarray(samples).shape)


@pytest.fixture
def window(qtbot, tmp_path):
    w = Window(ListeningTest("tester", tmp_path, hrtf=False), announcer=RecordingAnnouncer(), player=FakePlayer())
    qtbot.addWidget(w.dialog)
    w.dialog.show()
    return w


def test_it_speaks_the_instructions_and_has_a_close_button(window):
    assert window.announcer.texts[0].startswith("Block 1 of 5")
    assert window.close_button.text() == "Close"


def test_space_plays_then_digits_and_enter_answer(window, qtbot):
    qtbot.keyClick(window.entry, Qt.Key.Key_Space)
    assert len(window.player.played) == 1 and window.entry.text() == ""
    qtbot.keyClicks(window.entry, "3")
    qtbot.keyClick(window.entry, Qt.Key.Key_Return)
    assert "distance" in window.announcer.texts[-1]
    qtbot.keyClicks(window.entry, "2")
    qtbot.keyClick(window.entry, Qt.Key.Key_Return)
    assert window.announcer.texts[-1].startswith("Trial 2 of")
    assert window.test.results.path.exists()


def test_r_replays_only_when_the_box_is_empty(window, qtbot):
    qtbot.keyClick(window.entry, Qt.Key.Key_Space)
    qtbot.keyClick(window.entry, Qt.Key.Key_R)
    assert len(window.player.played) == 2
