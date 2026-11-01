"""Try the web version on this computer (spike S5).

Stages the core, checks Pyodide is present, serves the web folder at
http://127.0.0.1:8765 and opens it in the default browser. Press Ctrl+C in
this window to stop.

Run: .venv\\Scripts\\python.exe tools\\serve_web.py [--port 8765] [--no-browser]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "tools"))

import fetch_vendor  # noqa: E402
import stage_web  # noqa: E402


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm",
                      ".yaml": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the TobyMap web version on this computer.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    fetch_vendor.fetch_pyodide()
    stage_web.stage()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(Handler, directory=str(WEB)))
    url = f"http://127.0.0.1:{args.port}/index.html"
    print(f"TobyMap web version: {url}")
    print("Press Ctrl+C in this window to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
