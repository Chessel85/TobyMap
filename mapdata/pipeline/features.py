"""How a stage keeps its areas in the working folder (architecture 8.3).

Two files: features.json, the feature records in order, and shapes.wkb,
each shape in well-known binary, one after another, with the offsets in
features.json. Architecture 8.3 names GeoParquet; that needs pyarrow, a
large new dependency, so these plain files are used until a stage needs
GeoParquet's extra features.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import shapely

SHORT = 40   # a string value up to this long is shared between records that repeat it, such as a layer or a type


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


def load_layers(folder: Path, layers: set[str]) -> tuple[list[dict], list]:
    """The records and shapes of the named layers only, so a stage that needs only the countries does not decode
    the world's 1.4 GB of shapes."""
    data = json.loads((Path(folder) / "features.json").read_text(encoding="utf-8"))
    records, geoms = [], []
    with open(Path(folder) / "shapes.wkb", "rb") as f:
        for r, (a, n) in zip(data["records"], data["shapes"]):
            if r.get("layer") in layers:
                f.seek(a)
                records.append(r)
                geoms.append(shapely.from_wkb(f.read(n)))
    return records, geoms


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


# Kinder to memory (P4-T1l): a regional pack such as England has millions of features, so the stages that pass every
# feature through read the records without the shapes, read only the shapes they need, and keep the shapes file of
# the stage before as it is when they change no shape.

def write_json(path: Path, data) -> None:
    """features.json's text, written as it is made, not first held whole in memory; the same bytes as before."""
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        json.dump(data, out, ensure_ascii=False, sort_keys=True, indent=0)


def _shared_strings():
    seen: dict[str, str] = {}

    def hook(pairs):
        return {k: (seen.setdefault(v, v) if type(v) is str and len(v) <= SHORT else v) for k, v in pairs}
    return hook


def read_index(folder: Path) -> dict:
    """features.json as it is: {"records": [...], "shapes": [[offset, length], ...]}, with each short string that
    records repeat, such as "streets" or "Footpath", held once. A third less memory on the rehearsal."""
    with open(Path(folder) / "features.json", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_shared_strings())


def load_records(folder: Path) -> list[dict]:
    """The records alone, in order, without the shapes."""
    return read_index(folder)["records"]


def read_shapes(folder: Path, offsets: list, which) -> dict[int, object]:
    """The shapes of the features numbered in which, by number, read from shapes.wkb one by one."""
    out = {}
    with open(Path(folder) / "shapes.wkb", "rb") as f:
        for i in sorted(which):
            a, n = offsets[i]
            f.seek(a)
            out[i] = shapely.from_wkb(f.read(n))
    return out


def keep_file(src: Path, dst: Path) -> None:
    """A file of the stage before, unchanged: linked where the drive allows, else copied."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def save_records(folder: Path, records: list[dict], previous: Path, offsets: list, claim=lambda p: p) -> None:
    """Save records whose shapes are those of the stage before, in the same order: the shapes file is kept as it
    is, so the folder is the same, byte for byte, as save() with the shapes decoded and encoded again."""
    keep_file(Path(previous) / "shapes.wkb", claim(Path(folder) / "shapes.wkb"))
    write_json(claim(Path(folder) / "features.json"), {"records": records, "shapes": offsets})


class DiskShapes:
    """The shapes of a stage's folder as a list that reads each from shapes.wkb only when asked (P4-T1l): shapes[i]
    decodes one, shapes[a:b] several, iterating decodes them in order a chunk at a time, and blob(i) gives one's
    well-known binary as it is stored. Nothing is kept, so a pass over England's shapes holds one chunk at a time."""

    CHUNK = 20_000

    def __init__(self, folder: Path, offsets: list):
        self.path = Path(folder) / "shapes.wkb"
        self.offsets = offsets
        self._file = None
        ends = [a for a, _n in offsets]
        self._in_order = all(x <= y for x, y in zip(ends, ends[1:]))

    def _f(self):
        if self._file is None:
            self._file = open(self.path, "rb")
        return self._file

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def __len__(self) -> int:
        return len(self.offsets)

    def blob(self, i: int) -> bytes:
        a, n = self.offsets[i]
        f = self._f()
        f.seek(a)
        return f.read(n)

    def blobs(self, start: int, stop: int) -> list[bytes]:
        if start >= stop:
            return []
        if not self._in_order:
            return [self.blob(i) for i in range(start, stop)]
        first = self.offsets[start][0]
        last_a, last_n = self.offsets[stop - 1]
        f = self._f()
        f.seek(first)
        raw = f.read(last_a + last_n - first)
        return [raw[a - first:a - first + n] for a, n in self.offsets[start:stop]]

    def __getitem__(self, i):
        if isinstance(i, slice):
            start, stop, step = i.indices(len(self))
            if step != 1:
                return [self[k] for k in range(start, stop, step)]
            return list(shapely.from_wkb(self.blobs(start, stop))) if stop > start else []
        if i < 0:
            i += len(self)
        return shapely.from_wkb(self.blob(i))

    def __iter__(self):
        for at in range(0, len(self), self.CHUNK):
            yield from self[at:at + self.CHUNK]
