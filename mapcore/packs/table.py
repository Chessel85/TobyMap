"""The compact feature table, from pack format 5 (P4-T3f, DP225, architecture 6.2).

The store needs, for every feature, its identifier, layer, width and bounding box: the drawing's visible rule,
the places under a point and the merging of records across packs all use them. Before format 5 it read every
feature record to make them, and kept the records: 10.4 GB and 37 seconds for the England pack. A format 5 pack
stores them as a few records of whole numbers, read in one go, all in feature number order:

* table: JSON, {"count": features, "layers": [layer ids, in the order first met], "aliases": {alias: id},
  "boxes": how table/boxes is stored, "widths": how table/widths is stored}.
* table/boxes: each feature's bbox. "i4e7": west and south in ten-millionths of a degree, then east minus west and
  north minus south, as 4-byte whole numbers that wrap round (so a box across the 180 degree line is stored too);
  the four columns one after another. Used when every value is a whole number of ten-millionths, as the pipeline
  gives them. "f8": otherwise, west, south, east, north of each feature as 8-byte floats.
* table/widths: each feature's width_km. "i4e3": in metres as 4-byte whole numbers, -1 where the record has none;
  used when every width is a whole number of metres, as the pipeline gives them. "f8": otherwise, 8-byte floats,
  infinity where the record has none.
* table/layers: each feature's layer, as its place in "layers", 1 byte (2 bytes when there are over 256 layers).
* table/ids: the identifiers, UTF-8, one after another.
* table/id_lengths: each identifier's length in bytes, 2 bytes.

Every number is little-endian, and each record of numbers of more than one byte is stored byte-shuffled: the first
byte of every number, then the second byte of every number, and so on, which zlib compresses far better.

The identifiers in a group are in order (pack-format.md, features/G), so an identifier is found by a binary search of
its group's part of the table, with no feature record read.

Only the standard library and NumPy, so it runs in Pyodide, where NumPy is 32-bit: offsets are np.intp.
"""
from __future__ import annotations

import json
import math
from array import array

import numpy as np

KEYS = ("table", "table/boxes", "table/widths", "table/layers", "table/ids", "table/id_lengths")
MAX_ID_BYTES = 2 ** 31 - 1   # all the identifiers' bytes, so an offset fits Pyodide's 32-bit np.intp
MAX_ID_LENGTH = 65_535       # one identifier's bytes
DEGREE = 10_000_000          # "i4e7": ten-millionths of a degree, as compact coordinates (coords.SCALE)
METRES = 1_000               # "i4e3": metres in a kilometre


class TableError(ValueError):
    """The builder was given what the table cannot hold. The writer turns it into a PackWriteError."""


def _shuffle(values: np.ndarray) -> bytes:
    """A little-endian array's bytes, byte-shuffled."""
    size = values.dtype.itemsize
    data = np.frombuffer(np.ascontiguousarray(values).tobytes(), dtype=np.uint8)
    return data.reshape(-1, size).T.tobytes() if size > 1 else data.tobytes()


def _unshuffle(data: bytes, dtype: str) -> np.ndarray:
    size = np.dtype(dtype).itemsize
    raw = np.frombuffer(data, dtype=np.uint8)
    if len(raw) % size:
        raise ValueError("a feature table record is not whole")
    if size > 1:
        raw = np.ascontiguousarray(raw.reshape(size, -1).T)
    return raw.view(dtype).reshape(-1)


def _boxes_record(boxes: np.ndarray) -> tuple[str, bytes]:
    """boxes, (n, 4) float64, as the table stores them, and how."""
    scaled = np.round(boxes * DEGREE)
    if len(boxes) and not (np.isfinite(boxes).all() and np.abs(boxes).max() <= 180.0
                           and np.array_equal(scaled / DEGREE, boxes)):
        return "f8", _shuffle(boxes.astype("<f8"))
    whole = scaled.astype(np.int64).astype("<i4")
    columns = np.empty((4, len(boxes)), dtype="<u4")
    columns[0], columns[1] = whole[:, 0].view("<u4"), whole[:, 1].view("<u4")
    columns[2] = whole[:, 2].view("<u4") - whole[:, 0].view("<u4")   # wraps round, so east is always got back
    columns[3] = whole[:, 3].view("<u4") - whole[:, 1].view("<u4")
    return "i4e7", _shuffle(columns.reshape(-1))


def _read_boxes(how: str, data: bytes, n: int) -> np.ndarray:
    if how == "f8":
        return _unshuffle(data, "<f8").astype(np.float64).reshape(-1, 4)
    if how != "i4e7":
        raise ValueError(f"boxes stored as {how} are not read")
    columns = _unshuffle(data, "<u4").reshape(4, n)
    west, south = columns[0], columns[1]
    east, north = (west + columns[2]).view("<i4"), (south + columns[3]).view("<i4")
    out = np.empty((n, 4), dtype=np.float64)
    out[:, 0], out[:, 1], out[:, 2], out[:, 3] = west.view("<i4"), south.view("<i4"), east, north
    out /= DEGREE
    return out


def _widths_record(widths: np.ndarray) -> tuple[str, bytes]:
    finite = np.isfinite(widths)
    known = widths[finite]
    scaled = np.round(known * METRES)
    if not ((widths[~finite] == math.inf).all() and (known >= 0).all() and (scaled <= 2 ** 31 - 1).all()
            and np.array_equal(scaled / METRES, known)):
        return "f8", _shuffle(widths.astype("<f8"))
    out = np.full(len(widths), -1, dtype="<i4")
    out[finite] = scaled.astype(np.int64)
    return "i4e3", _shuffle(out)


def _read_widths(how: str, data: bytes) -> np.ndarray:
    if how == "f8":
        return _unshuffle(data, "<f8").astype(np.float64)
    if how != "i4e3":
        raise ValueError(f"widths stored as {how} are not read")
    whole = _unshuffle(data, "<i4")
    out = whole.astype(np.float64) / METRES
    out[whole < 0] = math.inf
    return out


class TableBuilder:
    """Collects the table as the writer writes the feature records, in feature number order, without holding them."""

    def __init__(self):
        self.count = 0
        self._boxes = array("d")
        self._widths = array("d")
        self._layer_code: dict[str, int] = {}
        self._layers = array("H")
        self._ids = bytearray()
        self._lengths = array("H")
        self._aliases: dict[str, str] = {}
        self._group = None
        self._last = b""

    def add(self, group: int, record: dict) -> None:
        """The next feature record, of feature group `group`. Within a group, identifiers come in order."""
        key = record["id"].encode("utf-8")
        if group == self._group and key <= self._last:
            raise TableError(f"feature {record['id']} is out of order in its group")
        if len(key) > MAX_ID_LENGTH or len(self._ids) + len(key) > MAX_ID_BYTES:
            raise TableError(f"feature {record['id']}: the identifiers are too long for the feature table")
        box = record["bbox"]
        if len(box) != 4:
            raise TableError(f"feature {record['id']} has a bbox without four numbers")
        self._group, self._last = group, key
        self._boxes.extend(float(v) for v in box)
        width = record.get("width_km")
        self._widths.append(math.inf if width is None else float(width))
        code = self._layer_code.setdefault(record.get("layer", ""), len(self._layer_code))
        self._layers.append(code)
        self._ids += key
        self._lengths.append(len(key))
        for alias in record.get("aliases") or ():
            self._aliases.setdefault(alias, record["id"])
        self.count += 1

    def records(self) -> list[tuple[str, bytes]]:
        """The table's records, (key, bytes), in the order of KEYS. The same calls give the same bytes (DMT-1)."""
        layers = list(self._layer_code)
        boxes_how, boxes = _boxes_record(np.frombuffer(self._boxes, dtype=np.float64).reshape(-1, 4))
        widths_how, widths = _widths_record(np.frombuffer(self._widths, dtype=np.float64))
        head = json.dumps({"count": self.count, "layers": layers, "aliases": self._aliases, "boxes": boxes_how,
                           "widths": widths_how}, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
        code_type = "<u1" if len(layers) <= 256 else "<u2"
        return [
            ("table", head),
            ("table/boxes", boxes),
            ("table/widths", widths),
            ("table/layers", _shuffle(np.frombuffer(self._layers, dtype=np.uint16).astype(code_type))),
            ("table/ids", bytes(self._ids)),
            ("table/id_lengths", _shuffle(np.frombuffer(self._lengths, dtype=np.uint16).astype("<u2"))),
        ]


class Identifiers:
    """Every feature's identifier, by feature number, kept as their UTF-8 bytes. Indexed like a NumPy array of text:
    by a number, or by an array of numbers or a mask, which gives an array of text (so .tolist() works)."""

    def __init__(self, blob: bytes, ends: np.ndarray):
        self.blob = blob
        self.ends = ends   # np.intp: where each identifier ends in blob

    def __len__(self) -> int:
        return len(self.ends)

    def start(self, i: int) -> int:
        return int(self.ends[i - 1]) if i else 0

    def key(self, i: int) -> bytes:
        return self.blob[self.start(i):int(self.ends[i])]

    def one(self, i: int) -> str:
        return self.key(i).decode("utf-8")

    def __getitem__(self, rows):
        if isinstance(rows, (int, np.integer)):
            i = int(rows)
            return self.one(i + len(self) if i < 0 else i)
        if isinstance(rows, slice):
            rows = np.arange(len(self), dtype=np.intp)[rows]
        rows = np.asarray(rows)
        if rows.dtype == bool:
            rows = np.flatnonzero(rows)
        out = np.empty(len(rows), dtype=object)
        for k, i in enumerate(rows.tolist()):
            out[k] = self.one(i)
        return out

    def tolist(self) -> list[str]:
        return [self.one(i) for i in range(len(self))]

    def find(self, identifier: str, lo: int, hi: int) -> int | None:
        """The feature number of an identifier among numbers lo to hi - 1, which are in order; None if not there."""
        key = identifier.encode("utf-8")
        while lo < hi:
            mid = (lo + hi) // 2
            got = self.key(mid)
            if got < key:
                lo = mid + 1
            elif got > key:
                hi = mid
            else:
                return mid
        return None


class FeatureTable:
    """A pack's compact feature table, read from its records (see the module's docstring)."""

    def __init__(self, records: dict[str, bytes]):
        head = json.loads(records["table"])
        n = int(head["count"])
        self.count = n
        self.layer_names: list[str] = [str(i) for i in head["layers"]]
        self.aliases: dict[str, str] = dict(head.get("aliases") or {})
        self.boxes = _read_boxes(head.get("boxes", "f8"), records["table/boxes"], n)
        self.widths = _read_widths(head.get("widths", "f8"), records["table/widths"])
        self.layer_codes = _unshuffle(records["table/layers"], "<u1" if len(self.layer_names) <= 256 else "<u2")
        lengths = _unshuffle(records["table/id_lengths"], "<u2")
        ends = np.cumsum(lengths, dtype=np.intp)
        self.ids = Identifiers(records["table/ids"], ends)
        if not (len(self.boxes) == len(self.widths) == len(self.layer_codes) == len(ends) == n):
            raise ValueError("the feature table's records do not agree on how many features there are")
        if n and (int(ends[-1]) != len(records["table/ids"]) or int(self.layer_codes.max()) >= len(self.layer_names)):
            raise ValueError("the feature table's identifiers or layers are not whole")
        self.numbers = np.arange(n, dtype=np.intp)

    def layer_of(self, number: int) -> str:
        return self.layer_names[int(self.layer_codes[number])]

    def layer_column(self) -> np.ndarray:
        """Each feature's layer id, as an array of text (shared strings, so one pointer each)."""
        return np.array(self.layer_names, dtype=object)[self.layer_codes]
