"""The pack manager in the web version (P4-T6d; PCK-2, PCK-4, PCK-5, ACC-7), in Chromium and Firefox.

P opens the pack manager. The catalogue comes from a stand-in on the local test server (the page is given its address
with ?catalogue=, as the web packs are not hosted yet), and the pack from the same stand-in as in the download tests.
Install downloads the pack into the browser's private storage and opens it, Update replaces it, Remove asks and then
deletes the file, and a pack this version cannot use is refused with the reason said.
"""
import hashlib
import json
import shutil

import pytest

from mapcore.packs.pack import Pack
from tests.web.conftest import _serve
from tests.web.test_pack_download_page import HAMPSHIRE, _DownloadHandler, _Stand, _stored, _texts
from tests.web.test_shell_page import open_app

pytest.importorskip("playwright")


class _CatalogueHandler(_DownloadHandler):
    catalogue: bytes = b""

    def do_GET(self):
        if self.path.split("?")[0] != "/catalogue.json":
            return super().do_GET()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.catalogue)))
        self.end_headers()
        self.wfile.write(self.catalogue)


@pytest.fixture(scope="module")
def manager_site(site_url, test_pack, tmp_path_factory):
    folder = tmp_path_factory.mktemp("no_packs_manager")
    stand = _Stand()
    stand.data = test_pack.read_bytes()
    pack = Pack(test_pack)
    stand.version = pack.manifest["version"]   # the catalogue says the version the pack has, so it is "installed"
    pack.close()
    handler = type("_Handler", (_CatalogueHandler,), {"packs_dir": folder, "stand": stand})
    server = _serve(handler)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    yield url, handler, stand
    server.shutdown()
    shutil.rmtree(folder, ignore_errors=True)


def _catalogue(url, stand, version=None, **change):
    entry = {"name": "test", "title": "Test world", "version": version or stand.version, "date": "2026-11-27", "size": len(stand.data),
             "sha256": hashlib.sha256(stand.data).hexdigest(), "url_desktop": "https://example.org/test.pack",
             "url_web": f"{url}/dl/test.pack", "app_versions": {"from": "0.0.1"}}
    entry.update(change)
    return json.dumps({"format": 1, "packs": [entry]}).encode()


def _open_manager(app):
    app.focus("#map")
    app.keyboard.press("p")
    app.wait_for_selector("#packmanagerdialog[open]")
    app.wait_for_function("document.querySelectorAll('#pm-list li').length > 0 && "
                          "document.getElementById('pm-note').textContent !== 'Reading the list of packs.'",
                          timeout=30_000)


def _line(app):
    return app.evaluate("document.querySelector('#pm-list li').textContent")


def _available(app, name):
    return app.get_attribute(f"#pm-{name}", "aria-disabled") == "false"


def _wait_text(app, text):
    app.wait_for_function("(text) => window.tobymap.announcements.some(a => a.text === text)", arg=text, timeout=60_000)


def test_install_update_and_remove_from_the_pack_manager(page, manager_site):
    url, handler, stand = manager_site
    stand.whole = stand.ranges = 0
    handler.catalogue = _catalogue(url, stand)
    app = open_app(page, url, state=HAMPSHIRE, query=f"?catalogue={url}/catalogue.json")
    _open_manager(app)
    megabytes = -(-len(stand.data) // 1_000_000)
    assert _line(app) == f"Test world, {megabytes} megabytes, 2026-11-27, not installed"
    assert _available(app, "install") and not _available(app, "update") and not _available(app, "remove")
    assert app.inner_text("#pm-close") == "Close"

    # Install: downloaded into private storage and opened; the line says so.
    app.click("#pm-install")
    _wait_text(app, "Test world is downloaded and open.")
    assert _stored(app) == ["test.pack"]
    app.wait_for_function("document.querySelector('#pm-list li').textContent.endsWith(', installed')")
    assert _available(app, "remove") and not _available(app, "install")
    assert stand.whole == 1

    # Update: a newer version is listed; the pack in use is closed and its file replaced.
    app.click("#pm-close")
    handler.catalogue = _catalogue(url, stand, version="9999.1.1")
    _open_manager(app)
    assert _line(app).endswith("update available") and _available(app, "update")
    app.evaluate("window.tobymap.announcements.length = 0")
    app.click("#pm-update")
    _wait_text(app, "Test world is downloaded and open.")
    assert _stored(app) == ["test.pack"]
    assert stand.whole == 2
    assert app.evaluate("window.tobymap.search('Hampshire')")["results"]

    # Remove: asks first, then the pack is out of use and its file is gone.
    # (The stand-in serves the same pack for the newer version, so the line may still say an update is available.)
    app.wait_for_function("document.getElementById('pm-remove').getAttribute('aria-disabled') === 'false'")
    app.click("#pm-remove")
    app.wait_for_selector("#messagebox[open]")
    assert app.evaluate("document.activeElement.id") == "messagebox-cancel"
    assert _stored(app) == ["test.pack"]   # asking changes nothing
    app.click("#messagebox-ok")
    app.wait_for_function("document.querySelector('#pm-list li').textContent.includes('not installed')")
    assert _stored(app) == []
    assert "Test world is removed." in _texts(app)
    assert app.evaluate("window.tobymap.search('Hampshire')")["results"] == []
    assert _available(app, "install") and not _available(app, "remove")


def test_a_pack_this_version_cannot_use_is_refused_with_the_reason(page, manager_site):
    url, handler, stand = manager_site
    stand.whole = stand.ranges = 0
    handler.catalogue = _catalogue(url, stand, app_versions={"from": "99.0.0"})
    app = open_app(page, url, state=HAMPSHIRE, query=f"?catalogue={url}/catalogue.json")
    _open_manager(app)
    app.click("#pm-install")
    refused = ("Test world needs TobyMap 99.0.0 or later, and this is TobyMap")
    app.wait_for_function("(text) => window.tobymap.announcements.some(a => a.text.startsWith(text))", arg=refused)
    assert "was not downloaded" in [t for t in _texts(app) if t.startswith(refused)][0]
    assert stand.whole == 0 and _stored(app) == []


def test_an_unreadable_catalogue_is_said_and_the_dialog_still_opens(page, manager_site):
    url, handler, stand = manager_site
    app = open_app(page, url, state=HAMPSHIRE, query=f"?catalogue={url}/missing.json")
    app.focus("#map")
    app.keyboard.press("p")
    app.wait_for_selector("#packmanagerdialog[open]")
    said = "The list of packs could not be read. Only the packs you have installed are shown."
    app.wait_for_function("(text) => window.tobymap.announcements.some(a => a.text.startsWith(text))", arg=said,
                          timeout=30_000)
    assert app.inner_text("#pm-close") == "Close"
    assert not _available(app, "install")


def _reload(app):
    app.reload()
    app.wait_for_function("window.tobymap && (window.tobymap.ready || window.tobymap.error)", timeout=120_000)
    assert app.evaluate("window.tobymap.error") is None


def test_a_newer_pack_is_offered_once_at_start(page, manager_site):
    url, handler, stand = manager_site
    stand.whole = stand.ranges = 0
    handler.catalogue = _catalogue(url, stand)
    app = open_app(page, url, state=HAMPSHIRE, query=f"?catalogue={url}/catalogue.json")
    _open_manager(app)
    app.click("#pm-install")
    _wait_text(app, "Test world is downloaded and open.")
    assert _stored(app) == ["test.pack"] and stand.whole == 1
    # The same version: no offer. A newer one: offered at the next start, with Update and Not now.
    _reload(app)
    app.wait_for_timeout(2000)
    assert not app.evaluate("document.getElementById('messagebox').open")
    handler.catalogue = _catalogue(url, stand, version="9999.1.1")
    _reload(app)
    app.wait_for_selector("#messagebox[open]", timeout=30_000)
    assert app.inner_text("#messagebox-ok") == "Update" and app.inner_text("#messagebox-cancel") == "Not now"
    assert "version 9999.1.1" in app.inner_text("#messagebox-text")
    # Not now: not offered again for that version.
    app.click("#messagebox-cancel")
    _reload(app)
    app.wait_for_timeout(2000)
    assert not app.evaluate("document.getElementById('messagebox').open")
    # A still newer version is offered, and Update replaces the pack.
    handler.catalogue = _catalogue(url, stand, version="9999.2.1")
    _reload(app)
    app.wait_for_selector("#messagebox[open]", timeout=30_000)
    app.click("#messagebox-ok")
    app.wait_for_function("window.tobymap.announcements.some(a => a.text === 'Test world is downloaded and open.')",
                          timeout=60_000)
    assert _stored(app) == ["test.pack"] and stand.whole == 2
