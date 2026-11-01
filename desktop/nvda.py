"""Braille-only messages through the NVDA Controller Client (architecture 4.4, SON-3).

The library, nvdaControllerClient.dll, is LGPL-2.1 and comes with each NVDA
release. tools/fetch_vendor.py puts the 64-bit copy in desktop/vendor, and the
installer bundles it. If the library or NVDA is missing, braille() returns
False and the caller speaks a fallback instead.

Nothing here is used by the tests except with a stand-in, so no test talks to
a running screen reader.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
DLL_NAME = "nvdaControllerClient.dll"


class NvdaClient:
    def __init__(self, dll_path: Path | None = None):
        self._dll = None
        if sys.platform != "win32":
            return
        path = dll_path or VENDOR_DIR / DLL_NAME
        if not path.is_file():
            return
        try:
            dll = ctypes.WinDLL(str(path))
            dll.nvdaController_testIfRunning.restype = ctypes.c_ulong
            dll.nvdaController_brailleMessage.argtypes = [ctypes.c_wchar_p]
            dll.nvdaController_brailleMessage.restype = ctypes.c_ulong
            self._dll = dll
        except (OSError, AttributeError):
            self._dll = None

    @property
    def loaded(self) -> bool:
        return self._dll is not None

    def is_running(self) -> bool:
        return bool(self._dll) and self._dll.nvdaController_testIfRunning() == 0

    def braille(self, text: str) -> bool:
        """Show text on the Braille display only. True if NVDA took it."""
        if not self.is_running():
            return False
        return self._dll.nvdaController_brailleMessage(text) == 0
