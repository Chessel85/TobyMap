# P2-T14: where the drawing time goes

Written by Claude Code on 5 November 2026, for P2-T14b and P2-T14c (DP140).

## In short

* Holding an arrow key now gives evenly spaced clicks, however long the map takes to draw. On the desktop the map is drawn in the background. In the web version the page plays each click on the sound card's own clock. With a stand-in drawing of 200 ms, every click of a 3 second hold came within 10 ms of its due time, on the desktop and in Chromium and Firefox. On the desktop most came within about 2 ms.
* While a key is held, the map is drawn at most 4 times a second, and the Information panel waits for the release. Bringing the panel up to date after every held step took up to 135 ms on the desktop, in the same place as the clicks. That was very likely a cause of the uneven clicks you heard.
* Once the shapes of a place are in memory, a drawing is quick: usually 28 ms or less on the desktop and 32 ms or less in the browsers, even for a continent.
* The slowest drawing is the first one in a new place, while its pack tiles are decoded. Decoding all the shapes of a pack tile together made it much quicker. The slowest of all walks went from 362 ms to 116 ms on the desktop, and from 1.2 seconds to 238 ms in the browsers. The worst place before, the Pacific near Fiji at a 2,500 km zoom, went from 1.2 seconds to 238 ms in Chromium, from 1.1 seconds to 185 ms in Firefox, and from 338 ms to 68 ms on the desktop.

## How it was measured

* A held key walk: from each of three places, 20 steps east, drawing every place, as when an arrow key is held. The places are Europe (from 48 north, 2 west), the Pacific near Fiji (from 17.5 south, 176 east, across the 180 degree line) and Antarctica (from 78 south, 0 east).
* Each walk at three zooms: 25 km (drawn from the exact shapes), 250 km and 2,500 km (both drawn from drawing tiles). The steps were 5 km, 100 km and 1,000 km.
* Each drawing is timed in three parts, which are now in the test trace, so Copy diagnostics shows them: choosing the shapes in view and cutting them to it, projecting them, and painting them.
* On the desktop: tools/time_drawing.py, painting on an image 900 by 760 pixels, the size of the map in the usual window.
* In the browsers: tools/time_drawing_web.py, the web version itself in Chromium and Firefox, on a 1200 by 800 page, reading the times from Copy diagnostics. The page sometimes draws once more as it starts, so a walk there has 21 or 22 drawings.
* All on the world pack, on your laptop. Each walk starts with nothing in memory, so its first drawing is the slowest.
* "Before" is the same code with each shape decoded on its own, as it was. Below, "usually" is the median, and "slowest" is the slowest drawing of the walk, which is nearly always the first.

## Where the time went before

* Choosing the shapes was the slowest part, and only on the first drawing in a new place: up to 326 ms on the desktop and 1.1 seconds in the browsers. Nearly all of it was decoding about 3,600 shapes one at a time.
* After the first drawing, choosing usually took 0 to 9 ms on the desktop and 1 to 16 ms in the browsers.
* Projecting took at most 7 ms on the desktop and 17 ms in the browsers. It is done for every point at once with NumPy.
* Painting took at most 35 ms on the desktop, 18 ms in Firefox and 6 ms in Chromium.
* On the desktop, bringing the Information panel up to date took longer than most drawings. It finds the nearest areas for Nearby. Before this change it was done after every held step, in the same place as the clicks:
* Europe, zoom 25 km: usually 13 ms, slowest 40 ms.
* Europe, zoom 250 km: usually 12 ms, slowest 34 ms.
* Europe, zoom 2,500 km: usually 15 ms, slowest 135 ms.
* The Pacific near Fiji, zoom 25 km: usually 7 ms, slowest 22 ms.
* The Pacific near Fiji, zoom 250 km: usually 5 ms, slowest 15 ms.
* The Pacific near Fiji, zoom 2,500 km: usually 6 ms, slowest 15 ms.
* Antarctica, zoom 25 km: usually 4 ms, slowest 23 ms.
* Antarctica, zoom 250 km: usually 2 ms, slowest 27 ms.
* Antarctica, zoom 2,500 km: usually 3 ms, slowest 7 ms.

## The two approaches tried on the slowest part (P2-T14c)

As in the build speed trials (DP107), two approaches were tried on the slowest part, choosing the shapes the first time a place is drawn. The figures are the core's part of each drawing, choosing and projecting, on the desktop, over all 9 walks of 21 drawings.

* Approach 1: decode all the shapes of a pack tile together, in one pass with NumPy, and keep them with the pack tile in the pack tile cache.
* Approach 2: keep decoding one by one, but read and decode the pack tiles the next step will need in the background, while the key is held.

The results:

Decoded one by one, as before:
* The first drawing of each walk: median 31 ms, 95th percentile 292 ms, slowest 292 ms
* Every drawing after it: median 1 ms, 95th percentile 14 ms, slowest 43 ms

Approach 1: the shapes of each pack tile decoded together:
* The first drawing of each walk: median 26 ms, 95th percentile 72 ms, slowest 72 ms
* Every drawing after it: median 2 ms, 95th percentile 14 ms, slowest 59 ms

Approach 2: one by one, with the next pack tiles read ahead in the background:
* The first drawing of each walk: median 37 ms, 95th percentile 399 ms, slowest 399 ms
* Every drawing after it: median 1 ms, 95th percentile 15 ms, slowest 16 ms
* Reading ahead, in the background: median 0 ms, 95th percentile 2 ms, slowest 5 ms

Both together:
* The first drawing of each walk: median 31 ms, 95th percentile 83 ms, slowest 83 ms
* Every drawing after it: median 2 ms, 95th percentile 15 ms, slowest 18 ms
* Reading ahead, in the background: median 0 ms, 95th percentile 1 ms, slowest 37 ms

Approach 1 is kept. It makes the slowest first drawing about 4 times quicker. Approach 2 did not help the first drawing at all, because you arrive at a new place before anything can be read ahead. It only made the later drawings, which were already quick, a little quicker still. Those are now drawn in the background, where they cannot delay a click, and approach 2 would need a thread that the web version does not have. So it was not kept.

The picture is unchanged: a test checks that a drawing from shapes decoded together matches one from shapes decoded one by one, point for point within one pixel.

The other candidates in the plan were not tried, because the measurements showed they would not help the slowest part:

* Shifting the last picture when the centre moves a little: projecting is not the slow part, and on a globe a shifted picture is not the same as a fresh one.
* Keeping each pack tile's projected points until the zoom changes: the same reason.
* Painting the land fill as a single path: painting is not the slow part either.

## The desktop, before and after

The whole drawing, the core's part and the painting together:

* Europe, zoom 25 km: usually 8 ms (was 8), slowest 34 ms (was 36).
* Europe, zoom 250 km: usually 11 ms (was 11), slowest 85 ms (was 136).
* Europe, zoom 2,500 km: usually 26 ms (was 26), slowest 116 ms (was 362).
* The Pacific near Fiji, zoom 25 km: usually 4 ms (was 4), slowest 19 ms (was 15).
* The Pacific near Fiji, zoom 250 km: usually 3 ms (was 4), slowest 67 ms (was 72).
* The Pacific near Fiji, zoom 2,500 km: usually 28 ms (was 26), slowest 68 ms (was 338).
* Antarctica, zoom 25 km: usually 4 ms (was 4), slowest 7 ms (was 8).
* Antarctica, zoom 250 km: usually 5 ms (was 4), slowest 6 ms (was 6).
* Antarctica, zoom 2,500 km: usually 5 ms (was 5), slowest 32 ms (was 82).

## Chromium, before and after

The core's part in the worker and the painting on the page together:

* Europe, zoom 25 km: usually 4 ms (was 3), slowest 107 ms (was 78).
* Europe, zoom 250 km: usually 8 ms (was 8), slowest 212 ms (was 335).
* Europe, zoom 2,500 km: usually 26 ms (was 27), slowest 204 ms (was 893).
* The Pacific near Fiji, zoom 25 km: usually 3 ms (was 3), slowest 93 ms (was 99).
* The Pacific near Fiji, zoom 250 km: usually 2 ms (was 2), slowest 98 ms (was 122).
* The Pacific near Fiji, zoom 2,500 km: usually 24 ms (was 24), slowest 238 ms (was 1166).
* Antarctica, zoom 25 km: usually 2 ms (was 2), slowest 99 ms (was 95).
* Antarctica, zoom 250 km: usually 2 ms (was 2), slowest 97 ms (was 111).
* Antarctica, zoom 2,500 km: usually 6 ms (was 7), slowest 125 ms (was 388).

## Firefox, before and after

* Europe, zoom 25 km: usually 8 ms (was 7), slowest 99 ms (was 108).
* Europe, zoom 250 km: usually 11 ms (was 12), slowest 180 ms (was 418).
* Europe, zoom 2,500 km: usually 32 ms (was 36), slowest 199 ms (was 878).
* The Pacific near Fiji, zoom 25 km: usually 4 ms (was 4), slowest 84 ms (was 86).
* The Pacific near Fiji, zoom 250 km: usually 3 ms (was 3), slowest 88 ms (was 113).
* The Pacific near Fiji, zoom 2,500 km: usually 29 ms (was 31), slowest 185 ms (was 1078).
* Antarctica, zoom 25 km: usually 3 ms (was 3), slowest 86 ms (was 83).
* Antarctica, zoom 250 km: usually 3 ms (was 3), slowest 88 ms (was 87).
* Antarctica, zoom 2,500 km: usually 7 ms (was 8), slowest 106 ms (was 311).

## What is left

* The first drawing in a new place still takes about 100 to 200 ms in the browsers, from reading the shapes and the areas' records. With the clicks no longer waiting for drawings, this is not heard. If the map is seen to lag, the next step is to keep each area's layer and colour with the pack tile too, which is about half of what is left.
* At the 25 km zoom the first drawing is about the same as before, between 90 and 110 ms in the browsers. There the drawing uses the same pack tiles as "where am I", whose shapes were already decoded, and now uses them as they are. One walk, Chromium in Europe at 25 km, came out at 107 ms against 78 ms before, which is within the spread between runs at that zoom.
* The figures above are from one run each. They vary by about 10 to 20% from run to run, and the slowest drawings vary more, because they depend on what Windows already has in memory.
* To measure again: .venv\Scripts\python.exe tools\time_drawing.py, with --one-by-one for the way before, or --trial for the two approaches; and .venv\Scripts\python.exe tools\time_drawing_web.py, also with --one-by-one, for the browsers.
