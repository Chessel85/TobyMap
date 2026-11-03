"""The overlap check: areas in one layer that share land (P1-T16, architecture 6.12).

Spike S2's check looked only for areas that partly overlap, so it missed
Sevastopol, which OSM holds twice with the same outline, one copy wholly on
top of the other. This check finds every pair of areas in a layer whose
insides meet, and says which of three kinds it is:

* same land: each holds at least SAME_SHARE of the other;
* wholly inside: the smaller lies at least SAME_SHARE inside the larger;
* partly overlapping: anything else, with the land they share.

Areas that only touch along their borders are not counted. Shapes are
compared as read, or as cut to the land; areas are measured on the WGS 84
ellipsoid.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely

from mapdata.stages.clip import polygonal
from mapdata.stages.geodesy import area_km2

SAME_SHARE = 0.99
SAME_LAND = "same land"
INSIDE = "wholly inside"
PARTLY = "partly overlapping"


@dataclass
class Overlap:
    first: int          # index of the first area; for "wholly inside", the smaller one
    second: int
    kind: str
    shared_km2: float
    first_km2: float
    second_km2: float


def find(shapes: list, min_km2: float = 0.0) -> list[Overlap]:
    """Every pair of areas whose insides meet, largest shared land first.

    Pairs sharing less than min_km2 are left out, except "same land" and
    "wholly inside", which are always kept, however small.
    """
    arr = np.array(shapes, dtype=object)
    if len(arr) < 2:
        return []
    tree = shapely.STRtree(arr)
    left, right = tree.query(arr, predicate="intersects")
    keep = left < right
    left, right = left[keep], right[keep]
    if len(left) == 0:
        return []
    # Insides meet: the first cell of the DE-9IM matrix is not F. This leaves
    # out areas that only touch along their borders.
    inside = shapely.relate_pattern(arr[left], arr[right], "T********")
    out = []
    for i, j in zip(left[inside].tolist(), right[inside].tolist()):
        o = classify(arr, i, j)
        if o.kind == PARTLY and o.shared_km2 < min_km2:
            continue
        out.append(o)
    out.sort(key=lambda o: (-o.shared_km2, o.first, o.second))
    return out


def classify(arr, i: int, j: int) -> Overlap:
    """Which kind of overlap two areas whose insides meet have."""
    shared = polygonal(shapely.intersection(arr[i], arr[j]))
    shared_km2 = area_km2(shared) if shared is not None and not shared.is_empty else 0.0
    ki, kj = area_km2(arr[i]), area_km2(arr[j])
    small, large = (i, j) if ki <= kj else (j, i)
    k_small, k_large = min(ki, kj), max(ki, kj)
    if k_small > 0 and shared_km2 >= SAME_SHARE * k_large:
        kind = SAME_LAND
    elif k_small > 0 and shared_km2 >= SAME_SHARE * k_small:
        kind = INSIDE
    else:
        kind = PARTLY
    return Overlap(small, large, kind, shared_km2, k_small, k_large)


def same_land(shapes: list) -> list[Overlap]:
    """Only the pairs with the same land: quicker than find(), as only pairs whose
    bounding boxes nearly match are measured."""
    arr = np.array(shapes, dtype=object)
    if len(arr) < 2:
        return []
    bounds = shapely.bounds(arr)
    size = np.maximum(bounds[:, 2] - bounds[:, 0], bounds[:, 3] - bounds[:, 1])
    left, right = shapely.STRtree(arr).query(arr)
    keep = left < right
    left, right = left[keep], right[keep]
    slack = 0.01 * np.maximum(size[left], size[right]) + 1e-9
    close = (np.abs(bounds[left] - bounds[right]) <= slack[:, None]).all(axis=1)
    out = []
    for i, j in zip(left[close].tolist(), right[close].tolist()):
        if not shapely.relate_pattern(arr[i], arr[j], "T********"):
            continue
        o = classify(arr, i, j)
        if o.kind == SAME_LAND:
            out.append(o)
    out.sort(key=lambda o: (-o.shared_km2, o.first, o.second))
    return out


def report(layer_name: str, overlaps: list[Overlap], names: list[str], log, most: int = 15) -> list[dict]:
    """Report lines and rows for one layer's overlaps."""
    counts = {k: sum(o.kind == k for o in overlaps) for k in (SAME_LAND, INSIDE, PARTLY)}
    if not overlaps:
        log(f"{layer_name}: no two areas share land.")
    else:
        log(f"{layer_name}: areas sharing land: {counts[SAME_LAND]} pairs with the same land, "
            f"{counts[INSIDE]} with one wholly inside the other, and {counts[PARTLY]} partly overlapping, "
            f"{sum(o.shared_km2 for o in overlaps):,.3f} km2 in all.")
    rows = []
    for k, o in enumerate(overlaps):
        a, b = names[o.first], names[o.second]
        if o.kind == SAME_LAND:
            text = f"{a} and {b} have the same land, {o.shared_km2:,.3f} km2."
        elif o.kind == INSIDE:
            text = f"{a}, {o.first_km2:,.3f} km2, is wholly inside {b}."
        else:
            text = f"{a} and {b} partly overlap, sharing {o.shared_km2:,.3f} km2."
        if k < most:
            log(f"  {text}")
        rows.append({"layer": layer_name, "kind": o.kind, "first": a, "second": b,
                     "shared_km2": o.shared_km2, "first_km2": o.first_km2, "second_km2": o.second_km2})
    if len(overlaps) > most:
        log(f"  and {len(overlaps) - most} more, listed in summary.json.")
    return rows
