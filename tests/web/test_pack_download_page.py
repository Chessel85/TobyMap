"""Installing a pack in the web version (P4-T6c; PCK-4, PCK-5, spike S3), in Chromium and Firefox.

The site has no pack of its own. A stand-in for Hugging Face on the local test server serves the test pack, with
range requests, and can hold the whole download back after its first bytes, so the test can show the map is read
while the pack is still downloading. Installing from a catalogue entry downloads the pack into the browser's
private storage, opens it at once, reads records by range requests until it is complete, and then from the file,
which the next visit opens without downloading. A pack that does not match its checksum is removed and said, and
one too big for the space the browser has left is refused, saying what is left.
"""
import hashlib
import re
import shutil
import threading

import pytest

from tests.web.conftest import _serve, _TwoPacksHandler
from mapcore.session import MapSession
from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

HAMPSHIRE = {"lat": 51.2000, "lon": -1.4000, "zoom_m": 5000, "step_m": 100}
FIRST_BYTES = 64 * 1024   # sent before a held download waits


class _Stand:
    """What the stand-in server serves, and what it saw: the pack, whether the whole download is held after its
    first bytes, and how many whole downloads and range requests came."""

    def __init__(self):
        self.data = b""
        self.release = threading.Event()
        self.release.set()
        self.whole = 0
        self.ranges = 0
        self.resumes: list[int] = []   # the start of each request for the rest of the pack (P4-T6f)


class _DownloadHandler(_TwoPacksHandler):
    stand: _Stand = None

    def do_GET(self):
        if not self.path.startswith("/dl/"):
            return super().do_GET()
        data, stand = self.stand.data, self.stand
        rest = re.fullmatch(r"bytes=(\d+)-", self.headers.get("Range", ""))
        if rest:   # a download that carries on (P4-T6f): everything from there, at once
            start = int(rest[1])
            stand.resumes.append(start)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data) - start))
            self.end_headers()
            try:
                self.wfile.write(data[start:])
            except OSError:
                pass
            return
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
        if match:
            stand.ranges += 1
            start, end = int(match[1]), min(int(match[2]), len(data) - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            body = data[start:end + 1]
        else:
            stand.whole += 1
            self.send_response(200)
            body = data
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        try:
            if match:
                self.wfile.write(body)
                return
            self.wfile.write(body[:FIRST_BYTES])
            self.wfile.flush()
            stand.release.wait(120)
            self.wfile.write(body[FIRST_BYTES:])
        except OSError:   # the browser stopped the download
            pass


@pytest.fixture(scope="module")
def stand():
    return _Stand()


@pytest.fixture(scope="module")
def download_site_url(site_url, test_pack, stand, tmp_path_factory):
    """The web version with no pack of its own (an empty packs folder), on its own origin, and the stand-in."""
    folder = tmp_path_factory.mktemp("no_packs")
    stand.data = test_pack.read_bytes()
    handler = type("_Handler", (_DownloadHandler,), {"packs_dir": folder, "stand": stand})
    server = _serve(handler)
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture
def entry(download_site_url, stand):
    stand.release.set()
    stand.whole = stand.ranges = 0
    stand.resumes.clear()
    return {"name": "test", "title": "Test world", "version": "2026.11.1", "date": "2026-11-27",
            "size": len(stand.data), "sha256": hashlib.sha256(stand.data).hexdigest(),
            "url_desktop": "https://example.org/test.pack", "url_web": f"{download_site_url}/dl/test.pack",
            "app_versions": {"from": "0.0.1"}}


def _texts(app):
    return app.evaluate("window.tobymap.announcements.map(a => a.text)")


def _stored(app):
    return sorted(app.evaluate("""async () => {
        const names = [];
        for await (const [name] of (await navigator.storage.getDirectory()).entries()) names.push(name);
        return names;
    }"""))


def _core_label(test_pack, state):
    from mapcore.packs.pack import Pack
    from mapcore.session import MapSession

    s = MapSession(platform="web", packs=[Pack(test_pack)], saved_state=state)
    try:
        s.start()
        return s.map_label(), s.start_label()
    finally:
        s.store.close()


def test_a_pack_is_read_while_downloading_then_stored_and_opened_from_storage(page, download_site_url, entry, stand,
                                                                               test_pack):
    app = open_app(page, download_site_url, state=HAMPSHIRE)
    assert app.get_attribute("#map", "aria-label").startswith("No map pack is installed")
    map_label, start_label = _core_label(test_pack, HAMPSHIRE)
    stand.release.clear()   # the download waits after its first bytes
    assert app.evaluate("(entry) => window.tobymap.install(entry)", entry) is True
    # The place is said from the pack before it has downloaded: its records come by range requests. The map is
    # named with it as the focus leaves the map (the name is not changed under the focus).
    app.evaluate("document.getElementById('map').blur()")
    assert app.get_attribute("#map", "aria-label") == map_label
    assert "Hampshire" in map_label
    assert stand.ranges > 0 and stand.whole == 1
    assert not [t for t in _texts(app) if "is downloaded" in t]
    assert _stored(app) == ["test.pack.part", "test.pack.part.json"]
    stand.release.set()
    app.wait_for_function("window.tobymap.announcements.some(a => a.text === 'Test world is downloaded and open.')",
                          timeout=60_000)
    assert _stored(app) == ["test.pack"]
    texts = _texts(app)
    assert not [t for t in texts if "could not" in t or "checksum" in t], texts
    # Read from the file now, with no more range requests, and opened from storage on the next visit.
    ranges = stand.ranges
    assert app.evaluate("window.tobymap.search('Hampshire')")["results"]
    assert stand.ranges == ranges
    app.reload()
    app.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert app.evaluate("window.tobymap.error") is None
    assert app.get_attribute("#map", "aria-label") == start_label
    assert stand.whole == 1 and stand.ranges == ranges


def test_a_pack_that_does_not_match_its_checksum_is_removed_and_said(page, download_site_url, entry, stand):
    app = open_app(page, download_site_url, state=HAMPSHIRE)
    entry["sha256"] = "0" * 64
    assert app.evaluate("(entry) => window.tobymap.install(entry)", entry) is True
    damaged = ("Test world did not match its checksum after downloading, so it may be damaged or incomplete. "
               "It has been removed. Download it again.")
    app.wait_for_function("(text) => window.tobymap.announcements.some(a => a.text === text)", arg=damaged,
                          timeout=60_000)
    assert _stored(app) == []
    assert not [t for t in _texts(app) if "is downloaded" in t]
    # The pack is out of use: the map has no pack again, and nothing more is read from the internet.
    app.evaluate("document.getElementById('map').blur()")
    no_pack = MapSession(platform="web", packs=[], saved_state=HAMPSHIRE)
    assert app.get_attribute("#map", "aria-label") == no_pack.map_label()
    ranges = stand.ranges
    assert app.evaluate("window.tobymap.search('Hampshire')")["results"] == []
    assert stand.ranges == ranges


def test_a_pack_too_big_for_the_space_left_is_refused_saying_what_is_left(page, download_site_url, entry, stand):
    app = open_app(page, download_site_url, state=HAMPSHIRE)
    worker = next(w for w in app.workers if w.url.endswith("/worker.js"))
    worker.evaluate("navigator.storage.estimate = async () => ({ quota: 10_000_000, usage: 9_999_000 })")
    assert app.evaluate("(entry) => window.tobymap.install(entry)", entry) is False
    need = -(-len(stand.data) // 1_000_000)
    refused = (f"Test world needs {need} megabytes, and this browser has 0 megabytes left for TobyMap, so it was not "
               "downloaded. Free some space, then try again.")
    assert refused in _texts(app)
    assert stand.whole == 0 and stand.ranges == 0
    assert _stored(app) == []
