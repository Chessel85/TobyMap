"""The bookmarks file on the desktop (P4-T8a; USR-1, USR-5, DP209, DP219, architecture 6.11): beside
settings.json, written safely, set aside when damaged, and left alone by Reset all settings."""
import os

import pytest
from PySide6.QtWidgets import QApplication

from desktop import storage
from desktop.announcer import RecordingAnnouncer
from desktop.sounds import RecordingSounds
from desktop.window import MainWindow
from mapcore import bookmarks as bm
from mapcore.describe import say
from mapcore.session import MapSession, Response

KENT = {"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000}


def some_text():
    b = bm.Bookmarks()
    b.add(0, "Rome", 41.9, 12.5, feature="Rome", note="Visited 2019")
    b.add(b.new_list("Castles"), "Bodiam", 51.0023, 0.5436, feature="Bodiam Castle")
    return b.to_text()


def make_window(qtbot, tmp_path, session):
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    QApplication.processEvents()
    return w


# The file, written safely -----------------------------------------------------------------------

def test_the_file_is_beside_the_settings_and_none_at_first(tmp_path):
    assert storage.bookmarks_file(tmp_path) == tmp_path / "bookmarks.geojson"
    assert storage.bookmarks_file(tmp_path).parent == storage.settings_file(tmp_path).parent
    assert storage.load_bookmarks(tmp_path) is None


def test_it_is_written_whole_and_read_back_exactly(tmp_path):
    text = some_text()
    storage.save_bookmarks(text, tmp_path)
    assert storage.load_bookmarks(tmp_path) == text
    assert (tmp_path / "bookmarks.geojson").read_bytes() == text.encode("utf-8")   # no CR added on Windows
    assert [p.name for p in tmp_path.iterdir()] == ["bookmarks.geojson"]          # no temporary file left


def test_a_crash_while_writing_leaves_the_old_file_whole(tmp_path, monkeypatch):
    storage.save_bookmarks(some_text(), tmp_path)

    def crash(_fd):
        raise OSError("the power went off")

    monkeypatch.setattr(os, "fsync", crash)
    with pytest.raises(OSError):
        storage.save_bookmarks(bm.Bookmarks().to_text(), tmp_path)
    assert storage.load_bookmarks(tmp_path) == some_text()


def test_a_damaged_file_is_set_aside_with_a_free_name(tmp_path):
    for n, expected in ((1, "bookmarks-damaged.geojson"), (2, "bookmarks-damaged-2.geojson")):
        (tmp_path / "bookmarks.geojson").write_text(f"damaged {n}", encoding="utf-8")
        aside = storage.set_aside_bookmarks(tmp_path)
        assert aside.name == expected and aside.read_text(encoding="utf-8") == f"damaged {n}"
    assert not (tmp_path / "bookmarks.geojson").exists()
    assert storage.set_aside_bookmarks(tmp_path) is None


# The window -------------------------------------------------------------------------------------

def test_the_window_reads_the_file_at_start(qtbot, test_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("TOBYMAP_PACKS", str(test_pack))
    storage.save_bookmarks(some_text(), tmp_path)
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    assert [l.name for l in w.session.bookmarks.lists] == ["Bookmarks", "Castles"]
    assert storage.load_bookmarks(tmp_path) == some_text()   # read, not written again


def test_a_damaged_file_is_kept_aside_said_and_a_new_list_started(qtbot, test_pack, tmp_path, monkeypatch):
    monkeypatch.setenv("TOBYMAP_PACKS", str(test_pack))
    (tmp_path / "bookmarks.geojson").write_bytes(b'{"type": "FeatureCollection", "feat\xff')
    w = MainWindow(announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    assert (tmp_path / "bookmarks-damaged.geojson").read_bytes() == b'{"type": "FeatureCollection", "feat\xff'
    assert not (tmp_path / "bookmarks.geojson").exists()
    assert [l.name for l in w.session.bookmarks.lists] == ["Bookmarks"]
    assert w.map.accessibleName().endswith(say("bookmarks.damaged"))


def test_a_change_is_written_to_the_file(qtbot, test_pack, tmp_path):
    w = make_window(qtbot, tmp_path, MapSession(packs=[test_pack], saved_state=dict(KENT)))
    w.session.bookmarks.add(0, "Here", 51.2, 1.2, feature="Kent")
    w.handle(w.session.bookmarks_changed(Response()))
    assert storage.load_bookmarks(tmp_path) == w.session.bookmarks.to_text()


def test_reset_all_settings_does_not_touch_the_bookmarks_file(qtbot, test_pack, tmp_path):
    """DP209: Reset all settings writes the new installation's settings, and leaves the bookmarks."""
    storage.save_bookmarks(some_text(), tmp_path)
    before = (tmp_path / "bookmarks.geojson").stat().st_mtime_ns
    session = MapSession(packs=[test_pack], saved_state=dict(KENT), settings={"values": {"units": "imperial"}, "keys": {}},
                         bookmarks=storage.load_bookmarks(tmp_path))
    w = make_window(qtbot, tmp_path, session)
    w.handle(w.session.run("settings.reset_confirm"))
    assert storage.load(tmp_path)["settings"]["values"].get("units", "metric") == "metric"   # the settings were reset
    assert storage.load_bookmarks(tmp_path) == some_text()
    assert (tmp_path / "bookmarks.geojson").stat().st_mtime_ns == before
    assert w.session.bookmarks.to_text() == some_text()
