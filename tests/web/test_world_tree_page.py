"""P3-T9 in the browser, in Chromium and Firefox. The site serves the plain test pack, which has no continents,
so the tree's branches are tested on the desktop and in the core (tests/mapcore/test_world_tree.py,
tests/desktop/test_world_tree_desktop.py); here W opens the tree as an ARIA tree with World at level 1, Enter on
World is refused with the core's words, Cancel closes, and Ctrl+Shift+F reaches the page (SRB-3, SRB-4, ACC-7)."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

HAMPSHIRE = {"lat": 51.06, "lon": -1.31, "zoom_m": 1000, "step_m": 100}


def test_w_opens_the_tree_with_world_at_level_1_and_enter_on_it_is_refused(page, site_url):
    open_app(page, site_url, state=HAMPSHIRE)
    page.keyboard.press("w")
    tree = page.locator("#world-tree")
    tree.wait_for(state="visible")
    assert tree.get_attribute("role") == "tree" and tree.get_attribute("aria-label") == "World tree"
    world = page.locator("#world-tree [role=treeitem]").first
    assert world.get_attribute("aria-level") == "1" and world.inner_text().startswith("World")
    world.focus()
    page.keyboard.press("Enter")
    page.locator("#world-tree-message").filter(has_text="The World is the top of the tree").wait_for(timeout=15000)
    page.locator("#world-tree-cancel").click()
    page.locator("#treedialog").wait_for(state="hidden")


def test_ctrl_shift_f_opens_the_list_of_kinds_inside_the_current_feature(page, site_url):
    open_app(page, site_url, state=HAMPSHIRE)
    page.keyboard.press("Control+Shift+F")
    page.locator("#dialog").wait_for(state="visible")
    assert "Inside " in page.locator("#dialog").inner_text()
