"""P3-T10b: the query builder's form in the browser, in Chromium and Firefox (INF-9, ACC-7)."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


def open_form(page, site_url):
    open_app(page, site_url, state=HAMPSHIRE)
    page.keyboard.press("Control+f")
    page.locator("#search-field").type("Germany")
    page.locator("#search-list option").first.wait_for(timeout=15000)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.locator("#searchdialog").wait_for(state="hidden")
    page.keyboard.press("q")
    page.locator("#query-layer").wait_for(state="visible")


def test_q_opens_the_form_with_the_distance_hidden(page, site_url):
    open_form(page, site_url)
    assert page.evaluate("document.activeElement.id") == "query-layer"
    assert page.locator("#query-ok").inner_text() == "OK" and page.locator("#query-cancel").inner_text() == "Cancel"
    assert page.locator("#query-distance").is_hidden()
    page.locator("#query-relation").select_option(label="within a distance of")
    assert page.locator("#query-distance").is_visible()


def test_ok_runs_the_query_and_closes(page, site_url):
    open_form(page, site_url)
    page.locator("#query-layer").select_option(label="Rivers")
    page.locator("#query-relation").select_option(label="crossing")
    page.locator("#query-ok").click()
    page.locator("#querydialog").wait_for(state="hidden")


def test_nothing_found_keeps_the_form_open_and_cancel_closes(page, site_url):
    open_form(page, site_url)
    page.locator("#query-layer").select_option(label="Lakes")
    page.locator("#query-relation").select_option(label="crossing")
    page.locator("#query-ok").click()
    page.locator("#query-message").filter(has_text="No lakes crossing Germany.").wait_for(timeout=15000)
    page.locator("#query-cancel").click()
    page.locator("#querydialog").wait_for(state="hidden")
