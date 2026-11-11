"""How a stage keeps its areas in the working folder (architecture 8.3).

Two files: features.json, the feature records in order, and shapes.wkb,
each shape in well-known binary, one after another, with the offsets in
features.json. Architecture 8.3 names GeoParquet; that needs pyarrow, a
large new dependency, so these plain files are used until a stage needs
GeoParquet's extra features.
"""
from __future__ import annotations

import json
from pathlib import Path

import shapely


def save(folder: Path, records: list[dict], geoms: list, claim=lambda p: p) -> None:
    blobs = [shapely.to_wkb(g) for g in geoms]
    offsets, at = [], 0
    for b in blobs:
        offsets.append([at, len(b)])
        at += len(b)
    with open(claim(Path(folder) / "shapes.wkb"), "wb") as out:
        for b in blobs:
            out.write(b)
    text = json.dumps({"records": records, "shapes": offsets}, ensure_ascii=False, sort_keys=True, indent=0)
    claim(Path(folder) / "features.json").write_text(text, encoding="utf-8", newline="\n")


def load(folder: Path) -> tuple[list[dict], list]:
    data = json.loads((Path(folder) / "features.json").read_text(encoding="utf-8"))
    raw = (Path(folder) / "shapes.wkb").read_bytes()
    geoms = [shapely.from_wkb(raw[a:a + n]) for a, n in data["shapes"]]
    return data["records"], geoms


def append(folder: Path, records: list[dict], blobs: list[bytes]) -> None:
    """Add records and their shapes, already in well-known binary, to a folder's areas, without reading the
    shapes already there."""
    path = Path(folder) / "features.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    shapes = Path(folder) / "shapes.wkb"
    at = shapes.stat().st_size
    with open(shapes, "ab") as out:
        for b in blobs:
            data["shapes"].append([at, len(b)])
            out.write(b)
            at += len(b)
    data["records"].extend(records)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8", newline="\n")
