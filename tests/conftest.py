"""Shared test set-up.

Rules this file enforces (architecture 3.5):

1. No window ever opens: QT_QPA_PLATFORM is forced to "offscreen" before
   anything imports PySide6.
2. No network connection is opened: sockets are blocked, except for the local
   web server the browser tests start (tests/web has its own conftest).
3. No audio device is opened: audio backends take a stand-in engine. There are
   none yet; the guard is added with the first backend.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
