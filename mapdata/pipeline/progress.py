"""Plain progress lines, a summary, and the full log in a text file (DMT-2, architecture 8.5).

Progress lines go to the screen no closer than 10 seconds apart. A line that
comes sooner is still written to the log, but not to the screen; the next
line after the 10 seconds is shown instead. Warnings, the reason a build
stopped and the summary are always shown. There are no progress bars and no
redrawn lines, so a screen reader reads each line once.
"""
from __future__ import annotations

import time
from pathlib import Path

INTERVAL_S = 10.0


class Progress:
    def __init__(self, say=print, clock=time.monotonic, interval: float = INTERVAL_S):
        self.say = say
        self.clock = clock
        self.interval = interval
        self.started = clock()
        self.last_shown: float | None = None
        self.lines: list[str] = []
        self.log_file = None

    def open_log(self, path: Path) -> None:
        """Write every line from now on, and every line so far, to a text file."""
        self.log_file = open(path, "w", encoding="utf-8", newline="\n")
        for line in self.lines:
            self.log_file.write(line + "\n")
        self.log_file.flush()

    def close(self) -> None:
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def _log(self, text: str) -> None:
        seconds = int(self.clock() - self.started)
        line = f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d} {text}"
        self.lines.append(line)
        if self.log_file is not None:
            self.log_file.write(line + "\n")
            self.log_file.flush()

    def line(self, text: str) -> None:
        """A progress line: always logged, shown only if 10 seconds have passed since the last line shown."""
        self._log(text)
        now = self.clock()
        if self.last_shown is None or now - self.last_shown >= self.interval:
            self.say(text)
            self.last_shown = now

    def log(self, text: str) -> None:
        """A line for the log only, such as each repair or each cached stage."""
        self._log(text)

    def always(self, text: str) -> None:
        """A line always shown: a warning, why a build stopped, or the summary."""
        self._log(text)
        self.say(text)
        self.last_shown = self.clock()

    def elapsed(self) -> float:
        return self.clock() - self.started

    # The spike S2 helpers take a callable "log"; a Progress can be passed as one.
    def __call__(self, text: str = "") -> None:
        self.line(text)


def duration_words(seconds: float) -> str:
    """'4 seconds', '2 minutes 5 seconds', '1 hour 3 minutes'."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} {secs} second{'s' if secs != 1 else ''}"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
