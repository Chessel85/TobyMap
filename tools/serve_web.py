"""Try the web version on this computer (spike S5).

Stages the core, checks Pyodide is present, serves the web folder at
http://127.0.0.1:8765 and opens it in the default browser. Press Ctrl+C in
this window to stop.

Run: .venv\\Scripts\\python.exe tools\\serve_web.py [--port 8765] [--no-browser] [--pack <world.pack>] [--pack <england.pack>]

With --pack, the pack is served from where it is, as packs/world.pack with its
packs/packs.json, so the page downloads it on the first visit as it would from
GitHub Pages. Nothing is copied into the web folder. Given more than once, each
pack is served under its own file name and all are listed, so the page opens
them together, such as the world pack and the England pack (P4-T3d).
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

    pack: Path | None = None   # one pack, served as world.pack
    packs: list[Path] = []     # several packs, each served under its own file name (P4-T3d)

    def _served(self) -> dict[str, Path]:
        if self.packs:
            return {p.name: p for p in self.packs}
        return {"world.pack": self.pack} if self.pack is not None else {}

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        served = self._served()
        name = path[len("/packs/"):] if path.startswith("/packs/") else None
        if served and name == "packs.json":
            body = json.dumps({"packs": [{"file": n, "bytes": f.stat().st_size} for n, f in served.items()]}).encode()
            self._headers("application/json", len(body))
            self.wfile.write(body)
        elif name in served:
            self._headers("application/octet-stream", served[name].stat().st_size)
            with served[name].open("rb") as f:
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
    parser.add_argument("--pack", action="append",
                        help="a pack file to serve as the web version's map, such as world.pack; more than once to "
                             "open several together")
    args = parser.parse_args(argv)
    given = [Path(g).resolve() for g in args.pack or []]
    for pack in given:
        if not pack.is_file():
            print(f"The pack {pack} is not there.")
            return 1
    if len({p.name for p in given}) < len(given):
        print("Two of the packs have the same file name. Each must have its own.")
        return 1
    if len(given) == 1:
        Handler.pack = given[0]
    elif given:
        Handler.packs = given
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
