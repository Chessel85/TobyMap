"""The earcons on the desktop (P2-T8; SON-6, SON-7, SON-8): your own file chosen in the Earcons
tab, a file that cannot be played refused or falling back to the default, said once, and the
earcon volume reaching the player. No sound device is opened."""
import wave

import pytest
from PySide6.QtWidgets import QApplication

from desktop.announcer import RecordingAnnouncer
from desktop.dialogs import SettingsDialog, SoundFileField
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


def test_a_readable_wav_is_known_from_one_that_is_not(tmp_path):
    assert readable_wav(a_wav(tmp_path / "mine.wav"))
    (tmp_path / "text.wav").write_text("not a sound")
    assert not readable_wav(tmp_path / "text.wav")
    assert not readable_wav(a_wav(tmp_path / "empty.wav", frames=0))
    assert not readable_wav(tmp_path / "missing.wav")


def test_the_earcons_tab_has_a_switch_and_an_own_file_for_each(window):
    dialog = open_settings(window)
    field = dialog.controls["earcon_tick"]
    assert isinstance(field, SoundFileField)
    assert field.edit.accessibleName() == "Tick: your own sound file"
    assert field.choose_button.accessibleName() == "Choose file for Tick"
    assert field.default_button.accessibleName() == "Use the default for Tick"
    assert dialog.controls["earcon_on_tick"].isChecked()
    dialog.cancel_button.click()


def test_choosing_your_own_file_keeps_it_and_use_the_default_clears_it(window, tmp_path):
    mine = a_wav(tmp_path / "mine.wav")
    dialog = open_settings(window)
    field = dialog.controls["earcon_blocked"]
    field._choose_dialog = lambda: str(mine)
    field.choose()
    dialog.ok_button.click()
    QApplication.processEvents()
    assert window.session.settings["earcon_blocked"] == str(mine)
    assert window.session.earcon_file("blocked")["custom"] == str(mine)
    dialog = open_settings(window)
    dialog.controls["earcon_blocked"].use_default()
    dialog.ok_button.click()
    QApplication.processEvents()
    assert window.session.settings["earcon_blocked"] == ""


def test_a_file_that_cannot_be_played_is_refused_and_you_are_told(window, tmp_path):
    (tmp_path / "notes.wav").write_text("not a sound")
    dialog = open_settings(window)
    field = dialog.controls["earcon_tick"]
    field._choose_dialog = lambda: str(tmp_path / "notes.wav")
    field.choose()
    assert field.text() == ""
    assert window.announcer.texts[-1] == "notes.wav could not be read as a WAV sound file, so the sound is not changed."
    dialog.cancel_button.click()


def test_switching_an_earcon_off_in_the_dialog_silences_it(window):
    dialog = open_settings(window)
    dialog.controls["earcon_on_blocked"].setChecked(False)
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


def test_the_earcon_volume_reaches_the_player(window):
    window.session.run("settings.set", field="earcon_volume", value=30)
    window.session.back_places.clear()
    window.dispatch("history.back")
    assert window.sounds.gains[-1] == pytest.approx(0.3)
