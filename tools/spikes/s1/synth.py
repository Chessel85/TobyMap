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
import math
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
    setup: str = "atmap"  # "atmap": a 3D source, as AtMap; "angular": an angle-panned source

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
        # AtMap's listener: at the origin, facing +y (north), with +z up.
        self.context.position.value = (0.0, 0.0, 0.0)
        self.context.orientation.value = (0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
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
        if live.setup == "angular":
            # Synthizer's angle-panned source: azimuth in degrees clockwise from
            # ahead, with no positions or listener involved.
            source = syz.AngularPannedSource(self.context, syz.PannerStrategy.HRTF, azimuth=live.bearing % 360)
        else:
            # As AtMap's CSpatialSource: a Source3D with the HRTF panner, placed by
            # x (east) and y (north), with the listener facing +y and z up.
            b = math.radians(live.bearing)
            source = syz.Source3D(self.context, syz.PannerStrategy.HRTF, position=(math.sin(b), math.cos(b), 0.0))
            source.distance_model.value = syz.DistanceModel.NONE  # SON-9 distance is already applied
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
