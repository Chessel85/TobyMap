"""The distance curve (SON-9): how loud and how muffled a sound is for its distance.

The distance is a fraction of the hearing range, which is the view radius at the
current zoom: 1 is the edge of the view. Phase 2's sound scene uses this code
too. All numbers are settings.

* From `near` of the range or closer: full loudness.
* Beyond that, each doubling of distance is equally quieter, down to
  `edge_db` at the edge of the view (SON-9).
* Beyond the view: the quiet, muffled `beyond_db` sound, unless the fixed
  tone alternative is chosen (DP80), which the sound scene handles.
* The second cue is muffling: the cut-off falls from `bright_hz` when near to
  `dull_hz` at the edge, and `beyond_hz` beyond it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CurveSettings:
    near: float = 0.05        # a twentieth of the range
    edge_db: float = -30.0
    beyond_db: float = -36.0
    bright_hz: float = 16000.0
    dull_hz: float = 1500.0
    beyond_hz: float = 900.0

    @classmethod
    def from_defaults(cls, d: dict) -> "CurveSettings":
        return cls(**{k: float(v) for k, v in d.get("sound", {}).get("curve", {}).items()})


DEFAULT = CurveSettings()


def distance_gain_db(fraction: float, s: CurveSettings = DEFAULT) -> float:
    if fraction <= s.near:
        return 0.0
    if fraction > 1.0:
        return s.beyond_db
    return s.edge_db * math.log2(fraction / s.near) / math.log2(1.0 / s.near)


def gain(fraction: float, s: CurveSettings = DEFAULT) -> float:
    """The same as a multiplier for the samples."""
    return 10 ** (distance_gain_db(fraction, s) / 20)


def muffle_cutoff_hz(fraction: float, s: CurveSettings = DEFAULT) -> float:
    if fraction > 1.0:
        return s.beyond_hz
    if fraction <= s.near:
        return s.bright_hz
    t = math.log2(fraction / s.near) / math.log2(1.0 / s.near)
    return s.bright_hz * (s.dull_hz / s.bright_hz) ** t
