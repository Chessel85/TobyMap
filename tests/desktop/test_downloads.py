"""Downloading a pack on the desktop (P4-T6b, PCK-5). The internet is a stand-in: no test opens a
network connection (rule 5)."""
import hashlib
import io
import threading
import time

import pytest

from desktop import storage
from desktop.announcer import RecordingAnnouncer
from desktop.downloads import Downloader
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.packs.catalogue import Entry


def entry_for(data: bytes, name: str = "test", **change) -> Entry:
    values = dict(name=name, version="2026.11.1", date="2026-11-20", size=len(data),
                  sha256=hashlib.sha256(data).hexdigest(), url_desktop=f"https://example.org/{name}.pack",
                  url_web=f"https://example.org/w/{name}.pack", app_versions={"from": "0.1.0"}, title="Test map")
    values.update(change)
    return Entry(**values)


class Internet:
    """A stand-in for the internet: each address's bytes, read a small chunk at a time."""

    def __init__(self, data: bytes, chunk: int = 4096, gate: threading.Event | None = None):
        self.data, self.chunk, self.gate = data, chunk, gate
        self.asked: list[str] = []

    def __call__(self, url):
        self.asked.append(url)
        internet = self

        class Source(io.BytesIO):
            def read(self, n=-1):
                if internet.gate is not None:
                    internet.gate.wait(10)
                return super().read(min(n, internet.chunk))

        return Source(self.data)


def listen(window) -> list[str]:
    """Every line the window is handed to say from now on."""
    lines: list[str] = []
    original = window.handle

    def handle(response, *a, **k):
        lines.extend(x["text"] for x in response.announcements)
        return original(response, *a, **k)

    window.handle = handle
    return lines


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.delenv("TOBYMAP_PACKS", raising=False)
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    return w


def test_a_good_download_lands_in_the_folder_and_opens(window, qtbot, tmp_path, test_pack):
    data = test_pack.read_bytes()
    internet = Internet(data, chunk=max(1, len(data) // 37))
    lines = listen(window)
    assert not window.session.store.packs
    assert window.install_pack(entry_for(data), opener=internet)
    qtbot.waitUntil(lambda: bool(window.session.store.packs), timeout=10000)
    folder = storage.packs_folder(tmp_path)
    assert (folder / "test.pack").read_bytes() == data
    assert not (folder / "test.pack.part").exists()
    assert internet.asked == ["https://example.org/test.pack"]
    assert [p.name for p in window.session.store.packs] == ["test.pack"]
    assert lines[-1] == "Test map is downloaded and open."
    progress = [t for t in lines if t.startswith("Downloading")]
    assert progress == [f"Downloading Test map: {n} percent." for n in range(10, 100, 10)]
    assert window.session.areas is not None
    assert [p.name for p in storage.find_packs(tmp_path)] == ["test.pack"]


def test_a_wrong_checksum_removes_the_file_and_says_so(window, qtbot, tmp_path, test_pack):
    data = test_pack.read_bytes()
    damaged = bytearray(data)
    damaged[100] ^= 0xFF
    lines = listen(window)
    assert window.install_pack(entry_for(data), opener=Internet(bytes(damaged)))
    qtbot.waitUntil(lambda: any("checksum" in t for t in lines), timeout=10000)
    folder = storage.packs_folder(tmp_path)
    assert not (folder / "test.pack").exists() and not (folder / "test.pack.part").exists()
    assert not window.session.store.packs
    assert lines[-1].startswith("Test map did not match its checksum") and "removed" in lines[-1]


def test_too_many_bytes_is_damaged_too(qtbot, tmp_path):
    data = b"pack" * 1000
    d = Downloader(folder=tmp_path, opener=Internet(data + b"more"), app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        assert d.start(entry_for(data)) is None
    _entry, path, text = signal.args
    assert path is None and "checksum" in text
    assert list(tmp_path.iterdir()) == []


def test_an_incompatible_pack_is_refused_before_downloading(window, qtbot, tmp_path):
    internet = Internet(b"never")
    lines = listen(window)
    assert not window.install_pack(entry_for(b"never", app_versions={"from": "99.0"}), opener=internet)
    assert internet.asked == []
    assert lines and "needs TobyMap 99.0 or later" in lines[0] and "not downloaded" in lines[0]
    assert not storage.packs_folder(tmp_path).exists() or not any(storage.packs_folder(tmp_path).iterdir())


def test_a_failed_connection_leaves_nothing_and_says_so(qtbot, tmp_path):
    def offline(url):
        raise OSError("no connection")

    d = Downloader(folder=tmp_path, opener=offline, app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        d.start(entry_for(b"abc"))
    assert signal.args[1] is None and "could not be downloaded" in signal.args[2]
    assert list(tmp_path.iterdir()) == []


def test_it_runs_on_a_thread_so_the_window_is_not_kept_waiting(window, qtbot, tmp_path, test_pack):
    data = test_pack.read_bytes()
    gate = threading.Event()
    started = time.perf_counter()
    assert window.install_pack(entry_for(data), opener=Internet(data, chunk=len(data) // 3 + 1, gate=gate))
    assert time.perf_counter() - started < 1.0
    d = window._downloader
    assert d.busy and d.thread is not threading.current_thread()
    lines = listen(window)
    assert not window.install_pack(entry_for(data, name="other"), opener=Internet(data))
    assert "still downloading" in lines[-1]
    gate.set()
    qtbot.waitUntil(lambda: bool(window.session.store.packs), timeout=10000)


def test_the_packs_folder_is_a_setting_kept_when_the_session_saves(tmp_path):
    assert storage.packs_folder(tmp_path) == storage.pack_folder(tmp_path)
    chosen = tmp_path / "elsewhere"
    storage.set_packs_folder(chosen, tmp_path)
    storage.save({"settings": {}, "state": {}}, tmp_path)
    assert storage.packs_folder(tmp_path) == chosen
    storage.set_packs_folder(None, tmp_path)
    assert storage.packs_folder(tmp_path) == storage.pack_folder(tmp_path)
