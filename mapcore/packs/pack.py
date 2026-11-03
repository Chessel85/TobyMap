"""Pack format 2: the writer and the reader (AD-5, architecture 6.2, PCK-5, DAT-9, NFR-4).

The specification is docs/developer/pack-format.md. In short:

* A 40-byte header: b"TOBYPACK", the format number (2), flags, reserved,
  where the directory starts and its length, the directory's check number,
  and the header's own check number.
* The records, one after another, each compressed with zlib.
* The directory: zlib-compressed JSON naming every record, with where it
  starts, its length and its check number.

A check number is the CRC-32 of a record's stored bytes, so a damaged record
is found when it is read, and the rest of the pack can still be used (NFR-4).
The checksum of the whole file is SHA-256, kept beside it in a .sha256 file
and later in the catalogue (PCK-5).

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
import zlib
from pathlib import Path

from mapcore.describe import say
from mapcore.packs import coords, tiles
from mapcore.packs.source import FileSource

MAGIC = b"TOBYPACK"
FORMAT = 2
_HEADER = struct.Struct("<8sHHIQQII")
HEADER_SIZE = _HEADER.size  # 40
GROUP_SIZE = 256  # feature records per group, on average

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


class PackWriteError(ValueError):
    """The builder asked for something the format does not allow. For the pipeline, not the user."""


# Small helpers -----------------------------------------------------------------

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

class PackWriter:
    """Writes a pack in format 2.

    The order of calls is: add_features once, then any number of add_tile and
    add_drawing_tile, then finish. Given the same calls in the same order,
    the bytes written are always the same (DMT-1): nothing comes from the
    clock, and the build date is the latest of the sources' dates.

    The target is a path, or a binary file that can seek. For a path, the
    checksum file is written beside it when the pack is finished.
    """

    def __init__(self, target):
        if isinstance(target, (str, Path)):
            self.path = Path(target)
            self.out = open(self.path, "wb")
        else:
            self.path = None
            self.out = target
        self.start = self.out.tell()
        self.out.write(bytes(HEADER_SIZE))
        self.directory: dict[str, list[int]] = {}
        self.numbers: dict[str, int] | None = None
        self.features: list[dict] = []
        self.group_starts: list[int] = []
        self.tile_levels: set[int] = set()
        self.drawing_used: dict[int, set[tuple[int, int]]] = {}
        self.finished = False

    def _put(self, key: str, data: bytes) -> None:
        if self.finished:
            raise PackWriteError("the pack is already finished")
        if key in self.directory:
            raise PackWriteError(f"record {key} is written twice")
        stored = zlib.compress(data, 9)
        self.directory[key] = [self.out.tell() - self.start, len(stored), check_number(stored)]
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
        self.features = ordered
        self.numbers = {r["id"]: n for n, r in enumerate(ordered)}
        self.group_starts = []
        n = 0
        for g in range(groups):
            self.group_starts.append(n)
            members = []
            while n < len(ordered) and feature_group(ordered[n]["id"], groups) == g:
                members.append(ordered[n])
                n += 1
            if members:
                self._put(f"features/{g}", _json(members))
        return dict(self.numbers)

    def _entries(self, entries, exact: bool, level: int) -> bytes:
        if self.numbers is None:
            raise PackWriteError("add_features comes before the tiles")
        entries = [tiles.TileEntry(*e) for e in entries]
        if not entries:
            raise PackWriteError("an empty tile is not stored")
        total = 0
        for e in entries:
            if not 0 <= e.feature < len(self.features):
                raise PackWriteError(f"feature number {e.feature} is not in the pack")
            if e.kind not in tiles.KINDS:
                raise PackWriteError(f"tile entry kind {e.kind} is not allowed")
            if e.kind == tiles.COVERED:
                if e.data:
                    raise PackWriteError("a covered note has no bytes")
                continue
            points = coords.point_count(e.data)
            total += points
            if exact and points > tiles.ENTRY_POINTS and level < tiles.MAX_TILE_LEVEL:
                raise PackWriteError(f"a tile entry at tile level {level} has {points} points; "
                                     f"the most is {tiles.ENTRY_POINTS}, so cut it at the next level")
        if exact and total > tiles.TILE_POINTS and level < tiles.MAX_TILE_LEVEL:
            raise PackWriteError(f"a pack tile at tile level {level} has {total} points; "
                                 f"the most is {tiles.TILE_POINTS}, so split it")
        return tiles.encode_entries(entries)

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
        return {
            **given,
            "format": FORMAT,
            "built": max(s["date"] for s in sources),
            "layers": [layer["id"] for layer in layers],
            "tile_levels": sorted(self.tile_levels),
            "coordinates": {"encoding": "compact", "scale": coords.SCALE},
            "features": {"count": len(self.features), "groups": len(self.group_starts),
                         "group_starts": self.group_starts},
            "limits": {"entry_points": tiles.ENTRY_POINTS, "tile_points": tiles.TILE_POINTS},
        }

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
        unknown = sorted({f["layer"] for f in self.features} - set(ids))
        if unknown:
            raise PackWriteError(f"features use layers not defined: {', '.join(unknown)}")
        self._put("manifest", _json(self._manifest(manifest, layers)))
        self._put("attribution", attribution.encode("utf-8"))
        self._put("licence", licence.encode("utf-8"))
        self._put("layers", _json(layers))
        directory = zlib.compress(_json({"records": self.directory}), 9)
        offset = self.out.tell() - self.start
        self.out.write(directory)
        end = self.out.tell()
        head = _HEADER.pack(MAGIC, FORMAT, 0, 0, offset, len(directory), check_number(directory), 0)
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
    """Reads records on demand from a pack in format 2.

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
        self._groups: dict[int, list[dict]] = {}
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
        if fmt < FORMAT:
            raise NotAPack(self.name)
        if fmt > FORMAT:
            raise NewerFormat(self.name)
        if fmt != FORMAT or check_number(head[:-4]) != head_check:
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

    def _group(self, g: int) -> list[dict]:
        if g not in self._groups:
            self._groups[g] = self.get_json(f"features/{g}") or []
        return self._groups[g]

    def feature(self, number: int) -> dict:
        """The feature record with this feature number, as tile entries give it."""
        if not 0 <= number < self.feature_count:
            raise IndexError(number)
        g = bisect.bisect_right(self.group_starts, number) - 1
        return self._group(g)[number - self.group_starts[g]]

    def feature_number(self, identifier: str) -> int | None:
        g = feature_group(identifier, len(self.group_starts))
        for i, record in enumerate(self._group(g)):
            if record["id"] == identifier:
                return self.group_starts[g] + i
        return None

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
