# P4-T1m the writing stage group by group: report

27 November 2026. The rest of the memory work begun in P4-T1l (docs/plan/p4-t1l-memory-report.md). The aim: no process above 12 GB for the England build.

## In short

* The writing stage no longer holds every feature in memory several times over. Its own process on the Hampshire and Isle of Wight rehearsal now peaks at 490 MB, against 1,095 MB before.
* The pack is the same, byte for byte, as the build's own.
* For England, the writing stage should need roughly 5 to 7 GB, against 20 to 30 GB before: within the aim.
* The rehearsal rebuild found a fault from P4-T1l's fix to the reading boxes, now fixed (below).

## What changed

* Feature numbers are worked out from the identifiers alone, before any feature record is made.
* Each feature record is set aside on disk as it is made, in a temporary file beside the pack, deleted at the end. Only the records of the world tree's layers (continents, countries, regions, counties) and the condominiums stay in memory.
* The relationships are read from the relationships stage straight into a second file on disk. Only those the stage changes, such as an area's counts, are kept in memory.
* The feature records and relationships are then written to the pack one feature group at a time, about 256 features each.
* Each pack tile's record is made and compressed in the worker processes, and set aside on disk until it is written. Before, the main process held every pack tile and compressed them one by one.
* The feature records are made before the cutting into pack tiles, so the records read from the stage before are let go before the cutting starts. On the world pack, where some parts are measured slowly in the background, they are still made after the cutting, as before.
* What each area holds is kept as lists of feature numbers, not sets (in the core, mapcore/store/contents.py: the same result, less memory).
* The search index keeps only what it needs of each named feature while it is made, and each of its rows once, however many search records it is filed in.
* Splitting full pack tiles now shares one full pack tile's entries among the workers. It saved only about 40 seconds on the rehearsal, so splitting is still most of the stage's time (below).

## Measurements on the rehearsal, the writing stage alone

Run with tools\time_stage.py hampshire-isle-of-wight write --workers 3. 306,860 features.

### Before

* The stage's own process: 1,095 MB.
* The largest worker: 483 MB.
* All together: 1,418 MB.
* Time: 361 seconds.

### After

* The stage's own process: 490 MB. Its peak is now while it reads the records at the start, not while it writes.
* The largest worker: 205 MB.
* All together: 897 MB.
* Time: 398 seconds. The run before was 361; each run differs by about a minute on the laptop.
* The pack and its checksum file: the same, byte for byte.

## The rehearsal rebuilt

Rebuilt on 27 November with mapdata build hampshire-isle-of-wight --workers 3, after the fault below was fixed. Stages 1 to 4 were skipped, as nothing they use had changed; the rest ran again.

* Check places: 20 of 20 pass.
* The pack: 43.2 MB, 328 pack tiles, 329,880 tile entries, as before.
* Time: 14 minutes 38 seconds, against 19 minutes 18 seconds on 26 November.
* The largest peak of any stage, all processes together: 1,460 MB, in relationships. Before P4-T1l it was 2.1 GB.
* Writing, from the build log: the stage's own process 522 MB, the largest worker 207 MB, all together 933 MB, in 5 minutes 24 seconds.
* Wikidata's own process peaked at 1,125 MB, now the largest single process on the rehearsal.

## The estimate for England

England has about 6 to 9 million features, about 29 times the rehearsal's land.

* The program itself: about 0.25 GB.
* What the stage reads at the start, the records and their strings: about 0.8 KB a feature, so 5 to 7 GB. This was there before too; the steps of writing no longer add to it.
* Each worker: about 0.2 GB on the rehearsal; the parts each cuts are of about the same size whatever the region.

So about 5 to 7 GB for the writing stage's own process. The estimate is a straight line from one small region; England's own peaks will be in the build log.

## Time

Splitting full pack tiles still takes about 190 of the stage's 400 seconds. Scaled to England, about 1.5 hours. It does not affect memory. A faster way would cut a large region's features at a deeper tile level from the start, but that could change the pack's bytes, so it is left for now.

## A fault found by the rebuild

P4-T1l's fix to the reading boxes (9c9fff1) kept every record with no shape, so osm-water's count record was not lost. But it also kept land areas whose shape was empty, and the land stage's joining failed on them: "IndexError: index 106397 is out of bounds". Now only count records are kept without a shape; a feature with an empty shape is left out, as before. A test covers both.

## Files

* mapdata/pipeline/spill.py: new. Values set aside on disk by number, and the relationships store.
* mapdata/stages/pack_write.py: the writing, as above.
* mapdata/stages/write.py: reads the relationships into the store.
* mapdata/stages/relationships.py, coast_stretches.py: the relationships changed one feature at a time as they are read.
* mapdata/stages/search_index.py: the leaner search index.
* mapcore/packs/pack.py: PackWriter writes feature records and relationships a group at a time, and takes pack tiles already compressed.
* mapcore/store/contents.py: lists in place of sets.
* mapdata/stages/osm_source.py: the reading box fix.
