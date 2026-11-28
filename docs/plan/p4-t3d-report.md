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

## With the compact feature table, 28 November

P4-T3f gave both packs the compact feature table (pack format 5), and they were rebuilt: the world pack 561 MB, the England pack 1,073 MB. The map then started with both packs together in both browsers, but each step was slow. P4-T3g found out why and fixed it.

### Before the fix

Measured with tools/time_pack_start.py web, the world and England packs together, starting at Winchester, with a walk of 30 held steps east.

* Chromium: ready in 11.7 seconds on the second visit, memory 1,757 MB, 2,030 MB after the walk, steps a median of 7,821 milliseconds.
* Firefox: ready in 12.0 seconds, memory 2,114 MB, 2,412 MB after the walk, steps a median of 7,791 milliseconds.
* The desktop with both packs: first place said in 4.5 seconds, memory 1.1 GB, steps a median of 123 milliseconds.

So the browsers' steps were about 60 times the desktop's. The world pack alone had stepped at about 500 milliseconds in the browsers before format 5.

### What the time went on

The core was timed inside the browser's worker, during 10 steps, with a temporary timing switch, since removed. Two things took nearly all the time.

* Nearby, worked out after each step and again after the search for what you crossed and passed. It measured the distance to every feature in both packs and sorted them all: England's 6.3 million each time, about 4 seconds in the browser. This was the larger part of each step.
* Reading feature records. Feature records are in feature groups by identifier, not by place, so the features of one view are spread across thousands of groups. To get one record, the store read and decoded its whole group, about 256 records, and with only 64 groups kept, almost every new feature in view meant a new group: about 4,000 groups read in each step, and 39,000 in the 10 steps. Each took about 2 milliseconds in the browser, about 1 on the desktop. The first drawing of the walk took about a minute in the browser, and 58 seconds on the desktop.
* The reads from the browser's storage and the garbage collector were small: 4 seconds each in all, over the 10 steps.
* England made the difference, not format 5: it has ten times the world pack's features.

### The fix

All in the core, so the desktop gains too.

* Nearby measures and sorts only the features whose bounding boxes are near enough in latitude to be within its distance. The answers are the same, in the same order. (mapcore/store/store.py)
* With the compact feature table, a feature record is read alone: its group's record is decompressed, the record is found by its identifier, which the table gives, and only that record is decoded. If it cannot be found so, the whole group is read, as before. Every record of both real packs that was checked, about 150,000, came out the same as from its whole group. The limits on what is kept, 64 groups and 50,000 records, are unchanged. (mapcore/packs/pack.py)
* The drawing takes each feature's identifier, layer and width from the feature table, and reads its record only when it needs the colour, the intervals or the name. A feature whose layer is in both packs is read as before, as its records are merged. (mapcore/render/scene.py, mapcore/store/store.py)
* The drawings of the first 6 steps from Winchester with both packs are the same as before, apart from their timings.

### After the fix

The same measurements again.

* Chromium: ready in 8.0 seconds on the second visit, memory 1,535 MB, 1,608 MB after the walk, steps a median of 667 milliseconds. Before: 7,821 milliseconds.
* Firefox: ready in 7.7 seconds, memory 1,889 MB, 1,953 MB after the walk, steps a median of 770 milliseconds. Before: 7,791 milliseconds.
* The desktop, 3 runs, the middle one: first place said in 2.4 seconds, memory 998 MB, 1,237 MB after the walk, steps a median of 119 milliseconds. Before: 4.5 seconds, 1.1 GB and 123 milliseconds.
* Outside the tool, on the desktop, the first drawing at Winchester took 5.5 seconds in place of 58, and a step with its drawing and Nearby about 0.2 seconds in place of 2.2.

Memory is now under 2 GB (NFR-3) in both browsers and on the desktop. The browsers' steps are still about 6 times the desktop's, which is about what Pyodide's slower Python gives.

### Tests

* New in tests/mapcore/test_feature_table.py: a record read alone is the same as its group's, for every feature of the test packs; a record not found alone is read with its group; the drawing is the same from format 5 packs and the same packs written as format 4, alone and together; and Nearby gives the same answers as when every feature is measured.
* Changed for the new reading: tests/mapcore/test_feature_table.py (the caches' limits) and tests/mapcore/test_pack_format.py (the reads a pack makes).
* Python tests in tests/mapcore: all pass. The web shell was not changed, so the browser tests were not run.
