"""The distance curve (SON-9): how loud and how muffled a sound is for its distance.

The distance is a fraction of the hearing range, which is the view radius at the
current zoom: 1 is the edge of the view. Phase 2's sound scene uses this code
too. All numbers are settings.

* From `near` of the range or closer: full loudness.
* Beyond that, the loudness falls in a straight line, down to `min_gain` at
  the edge of the view (the PO's choice, DP137). The other model, "log", makes
  each doubling of distance equally quieter, down to `edge_db`.
* No sound is ever quieter than `min_gain`, the minimum volume (DP137).
  Beyond the view a sound plays at that minimum, muffled, unless the fixed
  tone alternative is chosen (DP80), which the sound scene handles.
* The second cue is muffling: the cut-off falls from `bright_hz` when near to
  `dull_hz` at the edge, and `beyond_hz` beyond it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CurveSettings:
    model: str = "linear"     # "linear" or "log"
    near: float = 0.05        # a twentieth of the range
    min_gain: float = 0.2     # the minimum volume, as a multiplier: no sound is quieter
    edge_db: float = -30.0    # the "log" model's loudness at the edge of the view
    bright_hz: float = 16000.0
    dull_hz: float = 1500.0
    beyond_hz: float = 900.0

    @classmethod
    def from_defaults(cls, d: dict) -> "CurveSettings":
        values = d.get("sound", {}).get("curve", {})
        return cls(**{k: (str(v) if k == "model" else float(v)) for k, v in values.items()})


DEFAULT = CurveSettings()


def gain(fraction: float, s: CurveSettings = DEFAULT) -> float:
    """How loud a sound is for its distance, as a multiplier for the samples."""
    if fraction <= s.near:
        return 1.0
    if fraction >= 1.0:
        return s.min_gain
    t = (fraction - s.near) / (1.0 - s.near)
    if s.model == "log":
        g = 10 ** (s.edge_db * math.log2(fraction / s.near) / math.log2(1.0 / s.near) / 20)
    else:
        g = 1.0 - (1.0 - s.min_gain) * t
    return max(s.min_gain, g)


def distance_gain_db(fraction: float, s: CurveSettings = DEFAULT) -> float:
    """The same in decibels."""
    return 0.0 if fraction <= s.near else 20 * math.log10(gain(fraction, s))


def muffle_cutoff_hz(fraction: float, s: CurveSettings = DEFAULT) -> float:
    if fraction > 1.0:
        return s.beyond_hz
    if fraction <= s.near:
        return s.bright_hz
    t = math.log2(fraction / s.near) / math.log2(1.0 / s.near)
    return s.bright_hz * (s.dull_hz / s.bright_hz) ** t
