"""The web Information panel with the eight groups (P3-T4a; INF-10, NFR-1, DP135), in Chromium and Firefox:
a group not yet filled can be opened with Right and is filled then; Shift+5 goes to Bordering, filled;
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
    app.wait_for_function(f"{BORDERING}.getAttribute('aria-label') === 'Bordering Switzerland, 5 items'")
    assert app.evaluate(f"{BORDERING}.querySelectorAll('[role=treeitem]').length") == 5


def test_shift_5_goes_to_bordering_filled(page, site_url):
    app = open_app(page, site_url, state=SWITZERLAND)
    app.keyboard.press("Shift+Digit5")
    app.wait_for_function("document.getElementById('tree').contains(document.activeElement)"
                          " && document.activeElement.getAttribute('aria-level') === '2'")
    assert app.evaluate("document.activeElement.textContent").split(",")[0] in {
        "Austria", "France", "Germany", "Italy", "Liechtenstein"}


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
