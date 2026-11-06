"""The earcons in the web version (P2-T8; SON-6, SON-7, SON-8, DP123), in Chromium and Firefox.

Every earcon plays with no set-up. Your own file is chosen with Choose file, kept in the
browser's storage, and played from then on; Use the default goes back. A file that is not a
WAV sound is refused, shown and said. Each earcon has its own switch.
"""
import io
import json
import wave

import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")


def wav_bytes(frames=2000):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x10" * frames)
    return out.getvalue()


def open_earcons_tab(app):
    app.keyboard.press("Control+,")
    app.wait_for_function("document.getElementById('settings').open")
    app.click("#settings-tab-earcons")


def ok(app):
    app.click("#settings-ok")
    app.wait_for_function("!document.getElementById('settings').open")


def blocked(app):
    """Turning in north-fixed is blocked (NAV-12): the blocked earcon, nothing said."""
    app.focus("#map")
    count = app.evaluate("window.tobymap.earcons.length")
    app.keyboard.press("Shift+ArrowLeft")
    app.wait_for_timeout(400)
    return app.evaluate(f"window.tobymap.earcons.slice({count})")


def test_every_earcon_has_a_switch_and_your_own_file(page, site_url):
    app = open_app(page, site_url)
    open_earcons_tab(app)
    fields = app.evaluate("""[...document.querySelectorAll('#settings-page-earcons [data-field]')]
        .map(el => el.dataset.field)""")
    assert fields[0] == "earcon_volume"
    assert "earcon_on_tick" in fields and "earcon_tick" in fields and "earcon_on_crossed_added" in fields
    assert app.get_attribute("#settings-choose-tick", "aria-label") == "Choose file for Tick"
    assert app.get_attribute("#settings-default-tick", "aria-label") == "Use the default for Tick"
    assert app.get_attribute("#settings input[data-field=earcon_tick]", "placeholder") == "The default sound"
    app.click("#settings-cancel")


def test_your_own_file_is_kept_in_the_browser_and_played_and_the_default_comes_back(page, site_url):
    app = open_app(page, site_url)
    assert blocked(app) == ["blocked"]
    assert app.evaluate("window.tobymap.heard.at(-1)") == {"event": "blocked", "own": False}
    open_earcons_tab(app)
    app.set_input_files("#settings-file-blocked", files=[{"name": "my bump.wav", "mimeType": "audio/wav",
                                                           "buffer": wav_bytes()}])
    app.wait_for_function("document.querySelector('#settings input[data-field=earcon_blocked]').value === 'my bump.wav'")
    ok(app)
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))
    assert stored["settings"]["values"]["earcon_blocked"] == "my bump.wav"
    assert blocked(app) == ["blocked"]
    app.wait_for_function("window.tobymap.heard.at(-1).own === true")
    app.reload()                                        # kept in the browser between visits
    app.wait_for_function("window.tobymap && window.tobymap.ready", timeout=120_000)
    assert blocked(app) == ["blocked"]
    app.wait_for_function("window.tobymap.heard.length && window.tobymap.heard.at(-1).own === true")
    open_earcons_tab(app)
    app.click("#settings-default-blocked")
    ok(app)
    assert blocked(app) == ["blocked"]
    app.wait_for_function("window.tobymap.heard.at(-1).own === false")
    stored = json.loads(app.evaluate("localStorage.getItem('tobymap')"))
    assert stored["settings"]["values"]["earcon_blocked"] == ""


def test_a_file_that_is_not_a_wav_sound_is_refused_and_said(page, site_url):
    app = open_app(page, site_url)
    open_earcons_tab(app)
    app.set_input_files("#settings-file-tick", files=[{"name": "notes.wav", "mimeType": "audio/wav",
                                                        "buffer": b"not a sound at all"}])
    message = "notes.wav could not be read as a WAV sound file, so the sound is not changed."
    app.wait_for_function(f"document.getElementById('settings-file-message-tick').textContent === {json.dumps(message)}")
    assert app.input_value("#settings input[data-field=earcon_tick]") == ""
    assert app.evaluate("window.tobymap.announcements.at(-1).text") == message
    app.click("#settings-cancel")


def test_an_own_file_missing_from_the_browser_falls_back_and_is_said_once(page, site_url):
    app = open_app(page, site_url, values={"earcon_blocked": "gone.wav"})
    assert blocked(app) == ["blocked"]
    assert blocked(app) == ["blocked"]
    app.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('could not be played'))")
    app.wait_for_timeout(300)
    told = [t for t in app.evaluate("window.tobymap.announcements.map(a => a.text)") if "could not be played" in t]
    assert told == ["Your own sound file for Blocked could not be played, so the default sound is used."]
    assert app.evaluate("window.tobymap.heard.filter(h => h.event === 'blocked').map(h => h.own)") == [False, False]


def test_an_earcon_switched_off_is_silent_and_the_others_still_play(page, site_url):
    app = open_app(page, site_url)
    open_earcons_tab(app)
    app.uncheck("#settings input[data-field=earcon_on_blocked]")
    ok(app)
    assert blocked(app) == []
    app.evaluate("document.querySelector('[data-command=\"help.earcons\"]').click()")
    app.wait_for_function("document.activeElement.id === 'sounds-list'")
    app.click("#sounds-play")                           # The sounds in Help still plays it
    app.wait_for_function("window.tobymap.earcons.length >= 1")
    app.click("#dialog-close")


def test_the_earcon_volume_reaches_the_sound(page, site_url):
    app = open_app(page, site_url, values={"earcon_volume": 25})
    gains = app.evaluate("""async () => {
        const sounds = await import(new URL('./js/sounds.js', location.href).href);
        const ctx = sounds.audio();
        const made = [];
        const real = ctx.createGain.bind(ctx);
        ctx.createGain = () => { const g = real(); made.push(g); return g; };
        await sounds.play({event: 'tick', custom: null, default: 'click.wav', gain: 0.25});
        ctx.createGain = real;
        return made.map(g => g.gain.value);
    }""")
    assert gains == [0.25]
