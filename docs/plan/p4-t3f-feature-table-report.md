# P4-T3f The compact feature table: report

27 November 2026. Requirements: NFR-3, NFR-4, DMT-1, PLT-4, PCK-1. Discussion point: DP225.

## In short

* Packs are now written in pack format 5, which stores the feature table: every feature's identifier, layer, width and bounding box, as six records.
* The application reads the feature table in one go, in place of every feature record. Feature records are then read a feature group at a time, as needed, and only the most lately used are kept.
* Packs of format 4 and before still open, and are read the old way, but their feature records are no longer all kept.
* On the Hampshire and Isle of Wight pack, the first place is said in 1.6 seconds in place of 5.0, with 370 MB of memory in place of 900 MB.
* The pack is 11 percent larger: 48.1 MB in place of 43.2 MB.
* Writing takes the same time, and the pack written twice is the same, byte for byte.
* The world pack and the England pack need their writing stage run again to get the feature table. Until then they open the old way, now without keeping every feature record.

## The format added

Pack format 5 is format 4 with six more records. The specification is in docs/developer/pack-format.md, section "table and table/...".

* table: how many features, the layer ids, any aliases, and how the numbers are stored.
* table/boxes: each feature's bounding box, as whole numbers of ten-millionths of a degree: west, south, then the width and height of the box. A box across the 180 degree line comes back exactly.
* table/widths: each feature's width, in whole metres.
* table/layers: each feature's layer, as one byte.
* table/ids: the identifiers, one after another.
* table/id_lengths: each identifier's length.

Other points:

* If any value is not a whole number of ten-millionths of a degree, or of metres, that record is stored as plain 8-byte numbers instead, so the values read back are always exactly those in the feature records.
* The numbers are stored byte-shuffled, which halves the space they take once compressed.
* An identifier is found by a quick search of its feature group's part of the table, so no feature record is read to find a feature.
* The format number in the header and the manifest is now 5. An application older than this one refuses a format 5 pack, saying it needs a newer version of TobyMap. The catalogue's rules are unchanged: it has its own format number, and packs say which application versions they need.
* A damaged table record is noted in the problems list, and the application makes the feature table from the feature records instead (NFR-4).

## The cache and its limits

Two limits, both named constants in mapcore/packs/pack.py:

* GROUPS_KEPT, 64: the feature groups kept after reading, the least recently used let go first.
* FEATURES_KEPT, 50,000: the feature records kept one by one, the least recently used let go first.

Why two:

* A view needs the feature records of the features it draws, and these are scattered across many feature groups.
* With only the groups kept, the visible rule on the world pack took 233 milliseconds a frame, against its 25 millisecond test.
* With the records also kept one by one, it takes 17 milliseconds.
* 50,000 records is some tens of MB at most. 64 groups is about 16,000 records more.

Before, every feature record read was kept for as long as TobyMap ran.

Note, 28 November (P4-T3g): the limits are unchanged, but a pack with the feature table now reads a feature record alone, from its feature group's record, without reading the rest of the group, so its groups are no longer kept when one feature is asked for. Reading the whole group for each record made the browser's steps about 8 seconds with the world and England packs. See docs/plan/p4-t3d-report.md, section "With the compact feature table, 28 November".

## The Hampshire rehearsal

The writing stage was run alone on the Hampshire and Isle of Wight data on disk, with tools/time_stage.py, 3 workers, into working/hampshire-isle-of-wight-time-stage. The old code was run from a copy of the code before this change, so old and new read the same stage folders. No build folder was changed.

### Writing

* Old: 285.6 seconds. Peak memory: the stage's own process 494 MB, all together 906 MB.
* New: 285.4 seconds. Peak memory: the stage's own process 519 MB, all together 897 MB.
* New, run again: 285.6 seconds, the same pack byte for byte (DMT-1).

### Pack size

* Old: 43.2 MB, 306,860 features.
* New: 48.1 MB. The feature table takes 4.9 MB, about 16 bytes a feature.

### Making the feature table, alone

* Old code, old pack: 1.37 seconds, 509 MB more memory, every one of the 1,199 feature groups kept.
* New code, old pack: 1.34 seconds, 119 MB more memory, 8 feature groups kept.
* New code, new pack: 0.04 seconds, 26 MB more memory.

### Opening on the desktop

Measured with tools/time_pack_start.py desktop, 3 runs each, starting at Winchester. The times are the middle run.

* Old code, old pack: first place said in 5.0 seconds, memory 898 MB, 974 MB after the walk of 30 steps.
* New code, old pack: first place said in 5.1 seconds, memory 524 MB, 610 MB after the walk.
* New code, new pack: first place said in 1.6 seconds, memory 370 MB, 596 MB after the walk.

## Estimates for England and the world

These scale the Hampshire numbers by the number of features.

### England, 6,328,884 features

* Feature table in memory: about 540 MB on the desktop, and about 430 MB in the browser, where NumPy's numbers and pointers are half the size. The aim in DP225 was 300 to 400 MB, so the desktop is somewhat over it. Before: 10.4 GB.
* Reading it: about 1 second, in place of 37 seconds.
* Pack size: about 100 MB more, so about 1,070 MB in place of 968 MB.
* Writing: about the same time. Up to about 0.5 GB more memory at the end, where the table is put together.

### World, 612,356 features

* Feature table in memory: about 50 MB, in place of 1.3 GB.
* Reading it: about 0.1 seconds, in place of 4.2 seconds.
* Pack size: about 10 MB more.

## Tests

* New: tests/mapcore/test_feature_table.py, 16 tests. A format 5 pack has the table and it matches the records. The store gives the same answers from a new pack and from the same pack written as format 4: what is at 10 points, Nearby, search, the view at 3 zooms, and two packs merged. An old pack still opens. The group and record caches stay within their limits. A damaged table falls back to the records.
* Changed for the new format number: tests/mapcore/test_pack_format.py (and a test that a format 4 pack is still read), tests/mapdata/test_lines_and_points.py and tests/mapdata/test_pipeline.py.
* Python tests in tests/mapcore: 1,743 passed.
* Writing and pack tests in tests/mapdata: 113 passed.

## Left over

* The writing stage must be run again for the world pack, about 1.5 hours, and the England pack, about 1 hour 40 minutes, to give them the feature table. Then P4-T3d's memory measurement in the browsers can be run again.
* The desktop's feature table for England is estimated at 540 MB, above DP225's 300 to 400 MB. It could be brought down by not keeping a list of feature numbers and a list of layer names beside the layer numbers, about 100 MB for England. Not done, to keep the store's working the same.
* Each feature's relationships, once read, are still kept for as long as TobyMap runs, a feature group at a time. That was outside this task.
* The rehearsal's folders in working/hampshire-isle-of-wight-time-stage, write-p4t3f-old, write-p4t3f-new, write-p4t3f-new2, write-p4t3f-v2 and write-p4t3f-v2b, can be deleted. The first new and new2 folders hold an earlier draft of the table, before the numbers were stored as whole numbers.
