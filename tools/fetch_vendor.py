"""Fetch the third-party files that are not kept in git (implementation plan 1.3).

* Pyodide core and the NumPy, PyYAML and Shapely packages, into
  web/vendor/pyodide, for the web shell (AD-9). Pyodide is MPL-2.0; NumPy is
  BSD; PyYAML is MIT; Shapely is BSD-3-Clause, with GEOS (LGPL-2.1) built in.
  Shapely is used by the pack reader, from spike S4 on.
* coi-serviceworker 0.1.7 (MIT, Guido Zuidhof and contributors), into web/,
  with --web: the small helper script that makes the page cross-origin isolated
  where the server cannot send the headers, as on GitHub Pages, so the spatial
  voice can use four threads (DP105, P2-T7b).
* The NVDA Controller Client, 64-bit, into desktop/vendor, for Braille-only
  messages (architecture 4.4). It is LGPL-2.1.
* The MIT KEMAR head-related impulse responses (Gardner and Martin, MIT Media
  Lab, 1994, provided without usage restrictions), into desktop/vendor, for the
  desktop's HRTF sound mode (AD-10, P2-T6b). About 230 KB.
* Piper in the browser (spike S6, architecture 4.6), into web/vendor/piper:
  ONNX Runtime Web (MIT), which runs the voice, and phonemizer.js
  (Apache-2.0, with the eSpeak NG library and data built in, GPL-3.0), which
  turns text into the sounds of speech as Piper expects, and the Alba voice. Only with --piper.
* The Alba voice for Piper (Scottish English, female, CC-BY 4.0, from
  rhasspy/piper-voices), into desktop/vendor/piper, for the desktop's spatial
  voice (P2-T7, SON-3). About 63 MB. With --voice, or --piper for the web copy.

Each download is checked against a pinned SHA-256, so a changed file is never
used silently. Already-present files are kept.

Run: python tools/fetch_vendor.py [--web] [--nvda] [--kemar] [--voice] [--piper] [--axe]   (--web, --nvda and --kemar if none is given)
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

COI_URL = "https://registry.npmjs.org/coi-serviceworker/-/coi-serviceworker-0.1.7.tgz"
COI_SHA256 = "6a546d4748e215220de923cf5dbb887104cec1aa7bb9afc2e925ba376a229616"
COI_FILE = ROOT / "web" / "coi-serviceworker.js"

NVDA_VERSION = "2026.3"
NVDA_URL = f"https://download.nvaccess.org/releases/{NVDA_VERSION}/nvda_{NVDA_VERSION}_controllerClient.zip"
NVDA_SHA256 = "e38a00689eab422f13aaed9aaaacdd3ae96411643b6f2f5fbf86222660ac7938"
NVDA_DIR = ROOT / "desktop" / "vendor"

KEMAR_URL = "http://sound.media.mit.edu/resources/KEMAR/compact.zip"
KEMAR_SHA256 = "0bcd69f8e8760cf8eacff4a89594ceca7d44fb94f28ecf0bf19970003bbfb3e0"
KEMAR_FILE = ROOT / "desktop" / "vendor" / "mit_kemar_compact.zip"

# npm packages for Piper in the browser: (tarball URL, SHA-256, {file in the archive: name in web/vendor/piper}).
PIPER_DIR = ROOT / "web" / "vendor" / "piper"
PIPER_PACKAGES = {
    "onnxruntime-web 1.31.1 (MIT)": (
        "https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.31.1.tgz",
        "bdccdb9fbb9ab537247c0c734e9b1d2b1b338b4f2a09faa58f0dc1cfa27c312c",
        {"package/dist/ort.wasm.min.mjs": "ort.wasm.min.mjs",
         "package/dist/ort-wasm-simd-threaded.mjs": "ort-wasm-simd-threaded.mjs",
         "package/dist/ort-wasm-simd-threaded.wasm": "ort-wasm-simd-threaded.wasm"}),
    "phonemizer 1.2.1 (Apache-2.0; eSpeak NG inside, GPL-3.0)": (
        "https://registry.npmjs.org/phonemizer/-/phonemizer-1.2.1.tgz",
        "12f9f3582f8b5d557a0577180d83ff0458a4a5c15b2efb625ee71c3ebbee22e9",
        {"package/dist/phonemizer.js": "phonemizer.js",
         "package/LICENSE": "phonemizer-LICENSE.txt"}),
}
PIPER_NOTICE = """Third-party files for Piper in the browser, fetched by tools/fetch_vendor.py --piper.

* ONNX Runtime Web 1.31.1, Microsoft, MIT licence (github.com/microsoft/onnxruntime).
  ort.wasm.min.mjs, ort-wasm-simd-threaded.mjs and ort-wasm-simd-threaded.wasm.
* phonemizer.js 1.2.1, Xenova, Apache-2.0 (github.com/xenova/phonemizer.js), see phonemizer-LICENSE.txt.
  It has the eSpeak NG library and its data built in, GPL-3.0 (github.com/espeak-ng/espeak-ng).
"""


# The Alba voice (P2-T7, SON-3): {file name: SHA-256}, from Piper's voice collection, version 1.0.0.
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/"
VOICE_FILES = {
    "en_GB-alba-medium.onnx": "401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b",
    "en_GB-alba-medium.onnx.json": "aa965a2f02ecced632c2694e1fc72bbff6d65f265fab567ca945918c73dd89f4",
    "MODEL_CARD": "fa166b1779404c470b0b6b4ba0238bc4a35bf89d2cd130c6788f697188b737d6",
}
VOICE_DIR = ROOT / "desktop" / "vendor" / "piper"
VOICE_NOTICE = """The Alba voice for Piper, fetched by tools/fetch_vendor.py.

Voice: Alba, Scottish English female, medium quality, from Piper voices (github.com/rhasspy/piper,
huggingface.co/rhasspy/piper-voices), trained on the Alba recordings of the University of Edinburgh
(datashare.ed.ac.uk/handle/10283/3270), licensed CC-BY 4.0 (creativecommons.org/licenses/by/4.0).
See MODEL_CARD.
"""


# axe-core, the automatic accessibility checker used by the browser tests only (MPL-2.0, never distributed).
AXE_URL = "https://registry.npmjs.org/axe-core/-/axe-core-4.14.0.tgz"
AXE_SHA256 = "2277b0a3ef47af9b52497faa3e71598e86e0a0e5e6eb295207a5657ede4709af"
AXE_DIR = ROOT / "web" / "vendor" / "axe"


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


def fetch_coi() -> None:
    """The helper script must be at the top of the site, so its scope covers the page."""
    if not COI_FILE.is_file():
        data = download(COI_URL)
        check(data, COI_SHA256, "coi-serviceworker 0.1.7")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            COI_FILE.write_bytes(tar.extractfile("package/coi-serviceworker.js").read())
            (COI_FILE.parent / "coi-serviceworker-LICENSE.txt").write_bytes(tar.extractfile("package/LICENSE").read())
    print(f"coi-serviceworker is in {COI_FILE.parent}")


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


def fetch_kemar() -> None:
    if not KEMAR_FILE.is_file():
        data = download(KEMAR_URL)
        check(data, KEMAR_SHA256, "MIT KEMAR responses")
        KEMAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEMAR_FILE.write_bytes(data)
    print(f"The MIT KEMAR responses are in {KEMAR_FILE}")


def fetch_piper() -> None:
    for what, (url, sha, files) in PIPER_PACKAGES.items():
        if all((PIPER_DIR / name).is_file() for name in files.values()):
            continue
        data = download(url)
        check(data, sha, what)
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member, name in files.items():
                (PIPER_DIR / name).write_bytes(tar.extractfile(member).read())
    (PIPER_DIR / "NOTICE.txt").write_text(PIPER_NOTICE, encoding="utf-8")
    print(f"ONNX Runtime Web and phonemizer.js are in {PIPER_DIR}")
    fetch_voice(PIPER_DIR / "voice")


def fetch_voice(folder: Path = VOICE_DIR) -> None:
    """The Alba voice into folder, copied from the other copy if it is there, else downloaded."""
    folder.mkdir(parents=True, exist_ok=True)
    others = [d for d in (VOICE_DIR, PIPER_DIR / "voice", ROOT / "voices" / "piper") if d != folder]
    for name, sha in VOICE_FILES.items():
        target = folder / name
        if target.is_file():
            continue
        data = None
        for other in others:
            for candidate in (other / name, other / name.replace("MODEL_CARD", "en_GB-alba-medium.MODEL_CARD.txt")):
                if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == sha:
                    data = candidate.read_bytes()
                    break
            if data:
                break
        if data is None:
            data = download(VOICE_URL + name)
            check(data, sha, f"the Alba voice, {name}")
        target.write_bytes(data)
    (folder / "NOTICE.txt").write_text(VOICE_NOTICE, encoding="utf-8")
    print(f"The Alba voice is in {folder}")


def fetch_axe() -> None:
    if not (AXE_DIR / "axe.min.js").is_file():
        data = download(AXE_URL)
        check(data, AXE_SHA256, "axe-core 4.14.0 (MPL-2.0, test tool only)")
        AXE_DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            (AXE_DIR / "axe.min.js").write_bytes(tar.extractfile("package/axe.min.js").read())
            (AXE_DIR / "LICENSE.txt").write_bytes(tar.extractfile("package/LICENSE").read())
    print(f"axe-core is in {AXE_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch third-party files that are not kept in git.")
    parser.add_argument("--web", action="store_true", help="Pyodide for the web shell")
    parser.add_argument("--nvda", action="store_true", help="the NVDA Controller Client for the desktop")
    parser.add_argument("--kemar", action="store_true", help="the MIT KEMAR responses, for the desktop's HRTF mode")
    parser.add_argument("--voice", action="store_true", help="the Alba voice, for the desktop's spatial voice")
    parser.add_argument("--piper", action="store_true", help="ONNX Runtime Web, phonemizer.js and the Alba voice, for Piper in the browser")
    parser.add_argument("--axe", action="store_true", help="axe-core, for the browser tests' accessibility check (test tool only)")
    args = parser.parse_args(argv)
    both = not (args.web or args.nvda or args.kemar or args.voice or args.piper or args.axe)
    if args.web or both:
        fetch_pyodide()
        fetch_coi()
    if args.nvda or both:
        fetch_nvda()
    if args.kemar or both:
        fetch_kemar()
    if args.voice:
        fetch_voice()
    if args.piper:
        fetch_piper()
    if args.axe:
        fetch_axe()
    return 0


if __name__ == "__main__":
    sys.exit(main())
