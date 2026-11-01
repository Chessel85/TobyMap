"""The one announcer of the desktop shell (ACC-1, architecture 3.2).

All speech goes through here. Speech is sent as a Qt accessibility
announcement, which NVDA and JAWS receive as a UI Automation notification
(PySide6 6.8 or later). Assertive announcements interrupt the one before, so
holding an arrow key does not build up a queue of old places.

Braille-only messages go to the NVDA Controller Client.

Tests use RecordingAnnouncer, which only records (architecture 3.5).
"""
from __future__ import annotations

from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent
from PySide6.QtWidgets import QWidget

from desktop.nvda import NvdaClient


class Announcer:
    def __init__(self, widget: QWidget, nvda: NvdaClient | None = None):
        self._widget = widget
        self._nvda = nvda if nvda is not None else NvdaClient()

    def speak(self, text: str, priority: str = "polite") -> None:
        event = QAccessibleAnnouncementEvent(self._widget, text)
        event.setPoliteness(QAccessible.AnnouncementPoliteness.Assertive if priority == "assertive"
                            else QAccessible.AnnouncementPoliteness.Polite)
        QAccessible.updateAccessibility(event)

    def braille(self, text: str) -> bool:
        return self._nvda.braille(text)


class RecordingAnnouncer:
    """Stand-in for tests: records what would have been said or brailled."""

    def __init__(self, braille_works: bool = False):
        self.spoken: list[tuple[str, str]] = []
        self.brailled: list[str] = []
        self.braille_works = braille_works

    def speak(self, text: str, priority: str = "polite") -> None:
        self.spoken.append((text, priority))

    def braille(self, text: str) -> bool:
        if self.braille_works:
            self.brailled.append(text)
        return self.braille_works

    @property
    def texts(self) -> list[str]:
        return [t for t, _p in self.spoken]
