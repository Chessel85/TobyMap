"""Browser tests: serve web/ from a local server for Playwright (Chromium and Firefox).

Before serving, the core is staged into web/py (tools/stage_web.py). Pyodide
must already be in web/vendor (tools/fetch_vendor.py --web); continuous
integration fetches it in a set-up step, so the tests themselves never use the
network. Locally the tests are skipped with a message if it is missing; in
continuous integration they fail instead.
"""
import functools
import http.server
import json
import os
import shutil
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


class _IsolatedHandler(_QuietHandler):
    """Sends the two headers that make the page cross-origin isolated, as tools/serve_web.py does,
    so the spatial voice can use four threads (DP105)."""

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()


def _serve(handler_class):
    handler = functools.partial(handler_class, directory=str(WEB_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture(scope="session")
def plain_site_url(site_url):
    """The same site with no isolating headers, as GitHub Pages serves it: the helper script,
    coi-serviceworker.js, has to make the page isolated (P2-T7b)."""
    server = _serve(_QuietHandler)
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(scope="session")
def site_url(test_pack):
    if not (WEB_DIR / "vendor" / "pyodide" / "pyodide.mjs").is_file():
        message = "Pyodide is not in web/vendor. Run: python tools/fetch_vendor.py --web"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)
    stage_web.stage()
    # The test pack is served as the site's only pack (P1-T11), and removed afterwards.
    packs = WEB_DIR / "packs"
    packs.mkdir(exist_ok=True)
    shutil.copyfile(test_pack, packs / "test.pack")
    (packs / "packs.json").write_text(
        json.dumps({"packs": [{"file": "test.pack", "bytes": (packs / "test.pack").stat().st_size}]}), encoding="utf-8")
    server = _serve(_IsolatedHandler)
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    shutil.rmtree(packs, ignore_errors=True)
