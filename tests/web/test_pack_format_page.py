"""Pack format 2 read by the core in Pyodide, in Chromium and Firefox (P1-T2, PCK-5, NFR-4).

The worker runs mapcore.packs.selfcheck: a pack written in memory and read
back through a byte source, with a damaged record found and a pack for a later
application version refused. NumPy in Pyodide is 32-bit, so this is also the
check that compact coordinates decode the same there.
"""
import pytest

pytest.importorskip("playwright")


def test_pack_format_selfcheck_in_the_worker(page, site_url):
    page.goto(f"{site_url}/index.html")
    problems = page.evaluate("""() => new Promise((resolve, reject) => {
        const worker = new Worker('worker.js', { type: 'module' });
        worker.onmessage = (event) => {
            worker.terminate();
            if (event.data.ok) resolve(event.data.result);
            else reject(new Error(event.data.error));
        };
        worker.onerror = (event) => reject(new Error(event.message));
        worker.postMessage({ id: 1, type: 'packcheck' });
    })""")
    assert problems == []
