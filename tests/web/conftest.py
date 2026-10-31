"""Browser tests: serve web/ from a local server for Playwright (Chromium and Firefox)."""
import functools
import http.server
import threading
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def site_url():
    handler = functools.partial(_QuietHandler, directory=str(WEB_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
