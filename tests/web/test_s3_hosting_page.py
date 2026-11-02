"""Spike S3 page: reading parts of a file from a worker, and private storage (P0-T6).

Uses only servers on this computer: one that gives other pages permission to
read its files, and one that does not, as GitHub's download server does not.
"""
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

S3 = Path(__file__).resolve().parents[2] / "tools" / "spikes" / "s3"
sys.path.insert(0, str(S3))

import hosting  # noqa: E402


@pytest.fixture(scope="module")
def s3_page_url(tmp_path_factory):
    files = tmp_path_factory.mktemp("s3files")
    size = 8 * hosting.MiB
    hosting.write_test_file(files / hosting.TEST_FILE_NAME, size=size)
    with_cors = hosting.LocalServer(files, allow_other_origins=True).start()
    without_cors = hosting.LocalServer(files, allow_other_origins=False).start()
    sources = [
        {"name": "with permission", "url": f"{with_cors.url}/{hosting.TEST_FILE_NAME}", "pattern": True, "size": size},
        {"name": "without permission", "url": f"{without_cors.url}/{hosting.TEST_FILE_NAME}", "pattern": True,
         "size": size},
    ]
    page_server = hosting.LocalServer(S3 / "web", extra_files={"/sources.json": json.dumps(sources).encode()}).start()
    yield f"{page_server.url}/index.html"
    for server in (page_server, with_cors, without_cors):
        server.stop()


def test_reads_ranges_only_where_permitted(page, s3_page_url):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(s3_page_url)
    page.evaluate("window.s3.ready")
    assert page.locator("#sources input[type=checkbox]").count() == 2
    results = page.evaluate("window.s3.readTest(window.s3.sources())")
    allowed, blocked = results
    assert allowed["works"] and allowed["smallWrong"] == 0 and allowed["lastOk"] and allowed["bigOk"]
    assert allowed["cacheOk"] and allowed["sizeVisible"]
    assert blocked["blocked"] and not blocked["works"]
    assert "Reading test finished: 1 of 2 places work." in page.input_value("#results")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Reading test finished')")
    assert errors == []


def test_storage_writes_reads_back_and_cleans_up(page, s3_page_url):
    page.goto(s3_page_url)
    page.evaluate("window.s3.ready")
    result = page.evaluate("window.s3.storageTest(32)")
    assert result["writtenMegabytes"] == 32
    assert result["readBackOk"]
    assert result["after"]["usageMB"] < 16
    assert "Storage test finished: 32 megabytes stored." in page.input_value("#results")
