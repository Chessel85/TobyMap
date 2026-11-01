"""Stage the core for the web shell (artefacts section 3).

Copies mapcore (its Python, YAML and data files), version.txt and the web
bridge into web/py, and writes web/py/manifest.json listing them. The worker
reads the manifest and loads the same core the desktop uses, so no logic is
copied by hand (AD-1). web/py is not kept in git; run this after changing the
core. tools/serve_web.py and the browser tests run it for you.

Run: python tools/stage_web.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "py"
SUFFIXES = {".py", ".yaml", ".json"}


def stage() -> list[str]:
    if OUT.exists():
        shutil.rmtree(OUT)
    files: list[str] = []
    for path in sorted((ROOT / "mapcore").rglob("*")):
        if path.is_file() and path.suffix in SUFFIXES and "__pycache__" not in path.parts:
            rel = path.relative_to(ROOT).as_posix()
            (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, OUT / rel)
            files.append(rel)
    shutil.copyfile(ROOT / "version.txt", OUT / "version.txt")
    files.append("version.txt")
    shutil.copyfile(ROOT / "web" / "bridge.py", OUT / "tobymap_bridge.py")
    files.append("tobymap_bridge.py")
    (OUT / "manifest.json").write_text(json.dumps({"files": files}, indent=1), encoding="utf-8")
    return files


def main() -> int:
    files = stage()
    print(f"Staged {len(files)} files into {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
