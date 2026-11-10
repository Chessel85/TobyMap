"""The earcons on the desktop (P2-T8, P2-T17p; SON-6, SON-7, SON-8, DP163): the Earcons tab's one
list with a check box for each earcon, and one set of controls for the earcon chosen in it; your
own file, a file that cannot be played refused or falling back to the default, said once, and each
earcon's own volume reaching the player. No sound device is opened."""
import wave
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import EarconsPage, SettingsDialog, SoundFileField
from desktop.sounds import RecordingSounds, readable_wav
from desktop.window import MainWindow
from mapcore.session import MapSession


@pytest.fixture
def window(qtbot, test_pack, tmp_path):
    session = MapSession(packs=[test_pack], saved_state={"lat": 51.2, "lon": 1.2, "zoom_m": 25000, "step_m": 25000})
    w = MainWindow(session=session, announcer=RecordingAnnouncer(), sounds=RecordingSounds(), data_folder=tmp_path)
    qtbot.addWidget(w)
    w.show()
    yield w
    w.close()


def a_wav(path, frames=100):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x01\x00" * frames)
    return path


def open_settings(window):
    window.dispatch("settings.open")
    QApplication.processEvents()
    (dialog,) = [d for d in window.findChildren(SettingsDialog) if d.isVisible()]
    return dialog


def earcons_page(dialog) -> EarconsPage:
    dialog.tabs.setCurrentWidget(next(dialog.tabs.widget(i) for i in range(dialog.tabs.count())
                                      if dialog.tabs.widget(i).isAncestorOf(dialog.earcons)))
    return dialog.earcons


def choose_earcon(page, label):
    page.list.setCurrentRow(next(i for i, r in enumerate(page.rows) if r["label"] == label))


def test_a_readable_wav_is_known_from_one_that_is_not(tmp_path):
    assert readable_wav(a_wav(tmp_path / "mine.wav"))
    (tmp_path / "text.wav").write_text("not a sound")
    assert not readable_wav(tmp_path / "text.wav")
    assert not readable_wav(a_wav(tmp_path / "empty.wav", frames=0))
    assert not readable_wav(tmp_path / "missing.wav")


def test_the_earcons_tab_is_one_list_with_a_check_box_for_each(window):
    """P2-T17p, desktop checklist 10.6: one list of every earcon, each with a check box, and no
    volume for all of them together (DP163). The beacon is in the Sound tab."""
    dialog = open_settings(window)
    page = earcons_page(dialog)
    names = [page.list.item(i).text() for i in range(page.list.count())]
    assert names[:3] == ["Tick", "Blocked", "Something added"] and "Orientation beacon" not in names
    assert page.list.accessibleName() == "Earcons"
    assert all(page.list.item(i).checkState() == Qt.CheckState.Checked for i in range(page.list.count()))
    assert page.list.currentRow() == 0
    assert "earcon_volume" not in dialog.controls
    dialog.cancel_button.click()


def test_the_controls_below_the_list_are_for_the_earcon_chosen_in_it(window):
    dialog = open_settings(window)
    page = earcons_page(dialog)
    assert page.volume.accessibleName() == "Tick: volume, in percent" and page.volume.value() == 100
    assert page.volume_label.text() == "Tick: volume, in percent"
    field = page.file
    assert isinstance(field, SoundFileField)
    assert field.edit.accessibleName() == "Tick: your own sound file"
    assert field.choose_button.accessibleName() == "Browse"
    assert field.default_button.accessibleName() == "Use the default for Tick"
    choose_earcon(page, "Blocked")
    assert page.volume.accessibleName() == "Blocked: volume, in percent"
    assert field.edit.accessibleName() == "Blocked: your own sound file"
    assert field.choose_button.accessibleName() == "Browse"
    assert field.default_button.accessibleName() == "Use the default for Blocked"
    dialog.cancel_button.click()


def test_each_earcon_keeps_its_own_volume_and_file_and_ok_saves_them(window, tmp_path):
    mine = a_wav(tmp_path / "mine.wav")
    dialog = open_settings(window)
    page = earcons_page(dialog)
    choose_earcon(page, "Blocked")
    page.volume.setValue(40)
    page.file._choose_dialog = lambda: str(mine)
    page.file.choose()
    choose_earcon(page, "Tick")                       # the tick is as it was
    assert page.volume.value() == 100 and page.file.text() == ""
    choose_earcon(page, "Blocked")                    # and the blocked sound keeps its own
    assert page.volume.value() == 40 and page.file.text() == str(mine)
    dialog.ok_button.click()
    QApplication.processEvents()
    s = window.session.settings
    assert s["earcon_volume_blocked"] == 40 and s["earcon_blocked"] == str(mine)
    assert s["earcon_volume_tick"] == 100
    assert window.session.earcon_file("blocked")["custom"] == str(mine)
    dialog = open_settings(window)
    page = earcons_page(dialog)
    choose_earcon(page, "Blocked")
    assert page.volume.value() == 40
    page.file.use_default()
    dialog.ok_button.click()
    QApplication.processEvents()
    assert window.session.settings["earcon_blocked"] == ""


def test_cancel_keeps_nothing_changed_in_the_tab(window):
    dialog = open_settings(window)
    page = earcons_page(dialog)
    page.volume.setValue(10)
    page.list.item(0).setCheckState(Qt.CheckState.Unchecked)
    dialog.cancel_button.click()
    QApplication.processEvents()
    assert window.session.settings["earcon_volume_tick"] == 100 and window.session.settings["earcon_on_tick"]


def test_space_in_the_list_ticks_and_enter_presses_ok(window, qtbot):
    dialog = open_settings(window)
    page = earcons_page(dialog)
    choose_earcon(page, "Blocked")
    page.list.setFocus()
    qtbot.keyClick(page.list, Qt.Key.Key_Space)
    assert page.list.currentItem().checkState() == Qt.CheckState.Unchecked
    assert page.list.currentRow() == 1                 # Space did not move along the list
    qtbot.keyClick(page.list, Qt.Key.Key_Return)
    QApplication.processEvents()
    assert not dialog.isVisible()
    assert window.session.settings["earcon_on_blocked"] is False
    assert window.session.settings["earcon_on_tick"] is True


def test_the_beacons_own_file_is_in_the_sound_tab(window):
    dialog = open_settings(window)
    field = dialog.controls["earcon_beacon"]
    assert isinstance(field, SoundFileField)
    assert field.edit.accessibleName() == "Orientation beacon: your own sound file"
    assert field.choose_button.accessibleName() == "Browse"
    dialog.cancel_button.click()


def test_a_file_that_cannot_be_played_is_refused_and_you_are_told(window, tmp_path):
    (tmp_path / "notes.wav").write_text("not a sound")
    dialog = open_settings(window)
    field = earcons_page(dialog).file
    field._choose_dialog = lambda: str(tmp_path / "notes.wav")
    field.choose()
    assert field.text() == ""
    assert field.message.text() == "notes.wav could not be read as a WAV sound file, so the sound is not changed."
    dialog.cancel_button.click()


@pytest.mark.parametrize("renamed", [False, True], ids=["a .py file", "a .py file renamed to .wav"])
def test_the_message_stays_on_screen_and_takes_the_focus(window, tmp_path, qtbot, renamed):
    """PO note on checklist 14.5: no message was heard. Spoken alone, NVDA read the focus coming
    back from the file dialog over it. Now it stays next to the field and takes the focus."""
    import shutil

    source = Path(__file__).resolve().parents[2] / "desktop" / "sounds.py"
    chosen = shutil.copy(source, tmp_path / "sounds.wav") if renamed else source
    dialog = open_settings(window)
    field = earcons_page(dialog).file
    assert field.message.isHidden()
    field._choose_dialog = lambda: str(chosen)
    field.choose()
    said = f"{Path(chosen).name} could not be read as a WAV sound file, so the sound is not changed."
    assert field.text() == "" and field.message.text() == said and not field.message.isHidden()
    assert field.message.accessibleName() == said
    qtbot.waitUntil(lambda: QApplication.focusWidget() is field.message, timeout=2000)
    field.use_default()                          # the message goes when the sound is changed again
    assert field.message.isHidden()
    dialog.cancel_button.click()


def test_the_message_goes_when_another_earcon_is_chosen(window, tmp_path):
    (tmp_path / "notes.wav").write_text("not a sound")
    dialog = open_settings(window)
    page = earcons_page(dialog)
    page.file._choose_dialog = lambda: str(tmp_path / "notes.wav")
    page.file.choose()
    assert not page.file.message.isHidden()
    choose_earcon(page, "Blocked")
    assert page.file.message.isHidden()
    dialog.cancel_button.click()


def test_switching_an_earcon_off_in_the_dialog_silences_it(window):
    dialog = open_settings(window)
    page = earcons_page(dialog)
    page.list.item(1).setCheckState(Qt.CheckState.Unchecked)    # Blocked
    dialog.ok_button.click()
    QApplication.processEvents()
    window.sounds.played.clear()
    window.session.back_places.clear()
    window.dispatch("history.back")   # nowhere to go back to: blocked
    assert window.sounds.played == []


def test_an_own_file_that_fails_falls_back_and_is_said_once(window):
    window.session.run("settings.set", field="earcon_blocked", value="C:/gone/bump.wav")
    window.sounds.failed.append("C:/gone/bump.wav")
    window.session.back_places.clear()
    for _ in range(3):
        window.dispatch("history.back")
    told = [t for t in window.announcer.texts if "could not be played" in t]
    assert told == ["Your own sound file for Blocked could not be played, so the default sound is used."]
    assert window.sounds.played.count("blocked") == 3


def test_an_earcons_own_volume_reaches_the_player(window):
    window.session.run("settings.set", field="earcon_volume_blocked", value=30)
    window.session.back_places.clear()
    window.dispatch("history.back")
    assert window.sounds.gains[-1] == pytest.approx(0.3)
