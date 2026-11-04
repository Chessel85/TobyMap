r"""The listening test window (P1-T13): small, accessible, with a Close button.

Space plays a sound, you type the clock hour and the distance, R plays it again.
Run:  .venv\Scripts\python.exe -m tools.listening_test [--name NAME]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from tools.listening_test.run import ListeningTest

RESULTS = Path(__file__).resolve().parents[2] / "docs" / "spikes" / "listening-test"


class Window:   # built lazily, so importing this module never needs Qt
    def __init__(self, test: ListeningTest, announcer=None, player=None):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

        from PySide6.QtCore import QEvent, QObject

        class Keys(QObject):
            """Space and R are commands only while the answer box is empty, so digits still go to the box."""

            def eventFilter(inner, obj, event):
                return event.type() == QEvent.Type.KeyPress and self.handle_key(event)

        class Dialog(QDialog):
            pass

        self.test = test
        self.dialog = Dialog()
        self.dialog.setWindowTitle("TobyMap listening test")
        layout = QVBoxLayout(self.dialog)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setAccessibleName("Instructions")
        layout.addWidget(self.label)
        self.entry = QLineEdit()
        self.entry.setAccessibleName("Your answer")
        self.entry.returnPressed.connect(self.enter)
        self._keys = Keys(self.dialog)
        self.entry.installEventFilter(self._keys)
        self.dialog.installEventFilter(self._keys)
        layout.addWidget(self.entry)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.dialog.reject)
        layout.addWidget(self.close_button)
        self.Qt = Qt
        if announcer is None:
            from desktop.announcer import Announcer

            announcer = Announcer(self.dialog)
        self.announcer = announcer
        self.player = player or QtPlayer()
        self.dialog.resize(560, 260)
        self.say(self.test.start())
        self.entry.setFocus()

    def say(self, lines: list[str]) -> None:
        for line in lines:
            self.announcer.speak(line, "assertive")
        if lines:
            self.label.setText("\n".join(lines))

    def handle_key(self, event) -> bool:
        key = event.key()
        empty = self.entry.text() == ""
        if key == self.Qt.Key.Key_Space and (self.test.state == "ready" or empty):
            self.play()
            return True
        if key == self.Qt.Key.Key_R and empty and self.test.state in ("hour", "level"):
            self.play()
            return True
        return False

    def play(self) -> None:
        got = self.test.play()
        if got is not None:
            self.player.play(got[1])

    def enter(self) -> None:
        text = self.entry.text()
        self.entry.clear()
        self.say(self.test.submit(text))


class QtPlayer:
    """Plays stereo samples through a temporary WAV file and QSoundEffect."""

    def __init__(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QSoundEffect

        self._QUrl = QUrl
        self.effect = QSoundEffect()
        self.folder = Path(tempfile.mkdtemp(prefix="tobymap-listening-"))
        self.count = 0

    def play(self, samples) -> None:
        from desktop.audio import spatial

        self.count += 1
        path = self.folder / f"sound{self.count}.wav"
        path.write_bytes(spatial.to_wav_bytes(samples))
        self.effect.setSource(self._QUrl.fromLocalFile(str(path)))
        self.effect.play()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="listening_test")
    parser.add_argument("--name", default="po", help="who is taking the test, for the results file name")
    args = parser.parse_args(argv)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = Window(ListeningTest(args.name, RESULTS))
    window.dialog.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
