# P4-T2 report: the England pack

Written by Claude Code on 27 November 2026, for the product owner. It covers P4-T2b (the build), P4-T2c (the size) and P4-T2d (the checks). P4-T2a, the estimate, is in docs/plan/p4-t2a-estimate-report.md. P4-T2e, building it twice, waits for your yes.

## In short

* The England pack is built: E:\osmdata\tobymap\output\england\england.pack, 968.3 MB, 6,328,884 features, 7,117 pack tiles.
* It is under PCK-1's 1 GB, so no split is needed. It is larger than the estimate of about 850 MB, inside its range of 700 MB to 1 GB.
* Every check passes: 45 of 45 check places (Hampshire's 20 and 25 new ones from the rest of England), the streets, the islands and the sea off Cornwall.
* Step timing meets NFR-1 easily: over 1,000 steps, 99.3 percent were announced within 150 ms, against the 95 percent needed. The median step took 7 ms.
* The build found one slow step in writing the pack, which would have taken about 7 hours. It is fixed: the same result, in under 7 minutes.
* The villages stage used 13.0 GB in one process, over the 12 GB aim. The laptop had room, but it is worth fixing before a larger build.

## The build, P4-T2b

The build ran with --away (6 workers) from 20:44 on 26 November, under a supervisor that would restart it with fewer workers if memory ran out. Memory never ran out.

### The slow step, and its fix

Writing the pack starts by measuring each island's shore on each lake (P3-T32g). Every lake in England is inside the island of Great Britain, so for each of England's 170,012 lakes the step cut Great Britain's whole outline, 170,904 points, into short steps and tested them all against the lake. Measured on England's own data, that would have taken about 7 hours, and writing would have ended about 8 in the morning.

I stopped the build after 21 minutes of writing, and changed two things in mapdata/stages/write.py:

* Only the parts of an island's outline near the lake are cut and tested. A part of the outline far from the lake has no point near it, so it never counted towards the shore.
* The islands near each lake are found by their bounds alone. Before, the exact distance to Great Britain's outline was worked out for every lake, which alone took 35 minutes.

The result is the same, checked three ways:

* On the Hampshire rehearsal, everything the step stores is the same as before: 451 islands with a shore on a lake.
* On England, 2,365 island and lake pairs, nearly all of them near the coast, gave the same length to the last digit.
* On England, 3,000 lakes found the same islands, in the same order.

On all of England, the step now takes 6 minutes 50 seconds. A new test, in tests/mapdata/test_lake_shores.py, checks that the new way gives the same length as the old.

The build was then started again. Stages 1 to 20 were kept, and only writing and the checks ran.

### Time for each stage

* Stages 1 to 4, the countries, the grid squares, the joining and the coverage: 5 minutes. The estimate was 30 minutes to 1 hour.
* Stages 5 to 11, the parishes, small islands, lakes, ponds, rivers, streams and main lines: 10 minutes.
* Stage 12, streets, main roads and paths: 14 minutes.
* Stage 13, land use, parks and school grounds: 10.5 minutes.
* Stage 14, points of interest: 3.5 minutes. Stage 15, villages: 3.5 minutes.
* Stage 16, matching with the world pack: 3.5 minutes.
* Stage 17, Wikidata: 8 minutes.
* Stage 18, relationships: 1 hour 6 minutes.
* Stages 19 and 20, coast stretches and correction rules: 4 minutes.
* Stage 21, writing the pack: 1 hour 41 minutes, of which splitting full pack tiles took 45 minutes.
* Stage 22, the checks: under a minute.
* In all, without the slow step: about 4 hours, at the low end of the estimate of 4.5 to 7 hours.

### Peak memory for each stage

For the build's own process, against the 12 GB aim:

* Stages 1 to 11: under 1.3 GB each.
* Streets: 10.6 GB. The estimate was 8 GB.
* Land use: 8.6 GB. The estimate was 5 GB.
* Points of interest: 9.4 GB. The estimate was 4.5 GB.
* Villages: 13.0 GB, over the aim. The estimate was 7.5 GB.
* Matching: 5.5 GB. Wikidata: 5.4 GB.
* Relationships: 6.6 GB, and 10.9 GB with its 6 workers.
* Coast stretches: 9.1 GB. Correction rules: 7.7 GB.
* Writing: 7.6 GB, and 13.7 GB with its 6 workers.
* Checks: 10.6 GB.

The stages that read from the planet file used about twice the memory estimated. The estimate scaled the rehearsal's memory by the number of features, but these stages also hold every way and area of England's reading boxes at once, which grows faster. The memory work of P4-T1l and P4-T1m did not change these stages, as they were light on the rehearsal. The laptop had 13 GB or more free throughout.

## The size, P4-T2c

968.3 MB. The largest layers:

* The pack's own records (search index, relationships, directory): 317 MB. The estimate was 240 MB.
* Land use: 184 MB, 1,522,257 features.
* Streets and minor roads: 145 MB, 1,558,870 features.
* Paths and tracks: 97 MB, 965,782 features.
* Stops and crossings: 38 MB. Shops, cafes and pubs: 27 MB. Services and amenities: 26 MB.
* Lakes: 25 MB, 170,012 features, nearly all of them ponds and unnamed water.
* Streams and ditches: 22 MB. Post boxes, benches and bins: 21 MB. Parks and public spaces: 18 MB.
* Parishes and communities: 17 MB, 10,760 features.
* Every other layer: about 30 MB together.

As it is under 1 GB, nothing is split or left out. Unnamed land use stays, as you decided on 26 November. A later England build may pass 1 GB as OpenStreetMap grows. The largest share to look at then would be the pack's own records.

## The checks, P4-T2d

### Check places

The new file tests/acceptance/street_places_england.yaml holds 25 places away from Hampshire. The England pack's checks stage now reads it as well as the Hampshire file. All 45 places pass.

* The north: Roundhay Park in Leeds, Briggate in Leeds, Haworth (in Haworth and Stanbury parish), Hebden Bridge (in Hebden Royd), Heaton Park in Manchester, Grey Street in Newcastle, York Minster, Durham Cathedral, Hexham, Whitby, Keswick in the Lake District National Park, and Berwick-upon-Tweed.
* The east, London and the south-west: Norwich Cathedral, King's College in Cambridge, Hyde Park in London, and Truro Cathedral.
* The spike S2 coastline places that lie in England: London, and the Isle of Wight in its own county. The Solent is in the Hampshire file.

### Islands and the sea (DAT-3)

* The Isle of Wight is an island and its own county.
* St Mary's and Tresco are islands in the Isles of Scilly, a county of their own, each its own parish.
* Lindisfarne Priory is on the Holy Island of Lindisfarne, an island in Northumberland, in Holy Island parish.
* Lundy is an island in Devon.
* 2 km off Land's End, 2 km off the Lizard and 2 km off Newquay are said as the English Channel and the North Atlantic Ocean.

The England pack covers the land and the sea close to it, out to the edge of its pack tiles. In places this edge is only 1 to 2 km offshore: a point 2 km off St Ives or Bude is outside it, and the England pack alone has nothing there. When the England pack is used with the world pack (P4-T3, combining packs), the world pack says the sea there. The S2 sea places farther out (south of the Isle of Wight, the Dover Strait, the Irish Sea) are outside the England pack for the same reason. They are checked on the world pack.

### Streets

Through the application's own core (MapSession), going to a point on each street:

* Deansgate in Manchester: in Nearby, 11 metres west.
* Oxford Street in London: in Nearby, 5 metres north.
* Stonegate in York: in Nearby, 1 metre south-east.
* Grey Street in Newcastle: in Nearby, 6 metres east.
* Briggate in Leeds: search finds it, and going to it says "Briggate, Leeds, England, United Kingdom".

### Step timing (NFR-1)

1,000 steps of 50 metres at a zoom of 1 km, through MapSession, in five places, the England pack alone:

* Leeds city centre: median 9.2 ms, 95th percentile 14.3 ms.
* Central London: median 7.3 ms, 95th percentile 13.8 ms.
* Manchester: median 10.9 ms, 95th percentile 13.5 ms.
* Keswick and Derwentwater: median 5.0 ms, 95th percentile 7.9 ms.
* Penzance to the sea: median 6.0 ms, 95th percentile 9.1 ms.
* All 1,000 steps: median 7.3 ms, 95th percentile 13.5 ms, slowest 252 ms. 99.3 percent within 150 ms; NFR-1 needs 95 percent.

7 steps took over 150 ms, between 151 and 252 ms. Their cause was not looked into; the likeliest is a step into pack tiles not read before. Opening the pack and saying the first place took 0.3 seconds.

## Things to know

* The villages stage (osm-places) used 13.0 GB in one process, over the 12 GB aim. Streets, the points of interest, coast stretches and the checks were between 9 and 10.6 GB. A larger region, or England in a year or two, could pass the aim in these stages. They could be changed to read and keep less at once, as relationships and writing were in P4-T1l and P4-T1m.
* At drawing level 1 (wide zooms, up to 150 km), lakes hold 532,391 points over England, far more than the aim of about 10,000 points a layer for one frame (VIS-1). Most are small ponds. The drawing timing has not been measured on England. If wide zooms over England draw slowly, the lakes' smallest size at that level is the setting to raise.
* One correction rule found no feature: the Inner Seas off the West Coast of Scotland, which is not in England. This is expected.
* The fix to the lake shore step changes the writing stage's fingerprint, so the next world or trial build reruns writing and the checks. Its pack should be the same byte for byte, as the fix gave the same result on the rehearsal and on England.

## Your choice

1. P4-T2e: build England a second time and compare it byte for byte with the first (DMT-1). About 4 hours with --away, overnight. Should it run, and when?
