"""Spike S3 helpers: the test file's byte pattern and a local server that answers range requests (P0-T6).

The test file is a known pattern, so any range read from anywhere can be
checked without downloading the whole file: the file is a run of 4-byte
little-endian whole numbers, and the number at byte offset 4k is k.

The local server serves a folder and answers "Range: bytes=a-b" requests with
206 Partial Content, as GitHub's download server and Hugging Face do. It can
run with or without the header that lets web pages from other addresses read
its files (Access-Control-Allow-Origin). Without it, it behaves as GitHub's
download server does, so the browser tests can show both cases with no
internet connection.
"""
from __future__ import annotations

import functools
import http.server
import re
import threading
from pathlib import Path

import numpy as np

MiB = 1024 * 1024
TEST_FILE_NAME = "s3-test-64MiB.bin"
TEST_FILE_SIZE = 64 * MiB


def pattern_bytes(start: int, length: int) -> bytes:
    """The bytes of the test file from byte `start`, `length` bytes long."""
    if length <= 0:
        return b""
    first_word = start // 4
    last_word = (start + length - 1) // 4
    words = np.arange(first_word, last_word + 1, dtype="<u4")
    raw = words.tobytes()
    skip = start - first_word * 4
    return raw[skip:skip + length]


def write_test_file(path: Path, size: int = TEST_FILE_SIZE) -> Path:
    """Write the test file, unless it is already there with the right size."""
    path = Path(path)
    if path.is_file() and path.stat().st_size == size:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    step = 16 * MiB
    with open(path, "wb") as f:
        for start in range(0, size, step):
            f.write(pattern_bytes(start, min(step, size - start)))
    return path


def matches_pattern(start: int, data: bytes) -> bool:
    return data == pattern_bytes(start, len(data))


_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def parse_range(header: str, size: int) -> tuple[int, int] | None:
    """The first and last byte asked for, or None if the header is not one simple range."""
    m = _RANGE.match(header.strip())
    if not m or (m.group(1) == "" and m.group(2) == ""):
        return None
    if m.group(1) == "":
        suffix = int(m.group(2))
        return max(0, size - suffix), size - 1
    first = int(m.group(1))
    last = int(m.group(2)) if m.group(2) else size - 1
    if first >= size or last < first:
        return None
    return first, min(last, size - 1)


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    """Serves a folder, with range requests, and optionally the cross-origin permission."""

    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".mjs": "text/javascript", ".bin": "application/octet-stream"}
    allow_other_origins = False
    extra_files: dict[str, bytes] = {}

    def __init__(self, *args, allow_other_origins: bool = False, extra_files: dict | None = None, **kwargs):
        self.allow_other_origins = allow_other_origins
        self.extra_files = extra_files or {}
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        if self.allow_other_origins:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges")
        super().end_headers()

    def do_OPTIONS(self):
        if not self.allow_other_origins:
            self.send_error(405)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._serve(send_body=True)

    def do_HEAD(self):
        self._serve(send_body=False)

    def _serve(self, send_body: bool):
        name = self.path.split("?", 1)[0]
        if name in self.extra_files:
            body = self.extra_files[name]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)
            return
        path = Path(self.translate_path(self.path))
        if not path.is_file() or "Range" not in self.headers:
            if send_body:
                super().do_GET()
            else:
                super().do_HEAD()
            return
        size = path.stat().st_size
        wanted = parse_range(self.headers["Range"], size)
        if wanted is None:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        first, last = wanted
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
        self.send_header("Content-Length", str(last - first + 1))
        self.end_headers()
        if send_body:
            with open(path, "rb") as f:
                f.seek(first)
                self.wfile.write(f.read(last - first + 1))


class LocalServer:
    """A RangeHandler server on 127.0.0.1, in a background thread."""

    def __init__(self, directory: Path, allow_other_origins: bool = False, port: int = 0,
                 extra_files: dict | None = None):
        handler = functools.partial(RangeHandler, directory=str(directory),
                                    allow_other_origins=allow_other_origins, extra_files=extra_files)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self) -> "LocalServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
