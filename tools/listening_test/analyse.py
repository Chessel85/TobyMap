r"""Analyse the listening test results (P1-T13, SON-1, SON-9).

    .venv\Scripts\python.exe -m tools.listening_test.analyse docs\spikes\listening-test\*.csv

Reports, for each mode: the share of direction answers within 45 degrees (the
target is 80 percent), front and back confusions, how well the distance answers
follow the distance played, and how often "beyond the view" was recognised. It
writes docs/spikes/listening-test/findings.md for the PO, with the settings
proposed. Written for a screen reader: headings and lists, no tables.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from tools.listening_test.model import read_results

TARGET = 0.80
WITHIN = 45


def angle_difference(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def is_front(bearing: float) -> bool:
    return bearing % 360 < 90 or bearing % 360 > 270


def spearman(x, y) -> float | None:
    if len(x) < 3:
        return None
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def analyse(rows: list[dict]) -> dict:
    """Numbers per group of rows (mode, or block name for the special blocks)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["block_name"]].append(r)
    out = {}
    for name, rs in groups.items():
        answered = [r for r in rs if r["heard_hour"] not in ("", "0")]
        within = [angle_difference(float(r["played_bearing"]), float(r["heard_bearing"])) <= WITHIN for r in answered]
        confusions = [is_front(float(r["played_bearing"])) != is_front(float(r["heard_bearing"]))
                      for r in answered if float(r["played_bearing"]) % 180 != 0 and float(r["heard_bearing"]) % 180 != 0]
        with_level = [r for r in rs if r["heard_level"] != ""]
        beyond = [r for r in with_level if r["played_level"] == "5"]
        rho = spearman([float(r["played_fraction"]) for r in with_level], [float(r["heard_level"]) for r in with_level])
        out[name] = {
            "trials": len(rs), "cant_tell": len(rs) - len(answered),
            "within_45": (sum(within) / len(within)) if within else None,
            "front_back": (sum(confusions) / len(confusions)) if confusions else None,
            "distance_rho": rho,
            "beyond_recognised": (sum(r["heard_level"] == "5" for r in beyond) / len(beyond)) if beyond else None,
            "false_beyond": (sum(r["heard_level"] == "5" for r in with_level if r["played_level"] != "5")
                             / max(1, sum(r["played_level"] != "5" for r in with_level))) if with_level else None,
        }
        if name == "labels":
            by_style = defaultdict(list)
            for r in answered:
                by_style[r["style"]].append(angle_difference(float(r["played_bearing"]), float(r["heard_bearing"])) <= WITHIN)
            out[name]["by_style"] = {k: sum(v) / len(v) for k, v in by_style.items()}
        if name == "beyond":
            by_style = defaultdict(list)
            for r in beyond:
                by_style[r["style"]].append(r["heard_level"] == "5")
            out[name]["beyond_by_style"] = {k: sum(v) / len(v) for k, v in by_style.items()}
    return out


def percent(x) -> str:
    return "not enough answers" if x is None else f"{round(100 * x)} percent"


def findings(results: dict) -> str:
    lines = ["# Listening test findings", "",
             "Made by tools/listening_test/analyse.py from the results files in this folder. "
             f"The target is {round(TARGET * 100)} percent of direction answers within {WITHIN} degrees.", ""]
    proposals = []
    for name, r in results.items():
        lines += [f"## {name}", "", f"* Trials: {r['trials']}, of which you could not tell the direction in {r['cant_tell']}.",
                  f"* Direction answers within {WITHIN} degrees: {percent(r['within_45'])}.",
                  f"* Front and back confusions: {percent(r['front_back'])}.",
                  f"* Distance answers following the distance played (rank correlation, 1 is perfect): "
                  f"{'not enough answers' if r['distance_rho'] is None else f'{r['distance_rho']:.2f}'}.",
                  f"* Beyond the view recognised: {percent(r['beyond_recognised'])}; "
                  f"sounds inside the view wrongly called beyond: {percent(r['false_beyond'])}."]
        for key, label in (("by_style", "Direction within 45 degrees, by label style"),
                           ("beyond_by_style", "Beyond the view recognised, by style")):
            if key in r:
                lines += [f"* {label}:"] + [f"  * {s}: {percent(v)}" for s, v in sorted(r[key].items())]
        lines.append("")
        if r["within_45"] is not None and name in ("stereo", "hrtf_pitch"):
            met = r["within_45"] >= TARGET
            proposals.append(f"{name}: {'meets' if met else 'does not meet'} the {round(TARGET * 100)} percent target "
                             f"({percent(r['within_45'])}).")
    lines += ["## Settings I propose", ""]
    if proposals:
        lines += [f"* {p}" for p in proposals]
        lines.append("* Keep the distance curve as it is (full loudness within a twentieth of the range, minus 30 decibels at the edge) unless "
                     "the distance answers above follow the distance poorly; then make the edge quieter.")
    else:
        lines.append("* There are not enough results yet. Run the listening test, then this again.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    paths = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print("Give the results files (CSV) as arguments.")
        return 1
    rows = [r for p in paths for r in read_results(p)]
    target = Path(paths[0]).parent / "findings.md"
    text = findings(analyse(rows))
    target.write_text(text, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
