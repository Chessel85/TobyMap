# Spike S4 findings: the core in the browser

Task P0-T7. Architecture sections 4.3, AD-9 and 12.5. Done on 2 November 2026. Piper in the browser, the rest of spike S6, follows separately.

## The question

Is TobyMap's Python core fast enough in the browser? The web version runs the core in Pyodide, Python built for web pages, inside a worker. Pyodide is usually several times slower than Python on the desktop. The target is to hear where you are within 150 milliseconds of a key press (NFR-1).

The words used here, such as pack tile, lookup, decoding, pack tile cache and private storage, are in the glossary.

## Short answer

* Yes, after one change. The core's pack reader works in the browser unchanged, and found the right answer at all 18 check places in Chrome and Firefox.
* At first the slowest lookups took up to 168 ms in Chrome, over the target. About 95% of the time went on decoding the pack's compact coordinates, one number at a time in plain Python.
* Decoding now uses NumPy, all at once. It gives exactly the same shapes, and is about 4.5 times faster.
* After that change, the slowest "where am I" took 49 ms in Chrome and 34 ms in Firefox, and the slowest step with nothing cached 48 ms. With a pack tile cache, steps took 1 ms or less at the median, and 13 ms at most. All well within 150 ms.
* Start-up took about 4 to 4.5 seconds, and the first visit downloads 16.5 MB for Pyodide, NumPy and Shapely.
* Recommendation: AD-9 is confirmed. The web version keeps the core in a Pyodide worker, reads packs from private storage, and Phase 1's store keeps a pack tile cache (P1-T5).

## How it was tested

The spike is in tools\spikes\s4:

* A test page with a worker that starts Pyodide as the web version does, loads NumPy and Shapely, and loads the core's pack reader, mapcore/packs/archive.py, unchanged.
* The worker copies the pack into the browser's private storage, then reads it from there through a synchronous access handle, as spike S3 recommends (DP102). The core's reader now takes a byte source as well as a file, which is what made that possible.
* The timings, s4_bench.py, are the same Python code on the desktop and in the browser.
* A runner, run.py, serves the page and the pack from this computer, runs the timings on the desktop, then opens the page in Chromium and Firefox without a window, twice each. The second time is like a later visit: the pack is already in private storage.
* The results are in docs\spikes\s4-results, as text and JSON. The files stamped 2153 are from before the faster decoding, and those stamped 2158 after it.

The pack was spike S2's stage 2 pack, Norway and Sweden, with compact coordinates: 68.6 MB, 693 areas, at 13 tile levels. Norway's coast is among the most detailed anywhere, so it is a hard test.

What was timed:

* "Where am I" at the 18 stage 2 check places, with nothing cached, as the core does today.
* Four walks of 40 steps: west from Svolvær along Lofoten in 1 km steps; west from Bergen out through the islands in 0.5 km steps; east from Halden across the Swedish border in 1 km steps; and north-east from Stockholm through the archipelago in 2 km steps.
* Each walk twice: with nothing cached, and with a pack tile cache that keeps each pack tile's decoded shapes.
* For every lookup, how long went on reading pack tiles, decoding them, and testing the point.

## Results before the change

"Where am I", with nothing cached:

* The desktop: median 21 ms, slowest 45 ms.
* Chrome: median 67 to 73 ms, slowest 168 ms.
* Firefox: median 49 to 59 ms, slowest 132 ms.

Steps with nothing cached took up to 163 ms in Chrome; the Lofoten walk had a median of 114 ms. With the pack tile cache, steps took 1 ms or less at the median, and 48 ms at most.

So the browser was about three times slower than the desktop, and its slowest lookups missed the target. Decoding took about 95% of the time; reading the pack tiles and testing the point took the rest.

## The change: decoding with NumPy

* Compact coordinates are stored as a run of variable-length numbers. The first decoder read them one byte at a time in Python. On the desktop that was 80% of decoding.
* The new decoder reads all of a shape's numbers in one NumPy operation, and builds all its rings and polygons in one Shapely call (`decode_compact` in mapcore/packs/archive.py).
* It was checked against the first decoder: identical on every one of 156 real shapes from the pack tiles round the check places, and on test shapes with holes, many islands, and points near the 180 degree line. The first decoder is kept in the tests as the reference.
* It follows the project rule for NumPy in Pyodide, which is 32-bit: every index array is np.intp.
* The desktop gains too: "where am I" went from a median of 21 ms to 6 ms, which also speeds up the build's place checks.

## Results after the change

"Where am I", with nothing cached:

* The desktop: median 6 ms, slowest 12 ms.
* Chrome: median 16 to 18 ms, slowest 49 ms.
* Firefox: median 17 ms, slowest 34 ms.

Steps with nothing cached:

* Chrome: medians of 5 to 20 ms on the four walks, slowest 34 ms.
* Firefox: medians of 6 to 23 ms, slowest 48 ms.
* The Lofoten walk is the slowest, because each step there reads up to six detailed pack tiles.

Steps with the pack tile cache:

* Both browsers: medians of 1 ms or less, slowest 13 ms.
* The slowest steps are the ones that cross into a new pack tile and have to decode it.

The browser is still about three times slower than the desktop, but every lookup is now well within 150 ms, leaving room for describing, speaking and drawing.

## Start-up, download and memory

* Start-up, from starting the worker to the core being ready: 4.0 to 4.5 seconds in both browsers. Of that, Pyodide itself took about 2.6 to 2.9 seconds, NumPy and Shapely about 0.6 seconds, and the core's files with their imports about 0.8 seconds.
* This is from a server on this computer, so it is almost all start-up work, not downloading. Spike S5 measured 9 to 10 seconds for the whole application, which you accepted (DP96).
* A first visit downloads 16.5 MB for Pyodide, NumPy and Shapely. Shapely adds 0.8 MB, with GEOS (the geometry library) built into it. The web version also loads PyYAML (0.1 MB), and Piper's voice adds about 60 MB later (DP98).
* Copying the 68.6 MB pack into private storage took 0.15 to 0.5 seconds from this computer. From Hugging Face, spike S3 measured about 32 MB a second, so about 2 seconds.
* Opening the pack, which reads its directory, manifest and list of areas, took 23 to 38 ms.
* Python's memory in the browser was 52 MB at the end of each run.

## What this does not show

* The browsers ran on this laptop, without a window. A slower computer, or a phone, would be slower, and that was not tested.
* Only the lookup was timed. A real step also describes the place and redraws the map. Spike S5 looked at drawing separately, and found each frame must be kept to about 10,000 points.
* Only Norway and Sweden's pack was used. The world's base pack will have more areas, but a lookup reads at most one pack tile at each tile level, so its time depends on how detailed the coast is nearby, not on the size of the pack.
* The pack tile cache here has no size limit. Phase 1's cache needs one, because the WebAssembly memory is limited.

## Recommendations

* AD-9 is confirmed: the core runs in a Pyodide worker, unchanged.
* The web version loads Shapely in its worker, from Phase 1 on. tools/fetch_vendor.py now fetches it, and its licence (BSD-3-Clause, with GEOS under LGPL-2.1) is compatible with GPL-3.0.
* The faster decoding stays in the core.
* Phase 1's store (P1-T5) keeps a pack tile cache of decoded shapes, with a size limit, on both the desktop and the web.
* The pack reader's byte source becomes the interface P1-T2 asks for: a file on the desktop, private storage in the browser, and range requests while a pack downloads.
* The web performance target stays at 150 ms (NFR-1); no longer target is needed.

## Still to do

* Piper in the browser (spike S6's last part), next.
* The architecture update (P0-T11) records these results.
