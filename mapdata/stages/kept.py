"""Each country built and kept on its own (P1-T16, DP107, implementation plan P1-T16).

Each country's results, its land and its divisions' land, its counties and
the checks of its own layers, are kept in the working folder under a
fingerprint of everything that could change them:

* the planet file and the land polygons, so a new planet file rebuilds every
  country, and neighbours never come from OSM data of different dates;
* the country's shapes as read, and its settings, including its entry in the
  counties record;
* the version of the code that builds it.

A change for one country changes only its fingerprint, so only that country
is rebuilt.

Borders between countries are checked in pairs. After a country is rebuilt,
the check that neighbours meet exactly (AD-16) runs again on its border with
each neighbour. A pair where neither side was rebuilt keeps its last result.
If a border no longer matches, the neighbour is rebuilt too, from its shapes
as read and without its kept copy, and the border is checked again. If it
still does not match, the fault is in the data or the build, not in an old
kept copy, and the report says so.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely

STORE_VERSION = "kept-1"


def fingerprint(parts: dict) -> str:
    """A fingerprint of a dict of inputs. Shapes are given as their well-known binary."""
    h = hashlib.sha256(STORE_VERSION.encode())
    for key in sorted(parts):
        h.update(key.encode())
        value = parts[key]
        if isinstance(value, (bytes, bytearray)):
            h.update(bytes(value))
        else:
            h.update(json.dumps(value, sort_keys=True, default=str).encode())
    return h.hexdigest()[:20]


def shapes_print(shapes: list) -> str:
    """A fingerprint of shapes as read, in order."""
    h = hashlib.sha256()
    for item in shapes:
        if isinstance(item, str):
            h.update(item.encode())
        else:
            h.update(shapely.to_wkb(item))
    return h.hexdigest()


def _safe(identifier: str) -> str:
    return identifier.replace(":", "_").replace("/", "_")


class Store:
    """The kept countries and the kept border checks, in one folder of the working folder."""

    def __init__(self, folder: Path, claim=lambda p: p):
        self.folder = Path(folder)
        self.claim = claim

    def _country_path(self, country_id: str, fp: str) -> Path:
        return self.folder / "countries" / f"{_safe(country_id)}-{fp}.pkl"

    def load(self, country_id: str, fp: str):
        path = self._country_path(country_id, fp)
        if not path.is_file():
            return None
        return pickle.loads(path.read_bytes())

    def save(self, country_id: str, fp: str, built) -> None:
        path = self.claim(self._country_path(country_id, fp))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(built, protocol=pickle.HIGHEST_PROTOCOL))
        tmp.replace(path)

    def _border_path(self, a: tuple[str, str], b: tuple[str, str], extra: str) -> Path:
        (ia, fa), (ib, fb) = sorted([a, b])
        key = hashlib.sha256(f"{ia}{fa}{ib}{fb}{extra}".encode()).hexdigest()[:20]
        return self.folder / "borders" / f"{_safe(ia)}-{_safe(ib)}-{key}.json"

    def border(self, a, b, extra: str = "") -> dict | None:
        path = self._border_path(a, b, extra)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save_border(self, a, b, result: dict, extra: str = "") -> None:
        path = self.claim(self._border_path(a, b, extra))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, sort_keys=True, indent=1) + "\n", encoding="utf-8", newline="\n")


def neighbours(ids: list[str], raw: list) -> list[tuple[str, str]]:
    """Pairs of countries whose shapes as read touch or overlap, each pair once, in a fixed order."""
    arr = np.array(raw, dtype=object)
    tree = shapely.STRtree(arr)
    left, right = tree.query(arr, predicate="intersects")
    pairs = {tuple(sorted((ids[i], ids[j]))) for i, j in zip(left.tolist(), right.tolist()) if i != j}
    return sorted(pairs)


@dataclass
class BorderRow:
    first: str
    second: str
    matches: bool
    result: dict
    from_store: bool = False
    rebuilt: list[str] = field(default_factory=list)
    still_wrong: bool = False


def recheck_borders(pairs: list[tuple[str, str]], prints: dict[str, str], rebuilt: set[str], store: Store,
                    check, rebuild, extra: str = "") -> list[BorderRow]:
    """Check each pair's border, again only where a side was rebuilt.

    check(a, b) gives {"matches": bool, ...}; rebuild(country_id) builds that
    country again without its kept copy and returns its new fingerprint.
    prints is updated when a neighbour is rebuilt, and so is rebuilt.
    """
    rows = []
    for a, b in pairs:
        kept_result = store.border((a, prints[a]), (b, prints[b]), extra)
        if kept_result is not None and a not in rebuilt and b not in rebuilt:
            rows.append(BorderRow(a, b, bool(kept_result["matches"]), kept_result, from_store=True))
            continue
        result = check(a, b)
        row = BorderRow(a, b, bool(result["matches"]), result)
        if not row.matches:
            # The side not rebuilt in this run may be an out-of-date kept copy.
            for other in (b, a):
                if other in rebuilt:
                    continue
                prints[other] = rebuild(other)
                rebuilt.add(other)
                row.rebuilt.append(other)
            if row.rebuilt:
                result = check(a, b)
                row.matches, row.result = bool(result["matches"]), result
            row.still_wrong = not row.matches
        store.save_border((a, prints[a]), (b, prints[b]), row.result, extra)
        rows.append(row)
    return rows
