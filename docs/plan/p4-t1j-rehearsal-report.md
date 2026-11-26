# P4-T1j report: the Hampshire and Isle of Wight rehearsal

Written by Claude Code, 26 November 2026, for the product owner. Design: docs/plan/p4-t1-design.md sections 7 and 9 (P4-T1j).

## In short

* The rehearsal pack is built: 43.22 MB, 306,860 features in 25 layers, in 19 minutes 18 seconds with 3 workers. Peak memory was 2.1 GB.
* All 20 street check places pass.
* The rehearsal found five faults, now fixed and tested (listed below).
* The estimate for Great Britain: about 1.3 GB, likely between 1.1 and 1.5 GB. That is over PCK-1's 1 GB, so P4-T2b must propose a split or what to leave out. Nothing has been cut.
* Time: about 8 to 12 hours with --away, an overnight run.
* Memory is the main risk. Scaled from the rehearsal, the relationships and writing stages could need well over 12 GB for Great Britain. They should be changed to load only the layers they need before the Great Britain build (design 7.4).

## The build

* Built twice today from the planet file of 26 October 2026. The first build, at 14:05, showed the faults below. The second, at 16:23 after the fixes, is the pack described here.
* The pack: E:\osmdata\tobymap\output\hampshire-isle-of-wight\hampshire-isle-of-wight.pack, with its quality report beside it.
* The coverage: 57 pack tiles of tile level 12, 5,653 km2 of land and sea, reaching a few kilometres into Dorset, Wiltshire, Berkshire, Surrey and West Sussex.

### Time for each stage, second build, 3 workers

* Reading the administrative levels below the counties: 8 seconds.
* Small islands, the named areas layer, rivers, roads and railways: 1 or 2 seconds each.
* Lakes and ponds: 8 seconds. Streams and ditches: 8 seconds.
* Main roads, streets and paths: 1 minute 45 seconds (4 minutes 31 seconds in the first build, before fix 2).
* Land use, parks, school grounds and national parks: 1 minute 40 seconds.
* Points of interest: 42 seconds. Villages: 7 seconds.
* Matching with the world pack: 18 seconds.
* Wikidata: 15 seconds, as the facts were fetched by the first build (1 minute 22 seconds then).
* Relationships: 6 minutes 21 seconds.
* Coast stretches and correction rules: 7 seconds together.
* Writing the pack: 7 minutes 11 seconds.
* Checks: 2 seconds.
* Earlier, unchanged since: the countries and divisions from the planet file 1 minute 53 seconds, grid squares 13 seconds, joining 1 second, coverage under 1 second.

### Peak memory for each stage

The total of the build's Python processes, sampled every 10 seconds. The stages before the streets were not sampled; they are short and light.

* Streets: 1.1 GB, the largest process 0.9 GB.
* Land use: 0.8 GB. Points of interest: 0.9 GB. Matching: 0.6 GB.
* Wikidata: 1.4 GB.
* Relationships: 1.8 GB, the largest process 1.5 GB.
* Writing: 2.1 GB, the largest process 1.8 GB.
* Free memory stayed above 17 GB throughout.

### Space

The stage folders of the second build take about 1 GB in the working folder.

## Faults found and fixed

Each fix has a test in tests/mapdata (test_match, test_osm_source, test_coverage, test_land).

1. The reading stages that the rehearsal shares with the world (lakes, rivers, roads, railways and villages) read the outline's box, not the coverage, so their features reached beyond the coverage. The matching stage now cuts every feature to the coverage first: in the second build, 373 features were cut at its edge and 1,097 wholly outside it were left out (mapdata/stages/match.py).
2. Each reading box is a level 8 pack tile, and at the coverage's edge most of it lies outside. A reading box now keeps only the shapes within about 2 km of the coverage, enough for joining across its edge. This more than halved the time of the streets stage (mapdata/stages/osm_source.py).
3. GeoDesk refused a query with a value such as drive-through unless it is in quotes. Such values are now quoted when a query is passed to GeoDesk (mapdata/stages/osm_source.py).
4. Cutting a line to the coverage could leave a line of no length, which broke the joining of the cut parts. Empty parts are now dropped (mapdata/stages/coverage.py).
5. Several land use and parks classes named a Shortbread layer that does not hold them. Each class now names the right layer, or none (mapdata/config/land_classes.yaml).

## The check places

tests/acceptance/street_places_hampshire.yaml, 20 places, all passing. Each names the areas that must contain it, checked against the pack with mapdata inspect:

* Winchester, Southampton, Portsmouth, Basingstoke and Fareham town centres, which have no civil parish and say "Unparished area".
* Parishes in districts: Lymington and Pennington, Ringwood, Romsey, Andover, New Alresford.
* The national parks: Lyndhurst, Brockenhurst and Beaulieu in the New Forest National Park, Petersfield in the South Downs National Park, Yarmouth in the Isle of Wight National Landscape.
* The Isle of Wight, an island and a county of the same name: Newport, Cowes, Ryde, Ventnor.
* Portsmouth is on Portsea Island, not the island of Great Britain.
* The Solent, as sea.

The checks stage checks only which areas contain a place, not what Space says there. The design asked for both; checking Space needs the core, and is left for the acceptance scripts of P4-T3e.

## Estimate for Great Britain

### How it was made

Each layer of the rehearsal pack is multiplied by the United Kingdom's count over the count in the rehearsal's box (both from design section 3 and docs/plan/p4-t1f-poi-categories.csv). That is then divided by 0.724, as the coverage is 72.4 percent of the box the counts were made in, and multiplied by 0.97 to leave out Northern Ireland.

* Where no count was made (land use, parks, school grounds, streams), the design's 25 times the box is used.
* The outlines and the coast layers (counties, countries, islands, seas, rivers, national parks) are scaled by land area instead: Great Britain's land is about 55 times Hampshire and the Isle of Wight's.
* Villages are scaled from the United Kingdom's 90,219.
* The pack's own records (search, relationships, the directory) are scaled by the number of features.

### Size by layer, largest first

* The pack's own records: about 360 MB.
* Land use: about 315 MB, 2.6 million features.
* Streets and minor roads: about 190 MB, 2.1 million features.
* Paths and tracks: about 135 MB, 1.3 million features.
* Lakes: about 37 MB.
* Stops and crossings: about 36 MB.
* Parishes and communities: about 32 MB.
* Services and amenities: about 30 MB.
* Parks and public spaces: about 28 MB.
* Streams and ditches: about 26 MB.
* Shops, cafes and pubs: about 25 MB.
* Post boxes, benches and bins: about 20 MB.
* Every other layer: about 60 MB together.
* In all: about 1.3 GB, 8.7 million features, about 28 times the rehearsal.

The design's estimate was 800 MB; the difference is mostly land use (more features survive the joining than expected) and the pack's own records, which take 29 percent of the rehearsal pack.

### Time

Each stage scaled by its own layers, assuming time grows in step with the features:

* Reading from the planet file: about 2.5 to 3 hours together, most of it streets and land use.
* Wikidata, fetching facts the first time: up to about 40 minutes.
* Relationships: about 3 hours.
* Writing: about 3.5 hours with 3 workers, perhaps 2 with 6.
* In all: about 10 hours with 3 workers, 8 with --away, up to 12 if relationships or writing grow faster than the features do.

### Memory

* Measured: relationships held about 1.5 GB in one process and writing about 1.8 GB, for 307,000 features. Allowing about 0.3 GB for the program itself, that is about 4 KB a feature.
* Scaled to 8.7 million features, one process would need 35 GB or more, far over the 12 GB aim and the laptop's 32 GB.
* P4-T1k estimated 8.7 GB at the peak, from 4 million features at about 1.2 KB each. The rehearsal shows both figures were low.
* So before the Great Britain build, the relationships, writing and Wikidata stages should load only the layers they need, or the pack should be split. Splitting alone (England is about 57 percent of Great Britain's land, but holds most of its streets) may not bring England under 12 GB.

### Space

About 30 GB in the working folder (1 GB times 28), plus the pack. The data folder has room. great-britain.yaml's space_needed_mb of 150,000 can come down to about 60,000.

## Things noticed for later

* The Solent has no name of its own: Natural Earth has no Solent, so Space there says the English Channel.
* The quality report says "No county covers 9,577 km2 of England". That figure comes from the joining stage, which works on the wider box read before the cut to the coverage. Every point tried inside the coverage has its county. The report should measure gaps inside the coverage only (for P4-T11a).
* The correction rule for the Inner Seas off the West Coast of Scotland is reported as "not found", as that sea is not in the rehearsal. In Great Britain it will be found.
* Matching with the world pack: 99 features kept the world's id and 6 were matched by name, type and overlap (A3, A34, the West of England Line and others). Each match by name should be looked at in P4-T3.
* Wikidata matched 105 features by name. Some look doubtful, such as six parts of Brookly Stream, mapped as water areas, all given one Wikidata item. P4-T11a's report lists them.

## Choices for the product owner

1. The pack is likely over 1 GB. The design's options: split Great Britain (England, Scotland and Wales as three packs), or leave things out. The largest that could go: unnamed land use such as farmland and woodland (land use is about 315 MB plus its share of the records, about 420 MB in all), street furniture (about 30 MB with its records), unnamed service roads. P4-T2b will set these out for you.
2. Before the Great Britain build, the stages that load every feature should be changed to load only the layers they need. This is a new work item, after P4-T1j and before P4-T2. Should it be done first?

### The product owner's answers, 26 November 2026

1. Build England only, not all of Great Britain: it is large enough to be useful and is the area the PO knows best for testing. Unnamed land use stays: it is named by its use, such as "Farmland" or "Woodland" (docs/design/explanation.md, "How land use with no name is named").
2. Yes: the build must avoid using too much memory, so that work comes first.
3. National parks are said first.
