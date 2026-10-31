"""Placeholder web test (P0-T2): the page loads and announces through its live region."""
import pytest

pytest.importorskip("playwright")


def test_page_announces_ready(page, site_url):
    page.goto(f"{site_url}/index.html")
    assert page.title() == "TobyMap"
    announcer = page.locator("#announcer")
    assert announcer.get_attribute("aria-live") == "polite"
    assert announcer.text_content() == "TobyMap ready."
