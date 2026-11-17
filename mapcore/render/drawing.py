"""A drawing of the map made in steps, so it never holds up what is said (P3-T24a, DP202).

The rule, in both versions:

1. What is said is sent before the map is drawn. A key's answer never waits for a drawing.
2. The map is drawn in steps. Between steps a new key is answered first, and a drawing no
   longer needed is dropped, unless it has gone on so long that dropping it would leave the
   map behind while a key is held (KEEP_AFTER_S): then it is finished, and the newer one is
   drawn next.
3. A drawing has a limit on its features (session.DRAW_LIMIT): the smallest are left out.
4. A drawing that takes more than STILL_DRAWING_S says "Still drawing the map", once.

The shells drive it: the desktop's drawing thread, and the web worker when it is idle. Each
calls advance with a time budget, and checks still_due between calls.
"""
from __future__ import annotations

import time

STEP_S = 0.02            # a shell runs a drawing's steps for this long, then looks for a key
KEEP_AFTER_S = 0.5       # a drawing older than this is finished even when a newer one is wanted
STILL_DRAWING_S = 2.0    # after this, "Still drawing the map" is said, once


class Drawing:
    """One drawing, made by a generator of steps (SceneBuilder.steps) that returns the frame."""

    def __init__(self, steps, width: int, height: int, clock=time.perf_counter):
        self._steps = steps
        self.width, self.height = width, height
        self._clock = clock
        self.started = clock()
        self.frame: dict | None = None
        self.longest_step_s = 0.0   # the longest single step, for the timings (P3-T24a)
        self._still_said = False

    @property
    def done(self) -> bool:
        return self.frame is not None

    def advance(self, budget_s: float = STEP_S) -> dict | None:
        """Run steps until the budget is used or the drawing is done. The frame when done, else None."""
        if self.frame is not None:
            return self.frame
        until = self._clock() + budget_s
        while True:
            before = self._clock()
            try:
                next(self._steps)
            except StopIteration as finished:
                self.frame = finished.value
            now = self._clock()
            self.longest_step_s = max(self.longest_step_s, now - before)
            if self.frame is not None:
                return self.frame
            if now >= until:
                return None

    def finish(self) -> dict:
        """Run every step left, and return the frame."""
        while self.advance(3600.0) is None:
            pass
        return self.frame

    def age_s(self) -> float:
        return self._clock() - self.started

    def keep_over_newer(self) -> bool:
        """Whether to finish this drawing when a newer one is wanted, rather than drop it."""
        return self.age_s() >= KEEP_AFTER_S

    def still_due(self) -> bool:
        """True once, when the drawing has taken STILL_DRAWING_S and is not done."""
        if self._still_said or self.frame is not None or self.age_s() < STILL_DRAWING_S:
            return False
        self._still_said = True
        return True
