# P4-T2a report: the England estimate

Written by Claude Code on 26 November 2026, for the product owner. It is the first work item of P4-T2, the England pack. Nothing heavy has run. The build, P4-T2b, waits for your go-ahead.

## In short

* England holds about 20 times the rehearsal's features, layer by layer (between 18 and 24 times). That is less than its land, which is about 26 times the rehearsal's, because Hampshire is mapped more densely than most of England.
* Size: about 850 MB, likely between 700 MB and 1 GB. That is probably under PCK-1's 1 GB, so probably no split is needed. P4-T2c will measure the real size.
* Features: about 6 million, likely between 5.5 and 7.5 million.
* Time: about 6 hours with 3 workers, likely between 5 and 8.5 hours. With --away (6 workers), about 4.5 to 7 hours. Either way it is an overnight run.
* Memory: every stage is expected to stay under the 12 GB aim for one process. The highest are matching with the world pack (up to about 9.5 GB), streets (about 8 GB), the checks (about 8 GB) and villages (about 7.5 GB). The first four stages have never been measured, so they are the least certain.
* Space: about 20 to 25 GB of stage folders. The drive has 387 GB free.
* Ready to build: the England outline is fetched, the settings file is made, and every source is in place.

## How the estimate was made

### England against the rehearsal, counted

I counted the main kinds of feature in England's coverage and in the rehearsal's coverage. The counts came from your United Kingdom library, uk.gol, which is a light read. Each coverage is the pack tiles that the build will cover. The ratios, England over the rehearsal:

* Streets and main roads: 3.8 million ways against 209,000, 18.3 times.
* Paths and tracks: 18.1 times.
* Land use areas: 19.2 times. Natural areas such as woods and heath: 14.7 times.
* Parks and public spaces: 20.3 times.
* Water areas: 21.2 times. Streams and ditches: 21.3 times.
* Bus stops: 20.7 times. Crossings: 16.9 times.
* Shops: 24.3 times. Other amenities: 20.7 times. Benches and bins: 22.6 times.
* Villages, suburbs and hamlets: 20.1 times.
* Parishes: 18.4 times.

The ways are counted a little low for England, because a way that crosses a reading box's edge is counted once in each box, and the rehearsal has more edges for its size. So 20 times is used for the whole, with 18 and 24 as the range.

### The coverage

* England's coverage will be 4,865 pack tiles of tile level 12: 141,000 km2, of which 132,000 km2 is land. It reaches a little into Wales and Scotland at the borders.
* The rehearsal's coverage is 189 pack tiles: 5,700 km2, of which 5,100 km2 is land.

### Time and memory

Each stage's time and peak memory come from the rehearsal's rebuild after the memory work (P4-T1m), in the build log. Each is scaled by 20 times. For memory, the program's own 0.25 GB and each worker's share are not scaled, as they stay the same whatever the region.

## Size by layer

The rehearsal's size by layer, times that layer's own ratio:

* The pack's own records (search, relationships, the directory): about 240 MB.
* Land use: about 170 MB.
* Streets and minor roads: about 120 MB.
* Paths and tracks: about 85 MB.
* Stops and crossings: about 35 MB.
* Services and amenities: about 30 MB.
* Shops, cafes and pubs: about 25 MB.
* Lakes: about 25 MB.
* Post boxes, benches and bins: about 20 MB.
* Parks and public spaces: about 15 MB.
* Streams and ditches: about 15 MB.
* Parishes: about 10 MB.
* Every other layer: about 20 MB together.
* In all: about 810 MB. uk.gol is from October 2025, and OpenStreetMap grows a few percent a year, so about 850 MB.

## Time for each stage

With 3 workers:

* Stages 1 to 4, the countries and counties from the planet file, the grid squares, the joining and the coverage: about 30 minutes to 1 hour. These were not timed in the rebuild, and England's box is about 50 times the rehearsal's, so this is the least certain part.
* Parishes, small islands, lakes, ponds, rivers, streams and the main lines: about 10 minutes.
* Streets, main roads and paths: about 25 minutes.
* Land use, parks and school grounds: about 30 minutes.
* Points of interest: about 15 minutes. Villages: about 3 minutes.
* Matching with the world pack: about 7 minutes.
* Wikidata: about 30 to 45 minutes, as most of England's facts have not been fetched yet.
* Relationships: about 1.5 to 2 hours.
* Coast stretches and correction rules: about 5 minutes.
* Writing the pack: about 2 to 2.5 hours. Splitting full pack tiles is most of this time (P4-T1m).
* Checks: a minute or two.
* In all: about 6 hours, likely 5 to 8.5.

With --away, relationships and writing share their work among 6 workers, so about 4.5 to 7 hours.

## Peak memory for each stage

These figures are for one process, assuming memory grows in step with the features:

* Parishes and districts: about 1.5 GB.
* Streets: about 8 GB. This reading stage holds every way in England at once while it joins them, and reads the records of the stage before in full.
* Land use: about 5 GB. Points of interest: about 4.5 GB. Villages: about 7.5 GB.
* Matching with the world pack: up to about 9.5 GB. P4-T1l estimated 4 to 6 GB, as part of what it holds is the world pack, which does not grow with England.
* Wikidata: about 4 to 5 GB (P4-T1l).
* Relationships: the stage's own process about 5.5 GB, each worker about 0.6 GB, so about 7.5 GB together with 3 workers and 9 GB with 6.
* Coast stretches and correction rules: about 4 GB each.
* Writing: the stage's own process about 5.5 to 7 GB, about 6.5 to 7.5 GB with its workers (P4-T1m).
* Checks: up to about 8 GB, though it opens the pack as the application does and should need less.
* Stages 1 to 4: not measured on the rehearsal.

So no process is expected over 12 GB. The margin is smallest for streets, villages, matching and the checks. The memory work (P4-T1l, P4-T1m) did not change those stages, as the rehearsal showed them as light. With 17.7 GB free now and your programs open, the build fits. It has more room overnight with --away.

## What was got ready

* The England outline, Geofabrik's england.poly, is fetched into the downloads folder. It is listed as the source england-outline in mapdata/config/sources.yaml and in data sources.md: ODbL 1.0, as the Great Britain outline is.
* The settings file mapdata/config/packs/england.yaml is made from great-britain.yaml, which is kept for later. Only the lines marked "region:" differ: the name, the title, the outline, the box (England's outline widened by 0.1 degrees: 7.21 west to 2.35 east, 49.47 to 56.17 north), the space needed (40,000 MB) and the check places.
* The checks stage of the England build will check the rehearsal's 20 Hampshire places, as they are all in England. P4-T2d adds places away from Hampshire.
* A test now checks that england.yaml has the same stages as great-britain.yaml, and the regional pack tests cover it. 88 tests pass.
* mapdata check --pack england says the build fits in the free space and the data folder is ready. mapdata fetch --pack england says all 7 sources are ready: the planet file of 26 October 2026, the land polygons, the oceans, the marine areas, the England outline, the world pack of 21 November, and Wikidata.

## Things to know before the build

* The build reads the world pack of 21 November for its identifiers. If the world pack is rebuilt later, for P4-T13 groups of islands, the England build reruns from the matching stage onwards: about 4 to 5 hours, not the whole build.
* The run switch, continue.txt, says yes. Saying no stops the build cleanly after the stage it is on, and the next build carries on from there.
* The build will be watched for stalls, and each stage's peak memory will be checked against the 12 GB aim as it finishes.

## Your choice

1. P4-T2b, the England build, overnight with --away: about 4.5 to 7 hours. Should it start tonight? The laptop will be busy and may be slow while it runs.
