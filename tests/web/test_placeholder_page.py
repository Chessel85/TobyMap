"""The page's static structure, before the core has loaded (P0-T2, extended in P0-T8).

The P0-T2 placeholder announced "TobyMap ready." from the page itself. Since
spike S5 every announcement comes from the core, so this test now checks only
what the page holds before Pyodide starts: the title, the loading message, and
the announcer's live regions.
"""
import pytest

pytest.importorskip("playwright")


def test_page_structure_before_the_core_loads(page, site_url):
    # A worker that never answers keeps the page in its loading state.
    # The page is cross-origin isolated (P2-T7b), so the stand-in needs the header the server sends.
    page.route("**/worker.js", lambda route: route.fulfill(body="", content_type="text/javascript",
                                                         headers={"Cross-Origin-Embedder-Policy": "require-corp"}))
    page.goto(f"{site_url}/index.html")
    assert page.title() == "TobyMap"
    assert page.locator("#loading").text_content().startswith("Loading TobyMap")
    for name, live in (("live-polite-a", "polite"), ("live-polite-b", "polite"),
                       ("live-assertive-a", "assertive"), ("live-assertive-b", "assertive")):
        assert page.get_attribute(f"#{name}", "aria-live") == live
