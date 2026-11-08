"""Time stretching for the spatial voice: faster speech without the pitch going up (P2-T16g, SON-3).

Piper, the voice, can only shorten each sound so far: asked for 500 percent it is only about
2.2 times as fast. So above 100 percent:

1. Piper speaks as fast as it cleanly can, at most twice its own speed (split_rate). Asked
   for that, it is really about 1.6 times as fast (piper_speed, measured with Alba).
2. The gaps between words are shortened first, as screen readers do at high speeds, so less
   of the words themselves has to be cut (shorten_gaps).
3. WSOLA (waveform similarity overlap-add) makes up the rest of the speed (wsola). The
   speech is cut into slices of 25 ms, each long enough to hold a few repeats of the voice's
   wave, so each keeps its pitch. Only some slices are kept: for five times as fast, the
   kept slices are five times as far apart in the original as in the result. Each fades
   into the next. Before each join, the slice's start is nudged, by up to 8 ms, to where its
   wave best lines up with the slice before, so the joins are not rough or buzzy.

At 100 percent or below, nothing is stretched, as before.

NumPy only, so the desktop and the web version share it (AD-1). In Pyodide NumPy is 32-bit,
so offsets are np.intp.
"""
from __future__ import annotations

import math

import numpy as np

PIPER_MOST = 2.0        # the fastest Piper is asked to speak; faster than this it slurs
PIPER_EXPONENT = 0.7    # asked for p times as fast, Piper is about p ** 0.7 (1.54 to 1.67 at 2)
FRAME_S = 0.025         # each slice
SEARCH_S = 0.008        # how far a slice's start may be nudged, either way
GAP_WINDOW_S = 0.005    # the loudness is measured in windows this long
GAP_LEVEL = 0.03        # quieter than this, as a share of the loudest sample, is a gap
GAP_MIN_S = 0.06        # shorter gaps are left alone: they are part of the words
GAP_KEEP_S = 0.04       # a gap is never shortened below this
FADE = 32               # samples faded where a gap is cut


def piper_speed(rate: float) -> float:
    """How many times as fast Piper really speaks when asked for rate."""
    return rate if rate <= 1.0 else rate ** PIPER_EXPONENT


def split_rate(rate: float) -> tuple[float, float]:
    """The speed chosen, as (what Piper is asked for, the stretch that makes up the rest)."""
    if rate <= 1.0:
        return rate, 1.0
    piper = min(rate, PIPER_MOST)
    return piper, rate / piper_speed(piper)


def speed_up(samples: np.ndarray, rate_hz: int, factor: float) -> np.ndarray:
    """samples made factor times as fast, at the same pitch: gaps first, then WSOLA."""
    if factor <= 1.0 or len(samples) == 0:
        return samples
    target = len(samples) / factor
    shorter = shorten_gaps(samples, rate_hz, factor)
    rest = len(shorter) / target
    if rest <= 1.0:
        return shorter.astype(np.float32)
    return wsola(shorter, rate_hz, rest)


def shape_voice(samples: np.ndarray, rate_hz: int, stretch: float = 1.0, pitch: float = 1.0) -> np.ndarray:
    """A label from Piper made stretch times as fast and at pitch times the pitch, as the core's
    Response.voice asks. Both shells call this.

    The voice behind you is lower at the same speed (the PO chose this, sample 9, on 8 November
    2026): it is made shorter at the same pitch first, then played slower, which lowers the
    pitch and brings the length back. Both are done in one time stretching, so the speech is
    sliced only once."""
    if pitch >= 1.0:
        return speed_up(samples, rate_hz, stretch)
    shorter = speed_up(samples, rate_hz, stretch / pitch).astype(np.float64)
    n = int(len(shorter) / pitch)
    return np.interp(np.arange(n) * pitch, np.arange(len(shorter)), shorter).astype(np.float32)


def lower_pitch(samples: np.ndarray, rate_hz: int, ratio: float) -> np.ndarray:
    """samples at ratio times the pitch, below 1 lower, without slowing down."""
    return shape_voice(samples, rate_hz, 1.0, ratio)


def _gaps(samples: np.ndarray, rate_hz: int) -> list[tuple[int, int]]:
    """Where the quiet stretches between words are, as (start, end) sample offsets."""
    window = max(1, int(GAP_WINDOW_S * rate_hz))
    count = len(samples) // window
    top = float(np.abs(samples).max()) if len(samples) else 0.0
    if count == 0 or top == 0.0:
        return []
    rms = np.sqrt((samples[: count * window].astype(np.float64).reshape(count, window) ** 2).mean(axis=1))
    quiet = np.concatenate([[False], rms < GAP_LEVEL * top, [False]])
    edges = np.flatnonzero(np.diff(quiet.astype(np.int8)))
    shortest = int(GAP_MIN_S * rate_hz)
    gaps = []
    for start, end in zip(edges[0::2], edges[1::2]):
        a, b = int(start) * window, int(end) * window
        if b - a >= shortest:
            gaps.append((a, b))
    return gaps


def shorten_gaps(samples: np.ndarray, rate_hz: int, factor: float) -> np.ndarray:
    """The gaps between words shortened, by twice as much as the speed-up, but never below
    GAP_KEEP_S and never by more than the whole speed-up needs."""
    if factor <= 1.0:
        return samples
    gaps = _gaps(samples, rate_hz)
    if not gaps:
        return samples
    keep_least = int(GAP_KEEP_S * rate_hz)
    cuts = [max(0, (b - a) - max(keep_least, int((b - a) / (2 * factor)))) for a, b in gaps]
    needed = len(samples) - len(samples) / factor
    if sum(cuts) > needed:
        cuts = [int(c * needed / sum(cuts)) for c in cuts]
    parts, at = [], 0
    fade_out = np.linspace(1.0, 0.0, FADE, dtype=np.float32)
    for (a, b), cut in zip(gaps, cuts):
        if cut <= 2 * FADE:
            continue
        middle = (a + b) // 2
        left_end, right_start = middle - cut // 2, middle - cut // 2 + cut
        head = samples[at:left_end].astype(np.float32)
        if len(head) >= FADE:   # the cut fades across, so even a quiet hiss never clicks
            head = head.copy()
            head[-FADE:] = head[-FADE:] * fade_out + samples[right_start: right_start + FADE] * fade_out[::-1]
            at = right_start + FADE
        else:
            at = right_start
        parts.append(head)
    parts.append(samples[at:].astype(np.float32))
    return np.concatenate(parts)


def wsola(samples: np.ndarray, rate_hz: int, factor: float) -> np.ndarray:
    """samples factor times as fast at the same pitch, by waveform similarity overlap-add."""
    if factor <= 1.0:
        return samples
    x = np.asarray(samples, dtype=np.float64)
    frame = max(4, int(FRAME_S * rate_hz) // 2 * 2)
    hop = frame // 2                          # each kept slice overlaps the next by half
    search = max(1, int(SEARCH_S * rate_hz))
    out_len = int(len(x) / factor)
    if len(x) < frame + 2 * search or out_len < frame:
        return samples   # too short to slice: a label is never this short
    steps = math.ceil(out_len / hop) + 1
    far = int(math.ceil(steps * hop * factor))
    padded = np.concatenate([np.zeros(search), x, np.zeros(max(0, far - len(x)) + 2 * frame + 2 * search)])
    # A periodic Hann window: at half overlap the fades add up to exactly 1.
    window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(frame) / frame)
    first = window.copy()
    first[:hop] = 1.0                         # the very start is not faded in
    out = np.zeros(steps * hop + frame)
    out[:frame] = x[:frame] * first
    previous = 0                              # where in samples the last kept slice started
    ones = np.ones(frame)
    for k in range(1, steps):
        nominal = int(round(k * hop * factor))
        follow = padded[search + previous + hop: search + previous + hop + frame]   # what would come next
        region = padded[nominal: nominal + frame + 2 * search]                       # nominal - search onwards
        match = np.correlate(region, follow, mode="valid")
        energy = np.correlate(region * region, ones, mode="valid")
        best = int(np.argmax(match / np.sqrt(energy + 1e-9)))
        start = nominal - search + best
        out[k * hop: k * hop + frame] += padded[search + start: search + start + frame] * window
        previous = start
    return out[:out_len].astype(np.float32)
