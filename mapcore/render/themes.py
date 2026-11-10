"""Themes and the map display setting (P2-T12a, P2-T12b; VIS-2, DP108, AD-19).

The themes are in themes.yaml. effective() gives the theme the map is drawn with: the
chosen theme with the map display setting on top, which chooses the fill (different
colours for neighbours, one colour for all, or none), whether borders are drawn, and the
colours of the fill, the borders and the current outline. When the current outline is
drawn is the setting "Outline the current area" (P2-T17v, VIS-1).

The high contrast themes keep the 7 to 1 contrast of every outline and text colour
against what it is drawn on (VIS-2), with every choice: a chosen colour that would fall
below it is not used, and the theme's own is kept. contrast_problems() is the check.

The colour-blind safe theme is checked with a simulation of the three common kinds of
colour blindness (simulate()), so that neighbouring colours still differ.
"""
from __future__ import annotations

import itertools
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

THEMES_FILE = Path(__file__).resolve().parent / "themes.yaml"
TRANSPARENT = "#00000000"
HIGH_CONTRAST = 7.0
# Machado, Oliveira and Fernandes (2009), severity 1, in linear RGB.
SIMULATIONS = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}
# The settings that choose a colour, and the theme colour each one replaces.
COLOUR_SETTINGS = {"fill_colour": "fill", "border_colour": "border", "outline_colour": "current_outline"}


@lru_cache(maxsize=1)
def _data() -> dict:
    return yaml.safe_load(THEMES_FILE.read_text(encoding="utf-8"))


def names() -> list[str]:
    """The themes, in order."""
    return [k for k, v in _data().items() if isinstance(v, dict) and "land" in v]


def theme(name: str) -> dict:
    data = _data()
    return dict(data[name if name in data else "standard"])


def palette() -> dict[str, str]:
    return dict(_data()["palette"])


# Colour arithmetic -----------------------------------------------------------------

def _linear(colour: str) -> np.ndarray:
    c = np.array([int(colour[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminance(colour: str) -> float:
    """Relative luminance, as WCAG defines it."""
    return float(_linear(colour) @ np.array([0.2126, 0.7152, 0.0722]))


def contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio of two colours, 1 to 21."""
    low, high = sorted((luminance(a), luminance(b)))
    return (high + 0.05) / (low + 0.05)


def _lab(linear_rgb: np.ndarray) -> np.ndarray:
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) \
        @ np.clip(linear_rgb, 0.0, 1.0)
    t = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def difference(a: str, b: str, kind: str | None = None) -> float:
    """How different two colours look (CIE 1976 delta E), to normal sight or, with kind,
    to one of the SIMULATIONS. About 2 is just noticeable; 10 is clearly different."""
    m = np.eye(3) if kind is None else np.array(SIMULATIONS[kind])
    return float(np.linalg.norm(_lab(m @ _linear(a)) - _lab(m @ _linear(b))))


def least_difference(colours: list[str], kind: str | None = None) -> float:
    return min(difference(a, b, kind) for a, b in itertools.combinations(colours, 2))


# The checks --------------------------------------------------------------------------

def _shown(colour: str) -> bool:
    return colour != TRANSPARENT


def contrast_pairs(t: dict) -> list[tuple[str, str, str]]:
    """Every outline and text colour with each colour it is drawn on: (what, colour, under)."""
    fills = [c for c in t["land"] if _shown(c)] + [t["ocean"]]
    pairs = []
    if _shown(t["border"]):
        pairs += [("border", t["border"], f) for f in fills]
    pairs += [("current outline", t["current_outline"], f) for f in fills]
    pairs += [("line", t["line"], f) for f in fills]
    pairs += [("special line", t["special_line"], f) for f in fills]
    pairs += [("marker", t["marker"], f) for f in fills]
    pairs += [("marker outline", t["marker_outline"], t["marker"]),
              ("highlight outline", t["highlight_outline"], t["highlight_fill"]),
              ("cross", t["cross"], t["cross_halo"]),
              ("name", t["name_text"], t["name_halo"]),
              ("globe edge", t["globe_edge"], t["background"])]
    return pairs


def contrast_problems(t: dict, ratio: float = HIGH_CONTRAST) -> list[str]:
    """Each outline or text colour below the ratio against what it is drawn on."""
    return [f"{what} {fg} on {bg}: {contrast(fg, bg):.2f} to 1"
            for what, fg, bg in contrast_pairs(t) if contrast(fg, bg) < ratio]


# The map display setting (DP108) ---------------------------------------------------------

def _apply(t: dict, fill: str, borders: bool, colours: dict[str, str]) -> dict:
    t = dict(t)
    t["land"] = list(t["land"])
    if fill == "one":
        t["land"] = [colours.get("fill", t["land"][0])] * len(t["land"])
    elif fill == "none":
        t["land"] = [TRANSPARENT] * len(t["land"])
    if "border" in colours:
        t["border"] = colours["border"]
    if "current_outline" in colours:
        t["current_outline"] = colours["current_outline"]
    if not borders:
        t["border"] = TRANSPARENT
        t["border_width"] = 0
    return t


def effective(name: str, fill: str = "neighbours", borders: bool = True, fill_colour: str = "theme",
              border_colour: str = "theme", outline_colour: str = "theme") -> tuple[dict, list[str]]:
    """The theme to draw with, and the colour settings that were not used because, in a high
    contrast theme, they would fall below 7 to 1 (VIS-2, DP108). "theme" keeps the theme's own."""
    base = theme(name)
    colours_by_name = palette()
    chosen = {}
    for setting, value in (("fill_colour", fill_colour), ("border_colour", border_colour),
                           ("outline_colour", outline_colour)):
        if value != "theme" and value in colours_by_name:
            chosen[setting] = colours_by_name[value]
    if fill != "one":
        chosen.pop("fill_colour", None)   # the fill colour is used only for one colour for all
    refused = []
    if base.get("high_contrast"):
        # One at a time, in order, each kept only if the theme still passes with it.
        kept: dict[str, str] = {}
        for setting, colour in chosen.items():
            trial = dict(kept, **{COLOUR_SETTINGS[setting]: colour})
            if contrast_problems(_apply(base, fill, borders, trial)):
                refused.append(setting)
            else:
                kept = trial
        return _apply(base, fill, borders, kept), refused
    return _apply(base, fill, borders, {COLOUR_SETTINGS[s]: c for s, c in chosen.items()}), refused
