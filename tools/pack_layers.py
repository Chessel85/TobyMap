"""Each layer's share of a pack: its features, points and megabytes (P3-T1a, the size trial).

    .venv\\Scripts\\python.exe tools\\pack_layers.py <pack> [--json FILE]

A pack's records are compressed one by one. A pack tile or drawing tile holds
tile entries of several layers, so each record's stored bytes are shared out
between the layers by the size of their tile entries before compressing. A
group of feature records is shared out in the same way, by the length of each
feature record. What is left, the manifest, the attribution, the licence, the
layers list and the directory, is counted as "the pack's own records".

Plain lines for a screen reader (DMT-2); --json writes the same figures for
the size report.
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapcore.packs import coords, tiles  # noqa: E402
from mapcore.packs.pack import HEADER_SIZE, Pack  # noqa: E402


def entry_points(e: tiles.TileEntry) -> int:
    if e.kind == tiles.COMPACT:
        return coords.point_count(e.data)
    if e.kind == tiles.LINES:
        return coords.line_point_count(e.data)
    if e.kind == tiles.POINTS:
        return len(e.data) // 8 if e.data else 0   # an estimate; point layers are small
    return 0


def measure(path: Path) -> dict:
    with Pack(path, check_app=False) as p:
        layer_of = [p.feature(n)["layer"] for n in range(p.feature_count)]
        names = {layer["id"]: layer["name"] for layer in p.layers}
        out = {"file": str(path), "bytes": path.stat().st_size, "records": len(p.directory),
               "features": defaultdict(int), "parts": {}}
        for layer in layer_of:
            out["features"][layer] += 1
        # parts[layer][part] = {"bytes": stored bytes, "points": points, "records": records touched}
        parts: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"bytes": 0.0, "points": 0}))
        record_count = defaultdict(int)
        own = 0
        for key, (offset, length, _check) in p.directory.items():
            if key.startswith(("tile/", "draw/")):
                part = "pack tiles" if key.startswith("tile/") else f"drawing level {key.split('/')[1]}"
                record_count[part] += 1
                entries = p._entries(key)
                raw = defaultdict(int)
                pts = defaultdict(int)
                for e in entries:
                    layer = layer_of[e.feature]
                    raw[layer] += 9 + len(e.data)
                    pts[layer] += entry_points(e)
                total = sum(raw.values()) or 1
                for layer, n in raw.items():
                    parts[layer][part]["bytes"] += length * n / total
                    parts[layer][part]["points"] += pts[layer]
            elif key.startswith("features/"):
                record_count["feature records"] += 1
                members = json.loads(zlib.decompress(p.source.read(offset, length)))
                sizes = defaultdict(int)
                for m in members:
                    sizes[m["layer"]] += len(json.dumps(m, separators=(",", ":"), ensure_ascii=False).encode())
                total = sum(sizes.values()) or 1
                for layer, n in sizes.items():
                    parts[layer]["feature records"]["bytes"] += length * n / total
            else:
                own += length
        accounted = sum(v["bytes"] for layer in parts.values() for v in layer.values()) + own
        out["own_bytes"] = own + (out["bytes"] - accounted)   # the header and the directory
        out["parts"] = {layer: {k: {"bytes": round(v["bytes"]), "points": v["points"]} for k, v in d.items()}
                        for layer, d in parts.items()}
        out["names"] = names
        out["features"] = dict(out["features"])
        out["record_counts"] = dict(record_count)
        out["drawing_levels"] = p.manifest.get("drawing_levels", [])
        return out


def mb(n: float) -> str:
    return f"{n / 1e6:,.2f} MB"


def lines(m: dict) -> list[str]:
    out = [f"The pack {Path(m['file']).name}: {mb(m['bytes'])}, {m['records']:,} records."]
    for layer, d in sorted(m["parts"].items(), key=lambda kv: -sum(v["bytes"] for v in kv[1].values())):
        total = sum(v["bytes"] for v in d.values())
        out.append("")
        out.append(f"{m['names'].get(layer, layer)}: {m['features'].get(layer, 0):,} features, {mb(total)}, "
                   f"{100 * total / m['bytes']:.1f}% of the pack.")
        for part, v in sorted(d.items()):
            pts = f", {v['points']:,} points" if v["points"] else ""
            out.append(f"* {part}: {mb(v['bytes'])}{pts}")
    out.append("")
    out.append(f"The pack's own records (manifest, attribution, licence, layers list, directory): {mb(m['own_bytes'])}.")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    m = measure(args.pack)
    print("\n".join(lines(m)))
    if args.json:
        args.json.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
