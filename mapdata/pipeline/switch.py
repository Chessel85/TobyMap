"""The run switch: continue.txt, the data manager's yes or no for long builds.

continue.txt is a text file in the repository's top folder, not in git.
Its first line is "yes" or "no". The data manager changes it to "no" to
have the laptop back, for example for another project. A build reads it
before each stage, and long stages read it between their jobs. On "no",
the build finishes the job in hand, keeps everything finished so far in
the working folder, and stops. Run the same command again to carry on:
the finished stages are skipped.

With --wait-for-yes, mapdata waits instead, in a small process that uses
almost no memory or processor, and starts the build again when the file
says "yes".

Only a first line of "yes" means carry on: "no", or anything else, such as
"wait" or an empty line, pauses the build (the data manager, 10 November
2026). A missing file means carry on, so the automatic tests and a new copy
of the repository need none. Only the data manager edits the file; mapdata
only reads it. The MAPDATA_SWITCH
environment variable can name another file.
"""
from __future__ import annotations

import os
from pathlib import Path

from mapdata.pipeline.errors import BuildStopped

ENV_VAR = "MAPDATA_SWITCH"
DEFAULT = Path(__file__).resolve().parents[2] / "continue.txt"
PAUSED_EXIT = 3


class Paused(BuildStopped):
    """The run switch says no. Everything finished so far is kept."""


class Switch:
    def __init__(self, path: Path | None = None):
        if path is None:
            path = Path(os.environ[ENV_VAR]) if os.environ.get(ENV_VAR) else DEFAULT
        self.path = Path(path)

    def says_no(self) -> bool:
        try:
            with open(self.path, encoding="utf-8-sig") as f:
                first = f.readline()
        except FileNotFoundError:
            return False
        except OSError:
            return True   # there, but cannot be read just now: wait rather than guess
        return first.strip().lower() != "yes"

    def check(self, where: str) -> None:
        """Stop the build, cleanly, if the switch says no."""
        if self.says_no():
            raise Paused(f"Paused {where}, as the first line of {self.path.name} is not yes. Everything finished so far is kept. "
                         f"To carry on, change its first line to yes and run the same command again.")
