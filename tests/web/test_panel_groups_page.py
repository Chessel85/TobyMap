"""The web Information panel with the seven groups (P3-T4a; INF-10, NFR-1, DP135), in Chromium and Firefox:
a group not yet filled can be opened with Right and is filled then; Shift+3 goes to Bordering, filled;
an item under a heading inside a group has aria-level 3."""
import pytest

from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")

SWITZERLAND = {"lat": 46.8, "lon": 8.2, "zoom_m": 100000, "step_m": 1000}
BORDERING = "[...document.querySelectorAll('#tree > [role=treeitem]')].find(g => g.dataset.id === 'group:bordering')"


def test_a_closed_group_opens_with_right_and_is_filled(page, site_url):
    app = open_app(page, site_url, state=SWITZERLAND)
    assert app.evaluate("document.querySelectorAll('#tree > [role=treeitem]').length") == 8
    assert app.evaluate(f"{BORDERING}.getAttribute('aria-label')") == "Bordering Switzerland"
    assert app.evaluate(f"{BORDERING}.getAttribute('aria-expanded')") == "false"
    app.evaluate(f"{BORDERING}.focus()")
    app.keyboard.press("ArrowRight")
    app.wait_for_function(f"{BORDERING}.getAttribute('aria-label') === 'Bordering Switzerland, 5 items, clockwise from north'")
    assert app.evaluate(f"{BORDERING}.querySelectorAll('[role=treeitem]').length") == 5


def test_shift_3_goes_to_bordering_filled(page, site_url):
    app = open_app(page, site_url, state=SWITZERLAND)
    app.keyboard.press("Shift+Digit3")
    # On the group's heading, opened and filled, so its count is heard first (P3-T19c).
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)"
                          " && document.activeElement.getAttribute('aria-level') === '1'"
                          " && document.activeElement.getAttribute('aria-expanded') === 'true'"
                          " && document.activeElement.querySelectorAll('[role=\"treeitem\"]').length === 5")
    assert app.evaluate("document.activeElement.getAttribute('aria-label')").startswith("Bordering Switzerland, 5 items, clockwise from north")


def test_an_item_under_a_heading_is_level_3(page, site_url):
    """Contains will list types, then their features (P3-T4b): the tree shows any depth, with its level."""
    app = open_app(page, site_url, state=SWITZERLAND)
    levels = app.evaluate("""async () => {
        const { Tree } = await import('./js/tree.js');
        const el = document.createElement('ul');
        el.setAttribute('role', 'tree');
        document.body.appendChild(el);
        const t = new Tree(el, () => {});
        t.fill([{ id: 'contains', label: 'Contains Switzerland, 1 item', filled: true, items: [
            { id: 'heading:regions', label: 'Regions 2', children: [
                { id: 'osm:r1', label: 'Bern' }, { id: 'osm:r2', label: 'Uri' }] }] }]);
        t.focusItem('osm:r2', 'contains');
        const a = document.activeElement;
        return [a.getAttribute('aria-level'), a.textContent,
                a.parentElement.closest('[role=treeitem]').getAttribute('aria-expanded'),
                a.parentElement.closest('[role=treeitem]').getAttribute('aria-level')];
    }""")
    assert levels == ["3", "Uri", "true", "2"]


def test_a_neighbour_opens_with_right_to_the_ends_of_the_shared_border(page, site_url):
    """P3-T24f, DP201: Germany in Bordering can be opened before it has items; the core then lists the ends."""
    app = open_app(page, site_url, state=SWITZERLAND)
    app.keyboard.press("Shift+Digit3")
    app.wait_for_function(f"{BORDERING}.querySelectorAll('[role=treeitem]').length === 5")
    germany = f"[...{BORDERING}.querySelectorAll('[role=treeitem]')].find(i => i.textContent.startsWith('Germany'))"
    assert app.evaluate(f"{germany}.getAttribute('aria-expanded')") == "false"
    app.evaluate(f"{germany}.focus()")
    app.keyboard.press("ArrowRight")
    app.wait_for_function(f"{germany}.querySelectorAll('[role=treeitem]').length > 0")
    ends = app.evaluate(f"[...{germany}.querySelectorAll('[role=treeitem]')].map(i => i.textContent)")
    assert any(e.startswith("End of the border with Germany, where Austria meets it") for e in ends)
    assert app.evaluate(f"{germany}.querySelector('[role=treeitem]').getAttribute('aria-level')") == "3"


def test_shift_8_goes_to_the_bookmarks_group(page, site_url):
    """P4-T8c: Shift+8 is found by its place on the keyboard, as Shift+1 to Shift+7 are; with no bookmark the group
    is empty and its heading says so. Written, not yet run."""
    app = open_app(page, site_url, state=SWITZERLAND)
    app.keyboard.press("Shift+Digit8")
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)"
                          " && document.activeElement.getAttribute('aria-level') === '1'"
                          " && document.activeElement.dataset.id === 'group:bookmarks'")
    assert app.evaluate("document.activeElement.getAttribute('aria-label')") == "Bookmarks, no items"
