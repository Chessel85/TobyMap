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


def test_with_four_threads_a_label_is_placed_with_the_items_sound_and_can_be_repeated(page, site_url):
    """Also: the label is not spoken unless asked, and Shift+Space repeats it (one page load, not two)."""
    app = open_app(page, site_url, state=STATION_WEST)
    info = voice_ready(app)
    assert info["isolated"] and info["threads"] == min(4, app.evaluate("navigator.hardwareConcurrency"))
    before = app.evaluate("window.tobymap.announcements.length")
    label = on_station(app)
    assert label["text"].startswith("Southampton Central, ")
    assert 80 < label["relative_deg"] < 100 and label["pitch"] == 1
    placed = app.evaluate("window.tobymap.placed.slice(-2)")
    assert [p["sound"] for p in placed] == ["item_direction", "voice"]
    assert placed[0]["pan"] == placed[1]["pan"], "the label comes from the item's place"
    app.wait_for_timeout(300)
    assert label["text"] not in app.evaluate("window.tobymap.announcements.map(a => a.text)")[before:]
    made = sorted([label["made_ms"]] + [on_station(app)["made_ms"] for _ in range(4)])
    print(f"\n{app.context.browser.browser_type.name}, {info['threads']} threads: voice ready in "
          f"{info['load_ms']} ms; each label made in a median of {made[2]} ms, longest {made[-1]} ms; "
          f"the first heard {label['ms']} ms after asking, after the item's sound")
    app.keyboard.press("Shift+Space")
    app.wait_for_function("t => window.tobymap.announcements.some(a => a.text === t)", arg=label["text"])


def test_a_key_press_stops_the_voice_before_the_step_is_said(page, site_url):
    """P2-T17n, SON-3: a label is playing, Down is pressed: it stops."""
    app = open_app(page, site_url, state=STATION_WEST)
    voice_ready(app)
    on_station(app)
    halts = app.evaluate("window.tobymap.voiceHalts.halts")
    app.focus("#map")
    app.keyboard.press("ArrowDown")
    app.wait_for_function(f"window.tobymap.voiceHalts.halts > {halts}", timeout=10_000)


def test_with_one_thread_the_voice_still_works(page, site_url):
    app = open_app(page, site_url, state=STATION_WEST, query="?threads=1")
    info = voice_ready(app)
    assert info["threads"] == 1
    label = on_station(app)
    assert label["text"].startswith("Southampton Central, ")
    made = sorted([label["made_ms"]] + [on_station(app)["made_ms"] for _ in range(4)])
    print(f"\n{app.context.browser.browser_type.name}, 1 thread: each label made in a median of {made[2]} ms, "
          f"longest {made[-1]} ms")


def other_label(page, site_url, state=STATION_WEST, values=None):
    """The station's label in a second page with a browser storage of its own."""
    other = page.context.browser.new_context()
    try:
        app = open_app(other.new_page(), site_url, state=state, values=values)
        voice_ready(app)
        return on_station(app)
    finally:
        other.close()


def test_at_500_percent_the_core_stretches_the_label_and_behind_it_is_lower_at_the_same_speed(page, site_url):
    """Faster than Piper can speak, at the same pitch, by the core's time stretching (P2-T16g, SON-3).
    Behind you the label is lower at the same speed: the PO chose sample 9 on 8 November 2026.
    The label at 100 percent, ahead, is compared with both."""
    app = open_app(page, site_url, state=STATION_WEST)
    voice_ready(app)
    normal = on_station(app)
    assert normal["stretch"] == 1 and normal["pitch"] == 1
    assert normal["seconds"] == normal["piper_seconds"]

    fast = other_label(page, site_url, values={"voice_rate": 500})
    assert fast["stretch"] > 2.5
    # Piper at 100 percent against Piper at 200 then stretched: about five times as short in all.
    assert fast["seconds"] < normal["seconds"] / 4
    assert fast["seconds"] < fast["piper_seconds"] / 2
    print(f"\n{app.context.browser.browser_type.name}: {normal['seconds']:.2f} s at 100 percent, "
          f"{fast['seconds']:.2f} s at 500, made in {fast['made_ms']} ms")

    behind = other_label(page, site_url, state={**STATION_WEST, "orientation": "free", "heading": 270.0})  # facing west
    assert behind["pitch"] == pytest.approx(2 ** (-1.5 / 12), abs=0.001)
    assert abs(behind["relative_deg"]) > 170
    # Compared with Piper's own sound for the same label, as Piper's timing varies a little.
    assert behind["seconds"] == pytest.approx(behind["piper_seconds"], rel=0.02)


def test_the_helper_script_isolates_the_page_and_the_pack_still_downloads(page, plain_site_url):
    app = open_app(page, plain_site_url, state=STATION_WEST)
    app.wait_for_function("window.crossOriginIsolated === true", timeout=60_000)
    app.wait_for_function("window.tobymap && window.tobymap.ready", timeout=120_000)
    assert app.evaluate("window.tobymap.error") is None
    info = voice_ready(app)
    assert info["isolated"] and info["threads"] > 1 or app.evaluate("navigator.hardwareConcurrency") == 1
    nearby = app.evaluate("[...document.querySelectorAll('#tree [role=treeitem]')].map(e => e.firstChild.textContent)")
    assert any(t.startswith("Southampton Central") for t in nearby), "the pack was downloaded and read"


ITCHEN_WEST = {"lat": 50.9074977, "lon": -1.4442289, "zoom_m": 10000, "step_m": 1000}


def items_of(page, group):
    return page.evaluate(f"""() => [...document.querySelectorAll('[data-id="group:{group}"] [role=group] > [role=treeitem]')]
        .map((e) => e.firstChild.textContent)""")


def hear_item(page, group, index):
    """Focus an item of a group, as the arrow keys do, press Space, and give the label said."""
    page.evaluate(f"""() => {{
        const g = document.querySelector('[data-id="group:{group}"]');
        g.setAttribute('aria-expanded', 'true');
        g.querySelectorAll('[role=group] > [role=treeitem]')[{index}].focus();
    }}""")
    page.wait_for_timeout(200)
    count = page.evaluate("window.tobymap.labels.length")
    page.keyboard.press("Space")
    page.wait_for_function(f"window.tobymap.labels.length > {count}", timeout=30_000)
    return page.evaluate("window.tobymap.labels.at(-1).text")


def test_each_item_says_its_own_distance_when_an_area_is_in_two_groups(page, site_url):
    """Phase 2 web checklist: the first Nearby item said another distance. Five steps east cross
    the River Itchen, which is then first in Nearby, at its nearest point, and in Crossed and
    passed, where it was crossed. The item's words are compared with what the voice says."""
    app = open_app(page, site_url, state=ITCHEN_WEST)
    voice_ready(app)
    for _ in range(5):
        app.keyboard.press("ArrowRight")
        app.wait_for_timeout(300)
    app.wait_for_function("""() => document.querySelector('[data-id="group:crossed"] [role=group] > [role=treeitem]')
        .firstChild.textContent.startsWith('River Itchen')""", timeout=10_000)
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    near = items_of(app, "nearby")
    assert near[0] == "River Itchen, 320 metres north-west"
    for i, words in enumerate(near):
        said = hear_item(app, "nearby", i)
        assert words.startswith(said + " "), (words, said)
    assert items_of(app, "crossed")[0] == "River Itchen, crossed, 730 metres west"
    assert hear_item(app, "crossed", 0) == "River Itchen, 730 metres"
    # F3 goes back to the item last focused, in its own group.
    app.keyboard.press("F2")
    app.wait_for_function("document.activeElement.id === 'map'")
    app.keyboard.press("F3")
    app.wait_for_function("document.activeElement.getAttribute('role') === 'treeitem'")
    assert app.evaluate("document.activeElement.closest('[aria-expanded]').dataset.id") == "group:crossed"
