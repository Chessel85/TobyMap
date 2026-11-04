"""The web version of the listening test, blocks 1 and 3, in Chromium and Firefox (P1-T13). No sound is judged here."""
import functools
import http.server
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright")

FOLDER = Path(__file__).resolve().parents[2] / "tools" / "listening_test" / "web"


@pytest.fixture(scope="module")
def listening_url():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FOLDER))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_the_flow_runs_and_a_results_file_is_downloaded(page, listening_url):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{listening_url}/index.html")
    page.click("#start")
    assert page.text_content("#instructions").startswith("Block 1 of 2")
    page.keyboard.press("Space")
    page.keyboard.type("3")
    page.keyboard.press("Enter")
    assert "distance" in page.text_content("#instructions")
    page.keyboard.type("9")
    page.keyboard.press("Enter")
    assert page.text_content("#instructions").startswith("Type a distance")
    page.keyboard.type("2")
    page.keyboard.press("Enter")
    assert page.text_content("#instructions").startswith("Trial 2 of 12")
    assert errors == []


def test_it_has_a_close_button_and_answers_end_in_a_file(page, listening_url):
    page.goto(f"{listening_url}/index.html")
    assert page.text_content("#close") == "Close"
    page.click("#start")
    with page.expect_download() as download:
        for _block in (12, 10):
            for _ in range(_block):
                page.keyboard.press("Space")
                page.keyboard.type("6")
                page.keyboard.press("Enter")
                page.keyboard.type("2")
                page.keyboard.press("Enter")
    text = Path(download.value.path()).read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("block,trial,style") and len(text.splitlines()) == 23
