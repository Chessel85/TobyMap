"""P3-T12b in the browser, in Chromium and Firefox: names in another language carry their lang attribute, so a
screen reader set to switch voices can (ACC-9). With "Always the local name", Germany is Deutschland, marked
lang="de" where it is said and shown: in the live regions and in the Information panel. English words keep the
page's language."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

GERMANY = {"lat": 48.0, "lon": 8.5, "zoom_m": 100000, "step_m": 10000}


def test_a_local_name_carries_its_language_in_the_live_region_and_the_panel(page, site_url):
    # The live regions, not ariaNotify, as only elements can carry a language.
    open_app(page, site_url, state=GERMANY, values={"names": "local"}, query="?announcer=live")
    page.locator("#map").focus()
    page.keyboard.press("Space")   # Where am I
    marked = page.locator('[id^="live-"] span[lang="de"]', has_text="Deutschland")
    marked.first.wait_for(state="attached", timeout=15000)
    assert page.evaluate("window.tobymap.languageOf('Deutschland')") == "de"
    panel = page.locator('#tree span[lang="de"]', has_text="Deutschland")
    panel.first.wait_for(state="attached", timeout=15000)
    # The words round the name keep the page's own language.
    assert page.evaluate("document.documentElement.lang") == "en-GB"


def test_with_english_names_nothing_is_marked(page, site_url):
    open_app(page, site_url, state=GERMANY, query="?announcer=live")
    page.locator("#map").focus()
    page.keyboard.press("Space")
    page.wait_for_function("window.tobymap.announcements.some(a => a.text.includes('Germany'))", timeout=15000)
    assert page.locator('#tree span[lang], [id^="live-"] span[lang]').count() == 0
