# P4-T1l memory work: first report

26 November 2026. The memory aim (design docs/plan/p4-t1-design.md 7.4): no process above 12 GB for the England build.

## In short

* Done: the relationships, Wikidata, match, coast stretches and corrections stages now hold far less, and should fit England within the aim.
* Not yet: the writing stage. It is smaller than before, but still grows by about 3.4 KB a feature, so England would need about 20 to 30 GB in one process. It needs a change in how it works, described below, before the England build.
* Every changed stage was run alone on the Hampshire and Isle of Wight rehearsal and compared with the build's own output. All are the same, byte for byte, except relationships, where 30 of 306,860 features differ in rounding only (explained below).
* The build log now says each stage's peak memory, for the England build.

## How it was measured

A new tool runs one stage alone on a pack's kept stage folders, timed, says its peak memory, and compares its files with the build's, byte for byte:

* .venv\Scripts\python.exe tools\time_stage.py hampshire-isle-of-wight relationships --workers 3 --label now
* Each progress line starts with the time and the stage's own memory at that moment, to show which step holds the most.
* The peak is the build's own process, its largest worker, and all of them together, looked at every half second (mapdata/pipeline/peak.py). The build now writes the same sentence after each stage.

The rehearsal has 306,860 features. The program itself takes about 0.25 GB before any data.

## Peak memory, before and after, on the rehearsal

### Wikidata

* Before: 1,448 MB. After: 1,085 MB.
* It now reads the records alone and keeps the shapes file as it is. It reads the shapes only of the features matched by name, a few thousand.
* Most of what is left is the Wikidata facts file (96 MB of text), the same size whatever the region.

### Relationships

* Before: the stage's own process 1,478 MB, the largest worker 1,106 MB, all together 1,761 MB, in 373 seconds.
* After: the stage's own process 478 MB, the largest worker 583 MB, all together 1,382 MB, in 347 seconds.
* How: the light layers (streets, paths, land use and the like) are compared only with the other areas. So the other features are related first, as before. Then the light features are related in batches of features near each other, each batch in a worker with the areas cut to the batch's box. A batch holds about 400,000 points, whatever the size of the region. Only each light feature's finished relationships come back.
* Before, the whole rehearsal fell in one box of 45 degrees, so one worker did all the work. Now the batches share the work among the workers.
* The world pack has no light layers, so it is related exactly as before.

### Writing

* Before: the stage's own process 1,749 MB, all together 2,003 MB, in 465 seconds.
* After: the stage's own process 1,096 MB, all together 1,404 MB, in 407 seconds. The pack is the same, byte for byte.
* How: the shapes are read from the stage folder each time a step needs them, not all held; the cut parts stay in well-known binary, not as shapes; the relationships are read straight into their form by identifier; each record is replaced by its feature record as it is made; and the search index rows share their repeated words.

### Match, coast stretches and corrections

* Match 675 MB, coast stretches 418 MB, corrections 399 MB. Each is the same, byte for byte, as the build's.
* They now share each repeated short word in the records (a third less memory for the records) and write their files as they go, not as one long text first.

## The estimate for England

England's land is about 29 times the rehearsal's, so about 6 to 9 million features. Each stage's memory beyond the program itself, scaled:

* Wikidata: about 0.4 KB a feature for the records, so about 4 to 5 GB.
* Match: about 4 to 6 GB.
* Relationships: the stage's own process about 0.75 KB a feature, so about 5 to 7 GB; each worker about 0.6 GB whatever the region, so 2 GB with 3 workers.
* Coast stretches and corrections: about 0.5 KB a feature, so about 4 to 5 GB.
* Writing: about 3.4 KB a feature, so about 20 to 30 GB. Over the aim.

These are straight-line estimates from one small region; England's own peaks will be in the build log.

## What the writing stage still needs

The writing stage holds a Python record for every feature, several times over: the feature record, its relationships, its search rows and what each area holds. At millions of features, Python's own cost for each record (about 1 KB) is the problem, not the shapes.

The pack already keeps its feature records, relationships and contents in groups (features/G, relations/G, holds/G). The proposed change, as work item P4-T1m:

* Number every feature from the identifiers alone, as the pack writer does now: a list of identifiers, not records.
* Make, write and let go of the feature records, relationships and search rows one group at a time, in the workers. Keep in the main process only what joins the groups: the areas' records (few), the counts of what each area holds, and the search index's rows in a compact form.
* Keep the pack the same, byte for byte, on the rehearsal and on the test pack, as now.

If that proves too slow to build or too large a change, the other way is to build England as a few regional packs, combined in the application (P4-T3). That would be your decision, as it changes what you download.

## Time

* Splitting full pack tiles took about 250 to 300 of the writing stage's 400 seconds on the rehearsal. Scaled to England, that is about 2 hours. Not a memory problem, but worth a look in P4-T1m, as it is done one tile level at a time.

## Rounding in relationships

30 of the rehearsal's 306,860 features have relationships that differ from the build's, because the sums are added in a different order:

* A share differs in its fourth decimal place, such as 0.4995 against 0.4994; the largest difference is 0.0006.
* A track that enters several areas at one point lists them in another order, such as the United Kingdom, England, Hampshire and Test Valley instead of Hampshire, Test Valley, the United Kingdom and England. Both orders are right.

No feature gains or loses a relationship.
