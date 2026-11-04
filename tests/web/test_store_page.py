"""The store in Pyodide, in Chromium and Firefox (P1-T5, LOC-2, INF-3, INF-7, NFR-4).

The worker runs mapcore.store.selfcheck: a small pack in memory, asked what is
at a point (in the right order, and either side of the 180 degree line), for
the nearest point of an area with its distance and bearing, and with a
damaged pack tile. Shapely is loaded in the worker, as in the application.
"""
import pytest

pytest.importorskip("playwright")


def test_store_selfcheck_in_the_worker(page, site_url):
    page.goto(f"{site_url}/index.html")
    problems = page.evaluate("""() => new Promise((resolve, reject) => {
        const worker = new Worker('worker.js', { type: 'module' });
        worker.onmessage = (event) => {
            worker.terminate();
            if (event.data.ok) resolve(event.data.result);
            else reject(new Error(event.data.error));
        };
        worker.onerror = (event) => reject(new Error(event.message));
        worker.postMessage({ id: 1, type: 'storecheck' });
    })""")
    assert problems == []
