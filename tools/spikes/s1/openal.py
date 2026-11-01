"""OpenAL Soft's HRTF, for the spike S1 comparison (architecture 12.2).

OpenAL Soft (LGPL-2.1 or later) is loaded with ctypes from
tools/spikes/s1/vendor, which is not in git. It renders into memory through
the ALC_SOFT_loopback extension, so no sound device is opened here and the
result plays through the same route as the other engines.

OpenAL's own distance model is switched off. Distance is applied afterwards
with spike S1's SON-9 curve and muffling, so every engine is compared on
direction alone.
"""
from __future__ import annotations

import ctypes
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DLL = HERE / "vendor" / "openal-soft-1.25.2" / "soft_oal.dll"

# ALC and AL constants, from OpenAL Soft's alc.h, al.h, alext.h and efx.h.
ALC_FREQUENCY = 0x1007
ALC_FORMAT_CHANNELS_SOFT = 0x1990
ALC_FORMAT_TYPE_SOFT = 0x1991
ALC_STEREO_SOFT = 0x1501
ALC_FLOAT_SOFT = 0x1406
ALC_HRTF_SOFT = 0x1992
ALC_HRTF_STATUS_SOFT = 0x1993
ALC_HRTF_ENABLED_SOFT = 0x0001
ALC_HRTF_SPECIFIER_SOFT = 0x1995
ALC_TRUE = 1
AL_NONE = 0
AL_POSITION = 0x1004
AL_BUFFER = 0x1009
AL_SOURCE_RELATIVE = 0x202
AL_FORMAT_MONO_FLOAT32 = 0x10010
AL_SOURCE_STATE = 0x1010
AL_PLAYING = 0x1012

TAIL_FRAMES = 1024  # room for the HRTF's own length after the sound ends


def available() -> bool:
    return DLL.exists()


class OpenAL:
    """One loopback device with HRTF switched on, at the given rate."""

    def __init__(self, rate: int = 44100, dll: Path = DLL):
        if not dll.exists():
            raise FileNotFoundError(f"{dll} is missing. See docs/spikes/S1-spatial-sound.md.")
        self.rate = rate
        lib = self.lib = ctypes.CDLL(str(dll))
        lib.alcGetProcAddress.restype = ctypes.c_void_p
        lib.alcGetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.alcCreateContext.restype = ctypes.c_void_p
        lib.alcCreateContext.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
        lib.alcMakeContextCurrent.argtypes = [ctypes.c_void_p]
        lib.alcGetIntegerv.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        lib.alcGetString.restype = ctypes.c_char_p
        lib.alcGetString.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.alcDestroyContext.argtypes = [ctypes.c_void_p]
        lib.alcCloseDevice.argtypes = [ctypes.c_void_p]
        lib.alBufferData.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        lib.alSource3f.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float]
        lib.alSourcei.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_int]

        def proc(name, restype, *argtypes):
            address = lib.alcGetProcAddress(None, name.encode())
            if not address:
                raise RuntimeError(f"OpenAL Soft has no {name}")
            return ctypes.CFUNCTYPE(restype, *argtypes)(address)

        open_loopback = proc("alcLoopbackOpenDeviceSOFT", ctypes.c_void_p, ctypes.c_char_p)
        self._render = proc("alcRenderSamplesSOFT", None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
        self.device = open_loopback(None)
        if not self.device:
            raise RuntimeError("OpenAL Soft could not open a loopback device")
        attrs = (ctypes.c_int * 11)(ALC_FORMAT_CHANNELS_SOFT, ALC_STEREO_SOFT, ALC_FORMAT_TYPE_SOFT, ALC_FLOAT_SOFT,
                                    ALC_FREQUENCY, rate, ALC_HRTF_SOFT, ALC_TRUE, 0, 0, 0)
        self.context = lib.alcCreateContext(self.device, attrs)
        if not self.context:
            raise RuntimeError("OpenAL Soft could not create a context")
        lib.alcMakeContextCurrent(self.context)
        lib.alDistanceModel(AL_NONE)
        status = ctypes.c_int(0)
        lib.alcGetIntegerv(self.device, ALC_HRTF_STATUS_SOFT, 1, ctypes.byref(status))
        self.hrtf_enabled = status.value == ALC_HRTF_ENABLED_SOFT
        name = lib.alcGetString(self.device, ALC_HRTF_SPECIFIER_SOFT)
        self.hrtf_name = name.decode("utf-8", "replace") if name else ""

    def render(self, mono: np.ndarray, bearing: float) -> np.ndarray:
        """The sound from a direction in degrees clockwise from ahead, as stereo (n, 2)."""
        lib = self.lib
        data = np.ascontiguousarray(mono, dtype=np.float32)
        buf, src = ctypes.c_uint(0), ctypes.c_uint(0)
        lib.alGenBuffers(1, ctypes.byref(buf))
        lib.alGenSources(1, ctypes.byref(src))
        try:
            lib.alBufferData(buf.value, AL_FORMAT_MONO_FLOAT32, data.ctypes.data, data.nbytes, self.rate)
            lib.alSourcei(src.value, AL_BUFFER, buf.value)
            lib.alSourcei(src.value, AL_SOURCE_RELATIVE, ALC_TRUE)
            # OpenAL looks along -Z, with +X to the right.
            b = math.radians(bearing)
            lib.alSource3f(src.value, AL_POSITION, math.sin(b), 0.0, -math.cos(b))
            lib.alSourcePlay(src.value)
            frames = len(data) + TAIL_FRAMES
            out = np.zeros((frames, 2), dtype=np.float32)
            self._render(self.device, out.ctypes.data, frames)
            return out
        finally:
            lib.alSourceStop(src.value)
            lib.alSourcei(src.value, AL_BUFFER, 0)
            lib.alDeleteSources(1, ctypes.byref(src))
            lib.alDeleteBuffers(1, ctypes.byref(buf))

    def close(self):
        if self.context:
            self.lib.alcMakeContextCurrent(None)
            self.lib.alcDestroyContext(self.context)
            self.context = None
        if self.device:
            self.lib.alcCloseDevice(self.device)
            self.device = None


_shared: OpenAL | None = None


def shared(rate: int = 44100) -> OpenAL:
    global _shared
    if _shared is None:
        _shared = OpenAL(rate)
    return _shared
