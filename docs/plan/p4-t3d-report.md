# P4-T3d The web version with two packs: report

27 November 2026. Requirements: PLT-4, PCK-2, AD-14, NFR-3.

## In short

* The web version opens two packs together. With the test pack and the regional test pack, it says and finds what the desktop does, in Chromium and Firefox.
* With the real packs, the world pack and the England pack, it does not start, in either browser. It runs out of memory reading England's feature table.
* The desktop has the same fault: England's feature table costs about 10.4 GB of memory and 37 seconds when the first map is drawn, far over the 2 GB aim (NFR-3).
* The fix needs a change to the pack format and the writing stage rerun for both packs. It is proposed in DP225. P4-T3d stays open until it is done.

## What was done

* A browser test, tests/web/test_two_packs_page.py, with a site that lists the regional test pack and the test pack. In Chromium and Firefox, 8 of 8 pass:
  * both packs download into the browser's private storage on the first visit, and are read from there on the second;
  * at Winchester, inside the coverage, the map is named with the district only the regional pack holds, and Hampshire once, as the core says outside the browser;
  * outside the coverage the map says what the world pack alone says, and nothing about missing detail;
  * a search for Winchester, Hampshire, Lymington and New Forest gives the core's own results, with each feature once.
* The web shell needed no change: the worker already opened every pack listed in packs.json.
* tools/serve_web.py takes --pack more than once, to serve several packs together, each under its own file name.
* tools/time_pack_start.py web takes --together, to open the packs given together, and now measures the memory after a walk of 30 steps east as well. If the map does not start in one browser, it says so and tries the next. It removes each browser profile it made, trying again for a few seconds, as each holds a copy of the packs.

## Memory in the browsers

Each run starts from Winchester with a new, empty browser profile. Memory is the working set of all the browser's processes.

### Test pack and regional test pack together

* Chromium: ready in 5.5 seconds on the second visit, memory 909 MB, 928 MB after the walk.
* Firefox: ready in 5.4 seconds, memory 1,310 MB, 1,198 MB after the walk.

### World pack alone, for comparison

* Chromium: ready in 13.1 seconds on the second visit, storage 734 MB, memory 1,805 MB, 1,808 MB after the walk, steps a median of 500 milliseconds.
* Firefox: ready in 13.7 seconds, storage 616 MB, memory 2,132 MB, 2,105 MB after the walk, steps a median of 518 milliseconds.

### World pack and England pack together

* Chromium: the map did not start. Pyodide's memory ran out ("RangeError: offset is out of bounds") with the browser at 2,564 MB.
* Firefox: the map did not start ("RangeError: invalid or out-of-range index"), with the browser at 5,266 MB.

## Why

* When a pack is first used, the store reads every feature record in it to make the feature table: each feature's identifier, layer, width and bounding box. The drawing's visible rule, the places under a point and the merging of records all use it.
* Every feature record read is also kept for as long as the application runs.
* For the world pack, 612,356 features, this costs 1.3 GB and 4.2 seconds on the desktop. For the England pack, 6,328,884 features, it costs 10.4 GB and 36.7 seconds.
* The web version's Python has at most a few GB, so it fails. The desktop has the memory on this laptop, but it would take 40 seconds to show the first map and use over 10 GB.
* P4-T3a to P4-T3c were checked on the real packs with lookups and searches, which did not read England's whole table, so this was not seen then.

## Proposed fix (DP225)

* The writing stage stores a compact feature table in each pack: bounding boxes, widths, layers as small numbers, and the identifiers packed one after another. The application reads it as one record.
* Estimated memory: about 300 to 400 MB for England and about 40 MB for the world, in place of 10.4 GB and 1.3 GB. Read in about a second.
* Feature records are then read group by group as needed, with only a limited number of feature groups kept.
* Packs of the present format are still read, the old way.
* Needs the writing stage rerun for the world pack (about 1.5 hours) and the England pack (about 1 hour 40 minutes), with the laptop otherwise idle.
* After it, this task's memory measurement is run again, and P4-T7b follows.
