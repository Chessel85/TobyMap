"""The spatial voice in Chromium and Firefox (P2-T7b, P2-T7c; SON-3, ANN-3, ANN-4, DP105, DP143, NFR-1).

The voice runs in a worker of its own. With the page cross-origin isolated it uses four
threads, else one. On GitHub Pages the helper script makes the page isolated; the page must
still download and read the pack then. Each label is placed with the core's numbers, after
the item's sound. Needs tools/fetch_vendor.py --piper; skipped without it, failed in CI.
"""
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from tests.web.test_shell_page import open_app  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STATION_WEST = {"lat": 50.9074977, "lon": -1.4142289 - 0.03, "zoom_m": 5000, "step_m": 1000}


@pytest.fixture(autouse=True)
def needs_the_voice():
    if not (ROOT / "web" / "vendor" / "piper" / "voice" / "en_GB-alba-medium.onnx").is_file():
        message = "The web voice is not in web/vendor/piper. Run: python tools/fetch_vendor.py --piper"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(message)


def voice_ready(page):
    page.wait_for_function("window.tobymap.voiceState() !== 'loading'", timeout=120_000)
    assert page.evaluate("window.tobymap.voiceState()") == "ready"
    return page.evaluate("({...window.tobymap.voiceInfo})")


def on_station(page):
    """Focus Southampton Central in Nearby and press Space."""
    page.keyboard.press("F3")
    page.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    page.evaluate("""() => {
        const item = [...document.querySelectorAll('#tree [role=treeitem]')]
            .find((el) => el.firstChild.textContent.startsWith('Southampton Central'));
        item.closest('[aria-expanded]').setAttribute('aria-expanded', 'true');
        item.focus();
    }""")
    page.wait_for_timeout(200)
    count = page.evaluate("window.tobymap.labels.length")
    page.keyboard.press("Space")
    page.wait_for_function(f"window.tobymap.labels.length > {count}", timeout=30_000)
    return page.evaluate("window.tobymap.labels[window.tobymap.labels.length - 1]")


def test_with_four_threads_a_label_is_placed_with_the_items_sound(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST)
    info = voice_ready(app)
    assert info["isolated"] and info["threads"] == min(4, app.evaluate("navigator.hardwareConcurrency"))
    label = on_station(app)
    assert label["text"].startswith("Southampton Central, ")
    assert 80 < label["relative_deg"] < 100 and label["pitch"] == 1
    placed = app.evaluate("window.tobymap.placed.slice(-2)")
    assert [p["sound"] for p in placed] == ["item_direction", "voice"]
    assert placed[0]["pan"] == placed[1]["pan"], "the label comes from the item's place"
    made = sorted([label["made_ms"]] + [on_station(app)["made_ms"] for _ in range(4)])
    print(f"\n{app.context.browser.browser_type.name}, {info['threads']} threads: voice ready in "
          f"{info['load_ms']} ms; each label made in a median of {made[2]} ms, longest {made[-1]} ms; "
          f"the first heard {label['ms']} ms after asking, after the item's sound")


def test_with_one_thread_the_voice_still_works(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST, query="?threads=1")
    info = voice_ready(app)
    assert info["threads"] == 1
    label = on_station(app)
    assert label["text"].startswith("Southampton Central, ")
    made = sorted([label["made_ms"]] + [on_station(app)["made_ms"] for _ in range(4)])
    print(f"\n{app.context.browser.browser_type.name}, 1 thread: each label made in a median of {made[2]} ms, "
          f"longest {made[-1]} ms")


def test_the_label_is_kept_in_the_history_and_not_spoken_unless_asked(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST)
    voice_ready(app)
    before = app.evaluate("window.tobymap.announcements.length")
    label = on_station(app)
    app.wait_for_timeout(300)
    assert label["text"] not in app.evaluate("window.tobymap.announcements.map(a => a.text)")[before:]
    app.keyboard.press("Control+Shift+Space")
    app.wait_for_function("document.querySelector('#dialog[open]')")
    assert label["text"] in app.evaluate("document.querySelector('#dialog').textContent")


def test_the_helper_script_isolates_the_page_and_the_pack_still_downloads(page, plain_site_url):
    app = open_app(page, plain_site_url, state=STATION_WEST)
    app.wait_for_function("window.crossOriginIsolated === true", timeout=60_000)
    app.wait_for_function("window.tobymap && window.tobymap.ready", timeout=120_000)
    assert app.evaluate("window.tobymap.error") is None
    info = voice_ready(app)
    assert info["isolated"] and info["threads"] > 1 or app.evaluate("navigator.hardwareConcurrency") == 1
    nearby = app.evaluate("[...document.querySelectorAll('#tree [role=treeitem]')].map(e => e.firstChild.textContent)")
    assert any(t.startswith("Southampton Central") for t in nearby), "the pack was downloaded and read"
