"""Plain progress lines, a summary, and the full log in a text file (DMT-2, architecture 8.5).

Progress lines go to the screen no closer than 10 seconds apart. A line that
comes sooner is still written to the log, but not to the screen; the next
line after the 10 seconds is shown instead. Warnings, the reason a build
stopped and the summary are always shown. There are no progress bars and no
redrawn lines, so a screen reader reads each line once.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

INTERVAL_S = 10.0
HEARTBEAT_S = 300.0  # a "still running" line in the log at least this often, so a quiet log means a fault


class Progress:
    def __init__(self, say=print, clock=time.monotonic, interval: float = INTERVAL_S):
        self.say = say
        self.clock = clock
        self.interval = interval
        self.started = clock()
        self.last_shown: float | None = None
        self.lines: list[str] = []
        self.log_file = None
        self.lock = threading.Lock()
        self.last_logged = time.monotonic()
        self.last_text = ""
        self._beat: threading.Thread | None = None
        self._stop = threading.Event()

    def start_heartbeat(self, every: float = HEARTBEAT_S) -> None:
        """Write a "still running" line to the log whenever nothing else has been logged for a while, with
        the step it is on and the memory in use, so whoever watches the log can tell a long step from a fault."""
        def beat():
            while not self._stop.wait(min(every, 30.0)):
                self.beat_once(every)

        self._beat = threading.Thread(target=beat, daemon=True, name="heartbeat")
        self._beat.start()

    def beat_once(self, every: float = HEARTBEAT_S) -> bool:
        """One heartbeat: a "still running" line if nothing has been logged for `every` seconds."""
        quiet = time.monotonic() - self.last_logged
        if quiet < every:
            return False
        from mapdata.parallel import memory_mb

        mine, free = memory_mb()
        memory = f" Memory: this build {mine:,.0f} MB, free on the computer {free:,.0f} MB." if free else ""
        self._log(f"Still running, {quiet / 60:.0f} minutes since the last line, which was: {self.last_text}{memory}")
        return True

    def open_log(self, path: Path) -> None:
        """Write every line from now on, and every line so far, to a text file."""
        self.log_file = open(path, "w", encoding="utf-8", newline="\n")
        for line in self.lines:
            self.log_file.write(line + "\n")
        self.log_file.flush()

    def close(self) -> None:
        self._stop.set()
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def _log(self, text: str) -> None:
        seconds = int(self.clock() - self.started)
        line = f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d} {text}"
        with self.lock:
            self.lines.append(line)
            if not text.startswith("Still running,"):
                self.last_logged = time.monotonic()
                self.last_text = text.splitlines()[0][:200] if text else ""
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
