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


# Cancel and resume (P4-T6f, PCK-5) ------------------------------------------------------------------------------

class RangeInternet:
    """A stand-in that honours range requests (206), or ignores them (200) when honour is False. Each request is
    kept as (url, start). With stop_after, it waits at that byte until the gate is set."""

    def __init__(self, data: bytes, chunk: int = 4096, honour: bool = True, stop_after: int | None = None):
        self.data, self.chunk, self.honour, self.stop_after = data, chunk, honour, stop_after
        self.gate = threading.Event()
        self.reached = threading.Event()
        self.asked: list[tuple[str, int]] = []

    def __call__(self, url, start=0):
        self.asked.append((url, start))
        internet = self
        honoured = bool(start and self.honour)
        offset = start if honoured else 0

        class Source(io.BytesIO):
            status = 206 if honoured else 200

            def read(self, n=-1):
                if internet.stop_after is not None and self.tell() + offset >= internet.stop_after:
                    internet.reached.set()
                    internet.gate.wait(10)
                return super().read(min(n, internet.chunk))

        return Source(self.data[offset:])


def cancel_midway(qtbot, folder, entry, data, at) -> RangeInternet:
    internet = RangeInternet(data, chunk=1024, stop_after=at)
    d = Downloader(folder=folder, opener=internet, app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        assert d.start(entry) is None
        assert internet.reached.wait(10)
        d.cancel()
        internet.gate.set()
    assert signal.args[1] is None and signal.args[2] == ""
    return internet


def test_a_cancelled_download_keeps_its_part_and_resumes_asking_only_for_the_rest(qtbot, tmp_path):
    data = bytes(range(256)) * 200
    e = entry_for(data)
    cancel_midway(qtbot, tmp_path, e, data, 20 * 1024)
    part = tmp_path / "test.pack.part"
    held = part.stat().st_size
    assert 0 < held < len(data) and part.read_bytes() == data[:held]
    assert (tmp_path / "test.pack.part.json").exists()
    rest = RangeInternet(data, chunk=1024)
    d = Downloader(folder=tmp_path, opener=rest, app_version="0.1.1")
    said = []
    d.said.connect(said.append)
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        assert d.start(e) is None
    assert rest.asked == [("https://example.org/test.pack", held)]
    assert signal.args[1] == tmp_path / "test.pack" and (tmp_path / "test.pack").read_bytes() == data
    assert sorted(p.name for p in tmp_path.iterdir()) == ["test.pack"]
    percent = held * 100 // len(data)
    assert said[0] == f"Carrying on downloading Test map from {percent} percent."
    assert said[1:] and all(int(s.split()[-2]) > percent for s in said[1:])


def test_a_server_that_ignores_the_range_starts_again(qtbot, tmp_path):
    data = bytes(range(256)) * 200
    e = entry_for(data)
    cancel_midway(qtbot, tmp_path, e, data, 20 * 1024)
    whole = RangeInternet(data, honour=False)
    d = Downloader(folder=tmp_path, opener=whole, app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        d.start(e)
    assert whole.asked[0][1] > 0   # asked for the rest, and given everything
    assert signal.args[1] is not None and (tmp_path / "test.pack").read_bytes() == data


def test_a_part_from_another_version_is_started_again(qtbot, tmp_path):
    old = bytes(range(256)) * 200
    cancel_midway(qtbot, tmp_path, entry_for(old, version="2026.10.1"), old, 20 * 1024)
    new = bytes(reversed(old))
    fresh = RangeInternet(new)
    d = Downloader(folder=tmp_path, opener=fresh, app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        d.start(entry_for(new))
    assert fresh.asked == [("https://example.org/test.pack", 0)]
    assert signal.args[1] is not None and (tmp_path / "test.pack").read_bytes() == new


def test_a_resumed_download_that_does_not_match_is_removed(qtbot, tmp_path):
    data = bytes(range(256)) * 200
    e = entry_for(data)
    cancel_midway(qtbot, tmp_path, e, data, 20 * 1024)
    damaged = bytearray(data)
    damaged[-10] ^= 0xFF
    d = Downloader(folder=tmp_path, opener=RangeInternet(bytes(damaged)), app_version="0.1.1")
    with qtbot.waitSignal(d.finished, timeout=10000) as signal:
        d.start(e)
    assert signal.args[1] is None and "checksum" in signal.args[2]
    assert list(tmp_path.iterdir()) == []


def test_the_window_cancels_for_the_core_and_the_pack_opens_on_resume(window, qtbot, tmp_path, test_pack):
    from mapcore.session import Response

    data = test_pack.read_bytes()
    e = entry_for(data)
    first = RangeInternet(data, chunk=max(1, len(data) // 40), stop_after=len(data) // 2)
    assert window.install_pack(e, opener=first)
    assert first.reached.wait(10)
    assert window.download_status()["downloading"] == ["test"]
    window.handle(Response(cancel_download="other"))   # another pack's name: nothing is stopped
    assert window._downloader.downloading == ["test"]
    window.handle(Response(cancel_download="test"))
    first.gate.set()
    qtbot.waitUntil(lambda: not window._downloader.busy, timeout=10000)
    folder = storage.packs_folder(tmp_path)
    assert not window.session.store.packs and (folder / "test.pack.part").exists()
    status = window.download_status()
    assert status["downloading"] == [] and 0 < status["parts"]["test"]["size"] < len(data)
    rest = RangeInternet(data, chunk=max(1, len(data) // 40))
    assert window.install_pack(e, opener=rest)
    qtbot.waitUntil(lambda: bool(window.session.store.packs), timeout=10000)
    assert rest.asked[0][1] == status["parts"]["test"]["size"]
    assert (folder / "test.pack").read_bytes() == data
