"""Synthizer's HRTF, for the spike S1 comparison (architecture 12.2, DP91).

Synthizer 0.12.6 (Unlicense) is the library AtMap used. It has no Python 3.14
package, so it is built from source by build_synthizer.ps1. It can only play
to the sound device, with no way to render into memory, so its engine returns
a Live object, which spatial.play() hands back here. Nothing in this module
opens a device until play() is called, so the tests stay silent.

Synthizer's own distance model is switched off: the sound is given spike S1's
SON-9 loudness and muffling before Synthizer places it, so every engine is
compared on direction alone. (Both are linear filters, so the order does not
change the result.)
"""
from __future__ import annotations

import atexit
import time
from dataclasses import dataclass

import numpy as np


def available() -> bool:
    try:
        import synthizer  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class Live:
    """A sound for Synthizer to play from a direction: mono, ready for distance."""
    mono: np.ndarray
    bearing: float  # degrees clockwise from ahead
    rate: int

    @property
    def shape(self):  # so the demo's stand-in players can treat it like stereo samples
        return (len(self.mono), 2)


class _Player:
    def __init__(self):
        import synthizer
        self.syz = synthizer
        synthizer.initialize()
        self.context = synthizer.Context()
        self.context.default_panner_strategy.value = synthizer.PannerStrategy.HRTF
        # Synthizer's audio thread keeps Python running until it is shut down.
        atexit.register(self.close)

    def close(self) -> None:
        if self.context is not None:
            self.context.dec_ref()
            self.context = None
            self.syz.shutdown()

    def play(self, live: Live) -> None:  # pragma: no cover - opens the audio device
        syz = self.syz
        buffer = syz.Buffer.from_float_array(live.rate, 1, np.ascontiguousarray(live.mono, dtype=np.float32))
        # Synthizer's azimuth is in degrees clockwise from ahead, like the bearings here.
        source = syz.AngularPannedSource(self.context, syz.PannerStrategy.HRTF, azimuth=live.bearing % 360)
        generator = syz.BufferGenerator(self.context)
        generator.buffer.value = buffer
        source.add_generator(generator)
        time.sleep(len(live.mono) / live.rate + 0.25)
        for obj in (generator, source, buffer):
            obj.dec_ref()


_player: _Player | None = None


def play(live: Live) -> None:  # pragma: no cover - opens the audio device
    global _player
    if _player is None:
        _player = _Player()
    _player.play(live)
