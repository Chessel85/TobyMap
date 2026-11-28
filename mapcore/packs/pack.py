"""Pack format 5 (and reading formats 2 to 4): the writer and the reader (AD-5, architecture 6.2, PCK-5, DAT-9, NFR-4).

The specification is docs/developer/pack-format.md. In short:

* A 40-byte header: b"TOBYPACK", the format number (4), flags, reserved,
  where the directory starts and its length, the directory's check number,
  and the header's own check number.
* The records, one after another, each compressed with zlib.
* The directory: zlib-compressed JSON naming every record, with where it
  starts, its length and its check number.

A check number is the CRC-32 of a record's stored bytes, so a damaged record
is found when it is read, and the rest of the pack can still be used (NFR-4).
The checksum of the whole file is SHA-256, kept beside it in a .sha256 file
and later in the catalogue (PCK-5).

Format 5 adds the compact feature table (table.py, P4-T3f, DP225): the store reads it as a few records in place
of every feature record, and feature records are then read a group at a time as needed, the last GROUPS_KEPT
groups and the last FEATURES_KEPT records asked for kept. A pack of format 4 or before has no table, and the store
makes it from the feature records as before, without keeping them.

Format 1 was the spike S2 pack. It is no longer read: a file with that
number is not a TobyMap pack.

The reader needs only the Python standard library and a byte source
(source.py), so it runs unchanged in the browser.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import re
import struct
import threading
import zlib
from collections import OrderedDict
from pathlib import Path

from mapcore import memory
from mapcore.describe import say
from mapcore.packs import coords, table, tiles
from mapcore.packs.source import FileSource

MAGIC = b"TOBYPACK"
FORMAT = 5          # written: format 5 adds the compact feature table (P4-T3f); format 4 added facts and relationships
                    # (P3-T2b, P3-T3e); format 3 added line and point tile entries (P2-T10a)
OLDEST_FORMAT = 2   # read: formats 2 to 4 are format 5 without what it added, so they are read as they are
WRITABLE = (4, 5)   # the formats PackWriter writes: 4 only for tests of how an older pack is read
_HEADER = struct.Struct("<8sHHIQQII")
HEADER_SIZE = _HEADER.size  # 40
GROUP_SIZE = 256  # feature records per group, on average
SEARCH_KEPT = 32  # search records kept after reading (P3-T8b)
GROUPS_KEPT = 64   # feature groups kept after reading, the least recently used let go first (P4-T3f): about 256
                   # records each, so some tens of MB at most, where keeping every group read took 10.4 GB for England
FEATURES_KEPT = 50_000   # feature records kept one by one, the least recently used let go first (P4-T3f): the
                         # features of the views and places lately asked about, whose groups are scattered

# What a feature record must hold in Phase 1 (architecture 6.4).
FEATURE_FIELDS = ("id", "source", "layer", "type", "names", "rank", "area_km2", "bbox", "width_km",
                  "colour", "point", "parents")
# What the builder gives the writer for the manifest. The writer adds the rest.
MANIFEST_GIVEN = ("name", "version", "coverage", "app_versions", "sources", "drawing_levels")
MANIFEST_ADDED = ("format", "built", "layers", "tile_levels", "coordinates", "features", "limits")

# The notice the ODbL asks a database to carry (ODbL section 4.3).
ODBL_NOTICE = (
    "This TobyMap pack is made available under the Open Database License: "
    "http://opendatacommons.org/licenses/odbl/1.0/. Any rights in individual contents of the database "
    "are licensed under the Database Contents License: http://opendatacommons.org/licenses/dbcl/1.0/\n"
)


# Errors --------------------------------------------------------------------

class PackError(Exception):
    """A pack that cannot be used, or a record that cannot be read.

    The message comes from the templates (packs.<template>), so the
    application can show or speak it as it is.
    """

    template = "packs.not_a_pack"

    def __init__(self, pack: str, **values):
        self.pack = pack
        self.values = values
        super().__init__(say(self.template, name=pack, **values))

    @property
    def message(self) -> str:
        return str(self)


class NotAPack(PackError):
    template = "packs.not_a_pack"


class NewerFormat(PackError):
    template = "packs.newer_format"


class AppTooOld(PackError):
    template = "packs.app_too_old"


class AppTooNew(PackError):
    template = "packs.app_too_new"


class DamagedPack(PackError):
    """The header, directory or manifest is damaged, so nothing can be read."""
    template = "packs.damaged_pack"


class DamagedRecord(PackError):
    """One record is damaged. The rest of the pack can still be read."""
    template = "packs.damaged_record"

    def __init__(self, pack: str, record: str):
        self.record = record
        super().__init__(pack, record=record)


class ChecksumWrong(PackError):
    """The pack does not match the checksum beside it, as after a broken download."""
    template = "packs.checksum_wrong"


def is_damage(error: PackError) -> bool:
    """A pack that is broken, which is set aside, as against one that only needs another version of TobyMap."""
    return isinstance(error, (DamagedPack, ChecksumWrong, NotAPack))


def open_packs(sources, **options) -> tuple[list, list[PackError]]:
    """Open each pack, keeping those that pass their checks and returning the failures, so one bad pack
    never stops the others (NFR-4). Sources may be Packs already open."""
    opened, failed = [], []
    for source in sources:
        if isinstance(source, Pack):
            opened.append(source)
            continue
        try:
            opened.append(Pack(source, **options))
        except PackError as error:
            failed.append(error)
    return opened, failed


class PackWriteError(ValueError):
    """The builder asked for something the format does not allow. For the pipeline, not the user."""


# Small helpers -----------------------------------------------------------------

_DECODER = json.JSONDecoder()   # as json.loads reads a record


def check_number(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def version_tuple(text: str) -> tuple[int, ...] | None:
    """ "0.0.7" -> (0, 0, 7). None for anything else, such as "unknown"."""
    if not isinstance(text, str) or not re.fullmatch(r"\d+(\.\d+)*", text):
        return None
    return tuple(int(p) for p in text.split("."))


def _compare(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    n = max(len(a), len(b))
    a, b = a + (0,) * (n - len(a)), b + (0,) * (n - len(b))
    return (a > b) - (a < b)


def feature_group(identifier: str, groups: int) -> int:
    """Which group of feature records an identifier is in."""
    return check_number(identifier.encode("utf-8")) % groups


def checksum_path(path) -> Path:
    path = Path(path)
    return path.with_name(path.name + ".sha256")


def file_checksum(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_checksum(path) -> str:
    """Write <pack>.sha256 beside the pack, in the usual "hash *name" form."""
    value = file_checksum(path)
    checksum_path(path).write_text(f"{value} *{Path(path).name}\n", encoding="ascii", newline="\n")
    return value


def verify_checksum(path) -> bool:
    """True when the pack matches the checksum beside it (PCK-5)."""
    text = checksum_path(path).read_text(encoding="ascii").split()
    return bool(text) and text[0].lower() == file_checksum(path)


def require_checksum(path) -> None:
    """Raise ChecksumWrong unless the pack matches the checksum beside it (PCK-5)."""
    try:
        ok = verify_checksum(path)
    except OSError:
        ok = False
    if not ok:
        raise ChecksumWrong(Path(path).name)


# Writing -------------------------------------------------------------------

def tile_data(entries, exact: bool, level: int, count: int) -> bytes:
    """A pack tile's or drawing tile's record, checked: entries are (feature number, kind, bytes), with feature
    numbers below count. exact for a pack tile of exact shapes, whose limits on points are checked."""
    entries = [tiles.TileEntry(*e) for e in entries]
    if not entries:
        raise PackWriteError("an empty tile is not stored")
    total = 0
    for e in entries:
        if not 0 <= e.feature < count:
            raise PackWriteError(f"feature number {e.feature} is not in the pack")
        if e.kind not in tiles.KINDS:
            raise PackWriteError(f"tile entry kind {e.kind} is not allowed")
        if e.kind == tiles.COVERED:
            if e.data:
                raise PackWriteError("a covered note has no bytes")
            continue
        points = coords.point_count(e.data) if e.kind == tiles.COMPACT else coords.line_point_count(e.data)
        total += points
        if exact and points > tiles.ENTRY_POINTS and level < tiles.MAX_TILE_LEVEL:
            raise PackWriteError(f"a tile entry at tile level {level} has {points} points; "
                                 f"the most is {tiles.ENTRY_POINTS}, so cut it at the next level")
    if exact and total > tiles.TILE_POINTS and level < tiles.MAX_TILE_LEVEL:
        raise PackWriteError(f"a pack tile at tile level {level} has {total} points; "
                             f"the most is {tiles.TILE_POINTS}, so split it")
    return tiles.encode_entries(entries)


def stored_tile(entries, level: int, count: int) -> tuple[bytes, int]:
    """A pack tile's record compressed as the pack stores it, and its check number, for
    PackWriter.add_stored_tile. Made in a worker, so the main process neither holds the entries nor compresses
    them (P4-T1m)."""
    stored = zlib.compress(tile_data(entries, True, level, count), 9)
    return stored, check_number(stored)


class PackWriter:
    """Writes a pack in format 5 (or, given format=4, in format 4 with no feature table, for tests).

    The order of calls is: add_features once, then any number of add_tile and
    add_drawing_tile, then finish. Given the same calls in the same order,
    the bytes written are always the same (DMT-1): nothing comes from the
    clock, and the build date is the latest of the sources' dates.

    The target is a path, or a binary file that can seek. For a path, the
    checksum file is written beside it when the pack is finished.
    """

    def __init__(self, target, format: int = FORMAT):
        if format not in WRITABLE:
            raise PackWriteError(f"format {format} is not written")
        self.format = format
        self.table = table.TableBuilder() if format >= 5 else None
        if isinstance(target, (str, Path)):
            self.path = Path(target)
            self.out = open(self.path, "wb")
        else:
            self.path = None
            self.out = target
        self.start = self.out.tell()
        self.out.write(bytes(HEADER_SIZE))
        self.directory: dict[str, list[int]] = {}
        self.numbers: dict[str, int] | None = None   # or any mapping that answers `in` and [] (P4-T1m)
        self.count = 0   # how many features
        self.layers_used: set[str] = set()
        self.group_starts: list[int] = []
        self.tile_levels: set[int] = set()
        self.drawing_used: dict[int, set[tuple[int, int]]] = {}
        self.search: dict | None = None
        self.finished = False

    def _put(self, key: str, data: bytes) -> None:
        stored = zlib.compress(data, 9)
        self._put_stored(key, stored, check_number(stored))

    def _put_stored(self, key: str, stored: bytes, check: int) -> None:
        """A record already compressed, with its check number."""
        if self.finished:
            raise PackWriteError("the pack is already finished")
        if key in self.directory:
            raise PackWriteError(f"record {key} is written twice")
        self.directory[key] = [self.out.tell() - self.start, len(stored), check]
        self.out.write(stored)

    def add_features(self, records: list[dict]) -> dict[str, int]:
        """Write the feature records, in groups by identifier. Returns each
        identifier's feature number, which tile entries refer to."""
        if self.numbers is not None:
            raise PackWriteError("add_features is called once")
        seen = set()
        for r in records:
            missing = [f for f in FEATURE_FIELDS if f not in r]
            if missing:
                raise PackWriteError(f"feature {r.get('id', '?')} has no {', '.join(missing)}")
            if r["id"] in seen:
                raise PackWriteError(f"feature {r['id']} is given twice")
            seen.add(r["id"])
        groups = max(1, math.ceil(len(records) / GROUP_SIZE))
        ordered = sorted(records, key=lambda r: (feature_group(r["id"], groups), r["id"]))
        starts, by_group = [], []
        n = 0
        for g in range(groups):
            starts.append(n)
            members = []
            while n < len(ordered) and feature_group(ordered[n]["id"], groups) == g:
                members.append(ordered[n])
                n += 1
            if members:
                by_group.append((g, members))
        self.add_feature_groups(starts, by_group, {r["id"]: n for n, r in enumerate(ordered)})
        return dict(self.numbers)

    def add_feature_groups(self, group_starts: list[int], members, numbers) -> None:
        """Write the feature records a group at a time (P4-T1m), as add_features does: members gives (group, its
        records in their order) for each group that has any, in order, and numbers each identifier's feature
        number, a mapping that answers `in`, [] and len. The caller has put them in order and numbered them as
        add_features would; only one group's records need be held at once."""
        if self.numbers is not None:
            raise PackWriteError("add_features is called once")
        self.numbers = numbers
        self.group_starts = list(group_starts)
        written = 0
        for g, records in members:
            for r in records:
                missing = [f for f in FEATURE_FIELDS if f not in r]
                if missing:
                    raise PackWriteError(f"feature {r.get('id', '?')} has no {', '.join(missing)}")
                self.layers_used.add(r["layer"])
                if self.table is not None:   # the compact feature table, row by row in feature number order (P4-T3f)
                    if numbers[r["id"]] != self.table.count:
                        raise PackWriteError(f"feature {r['id']} is not written in its feature number's place")
                    try:
                        self.table.add(g, r)
                    except table.TableError as exc:
                        raise PackWriteError(str(exc)) from None
            written += len(records)
            if records:
                self._put(f"features/{g}", _json(records))
        if written != len(numbers):
            raise PackWriteError(f"{written} feature records written for {len(numbers)} features")
        self.count = written

    def add_relationship_groups(self, per_group) -> None:
        """add_relationships a group at a time (P4-T1m): per_group gives (group, {identifier: relationships}) for
        each group whose features have any, in order. The caller makes sure each identifier is in the pack."""
        if self.numbers is None:
            raise PackWriteError("add_features comes before the relationships")
        for g, by_id in per_group:
            if by_id:
                self._put(f"relations/{g}", _json(by_id))

    def add_relationships(self, by_id: dict[str, dict]) -> None:
        """Write each feature's relationships (P3-T3e, architecture 6.5), in the feature records' groups: record
        relations/G holds, as a JSON object by identifier, those of group G's features that have any."""
        if self.numbers is None:
            raise PackWriteError("add_features comes before the relationships")
        unknown = sorted(f for f in by_id if f not in self.numbers)
        if unknown:
            raise PackWriteError(f"relationships of features not in the pack: {', '.join(unknown[:5])}")
        groups = max(1, len(self.group_starts))
        per: dict[int, dict] = {}
        for fid, rel in by_id.items():
            if rel:
                per.setdefault(feature_group(fid, groups), {})[fid] = rel
        for g in sorted(per):
            self._put(f"relations/{g}", _json(per[g]))

    def add_contents(self, tree: dict[str, list[str]], names: dict[str, dict],
                     holds: dict[str, dict[str, tuple[list[int], list[int]]]]) -> None:
        """Write what is inside each area (P3-T20c, DP194): record tree, the world tree as {"children": {parent:
        [ids]}, "names": {id: what says its name}}; and records holds/G, in the feature records' groups, each a JSON
        object by an area's identifier of {layer: [[feature numbers], [those only partly inside]]}, each list as
        steps (mapcore.store.contents)."""
        from mapcore.store import contents

        if self.numbers is None:
            raise PackWriteError("add_features comes before the contents")
        if "tree" in self.directory:
            raise PackWriteError("add_contents is called once")
        named = {i for ids in tree.values() for i in ids if not i.startswith(contents.DISPUTE_PREFIX)}
        unknown = sorted(f for f in (named | set(holds)) if f not in self.numbers)
        if unknown:
            raise PackWriteError(f"the contents name features not in the pack: {', '.join(unknown[:5])}")
        self._put("tree", _json({"children": {k: list(v) for k, v in tree.items()}, "names": names}))
        groups = max(1, len(self.group_starts))
        per: dict[int, dict] = {}
        for fid, by_layer in holds.items():
            for layer, (numbers, partly) in by_layer.items():
                if any(not 0 <= n < self.count for n in numbers) or not set(partly) <= set(numbers):
                    raise PackWriteError(f"the contents of {fid} give a feature number not in the pack")
            per.setdefault(feature_group(fid, groups), {})[fid] = {
                layer: [contents.to_steps(sorted(numbers)), contents.to_steps(sorted(partly))]
                for layer, (numbers, partly) in by_layer.items() if numbers}
        for g in sorted(per):
            self._put(f"holds/{g}", _json(per[g]))

    def add_search(self, buckets: int, records: dict[int, list[list]], rows: int) -> None:
        """Write the search index (P3-T8a, architecture 7.9): record search/B holds the rows filed under the
        prefixes that mapcore.search.bucket puts in B, as a JSON list. The manifest gets search: {"buckets",
        "rows"}, so the reader knows how many records there are."""
        if self.numbers is None:
            raise PackWriteError("add_features comes before the search index")
        if self.search is not None:
            raise PackWriteError("add_search is called once")
        for b in sorted(records):
            if not 0 <= b < buckets:
                raise PackWriteError(f"search record {b} is not one of the {buckets}")
            unknown = [r[2] for r in records[b] if r[2] not in self.numbers]
            if unknown:
                raise PackWriteError(f"the search index names features not in the pack: {', '.join(unknown[:5])}")
            self._put(f"search/{b}", _json(records[b]))
        self.search = {"buckets": int(buckets), "rows": int(rows)}

    def _entries(self, entries, exact: bool, level: int) -> bytes:
        if self.numbers is None:
            raise PackWriteError("add_features comes before the tiles")
        return tile_data(entries, exact, level, self.count)

    def add_stored_tile(self, level: int, x: int, y: int, stored: bytes, check: int) -> None:
        """add_tile with the record already made and compressed by stored_tile, such as in a worker (P4-T1m)."""
        if self.numbers is None:
            raise PackWriteError("add_features comes before the tiles")
        if not tiles.in_grid(level, x, y):
            raise PackWriteError(f"pack tile {level}/{x}/{y} is not in the grid")
        self._put_stored(tiles.tile_key(level, x, y), stored, check)
        self.tile_levels.add(level)

    def add_tile(self, level: int, x: int, y: int, entries) -> None:
        """A pack tile of exact shapes: entries are (feature number, kind, bytes)."""
        if not tiles.in_grid(level, x, y):
            raise PackWriteError(f"pack tile {level}/{x}/{y} is not in the grid")
        data = self._entries(entries, True, level)
        self._put(tiles.tile_key(level, x, y), data)
        self.tile_levels.add(level)

    def add_drawing_tile(self, drawing_level: int, x: int, y: int, entries) -> None:
        """A drawing tile of simplified shapes for one drawing level."""
        data = self._entries(entries, False, 0)
        self._put(tiles.drawing_key(drawing_level, x, y), data)
        self.drawing_used.setdefault(drawing_level, set()).add((x, y))

    def _manifest(self, given: dict, layers: list[dict]) -> dict:
        missing = [k for k in MANIFEST_GIVEN if k not in given]
        if missing:
            raise PackWriteError(f"the manifest has no {', '.join(missing)}")
        extra = [k for k in given if k in MANIFEST_ADDED]
        if extra:
            raise PackWriteError(f"the writer sets {', '.join(extra)} itself")
        apps = given["app_versions"]
        if version_tuple(apps.get("from")) is None or ("before" in apps and version_tuple(apps["before"]) is None):
            raise PackWriteError("app_versions needs 'from', and optionally 'before', as numbers like 0.1.0")
        sources = given["sources"]
        if not sources:
            raise PackWriteError("a pack has at least one source")
        for s in sources:
            for field in ("name", "licence", "date"):
                if not s.get(field):
                    raise PackWriteError(f"source {s.get('name', '?')} has no {field}")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["date"]):
                raise PackWriteError(f"source {s['name']} has date {s['date']}; use YYYY-MM-DD")
        declared = {}
        for d in given["drawing_levels"]:
            if not isinstance(d.get("id"), int) or not isinstance(d.get("tile_level"), int):
                raise PackWriteError("each drawing level has an id and a tile_level")
            declared[d["id"]] = d["tile_level"]
        for d, used in sorted(self.drawing_used.items()):
            if d not in declared:
                raise PackWriteError(f"drawing level {d} has drawing tiles but is not in the manifest")
            for x, y in used:
                if not tiles.in_grid(declared[d], x, y):
                    raise PackWriteError(f"drawing tile {d}/{x}/{y} is not in tile level {declared[d]}")
        if "search" in given:
            raise PackWriteError("the writer sets search itself, from add_search")
        out = {
            **given,
            "format": self.format,
            "built": max(s["date"] for s in sources),
            "layers": [layer["id"] for layer in layers],
            "tile_levels": sorted(self.tile_levels),
            "coordinates": {"encoding": "compact", "scale": coords.SCALE},
            "features": {"count": self.count, "groups": len(self.group_starts),
                         "group_starts": self.group_starts},
            "limits": {"entry_points": tiles.ENTRY_POINTS, "tile_points": tiles.TILE_POINTS},
        }
        if self.search is not None:
            out["search"] = self.search
        return out

    def finish(self, manifest: dict, attribution: str, layers: list[dict], licence: str = ODBL_NOTICE) -> str | None:
        """Write the manifest, attribution, licence, layers and directory.
        Returns the checksum when writing to a path."""
        if self.numbers is None:
            self.add_features([])
        if not attribution.strip():
            raise PackWriteError("a pack has attribution text (DAT-9)")
        ids = [layer.get("id") for layer in layers]
        if any(not i or not layers[n].get("name") for n, i in enumerate(ids)) or len(set(ids)) != len(ids):
            raise PackWriteError("each layer has its own id and a name")
        unknown = sorted(self.layers_used - set(ids))
        if unknown:
            raise PackWriteError(f"features use layers not defined: {', '.join(unknown)}")
        manifest = self._manifest(manifest, layers)
        if self.table is not None:
            for key, data in self.table.records():
                self._put(key, data)
        self._put("manifest", _json(manifest))
        self._put("attribution", attribution.encode("utf-8"))
        self._put("licence", licence.encode("utf-8"))
        self._put("layers", _json(layers))
        directory = zlib.compress(_json({"records": self.directory}), 9)
        offset = self.out.tell() - self.start
        self.out.write(directory)
        end = self.out.tell()
        head = _HEADER.pack(MAGIC, self.format, 0, 0, offset, len(directory), check_number(directory), 0)
        head = head[:-4] + struct.pack("<I", check_number(head[:-4]))
        self.out.seek(self.start)
        self.out.write(head)
        self.out.seek(end)
        self.finished = True
        if self.path is not None:
            self.out.close()
            return write_checksum(self.path)
        return None


# Reading -------------------------------------------------------------------

def read_format(source) -> int | None:
    """The format number in a pack's header, or None if it is not a pack."""
    if source.size < 16:
        return None
    head = bytes(source.read(0, 16))
    if head[:8] != MAGIC:
        return None
    return struct.unpack_from("<H", head, 8)[0]


class Pack:
    """Reads records on demand from a pack in format 4, 3 or 2.

    `source` is a path or a byte source (source.py). The pack is refused,
    with a PackError whose message comes from the templates, when it is not a
    pack, is in a newer format, is damaged in its header,
    directory or manifest, or was made for other application versions
    (PCK-5). `app_version` is the application's version; None means this
    one. A version that is not a number, as in a development copy that
    cannot find version.txt, is not checked. mapdata passes check_app=False.

    Every read goes through the byte source, and `reads` counts them.
    """

    def __init__(self, source, *, app_version: str | None = None, check_app: bool = True):
        if isinstance(source, (str, Path)):
            source = FileSource(source)
        self.source = source
        self.name = getattr(source, "name", None) or "This pack"
        self.reads = 0
        # The feature groups read, the least recently used first, at most GROUPS_KEPT (P4-T3f); and for a pack with
        # no feature table, each group's identifiers to their place in it, let go with the group.
        self._groups: OrderedDict[int, list[dict]] = OrderedDict()
        self._group_ids: dict[int, dict[str, int]] = {}
        self._records: OrderedDict[int, dict] = OrderedDict()   # by feature number, at most FEATURES_KEPT
        self._groups_lock = threading.Lock()
        self._relations: dict[int, dict] = {}
        self._table: table.FeatureTable | None = None
        self._table_tried = False
        self._table_lock = threading.Lock()
        self.table_problem: DamagedRecord | None = None   # set when the feature table is damaged
        self._search: OrderedDict[int, list] = OrderedDict()
        try:
            self._open(app_version, check_app)
        except Exception:
            self.close()
            raise

    def _open(self, app_version, check_app) -> None:
        if self.source.size < HEADER_SIZE:
            raise NotAPack(self.name)
        head = bytes(self.source.read(0, HEADER_SIZE))
        magic, fmt, _flags, _reserved, offset, length, dir_check, head_check = _HEADER.unpack(head)
        if magic != MAGIC:
            raise NotAPack(self.name)
        if fmt < OLDEST_FORMAT:
            raise NotAPack(self.name)
        if fmt > FORMAT:
            raise NewerFormat(self.name)
        self.format = fmt
        if check_number(head[:-4]) != head_check:
            raise DamagedPack(self.name, record="header")
        stored = bytes(self.source.read(offset, length)) if offset + length <= self.source.size else b""
        if len(stored) != length or check_number(stored) != dir_check:
            raise DamagedPack(self.name, record="directory")
        try:
            self.directory = {k: tuple(v) for k, v in json.loads(zlib.decompress(stored))["records"].items()}
        except (ValueError, KeyError, zlib.error):
            raise DamagedPack(self.name, record="directory") from None
        try:
            self.manifest = self.get_json("manifest")
            self.layers = self.get_json("layers")
        except DamagedRecord as exc:
            raise DamagedPack(self.name, record=exc.record) from None
        if self.manifest is None or self.layers is None:
            raise DamagedPack(self.name, record="manifest")
        try:
            self.tile_levels = self.manifest["tile_levels"]
            self.drawing_levels = {d["id"]: d for d in self.manifest["drawing_levels"]}
            self.group_starts = self.manifest["features"]["group_starts"]
            self.feature_count = self.manifest["features"]["count"]
            if version_tuple(self.manifest["app_versions"]["from"]) is None:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            # Its check number was right, so it was written wrongly, not damaged later.
            raise DamagedPack(self.name, record="manifest") from None
        if check_app:
            self._check_app(app_version)

    def _check_app(self, app_version) -> None:
        if app_version is None:
            import mapcore
            app_version = mapcore.version()
        have = version_tuple(app_version)
        if have is None:
            return
        apps = self.manifest["app_versions"]
        if _compare(have, version_tuple(apps["from"])) < 0:
            raise AppTooOld(self.name, need=apps["from"], have=app_version)
        if apps.get("before") and _compare(have, version_tuple(apps["before"])) >= 0:
            raise AppTooNew(self.name, before=apps["before"], have=app_version)

    def close(self) -> None:
        close = getattr(self.source, "close", None)
        if close is not None:
            close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # Records -----------------------------------------------------------------

    def keys(self) -> list[str]:
        return sorted(self.directory)

    def get(self, key: str) -> bytes | None:
        """A record's bytes, or None if the pack has no such record.
        Raises DamagedRecord if its check number does not match (NFR-4)."""
        entry = self.directory.get(key)
        if entry is None:
            return None
        offset, length, number = entry
        if offset < HEADER_SIZE or offset + length > self.source.size:
            raise DamagedRecord(self.name, key)
        self.reads += 1
        stored = bytes(self.source.read(offset, length))
        if len(stored) != length or check_number(stored) != number:
            raise DamagedRecord(self.name, key)
        try:
            return zlib.decompress(stored)
        except zlib.error:
            raise DamagedRecord(self.name, key) from None

    def get_json(self, key: str):
        data = self.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except ValueError:
            raise DamagedRecord(self.name, key) from None

    def check(self) -> list[str]:
        """Read every record. Returns the names of any that are damaged."""
        damaged = []
        for key in self.keys():
            try:
                self.get(key)
            except DamagedRecord:
                damaged.append(key)
        return damaged

    @property
    def attribution(self) -> str:
        return self.get("attribution").decode("utf-8")

    @property
    def licence(self) -> str:
        return self.get("licence").decode("utf-8")

    # Feature records -----------------------------------------------------------

    @property
    def has_table(self) -> bool:
        """Whether the pack stores the compact feature table (format 5, P4-T3f)."""
        return self.format >= 5 and all(k in self.directory for k in table.KEYS)

    def table(self) -> table.FeatureTable | None:
        """The compact feature table, read once and kept; None for a pack with none, or whose table is damaged (then
        table_problem says which record), so the caller makes it from the feature records instead (NFR-4)."""
        if self._table_tried:
            return self._table
        with self._table_lock:
            if not self._table_tried:
                if self.has_table:
                    try:
                        got = {}
                        for key in table.KEYS:
                            got[key] = self.get(key)
                        try:
                            self._table = table.FeatureTable(got)
                        except (ValueError, KeyError, TypeError):
                            raise DamagedRecord(self.name, "table") from None
                        if self._table.count != self.feature_count:
                            self._table = None
                            raise DamagedRecord(self.name, "table")
                    except DamagedRecord as exc:
                        self.table_problem = exc
                self._table_tried = True
        return self._table

    def _group(self, g: int) -> list[dict]:
        """Group g's feature records, kept among the last GROUPS_KEPT groups read (P4-T3f)."""
        with self._groups_lock:
            got = self._groups.get(g)
            if got is not None:
                self._groups.move_to_end(g)
                return got
        got = self.get_json(f"features/{g}") or []
        with self._groups_lock:
            self._groups[g] = got
            self._groups.move_to_end(g)
            while len(self._groups) > GROUPS_KEPT:
                old, _records = self._groups.popitem(last=False)
                self._group_ids.pop(old, None)
        memory.settle()   # kept a while, so out of full garbage collections (P3-T24a)
        return got

    def read_group(self, g: int) -> list[dict]:
        """Group g's feature records, from those kept or read afresh, without keeping them, for a reading of every
        group such as scan's or the store's feature table for a pack with none."""
        got = self._groups.get(g)
        return got if got is not None else (self.get_json(f"features/{g}") or [])

    @property
    def groups_kept(self) -> int:
        """How many feature groups are kept now (at most GROUPS_KEPT)."""
        return len(self._groups)

    @property
    def records_kept(self) -> int:
        """How many feature records are kept one by one now (at most FEATURES_KEPT)."""
        return len(self._records)

    def feature(self, number: int) -> dict:
        """The feature record with this feature number, as tile entries give it."""
        if not 0 <= number < self.feature_count:
            raise IndexError(number)
        with self._groups_lock:
            got = self._records.get(number)
            if got is not None:
                self._records.move_to_end(number)
                return got
        g = bisect.bisect_right(self.group_starts, number) - 1
        got = None
        if g not in self._groups and self.table() is not None:
            got = self._one_record(g, number)
        if got is None:
            got = self._group(g)[number - self.group_starts[g]]
        with self._groups_lock:
            self._records[number] = got
            while len(self._records) > FEATURES_KEPT:
                self._records.popitem(last=False)
        return got

    def _one_record(self, g: int, number: int) -> dict | None:
        """One feature record of group g, found by its identifier from the feature table and read alone, without
        reading the rest of its group (P4-T3g); None if it cannot be found so, and the caller reads the group.
        Feature groups are by identifier, not by place, so the features of a view are in many groups: reading
        each whole, some 256 records, for one record took about 2 ms in the browser, a minute for England's
        first drawing. The record is the same as the group's own: the same JSON decoder reads it from its start."""
        data = self.get(f"features/{g}")
        if data is None:
            return None
        identifier, layer = self._table.ids.one(number), self._table.layer_of(number)
        text = data.decode("utf-8")
        at = text.find('"id":' + json.dumps(identifier, ensure_ascii=False))
        if at < 0:
            return None
        start = text.rfind("{", 0, at)
        for _ in range(64):   # back over any object inside the record before its identifier, such as "exclave"
            if start <= 0:
                return None
            try:
                found, end = _DECODER.raw_decode(text, start)
            except ValueError:
                found, end = None, 0
            if isinstance(found, dict) and end > at and found.get("id") == identifier \
                    and found.get("layer", "") == layer and text[start - 1] in "[," and end < len(text) \
                    and text[end] in ",]":
                return found
            start = text.rfind("{", 0, start)
        return None

    def scan(self, layers):
        """The feature records of these layers, group by group (P3-T9). A group is read again each time unless
        already held, and none is kept, so a scan of one layer does not fill the memory with the others."""
        wanted = set(layers)
        for g in range(len(self.group_starts)):
            for record in self.read_group(g):
                if record["layer"] in wanted:
                    yield record

    def feature_number(self, identifier: str) -> int | None:
        g = feature_group(identifier, len(self.group_starts))
        found = self.table()
        if found is not None:   # a binary search of the group's part of the table, with no record read (P4-T3f)
            end = self.group_starts[g + 1] if g + 1 < len(self.group_starts) else self.feature_count
            return found.ids.find(identifier, self.group_starts[g], end)
        ids = self._group_ids.get(g)
        if ids is None:   # made once for each group kept, so a look-up is not a search through the group (P3-T20b)
            ids = {}
            for i, record in enumerate(self._group(g)):
                ids.setdefault(record["id"], i)   # the first, as before, should an identifier be there twice
            with self._groups_lock:
                if g in self._groups:
                    self._group_ids[g] = ids
        i = ids.get(identifier)
        return None if i is None else self.group_starts[g] + i

    @property
    def has_contents(self) -> bool:
        """Whether the pack stores the world tree and what is inside each area (P3-T20c, DP194)."""
        return "tree" in self.directory

    def tree(self) -> dict | None:
        """The stored world tree, {"children": {parent: [ids]}, "names": {id: {...}}}, or None for a pack with none.
        Not kept here: the store keeps what it needs."""
        return self.get_json("tree") if self.has_contents else None

    def holds(self, identifier: str) -> dict[str, tuple[list[int], set[int]]] | None:
        """The feature numbers of every feature inside an area of the tree's layers, by layer, with those only
        partly inside (P3-T20c, P3-T25b); empty for an area with nothing inside, or none of those layers; None for
        a pack that does not store them."""
        from mapcore.store import contents

        if not self.has_contents:
            return None
        g = feature_group(identifier, len(self.group_starts))
        got = (self.get_json(f"holds/{g}") or {}).get(identifier, {})
        return {layer: (contents.from_steps(every), set(contents.from_steps(partly)))
                for layer, (every, partly) in got.items()}

    def relationships(self, identifier: str) -> dict:
        """A feature's relationships, from format 4 (P3-T3e): what it is inside, beside, overlapping and crossing,
        by the identifiers of the other features. Empty for a feature with none, or a pack written before."""
        g = feature_group(identifier, len(self.group_starts))
        if g not in self._relations:
            self._relations[g] = self.get_json(f"relations/{g}") or {}
        return self._relations[g].get(identifier, {})

    def relationships_passing(self, identifiers) -> dict[str, dict]:
        """Many features' relationships, as relationships() gives them, reading each record once and keeping only
        those already kept: the islands round an ocean are in nearly every record, and keeping them all took
        nearly 3 GB (P3-T32g)."""
        by_group: dict[int, list[str]] = {}
        for identifier in identifiers:
            by_group.setdefault(feature_group(identifier, len(self.group_starts)), []).append(identifier)
        out = {}
        for g, ids in by_group.items():
            got = self._relations.get(g)
            if got is None:
                got = self.get_json(f"relations/{g}") or {}
            for identifier in ids:
                out[identifier] = got.get(identifier, {})
        return out

    @property
    def search_buckets(self) -> int:
        """How many search records the pack has (P3-T8a); 0 for a pack written before the search index."""
        return int((self.manifest.get("search") or {}).get("buckets") or 0)

    def search_rows(self, b: int) -> list[list]:
        """The rows of search record b (mapcore.search.ROW). The last SEARCH_KEPT records read are kept, so
        typing on reads each record once, and the memory they take stays small."""
        if b in self._search:
            self._search.move_to_end(b)
            return self._search[b]
        from mapcore import search

        rows = self.get_json(f"search/{b}") or []
        for row in rows:   # what the pack leaves out to save space, put back (pack-format.md, search/B)
            name = row[search.NAME]
            if not row[search.KEY]:
                row[search.KEY] = search.normalise(name)
            row[search.DESCRIPTION] = f"{name}, {row[search.DESCRIPTION]}" if row[search.DESCRIPTION] else name
        self._search[b] = rows
        while len(self._search) > SEARCH_KEPT:
            self._search.popitem(last=False)
        return rows

    def feature_by_id(self, identifier: str) -> dict | None:
        number = self.feature_number(identifier)
        return None if number is None else self.feature(number)

    # Pack tiles and drawing tiles ----------------------------------------------

    def _entries(self, key: str) -> list[tiles.TileEntry]:
        data = self.get(key)
        if data is None:
            return []
        try:
            return tiles.decode_entries(data)
        except (ValueError, struct.error):
            raise DamagedRecord(self.name, key) from None

    def tile(self, level: int, x: int, y: int) -> list[tiles.TileEntry]:
        """The tile entries of a pack tile of exact shapes; empty if none is stored."""
        return self._entries(tiles.tile_key(level, x, y))

    def drawing_tile(self, drawing_level: int, x: int, y: int) -> list[tiles.TileEntry]:
        return self._entries(tiles.drawing_key(drawing_level, x, y))
