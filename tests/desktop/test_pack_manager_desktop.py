"""The pack manager on the desktop (P4-T6d; PCK-2, PCK-5, ACC-7): P opens it, the catalogue is read on a thread, and
Install, Update and Remove work on the packs folder. The internet is a stand-in: no test opens a connection (rule 5)."""
import hashlib
import io
import json
import shutil
import sys

import pytest
from PySide6.QtWidgets import QApplication

from desktop import storage
from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import ConfirmBox, PackManagerDialog
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.packs.pack import Pack


class Internet:
    """The stand-in: each address's bytes, the catalogue among them. An address not known is a lost connection."""

    def __init__(self, files: dict):
        self.files = files
        self.asked: list[str] = []

    def __call__(self, url):
        self.asked.append(url)
        if url not in self.files:
            raise OSError("no connection")
        return io.BytesIO(self.files[url])


def catalogue(data: bytes, name: str, **change) -> bytes:
    entry = {"name": name, "title": "Test map", "version": "2026.11.1", "date": "2026-11-27", "size": len(data),
             "sha256": hashlib.sha256(data).hexdigest(), "url_desktop": f"https://example.org/{name}.pack",
             "url_web": f"https://example.org/w/{name}.pack", "app_versions": {"from": "0.1.0"}}
    entry.update(change)
    return json.dumps({"format": 1, "packs": [entry]}).encode()


@pytest.fixture
def pack_version(test_pack):
    pack = Pack(test_pack)
    try:
        return pack.manifest["version"]
    finally:
        pack.close()


@pytest.fixture
def pack_name(test_pack):
    pack = Pack(test_pack)
    try:
        return pack.manifest["name"]
    finally:
        pack.close()


def make_window(qtbot, tmp_path, monkeypatch, internet, installed=None):
    monkeypatch.delenv("TOBYMAP_PACKS", raising=False)
    if installed is not None:
        folder = storage.packs_folder(tmp_path)
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(installed, folder / "test.pack")
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.pack_opener = internet
    w.show()
    qtbot.waitExposed(w)
    w.map.setFocus()
    QApplication.processEvents()
    return w


def open_manager(window, qtbot) -> PackManagerDialog:
    window.dispatch("packs.manager_open")
    QApplication.processEvents()
    (box,) = [d for d in window.findChildren(PackManagerDialog) if d.isVisible()]
    qtbot.waitUntil(lambda: any(i["entry"] for i in box.items) or box.note.text() != "Reading the list of packs.",
                    timeout=10000)
    return box


def test_p_opens_the_pack_manager_with_each_packs_name_size_date_and_state(qtbot, tmp_path, monkeypatch, test_pack,
                                                                           pack_name):
    data = test_pack.read_bytes()
    internet = Internet({})
    w = make_window(qtbot, tmp_path, monkeypatch, internet)
    internet.files = {w.session.defaults["packs"]["catalogue_url_desktop"]: catalogue(data, pack_name)}
    assert w.session.registry()  # the key is in the registry: P is the pack manager
    assert w.session.command_for_key("P", "map").name == "packs.manager_open"
    box = open_manager(w, qtbot)
    assert len(internet.asked) == 1   # the catalogue, read once
    (item,) = box.items
    megabytes = -(-len(data) // 1_000_000)
    assert box.list.item(0).text() == f"Test map, {megabytes} megabytes, 2026-11-27, not installed"
    assert box.install_button.available and not box.update_button.available and not box.remove_button.available
    assert box.close_button.text() == "Close"
    box.close_button.click()
    assert not box.isVisible()


def test_install_puts_the_pack_in_the_folder_and_opens_it(qtbot, tmp_path, monkeypatch, test_pack, pack_name,
                                                          pack_version):
    data = test_pack.read_bytes()
    url = f"https://example.org/{pack_name}.pack"
    internet = Internet({})
    w = make_window(qtbot, tmp_path, monkeypatch, internet)
    internet.files = {w.session.defaults["packs"]["catalogue_url_desktop"]: catalogue(data, pack_name, version=pack_version),
                      url: data}
    box = open_manager(w, qtbot)
    assert not w.session.store.packs
    box.install_button.click()
    qtbot.waitUntil(lambda: bool(w.session.store.packs), timeout=10000)
    assert (storage.packs_folder(tmp_path) / f"{pack_name}.pack").read_bytes() == data
    qtbot.waitUntil(lambda: box.items and box.items[0]["state"] == "installed", timeout=10000)
    assert box.remove_button.available and not box.install_button.available
    assert box.list.item(0).text().endswith("installed")


def test_an_incompatible_pack_is_refused_with_a_clear_message(qtbot, tmp_path, monkeypatch, test_pack, pack_name):
    data = test_pack.read_bytes()
    internet = Internet({})
    w = make_window(qtbot, tmp_path, monkeypatch, internet)
    internet.files = {w.session.defaults["packs"]["catalogue_url_desktop"]:
                      catalogue(data, pack_name, app_versions={"from": "99.0.0"})}
    lines = []
    original = w.handle
    w.handle = lambda r, *a, **k: (lines.extend(x["text"] for x in r.announcements), original(r, *a, **k))[1]
    box = open_manager(w, qtbot)
    box.install_button.click()
    assert lines[-1].startswith("Test map needs TobyMap 99.0.0 or later") and "was not downloaded" in lines[-1]
    assert not w.session.store.packs
    assert not list(storage.packs_folder(tmp_path).glob("*.pack*"))
    assert len(internet.asked) == 1   # only the catalogue was read


def test_an_unreadable_catalogue_is_said_and_the_installed_packs_are_shown(qtbot, tmp_path, monkeypatch, test_pack):
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    lines = []
    original = w.handle
    w.handle = lambda r, *a, **k: (lines.extend(x["text"] for x in r.announcements), original(r, *a, **k))[1]
    box = open_manager(w, qtbot)
    qtbot.waitUntil(lambda: bool(lines), timeout=10000)
    assert "could not be read" in lines[-1]
    assert box.list.count() == 1 and box.remove_button.available


def test_remove_asks_then_deletes_the_file(qtbot, tmp_path, monkeypatch, test_pack, pack_name):
    data = test_pack.read_bytes()
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    w.pack_opener = Internet({w.session.defaults["packs"]["catalogue_url_desktop"]: catalogue(data, pack_name)})
    box = open_manager(w, qtbot)
    qtbot.waitUntil(lambda: any(i["entry"] for i in box.items), timeout=10000)
    file = storage.packs_folder(tmp_path) / "test.pack"
    assert w.session.store.packs and file.exists()
    box.remove_button.click()
    QApplication.processEvents()
    ask = box.child_box
    assert isinstance(ask, ConfirmBox) and ask.cancel_button is ask.defaultButton()
    assert file.exists() and w.session.store.packs   # asking changes nothing
    ask.ok_button.click()
    qtbot.waitUntil(lambda: not w.session.store.packs, timeout=10000)
    assert not file.exists()
    assert box.items[0]["state"] == "not installed" and not box.remove_button.available


def test_update_closes_the_pack_in_use_and_replaces_it(qtbot, tmp_path, monkeypatch, test_pack, pack_name):
    data = test_pack.read_bytes()
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    url = f"https://example.org/{pack_name}.pack"
    w.pack_opener = Internet({w.session.defaults["packs"]["catalogue_url_desktop"]:
                              catalogue(data, pack_name, version="9999.1.1"), url: data})
    old = w.session.store.packs[0]
    box = open_manager(w, qtbot)
    qtbot.waitUntil(lambda: any(i["entry"] for i in box.items), timeout=10000)
    assert box.update_button.available and box.items[0]["state"] == "update available"
    box.update_button.click()
    qtbot.waitUntil(lambda: w.session.store.packs and w.session.store.packs[0] is not old, timeout=10000)
    folder = storage.packs_folder(tmp_path)
    assert [p.name for p in folder.iterdir()] == ["test.pack"]
    assert (folder / "test.pack").read_bytes() == data
    assert [p.name for p in w.session.store.packs] == ["test.pack"]


def test_the_first_start_with_no_world_pack_offers_to_download_it(qtbot, tmp_path, monkeypatch, test_pack):
    data = test_pack.read_bytes()
    monkeypatch.delenv("TOBYMAP_PACKS", raising=False)
    internet = Internet({})
    from desktop.window import MainWindow as Window
    w = Window(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path, offer_world=False)
    qtbot.addWidget(w)
    w.pack_opener = internet
    internet.files = {w.session.defaults["packs"]["catalogue_url_desktop"]: catalogue(data, "world", size=len(data))}
    w.offer_world = True
    w._offer_world(w.session.start().world_offer)
    qtbot.waitUntil(lambda: any(isinstance(d, ConfirmBox) for d in w._dialogs), timeout=10000)
    (ask,) = [d for d in w._dialogs if isinstance(d, ConfirmBox)]
    assert ask.windowTitle() == ("" if sys.platform == "darwin" else "Download the world pack")   # a Mac message box has no title
    assert "world pack" in ask.text()
    assert ask.ok_button.text() == "Download" and ask.cancel_button.text() == "Not now"
    internet.files["https://example.org/world.pack"] = data
    ask.ok_button.click()
    qtbot.waitUntil(lambda: bool(w.session.store.packs), timeout=10000)
    assert (storage.packs_folder(tmp_path) / "world.pack").read_bytes() == data


def test_a_newer_pack_is_offered_at_start_and_update_replaces_the_pack(qtbot, tmp_path, monkeypatch, test_pack,
                                                                        pack_name):
    data = test_pack.read_bytes()
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    w.offer_world = True
    w.pack_opener = Internet({w.session.defaults["packs"]["catalogue_url_desktop"]:
                              catalogue(data, pack_name, version="9999.1.1"),
                              f"https://example.org/{pack_name}.pack": data})
    old = w.session.store.packs[0]
    w._offer_update(w.session.start().update_check)
    qtbot.waitUntil(lambda: any(isinstance(d, ConfirmBox) for d in w._dialogs), timeout=10000)
    (ask,) = [d for d in w._dialogs if isinstance(d, ConfirmBox)]
    assert ask.ok_button.text() == "Update" and ask.cancel_button.text() == "Not now"
    assert "version 9999.1.1" in ask.text()
    ask.ok_button.click()
    qtbot.waitUntil(lambda: w.session.store.packs and w.session.store.packs[0] is not old, timeout=10000)
    folder = storage.packs_folder(tmp_path)
    assert [p.name for p in folder.iterdir()] == ["test.pack"]


def test_an_unreadable_catalogue_at_start_says_nothing(qtbot, tmp_path, monkeypatch, test_pack):
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    w.offer_world = True
    lines = []
    original = w.handle
    w.handle = lambda r, *a, **k: (lines.extend(x["text"] for x in r.announcements), original(r, *a, **k))[1]
    w._offer_update(w.session.start().update_check)
    w._catalogues.wait(10)
    qtbot.wait(300)
    assert not lines and not [d for d in w._dialogs if isinstance(d, ConfirmBox)]


def test_cancel_download_keeps_the_part_and_install_carries_on(qtbot, tmp_path, monkeypatch, test_pack, pack_name,
                                                               pack_version):
    """P4-T6f: Cancel download is available only while the pack downloads; the line then says how much is held, and
    Install asks only for the rest."""
    import threading

    data = test_pack.read_bytes()
    url = f"https://example.org/{pack_name}.pack"
    gate, reached = threading.Event(), threading.Event()
    step = max(1, len(data) // 20)

    class Slow(io.BytesIO):
        status = 200

        def read(self, n=-1):
            if self.tell() >= len(data) // 2:
                reached.set()
                gate.wait(10)
            return super().read(min(n, step))

    asked = []
    w = make_window(qtbot, tmp_path, monkeypatch, None)
    listing = w.session.defaults["packs"]["catalogue_url_desktop"]

    def internet(u, start=0):
        asked.append((u, start))
        if u == url:
            if start:
                rest = io.BytesIO(data[start:])
                rest.status = 206
                return rest
            return Slow(data)
        if u == listing:
            return io.BytesIO(catalogue(data, pack_name, version=pack_version))
        raise OSError("no connection")

    w.pack_opener = internet
    box = open_manager(w, qtbot)
    assert box.cancel_button.text() == "Cancel download" and not box.cancel_button.available
    box.install_button.click()
    try:   # the window's thread keeps running while it waits, so the queued signals are delivered
        qtbot.waitUntil(reached.is_set, timeout=30000)
    except Exception:
        gate.set()
        raise AssertionError(f"the download never reached half; asked {asked}, said {w.announcer.spoken}")
    qtbot.waitUntil(lambda: box.items[0]["label"].endswith("downloading"), timeout=10000)
    assert box.cancel_button.available and not box.install_button.available
    box.cancel_button.click()
    gate.set()
    qtbot.waitUntil(lambda: "percent downloaded" in box.items[0]["label"], timeout=10000)
    assert box.install_button.available and not box.cancel_button.available
    assert any("is cancelled" in text for text, _p in w.announcer.spoken)
    held = (storage.packs_folder(tmp_path) / f"{pack_name}.pack.part").stat().st_size
    assert 0 < held < len(data)
    box.install_button.click()
    qtbot.waitUntil(lambda: bool(w.session.store.packs), timeout=10000)
    assert asked[-1] == (url, held)
    assert (storage.packs_folder(tmp_path) / f"{pack_name}.pack").read_bytes() == data
    qtbot.waitUntil(lambda: box.items and box.items[0]["state"] == "installed", timeout=10000)


# The packs folder and its free space (P4-T6g) ---------------------------------------------------

def move_setup(qtbot, tmp_path, monkeypatch, test_pack, free=10_000_000_000):
    w = make_window(qtbot, tmp_path, monkeypatch, Internet({}), installed=test_pack)
    old = storage.packs_folder(tmp_path)
    new = tmp_path / "elsewhere" / "packs"
    new.mkdir(parents=True)
    w.free_space = lambda folder: free
    w.folder_chooser = lambda parent, title, start: str(new)
    said_ = []
    original = w.handle
    w.handle = lambda r, *a, **k: (said_.extend(x["text"] for x in r.announcements), original(r, *a, **k))[1]
    return w, old, new, said_


def test_the_pack_manager_says_the_free_space_in_the_packs_folder(qtbot, tmp_path, monkeypatch, test_pack):
    w, old, new, said_ = move_setup(qtbot, tmp_path, monkeypatch, test_pack, free=12_300_000_000)
    box = open_manager(w, qtbot)
    assert box.space.text() == f"Packs folder: {old}. 12.3 gigabytes free."
    assert box.move_button.text() == "Move packs folder"


def test_move_puts_the_packs_in_the_new_folder_and_saves_the_choice(qtbot, tmp_path, monkeypatch, test_pack):
    w, old, new, said_ = move_setup(qtbot, tmp_path, monkeypatch, test_pack)
    (old / "test.pack.part").write_bytes(b"half")
    (old / "test.pack.part.json").write_text("{}")
    (old / "notes.txt").write_text("not ours")
    box = open_manager(w, qtbot)
    box.move_button.click()
    assert sorted(p.name for p in new.iterdir()) == ["test.pack", "test.pack.part", "test.pack.part.json"]
    assert [p.name for p in old.iterdir()] == ["notes.txt"]   # only our files moved
    assert storage.load(tmp_path)["packs_folder"] == str(new)
    assert storage.packs_folder(tmp_path) == new
    assert len(w.session.store.packs) == 1 and w.session.store.packs[0].name == 'test.pack'
    assert said_[-1] == f"The packs are now in {new}."
    assert box.space.text().startswith(f"Packs folder: {new}.")


def test_move_is_refused_when_the_new_folder_has_no_room(qtbot, tmp_path, monkeypatch, test_pack):
    w, old, new, said_ = move_setup(qtbot, tmp_path, monkeypatch, test_pack, free=1000)
    box = open_manager(w, qtbot)
    box.move_button.click()
    assert any("so nothing was moved" in t and "Choose a folder with more room" in t for t in said_)
    assert (old / "test.pack").exists() and not list(new.iterdir())
    assert "packs_folder" not in storage.load(tmp_path)
    assert len(w.session.store.packs) == 1


def test_move_into_the_same_or_an_inner_folder_is_refused(qtbot, tmp_path, monkeypatch, test_pack):
    w, old, new, said_ = move_setup(qtbot, tmp_path, monkeypatch, test_pack)
    assert not w.move_packs_folder(old)
    assert "is the packs folder already" in said_[-1]
    inner = old / "inner"
    assert not w.move_packs_folder(inner)
    assert "is inside the packs folder" in said_[-1]
    assert not inner.exists() and (old / "test.pack").exists()


def test_a_failure_part_way_puts_the_packs_back(qtbot, tmp_path, monkeypatch, test_pack):
    w, old, new, said_ = move_setup(qtbot, tmp_path, monkeypatch, test_pack)
    (old / "test.pack.part").write_bytes(b"half")
    real = shutil.move
    calls = []

    def flaky(src, dst):
        calls.append(src)
        if str(src).endswith(".part") and str(dst).startswith(str(new)):
            raise OSError("disk full")
        return real(src, dst)

    monkeypatch.setattr(storage.shutil, "move", flaky)
    assert not w.move_packs_folder(new)
    assert sorted(p.name for p in old.iterdir()) == ["test.pack", "test.pack.part"]
    assert not list(new.iterdir())
    assert "packs_folder" not in storage.load(tmp_path)
    assert len(w.session.store.packs) == 1 and w.session.store.packs[0].name == 'test.pack'
    assert "back where they were" in said_[-1]
