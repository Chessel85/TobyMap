"""Browser tests: serve web/ from a local server for Playwright (Chromium and Firefox).

Before serving, the core is staged into web/py (tools/stage_web.py). Pyodide
must already be in web/vendor (tools/fetch_vendor.py --web); continuous
integration fetches it in a set-up step, so the tests themselves never use the
network. Locally the tests are skipped with a message if it is missing; in
continuous integration they fail instead.
"""
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
sys.path.insert(0, str(ROOT / "tools"))

import stage_web  # noqa: E402


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm"}

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def site_url():
    if not (WEB_DIR / "vendor" / "pyodide" / "pyodide.mjs").is_file():
        message = "Pyodide is not in web/vendor. Run: python tools/fetch_vendor.py --web"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)
    stage_web.stage()
    handler = functools.partial(_QuietHandler, directory=str(WEB_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
