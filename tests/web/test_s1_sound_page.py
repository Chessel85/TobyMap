"""Spike S1 Web Audio demo page: every button works and the quiz records results (P0-T4).

The headless browsers have no sound card, so this checks the page logic, not
what is heard. The PO listens.
"""
from pathlib import Path

import pytest

pytest.importorskip("playwright")

PAGE = (Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s1" / "web" / "index.html").as_uri()


def test_buttons_play_without_errors_and_quiz_records(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(PAGE)
    assert page.locator("#directions button").count() == 8
    assert page.locator("#distances button").count() == 6
    for engine in ("hrtf", "stereo"):
        page.check(f"input[name=engine][value={engine}]")
        for sound in ("noise", "chime"):
            page.check(f"input[name=sound][value={sound}]")
            page.locator("#directions button").nth(3).click()
            page.locator("#distances button").nth(5).click()
    page.click("#quiz-start")
    for _ in range(8):
        page.click("#quiz-play")
        page.locator("#answers button").first.click()
    lines = page.input_value("#results").splitlines()
    assert lines[0].startswith("time,engine,sound,played_degrees")
    assert len(lines) == 9
    assert all(line.split(",")[4] == "0" for line in lines[1:])
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Quiz finished')")
    assert errors == []
