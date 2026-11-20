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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapdata.pipeline.pack_size import entry_points, measure  # noqa: E402,F401  (moved there for the quality report)


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
