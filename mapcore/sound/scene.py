"""The sound scene (P2-T6a; SON-1, SON-2, SON-9, AD-10, architecture 7.8).

For each sound to play, the core works out how it should sound, and the shells' sound
players only carry that out. Both players take these numbers as they are, so the
desktop and the web version place a sound the same way:

* relative_deg: the direction relative to ahead, clockwise: 0 ahead, 90 right, 180
  behind (SON-2). Ahead is north in north-fixed, and the way you face in cardinal and
  free facing.
* pan: from -1, full left, to 1, full right: the sine of the direction, for an
  equal-power panner. The stereo mode uses it; the HRTF mode uses relative_deg.
* gain: the loudness as a multiplier, from the distance curve (linear by default,
  DP137), never below the minimum volume.
* pitch: the playback rate. Below 1 behind you, about three semitones lower, in both
  modes (DP100).
* cutoff_hz: the muffling filter's cut-off. Lower with distance, lower still behind
  you (slightly), and lowest beyond the view.
* beyond: the sound is beyond the hearing range, which is the zoom distance (SON-9).
  It plays at the minimum volume, muffled, or as the fixed tone if that setting is
  chosen (DP80), when `sound` is the fixed tone's earcon instead.

The core plays nothing (AD-10).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from mapcore.sound.curve import CurveSettings, gain, muffle_cutoff_hz

BEHIND_PITCH = 0.84          # about three semitones lower (2 ** (-3 / 12) is 0.841)
BEHIND_MUFFLE = 0.7          # behind you, the cut-off is this much lower: slight muffling
BEYOND_TONE = "beyond_view"  # the fixed tone's earcon, for "beyond the view: a fixed tone" (DP80)
MODES = ("stereo", "hrtf")   # stereo with pitch, the default, and HRTF with pitch (DP100)


@dataclass(frozen=True)
class Placed:
    sound: str
    relative_deg: float
    pan: float
    gain: float
    pitch: float
    cutoff_hz: float
    behind: bool
    beyond: bool
    distance_m: float
    mode: str

    def to_dict(self) -> dict:
        return asdict(self)


def relative(bearing_deg: float, ahead_deg: float) -> float:
    """The direction relative to ahead, 0 to 360 clockwise."""
    return (bearing_deg - ahead_deg) % 360.0


def is_behind(relative_deg: float) -> bool:
    """Behind you: more than 90 degrees from ahead. Exactly to the side is not behind."""
    return math.cos(math.radians(relative_deg)) < -1e-9


def place(sound: str, bearing_deg: float, distance_m: float, ahead_deg: float, range_m: float,
          curve: CurveSettings = CurveSettings(), mode: str = "stereo", beyond_tone: bool = False) -> Placed:
    """How to play `sound` heard from a compass bearing and distance, facing `ahead_deg`, with
    the hearing range `range_m` (the zoom distance, SON-9)."""
    if mode not in MODES:
        raise ValueError(f"{mode!r} is not a sound mode")
    rel = relative(bearing_deg, ahead_deg)
    fraction = distance_m / range_m if range_m > 0 else math.inf
    beyond = fraction > 1.0
    behind = is_behind(rel)
    cutoff = muffle_cutoff_hz(fraction, curve) * (BEHIND_MUFFLE if behind else 1.0)
    pan = math.sin(math.radians(rel))
    return Placed(sound=BEYOND_TONE if beyond and beyond_tone else sound, relative_deg=round(rel, 6),
                  pan=0.0 if abs(pan) < 1e-12 else round(pan, 6), gain=gain(fraction, curve),
                  pitch=BEHIND_PITCH if behind else 1.0, cutoff_hz=cutoff, behind=behind, beyond=beyond,
                  distance_m=distance_m, mode=mode)
