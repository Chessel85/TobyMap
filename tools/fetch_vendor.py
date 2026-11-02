"""Fetch the third-party files that are not kept in git (implementation plan 1.3).

* Pyodide core and the NumPy, PyYAML and Shapely packages, into
  web/vendor/pyodide, for the web shell (AD-9). Pyodide is MPL-2.0; NumPy is
  BSD; PyYAML is MIT; Shapely is BSD-3-Clause, with GEOS (LGPL-2.1) built in.
  Shapely is used by the pack reader, from spike S4 on.
* The NVDA Controller Client, 64-bit, into desktop/vendor, for Braille-only
  messages (architecture 4.4). It is LGPL-2.1.

Each download is checked against a pinned SHA-256, so a changed file is never
used silently. Already-present files are kept.

Run: python tools/fetch_vendor.py [--web] [--nvda]   (both if neither is given)
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYODIDE_VERSION = "314.0.7"
PYODIDE_CORE_URL = (f"https://github.com/pyodide/pyodide/releases/download/{PYODIDE_VERSION}/"
                    f"pyodide-core-{PYODIDE_VERSION}.tar.bz2")
PYODIDE_CORE_SHA256 = "2abdcc2e35208af406e07724cffa85bc582ced97e9028383ecf5462541393f95"
PYODIDE_CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
PYODIDE_PACKAGES = ("numpy", "pyyaml", "shapely")
PYODIDE_DIR = ROOT / "web" / "vendor" / "pyodide"
# Node.js launchers and type files in the archive, which a browser never loads.
BROWSER_UNUSED = {"python", "python.bat", "python.exe", "python_cli_entry.mjs"}

NVDA_VERSION = "2026.3"
NVDA_URL = f"https://download.nvaccess.org/releases/{NVDA_VERSION}/nvda_{NVDA_VERSION}_controllerClient.zip"
NVDA_SHA256 = "e38a00689eab422f13aaed9aaaacdd3ae96411643b6f2f5fbf86222660ac7938"
NVDA_DIR = ROOT / "desktop" / "vendor"


def download(url: str) -> bytes:
    print(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "TobyMap fetch_vendor"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def check(data: bytes, expected: str, what: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if expected.startswith("PIN_"):
        print(f"No checksum pinned yet for {what}. Its SHA-256 is {actual}.")
        return
    if actual != expected:
        raise SystemExit(f"Checksum mismatch for {what}: expected {expected}, got {actual}. Nothing was written.")


def fetch_pyodide() -> None:
    marker = PYODIDE_DIR / "pyodide.js"
    if not marker.is_file():
        data = download(PYODIDE_CORE_URL)
        check(data, PYODIDE_CORE_SHA256, "Pyodide core")
        if PYODIDE_DIR.exists():
            shutil.rmtree(PYODIDE_DIR)
        PYODIDE_DIR.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:bz2") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = Path(member.name).name  # the archive has one "pyodide/" folder
                if name in BROWSER_UNUSED or name.endswith(".d.ts"):
                    continue
                (PYODIDE_DIR / name).write_bytes(tar.extractfile(member).read())
    lock = json.loads((PYODIDE_DIR / "pyodide-lock.json").read_text(encoding="utf-8"))
    for package in PYODIDE_PACKAGES:
        info = lock["packages"][package]
        target = PYODIDE_DIR / info["file_name"]
        if target.is_file():
            continue
        data = download(PYODIDE_CDN + info["file_name"])
        check(data, info["sha256"], info["file_name"])  # the lock file pins these
        target.write_bytes(data)
    print(f"Pyodide {PYODIDE_VERSION} is in {PYODIDE_DIR}")


def fetch_nvda() -> None:
    target = NVDA_DIR / "nvdaControllerClient.dll"
    if not target.is_file():
        data = download(NVDA_URL)
        check(data, NVDA_SHA256, "NVDA Controller Client")
        NVDA_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            target.write_bytes(z.read("x64/nvdaControllerClient.dll"))
            (NVDA_DIR / "nvdaControllerClient-license.txt").write_bytes(z.read("license.txt"))
    print(f"NVDA Controller Client {NVDA_VERSION} is in {NVDA_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch third-party files that are not kept in git.")
    parser.add_argument("--web", action="store_true", help="Pyodide for the web shell")
    parser.add_argument("--nvda", action="store_true", help="the NVDA Controller Client for the desktop")
    args = parser.parse_args(argv)
    both = not (args.web or args.nvda)
    if args.web or both:
        fetch_pyodide()
    if args.nvda or both:
        fetch_nvda()
    return 0


if __name__ == "__main__":
    sys.exit(main())
