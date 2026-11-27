"""A damaged pack set aside (P4-T7a; NFR-4): said at start, moved out of use, the others carry on.
An incompatible pack is said and skipped but not renamed."""
import shutil

from PySide6.QtWidgets import QApplication

from desktop import storage
from desktop.announcer import RecordingAnnouncer
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore.describe import say
from mapcore.session import MapSession


def make_folder(tmp_path, test_pack, bad: dict[str, bytes | None]):
    """A packs folder with a good pack and the named bad ones: a name with a header change, or damaged bytes."""
    packs = tmp_path / "packs"
    packs.mkdir()
    shutil.copy(test_pack, packs / "a-good.pack")
    raw = test_pack.read_bytes()
    for name, kind in bad.items():
        data = bytearray(raw)
        if kind == "damaged":
            data[20] ^= 0xFF           # inside the header, so its check number is wrong
        elif kind == "newer":
            data[8] = 99               # a format this version does not know
        (packs / name).write_bytes(bytes(data))
    return packs


def spoken(response):
    return [a["text"] for a in response.announcements] if response.announcements and isinstance(
        response.announcements[0], dict) else [str(a) for a in response.announcements]


def test_a_damaged_pack_among_good_ones_is_said_and_left_out(tmp_path, test_pack):
    packs = make_folder(tmp_path, test_pack, {"b-bad.pack": "damaged"})
    s = MapSession(packs=storage.find_packs(tmp_path))
    r = s.start()
    assert len(s.store.packs) == 1
    assert r.packs_damaged == ["b-bad.pack"]
    assert any("b-bad.pack is damaged" in t and "moved out of use" in t for t in spoken(r))
    assert packs.exists()


def test_the_window_renames_it_aside_and_a_second_start_no_longer_sees_it(qtbot, tmp_path, test_pack, monkeypatch):
    monkeypatch.delenv("TOBYMAP_PACKS", raising=False)
    packs = make_folder(tmp_path, test_pack, {"b-bad.pack": "damaged"})
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    QApplication.processEvents()
    assert (packs / "b-bad.pack.damaged").is_file() and not (packs / "b-bad.pack").exists()
    assert [p.name for p in storage.find_packs(tmp_path)] == ["a-good.pack"]
    assert not MapSession(packs=storage.find_packs(tmp_path)).start().packs_damaged


def test_the_set_aside_name_is_free_and_nothing_is_deleted(tmp_path):
    f = tmp_path / "x.pack"
    for n, expected in ((1, "x.pack.damaged"), (2, "x.pack.damaged-2")):
        f.write_bytes(b"d%d" % n)
        assert storage.set_aside_pack(f).name == expected
    assert (tmp_path / "x.pack.damaged").read_bytes() == b"d1"
    assert storage.set_aside_pack(f) is None


def test_an_incompatible_pack_is_said_and_skipped_but_not_renamed(tmp_path, test_pack):
    packs = make_folder(tmp_path, test_pack, {"b-new.pack": "newer"})
    s = MapSession(packs=storage.find_packs(tmp_path))
    r = s.start()
    assert len(s.store.packs) == 1
    assert r.packs_damaged == []
    assert any("b-new.pack needs a newer version" in t for t in spoken(r))
    assert (packs / "b-new.pack").is_file()


def test_when_every_pack_is_damaged_none_installed_is_said(tmp_path, test_pack):
    packs = make_folder(tmp_path, test_pack, {"b-bad.pack": "damaged"})
    (packs / "a-good.pack").unlink()
    r = MapSession(packs=storage.find_packs(tmp_path)).start()
    assert say("packs.none_installed") in spoken(r)
    assert r.packs_damaged == ["b-bad.pack"]
