"""Starting the desktop application: Windows messages are read just before the window appears (ACC-1).

On a first start after an install, setting up takes more than 5 seconds without reading Windows
messages, and Windows then calls the program "not responding". A window that first appears then
is answered for by Windows as having no UI Automation, and NVDA heard none of TobyMap's
announcements in that run (PO report, 8 Nov 2026). Queuing the show for the event loop is not
enough: Qt runs queued calls before it reads the Windows messages.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from desktop import app as app_module

steps: list[str] = []


class _FakeSession:
    def startup_took(self, ms: float) -> None:
        steps.append("timed")


class _FakeWindow:
    def __init__(self, start_at=None):
        self.session = _FakeSession()
        steps.append("built")

    def show(self) -> None:
        steps.append("shown")


def test_messages_are_read_after_setting_up_and_just_before_the_window_is_shown(monkeypatch):
    import desktop.window

    qapp = QApplication.instance() or QApplication([])
    monkeypatch.setattr(desktop.window, "MainWindow", _FakeWindow)
    monkeypatch.setattr(qapp, "processEvents", lambda *a: steps.append("messages read"))
    monkeypatch.setattr(qapp, "exec", lambda: steps.append("loop") or 0)
    steps.clear()
    assert app_module.main([]) == 0
    assert steps == ["built", "timed", "messages read", "shown", "loop"]
