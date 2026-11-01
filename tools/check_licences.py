"""Dependency licence check (SCP-4, implementation plan 1.3).

Lists every installed Python distribution and fails if any licence is not known
to be compatible with GPL-3.0. Unknown licences fail too, so each new
dependency is looked at once and recorded in REVIEWED below.

Run: python tools/check_licences.py
Standard library only, so it runs before anything else is installed.
"""
from __future__ import annotations

import sys
from importlib import metadata

# Licence words that are compatible with distributing the whole as GPL-3.0.
COMPATIBLE = (
    "MIT", "BSD", "APACHE", "ISC", "PSF", "PYTHON SOFTWARE FOUNDATION", "LGPL",
    "GPL-3", "GPLV3", "GPL V3", "GNU GENERAL PUBLIC LICENSE V3", "GPL-2.0-OR-LATER",
    "GPLV2+", "MPL", "MOZILLA PUBLIC LICENSE 2", "ZLIB", "UNLICENSE", "CC0",
    "PUBLIC DOMAIN", "0BSD", "HPND", "UNIVERSAL PERMISSIVE",
)

# Packages checked by hand, with the reason. Keys are lower case.
REVIEWED = {
    "pyside6": "LGPL-3.0 (Qt for Python), dual licensed with commercial",
    "pyside6-essentials": "LGPL-3.0, part of PySide6",
    "pyside6-addons": "LGPL-3.0, part of PySide6",
    "shiboken6": "LGPL-3.0, part of PySide6",
    "pyinstaller": "GPL-2.0-or-later with a bootloader exception that allows any licence for the built program",
    "pyinstaller-hooks-contrib": "GPL-2.0-or-later and Apache-2.0",
    "playwright": "Apache-2.0, test tool only, not distributed",
    "pytest-playwright": "Apache-2.0, test tool only, not distributed",
    "greenlet": "MIT and PSF",
    "pefile": "MIT",
    "certifi": "MPL-2.0",
    "text-unidecode": "Artistic or GPL-2.0-or-later",
    "pip": "MIT",
    "espeakng-loader": "MIT (github.com/thewh1teagle/espeakng-loader), bundling the eSpeak NG library, GPL-3.0; spike S6",
}

# Licences that must never be accepted, even if a compatible word also appears.
INCOMPATIBLE = ("AGPL", "SSPL", "BUSL", "COMMONS CLAUSE", "NON-COMMERCIAL", "CC-BY-NC", "PROPRIETARY")


def licence_text(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    parts = [meta.get("License-Expression") or "", meta.get("License") or ""]
    parts += [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    return " | ".join(p.strip() for p in parts if p and p.strip())[:300]


def judge(name: str, text: str) -> tuple[bool, str]:
    key = name.lower()
    if key in REVIEWED:
        return True, f"reviewed: {REVIEWED[key]}"
    upper = text.upper()
    if any(bad in upper for bad in INCOMPATIBLE):
        return False, f"incompatible: {text}"
    if any(good in upper for good in COMPATIBLE):
        return True, text
    return False, f"unknown: {text or 'no licence given'}"


def main() -> int:
    failures = []
    seen = set()
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "?"
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        ok, why = judge(name, licence_text(dist))
        print(f"{'OK  ' if ok else 'FAIL'} {name} {dist.version}: {why}")
        if not ok:
            failures.append(name)
    if failures:
        print(f"Licence check failed for {len(failures)} package(s): {', '.join(failures)}.")
        print("Check each licence by hand, and add it to REVIEWED in tools/check_licences.py if compatible.")
        return 1
    print(f"Licence check passed for {len(seen)} packages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
