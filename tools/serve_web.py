"""Try the web version on this computer (spike S5).

Stages the core, checks Pyodide is present, serves the web folder at
http://127.0.0.1:8765 and opens it in the default browser. Press Ctrl+C in
this window to stop.

Run: .venv\\Scripts\\python.exe tools\\serve_web.py [--port 8765] [--no-browser] [--pack <world.pack>]

With --pack, the pack is served from where it is, as packs/world.pack with its
packs/packs.json, so the page downloads it on the first visit as it would from
GitHub Pages. Nothing is copied into the web folder.
"""
from __future__ import annotations

import argparse
import functools
import json
import shutil
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
        # Cross-origin isolated, so the spatial voice uses four threads (DP105).
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def log_message(self, *args):
        pass

    pack: Path | None = None   # set by --pack

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if self.pack is not None and path == "/packs/packs.json":
            body = json.dumps({"packs": [{"file": "world.pack", "bytes": self.pack.stat().st_size}]}).encode()
            self._headers("application/json", len(body))
            self.wfile.write(body)
        elif self.pack is not None and path == "/packs/world.pack":
            self._headers("application/octet-stream", self.pack.stat().st_size)
            with self.pack.open("rb") as f:
                shutil.copyfileobj(f, self.wfile, 1 << 20)
        else:
            super().do_GET()

    def _headers(self, kind: str, length: int):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(length))
        self.end_headers()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the TobyMap web version on this computer.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--pack", help="a pack file to serve as the web version's map, such as world.pack")
    args = parser.parse_args(argv)
    if args.pack:
        Handler.pack = Path(args.pack).resolve()
        if not Handler.pack.is_file():
            print(f"The pack {Handler.pack} is not there.")
            return 1
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
