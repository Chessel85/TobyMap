# Spike S2 findings: countries, coastlines and islands

Task P0-T5. Architecture sections 6.12, 6.13 and 12.3. Stage 1 is complete (1 November). Stage 2 is complete, and stage 3 nearly so (2 November): see the next section. Stage 4, Argentina, is parked.

## Stages 2 and 3, 2 November

### What was built

* One build program now runs both stages from a settings file each: `.venv\Scripts\python.exe -m mapdata spike-s2 2` for Norway and Sweden, and `spike-s2 3` for Fiji, Russia, the USA, Kiribati and Antarctica. The settings are in mapdata/config/s2_stage2.yaml and s2_stage3.yaml, and the check places in tests/acceptance/coastline_places_stage2.yaml and coastline_places_stage3.yaml.
* It reads the planet file in its own short-lived process, as stage 1 recommended. That worked: each read took a few minutes and the memory was given back when the process ended.
* The reading boxes for the land polygons are now worked out from the countries' shapes and read in one pass: 5 for stage 2, 35 for stage 3.
* The counties layer follows discussion point 101, with the counties record in mapdata/config/county_levels.yaml.
* Areas are now worked out on the WGS 84 ellipsoid, not a sphere. A one-degree square at the equator is 12,308 km², which is the right figure; the old sphere figure was 12,364 km².
* New checks: islands shared between countries, land far from a country's largest part (for country units), and, for stage 3, the 180 degree line: bounding box and centre across the line, area against Wikidata, isolated drawing, the globe, and artificial edges.

### A fault in the OSM data: Russia's outline is not closed

* In the planet file of 22 November 2025, Russia's level 2 outline has one open end, 11 km wide, on the Perekop isthmus at the north of Crimea, between 46.1347 north, 33.6147 east and 46.2283 north, 33.6327 east.
* Because of that, GeoDesk could not form Russia's mainland at all. Its shape was 30 islands and the part of Chukotka east of the 180 degree line, with no mainland. Moscow was not in Russia.
* Fix in the build: when a country's outline has an open end shorter than half a degree, the member ways are joined and the gap is closed with a straight line. The repair is listed in the report. With it, Russia is one shape of 31 parts, and Moscow, Murmansk, Kaliningrad and Anadyr are all in it.
* The other countries checked, the USA, Fiji, Kiribati, Antarctica and Norway, have closed outlines.
* In this planet file, Russia's outline includes Crimea. This is a fact about the OSM data, recorded here for the PO.
* For Phase 1: the pipeline must check every outline is closed, and close or correct open ones with a correction rule (DMT-4), because one missing way can lose a whole country without any error.

### Stage 2: Norway and Sweden, complete

The run on the afternoon of 2 November passed every check. The report is in the data folder's tobymap\output\s2-stage2 folder, with the packs and six pictures.

Areas against Wikidata:

* Norway: 384,749 km² of land, Wikidata 385,207 km², 0.1% less. Norway's shape includes Svalbard, Jan Mayen and Bouvet Island.
* Sweden: 450,198 km², Wikidata 447,425 km², 0.6% more.
* Finland, as a neighbour: 338,481 km², Wikidata 338,478 km².

The counties layer, by the rule of discussion point 101:

* Neither country has anything at level 6. Norway has 357 municipalities at level 7, and Sweden 290, so both counties layers come from level 7 by the general rule, with no setting needed.
* Svalbard, Jan Mayen and Bouvet Island have no municipalities, so each is used as its own county, as the rule says: 60,531 km², 377 km² and 49 km².
* No land is left in no county.
* Both countries are now in the counties record, mapdata/config/county_levels.yaml. The second run read them from the record instead of working them out.

Gaps:

* No land within about 1 km of Norway or Sweden is in no country.
* No land in either country is in no region (level 4).

Islands:

* Norway's land is in 118,845 separate parts, with 7.4 million points. OSM has 150,133 named islands and islets there. 79,571 parts have a name and 39,273 have none. 17,444 parts are 1 hectare or more, of which 2,594 have no name; 758 are 1 km² or more.
* Sweden's land is in 64,135 parts, with 3.2 million points. 41,432 have a name and 22,702 have none.

Shared islands:

* No island at sea is shared between Norway and Sweden. Lakes and rivers count as land here, so any island in a border lake or river is joined to the mainland around it, and is not a separate island.
* Seven shared islands were found, all between Sweden and Finland, and all meet exactly across the border:
  * four in the mouth of the Torne river near Haparanda and Tornio: Kataja (two places where its halves meet), Hamppuleiviskä with Tirro, and Leppikari, with one more too small to have a name;
  * Märket, in the Åland Sea, in two parts, with borders of 311 m and 42 m across them. It is listed without a name, probably because island names were read only for Norway and Sweden, and Märket's name is likely recorded on the Finnish side.

Parts far from the mainland (for country units):

* Norway has land more than 1,000 km from its largest part in Svalbard (1,637 km² of it), Jan Mayen (377 km²) and Bouvet Island (49 km²).
* But most of Svalbard, 59,000 km², is closer than 1,000 km to the mainland, so the 1,000 km rule from architecture 6.12 would not, on its own, find Svalbard as a country unit. The rule needs a different test, such as a sea gap of more than 300 km.
* Sweden has no far parts.

Neighbours meeting exactly (AD-16):

* All five layers meet exactly after cleaning and after simplifying, with no overlap: the countries, Norway's regions and counties, and Sweden's regions and counties.
* Cleaning moved 2.9 km² among Norway's municipalities, and nothing measurable elsewhere.
* The check now looks only within 5 km of the land borders, where neighbours meet. Checking along every coast too took over half an hour per layer for Norway.

Packs and places:

* All 18 check places pass, including Oslo, Bergen, Longyearbyen, Stockholm, Visby, Haparanda and Tornio, and five points at sea.
* Compact coordinates make the pack 4.9 times smaller: 72.0 MB instead of 350.4 MB.
* A lookup takes 20.5 ms (median), at most 49 ms.
* The first run's lookups took 744 ms, because one pack tile held 332 of Norway's municipalities: 690,000 points, 2.9 MB. Pack tiles are now also split when their tile entries together have more than 20,000 points. That matters even more for the web version, where each pack tile read is one download.

Time and memory:

* The whole run took 35.5 minutes, with a peak of 3.9 GB of memory, once the planet read and the cutting were cached.
* Writing the two packs took 16 of those minutes, even with each written in its own process. The pack writer cuts shapes into pack tiles in Python, one at a time; it needs a faster method for the world.

### Stage 3: the 180 degree line and the South Pole, complete

The first full run finished on the afternoon of 2 November: 24 of 27 places passed. The three failures are explained below. The confirming run, the same evening, passed all 27: see "Stage 3 confirmed" below. The figures in this section are from the first run, except where that section says otherwise. The report is in the data folder's tobymap\output\s2-stage3 folder.

Areas, against Wikidata (the 1% check):

* Russia: 16,971,396 km², 0.6% less than Wikidata's 17,075,400 km². Passes.
* Fiji: 18,757 km², 2.6% more than 18,274 km². Fails.
* Kiribati: 1,097 km², 35% more than 811 km². Fails. Kiribati is made of atolls; the land polygons probably count reef flats, or lagoons closed off by the coastline, as land. This needs looking at before the world build, because many Pacific countries are atolls.
* The USA: 9,488,731 km², 3.4% less than 9,826,675 km². This is expected: Wikidata's figure includes coastal waters, and ours keeps the Great Lakes and other inland water but no sea.
* Antarctica: 12,991,389 km², 5.3% less than 13,720,000 km². The cause: the OSM land polygons stop at 86 degrees south, so the South Pole was in the sea, and about 620,000 km² round the pole was missing. The build now adds the cap south of that as land, because the ice sheet is land all the way to the pole. That should bring Antarctica to about 13.6 million km², within 1%. To be confirmed.

Bounding box and centre across the line:

* Each country's bounding box, allowing for the line, is the right size: Fiji 7.1 degrees of longitude, Kiribati 40.3, Russia 171.4, the USA 150.8. Worked out without allowing for the line, each would be nearly 360 degrees.
* Russia's centre is on its land, in Siberia. Antarctica, which goes all the way round the pole, should have the pole as its centre; that waits for the polar cap fix.
* For countries spread over the ocean, the middle of the bounding box is in the sea: Fiji 20 km from its nearest land, Kiribati 56 km, the USA 1,800 km (in the Pacific, because it stretches from Guam to Puerto Rico). Hierarchy mode and search need a label point instead, such as the nearest land to the middle, which the build already works out, or the middle of the largest part.

Artificial edges along the line:

* Russia has 500 km of edges along the 180 degree line on each side, and Fiji 28 km. On both, every edge on one side is matched exactly by one on the other, so the line only splits the shape and loses nothing.
* Antarctica has 817 km on one side and 739 km on the other, with 78 km on one side only. This is near the pole, where the land polygons stop; to be checked again after the polar cap fix.
* No land border or coast was found along the line, other than these artificial edges.
* The isolated drawings show Fiji and Russia each as one compact shape. But a thin line is drawn where the two halves meet at the 180 degree line, on Taveuni and across Chukotka. The shells must not outline artificial edges, in the isolated drawing as on the globe (AD-17).

Places:

* Passed: both sides of the line on Wrangel Island and Taveuni, Anadyr and Uelen, Big Diomede (Russia) and Little Diomede (the USA) with the sea between them, Attu, the Bering Sea at the line, Washington, Honolulu, Moscow, Kaliningrad, Tarawa, Kiritimati, McMurdo, the Ross Ice Shelf on both sides of the line, the Ross Sea and the Southern Ocean.
* Failed: the South Pole, which was in the sea (see Antarctica above).
* Failed: Taveuni west of the line, and Amchitka. Both points I had chosen were about 1 km offshore; land was found 1 km away in each case. They have been moved onto the islands, with a note in the places file.

The counties layer, by the rule of discussion point 101:

* Fiji: its 14 provinces at level 6, and Rotuma, which has none, as its own county.
* Kiribati: nothing at levels 6 or 7, so its 24 island councils at level 8, with the Line Islands and Phoenix Islands used as their own county where no council covers them.
* Russia and the USA, near the line only: level 6, with small gaps filled by their regions: 154 km² of Kamchatka, 211 km² of Sakha, 5 km² of Chukotka, and 31 km² of Alaska.
* All four are now in the counties record.

Gaps:

* Land in no country near the line: two specks of 0.08 hectares each, exactly on the 180 degree line in Chukotka. They are where the land tiles and Russia's outline meet the line very slightly differently; harmless, but the real pipeline should snap shapes to the line.
* Russia: 5 km² in no region, on the Perekop isthmus. That is the straight line that closed Russia's open outline.
* The USA: 31 km² in no state. The largest part, 6 km², is Wake Island, which belongs to the USA but to no state, which is correct.

Neighbours meeting exactly (AD-16):

* All nine layers meet exactly after cleaning and after simplifying, with no overlap.
* Cleaning moved 864 km² between Russia's regions. OSM's borders between some of Russia's regions overlap; which ones is still to be found.

Parts far from the mainland (for country units):

* The USA: Alaska, Hawaii, Puerto Rico, Guam, the Northern Mariana Islands, the US Virgin Islands and American Samoa are each more than 1,000 km from its largest part. These are the expected country units.
* Kiribati: its three island groups are each more than 1,000 km from Tarawa's.
* Russia: the check wrongly listed Chukotka east of the line as far away, because the check did not allow for the line. That is fixed in the build, with a test.

Packs:

* Compact coordinates make the pack 4.6 times smaller: 56.9 MB instead of 260.8 MB.
* A lookup takes 16.6 ms (median), at most 54 ms.
* Cutting the 155 areas to the land took 6 minutes with 3 workers. The USA alone took 5.7 minutes, while the other workers had finished.
The globe (VIS-5), drawn as the shells will draw it, with artificial edges filled but not outlined:

* Fiji at the 180 degree line, enlarged six times: the islands either side of the line join up, and the 5 edges along the line are filled but not outlined.
* The Pacific centred on the line: 283,700 points, nothing drawn across the globe.
* The South Pole: Antarctica is drawn whole round the pole, with no stray lines.
* The Bering Strait: Chukotka and the Aleutian chain run across the line with no gap or stray line. The automatic check flagged one long edge, but it is Alaska's border with Canada along 141 degrees west, a real straight line about 1,000 km long; Canada is not in this build, so that border shows as an edge. The check is too blunt: it should look only at edges near the 180 degree line.

Time and memory:

* The whole run took 75.7 minutes, with a peak of 4.6 GB of memory.
* About 45 minutes of that was drawing the pictures, mostly the isolated USA and preparing the globe's shapes, all on one thread. Writing the two packs took 11 minutes, and cutting to the land 6.

### How the runs went, and what was fixed on the way

* The first try ran stages 2 and 3 at the same time. Together they ran the laptop short of memory and Claude Code stopped both. Since then, one heavy build runs at a time.
* The builds now record their memory at each step, and stop themselves cleanly, with a line in the report, if free memory falls below 3 GB. This worked three times. But it also stopped stage 4 wrongly while the planet file was being read: GeoDesk's mapping of the file counts as used memory, though Windows can take it back. The guard needs to pause during the planet read.
* Slow steps found and fixed, with tests:
  * finding land in no county or region now works from the shapes as read, then cuts only the leftover to the land (over half an hour for Norway before, seconds now);
  * matching island names to land parts prepares each part once (over 25 minutes for Norway before, seconds now);
  * the check that neighbours meet looks only within 5 km of the land borders, and the band round the borders is built from widened shapes, not widened lines (which used 18 GB);
  * pack tiles are split when their entries hold more than 20,000 points (lookups 744 ms before, 20 ms now);
  * pictures are trimmed to their frame before drawing.
* Worker processes, as in the PO's OMR project: cutting to the land, the layer checks and the two packs now run 3 at a time (mapdata/parallel.py, `--workers`). Most other steps still use one thread, so the processor was about 30% busy. Discussion point 103 asks how the full pipeline should use the laptop's cores before any bulk build.

### Discussion point 103: using the laptop's cores, actioned

The PO agreed the recommendation and asked to test it on the stage 3 rerun for Antarctica. Built on 2 November, before that run (architecture 8.6, and explanation.md, "How the build shares its work between the processor's cores"):

* The memory check pauses while the planet file is read, so it no longer stops a build wrongly, as it did stage 4.
* A new job starts only while at least 6 GB of memory is free; below 3 GB the build stops cleanly, as before.
* The pack is now cut into pack tiles once, for both kinds of coordinates, instead of once for each, with the cutting and the encoding shared among workers. Before, two packs took 11 to 16 minutes, each written separately.
* Each picture, and the globe views, are drawn in their own worker. Before, stage 3's pictures took about 45 minutes on one thread.
* `--away` uses 6 workers instead of 3.
* The report's first lines say how many workers the build uses, and how long the last run of the same stage took.
* Tests cover each of these, and all 207 Python tests pass. None of it has run on real data yet: the Antarctica rerun is the test.

### Room for more speed

Yes, there is more to gain. In order of how much I expect each to help:

1. Cutting shapes into pack tiles works through each shape one pack tile at a time in Python. Cutting a whole grid of pack tiles in one call would be much faster, and pack writing was the slowest step left in stage 2.
2. Drawing hands each point to Qt one at a time. Passing whole outlines at once would speed up the pictures, and the globe's shapes are prepared slowly for reasons not yet found. Pictures are for checking only, so the real pipeline could also draw fewer of them.
3. A very big country is one job, so one worker is busy while the others wait: the USA took 5.7 minutes to cut while the rest took under a minute. Cutting it region by region, then joining, spreads it out.
4. Areas are measured one part at a time; Norway has 118,845 parts. Measuring them all in one call would be faster.
5. Reading the land polygons scans the whole 885 MB file for each new set of reading boxes. Converting it once to a format with a spatial index would make that near instant.

Separately, for the application rather than the build: looking up a place decodes compact coordinates in plain Python. Doing that with NumPy would make each step faster, which matters for NFR-1.

### Next: faster algorithms, proved on stage 1 (the PO's request, 2 November)

Before the Antarctica run, the algorithms are made faster, then stage 1 (the UK, France and Spain) is built again with them, to show both that it is faster and that the results are the same.

The times to beat, from stage 1's last full run on 1 November (its report in tobymap\output\s2-stage1), with the cutting to the land already cached:

* total: 20.9 minutes, with a peak of 5.9 GB of memory;
* finding land in no country and in no division: 548 seconds;
* checking that neighbours meet (5 layers): 165 seconds;
* islands and drawing levels: 58 seconds;
* writing the two packs, the places check and the pictures: about 480 seconds between them;
* and from its first run, with nothing cached: about 30 minutes in all, 5 of them cutting to the land.

The algorithm changes, from "Room for more speed" above, in this order:

1. Cut whole grids of pack tiles at once, instead of one pack tile at a time.
2. Draw whole outlines at once, and find what makes preparing the globe's shapes slow.
3. Cut very big countries region by region, then join them, so the work is spread across workers.
4. Measure all of a country's parts in one go.
5. Convert the land polygons once into a format with a spatial index, so a build reads only what it needs.
6. Stage 1 is built by the same program as stages 2 and 3, so it gets the earlier speed-ups too (gaps worked out from the shapes as read, the border window, workers, and the pack tile limit).

How "the same results" is checked, by a comparison script that reads the old summary and the new one, and writes a report of every difference:

* the cut shapes: every area's land must be the same shape as the one cached on 1 November, apart from differences under a square metre;
* the 22 check places: the same areas found at each, in the same order;
* the UK's islands: the same number of parts, named and unnamed, at each size;
* land in no country: still none; land in no region: the same slivers;
* neighbours: every layer still meets exactly after cleaning and simplifying;
* the packs: the same areas found at a grid of test points across the three countries.

Two differences are expected and are not faults:

* areas are now measured on the ellipsoid instead of a sphere, so area figures move by a fraction of a percent. The comparison measures both old and new shapes the new way;
* the counties layer now follows discussion point 101, so it gains the areas that level 6 left out, such as London's boroughs, Northern Ireland's districts, and French Guiana as its own county. The comparison checks the level 6 areas are unchanged, and lists what was added.

The cut shapes cached on 1 November are kept, so both runs can be timed the same way: once with the cutting cached, against the 20.9 minutes, and once from scratch, against the 30 minutes.

### Faster algorithms: what was done, 2 November evening

Each slow step was timed on the real shapes before it was changed, and each new method was checked against the old one on the same shapes. Three of the plan's guesses were wrong, so the changes differ from the list above.

1. Cutting shapes into pack tiles. Python's step-by-step handling took under 1% of the time; the cut itself took the rest. A cut made for rectangles (GEOS clip_by_rect) replaces the general one: the UK in 16 seconds instead of 52, with exactly the same pack tiles and shapes. If the rectangle cut ever gives an invalid shape, the general cut is used instead.
2. Drawing. The globe's shapes were slow to prepare because simplifying a whole country checks every island against every other: Russia took 52 seconds, and the USA had not finished after 15 minutes. Each part is now simplified on its own: Russia in 5.5 seconds, the USA in 16.5. Whole outlines are also handed to Qt in one step, instead of one point at a time, and the artificial edges are left out by lifting the pen. Stage 3's four globe views took 27 seconds; the old code had not finished after 25 minutes. The figures match stage 3's report, with a few per cent fewer points drawn. The core's globe now finds the artificial edges for every ring at once (mapcore/render/globe.py).
3. Cutting very big countries in parts. Tried on the UK, and slower: 310 seconds instead of 47, because joining the big parts back costs as much as the whole. The real cost was joining the land tiles, 36 of the 47 seconds. Shapely's join for separate groups (disjoint_subset_union_all) does it in 8 seconds, with exactly the same shape, because most land tiles are islands that touch no other.
4. Measuring many parts in one call (geodesy.areas_km2). It gives the same figures as one part at a time.
5. The land index (glossary). The land polygons are converted once after each download, in 24 seconds, into the data folder's tobymap\working folder. Europe's reading box then loads in 5 seconds, instead of a scan of the whole file, with exactly the same 86,656 land tiles as the 1 November cache.
6. Stage 1 by the same program as stages 2 and 3: `python -m mapdata spike-s2 1`, with the settings in mapdata/config/s2_stage1_again.yaml. It has France's country units and stage 1's reading boxes, and writes to its own folders (s2-stage1-again), so the 1 November results are kept. A comparison program, `python -m mapdata spike-s2-compare`, reads both builds and writes a report of every difference, as described above.

Tests: 18 new ones, each comparing a new method with the old one, or with what the download gives. All 225 Python tests pass.

### Stage 3 confirmed: 27 of 27 places, 2 November evening

The confirming run with 6 workers (`--away`) passed all 27 places. The report is in the data folder's tobymap\output\s2-stage3 folder.

The South Pole needed a second fix:

* The run before it still found the sea at the South Pole, and Antarctica's area had not changed at all. The polar cap had been added to the land tiles, but OSM's outline of Antarctica itself stops at 85.05 degrees south, the limit of the web map projection. Cutting to the land keeps only what is inside the country's outline, so the cap was cut away again.
* The build now also extends any outline that goes all the way round the pole, but stops short of it, down to the pole (`outline_to_the_pole` in mapdata/stages/s2_stage.py, with a test). The report says when it does this.

Results:

* The South Pole is in Antarctica, and Antarctica's centre is now the pole.
* Taveuni west of the line and Amchitka, the two moved places, both pass.
* Antarctica's area is 13,950,822 km², 1.7% more than Wikidata's 13,720,000 km², so it does not pass the 1% check. It was 5.3% less before. Published figures for Antarctica differ by about half a million km², depending on whether the ice shelves are counted. The Ross Ice Shelf is land in the OSM land polygons, so it is counted here. I have not checked which definition Wikidata's figure uses. For the world build, Antarctica needs its own expected figure, with the ice shelves included.
* Antarctica's edges along the 180 degree line are now 1,367 km on the east side and 1,289 km on the west, because they now run on to the pole. The 78 km on one side only has not changed, so it is not caused by where the land polygons stop. Its cause is still to be found.
* The globe centred on the South Pole draws Antarctica whole, with the edge at the pole filled but not outlined, and no edge jumping across the globe.
* The other figures are the same as in the first run: the other countries' areas, the counties, the gaps, neighbours meeting exactly, and the pack sizes (56.8 MB compact, 261.1 MB WKB).

Time, the test of discussion point 103:

* The whole run took 13.1 minutes, against 75.7 minutes for the first run. Peak memory was 3.3 GB, against 4.6 GB.
* Drawing the pictures took 36 seconds, against about 45 minutes. Writing both packs took 2 minutes, against 11.
* The slowest steps now are checking that neighbours meet (3.2 minutes, mostly the 15,577 areas of the USA's counties layer), writing the packs (2 minutes) and the counties step (2 minutes).
* Only Antarctica was cut again, and the planet file's extract came from the cache, so this was not a run from scratch.
* Lookups in the compact pack took 13.4 ms (median), at most 59 ms.

One fault was found on the way. The first try stopped while printing a Russian name, because its output was going to a file, and Windows then uses its old character set. mapdata now always writes its output as UTF-8.

### Stage 1 again: not finished, because of the counties step

Stage 1 was started again three times. The planet read, the land tiles and cutting all 64 countries, units and regions to the land took about a minute (67 seconds for the cutting, with 3 workers). Each time, the build then spent a long time in the counties step and was stopped.

* The counties step is new work: stage 1 on 1 November made its counties from level 6 alone. Discussion point 101 also looks at levels 7 and 8 wherever level 6 leaves a gap. France has 34,874 areas at level 8.
* After level 6, France's gap is 195,763 separate parts, mostly thin strips along the coast, with 1.4 million points. Each area that touches the gap is measured against all of it, which took over 10 seconds for each of France's arrondissements.
* Two changes were tried: skipping areas that touch only the gap's sea, and measuring each area only against the parts of the gap near it. With them, the UK's counties step was slower than before (over 20 minutes, against about 9), and the cause was not found. The PO asked to stop and move on, so the counties step is back as it was this morning.
* So the whole-run comparison with 1 November has not been made. The comparison program is ready for it.

For Phase 1: the counties rule needs a faster way to find which areas fill a gap. It should look only at areas whose land is mostly in the gap, found without measuring each one against the whole gap. A likely first step is to drop the gap's strips under a set size before testing any area.

The lesson from all of these: the slow steps were each an operation on a whole country, or a whole gap, made of many thousands of separate parts, when each step needed only the few parts nearby. That will matter far more for the whole world.

### Still to do

* Stage 1 again: finish the whole run and the comparison once the counties step is faster, or run it with the counties step timed separately.
* Antarctica: which definition Wikidata's area uses, and the cause of the 78 km of edges along the 180 degree line that are on one side only.
* Look into Kiribati's area (35% more than Wikidata), Fiji's (2.6% more), and the 864 km² that cleaning moved between Russia's regions.
* Make the globe check look only at edges near the 180 degree line.

### Stage 4, Argentina: parked

* The PO added Argentina on 2 November, because their earlier work had trouble there with lines that crossed. It tests Tierra del Fuego, an island shared with Chile, the long Andes border, the undecided border on the Southern Patagonian Ice Field, and the Falkland Islands.
* Its settings and check places are ready: mapdata/config/s2_stage4.yaml and tests/acceptance/coastline_places_stage4.yaml. The first try stopped twice, once on the memory guard during the planet read and once because OSM names Paraguay "Paraguay / Paraguái"; the name is corrected. Bolivia's and the Falkland Islands' names are not yet checked against OSM.
* Parked by the PO on 2 November, to be picked up later.

Everything below this point is about stage 1, the UK, France and Spain, from 1 November.

## Afternoon runs, 1 November

### Why the runs stopped

* The build itself uses under 2 GB of memory.
* GeoDesk maps the whole planet file into memory while it reads it. On the laptop that mapping grew to about 24 GB, and stayed until the run ended.
* With that, and other programs, the laptop ran short of free memory, and Claude Code stopped the run. The night's stop was very likely the same.
* Fix: everything the build needs from the planet file is now read once and saved in the working folder. Later runs do not open the planet file at all.
* Closing GeoDesk inside the same program did not give the memory back: after the extract, the build still held about 24 GB. Only ending the program did.
* Lesson for the real pipeline (Phase 1): reading the planet file must run in its own short-lived process, which hands its results to the rest of the build and then ends.

### Two faults, fixed

* Some areas cut to the land came out as a mixed collection: areas with stray lines or points. Two later steps could not accept those. Every cut shape now keeps only its areas, and there are tests for this.
* Suriname and Brazil were missing from the neighbours, so French Guiana's border strip showed up as 1,313 km² of land in no country. They are now in the stage 1 list, and with them there is no land at all within about 1 km of the UK, France and Spain that is in no country.

### Cutting to the land

* All 351 areas are cut in under 2 minutes, once the land polygons are loaded.
* The UK, France and Spain cover 2,241,996 km² with their territorial waters, and 1,386,307 km² of land.
* United Kingdom: 243,533 km² of land. France: 637,350 km². Spain: 505,424 km².
* Gibraltar: 93 km² with its waters, 7 km² of land. Andorra is unchanged at 467 km², as a country with no coast should be.

### Land in a country but in none of its divisions

* Regions, level 4: almost nothing is missed. The UK has none. France has 75 km² in 2,852 small slivers. Spain has 10 km² in 1,901 slivers. These are where a region's boundary and the country's do not quite meet at the coast.
* Counties, level 6: whole areas are missing, because OSM uses a different level there.
  * United Kingdom: 22,643 km². The largest piece is Northern Ireland, 14,087 km², whose districts are at level 8 in OSM. The rest is still to be identified.
  * France: 89,260 km². The largest piece is French Guiana, 83,985 km², which has no département level in OSM. Martinique is likely the same.
  * Spain: 44 km², the largest piece 16 km². This may be Ceuta and Melilla, which are cities with no province.
* Checked in the UK GOL file, against the OSM wiki's table of levels for each country:
  * England: level 5 is Greater London and the combined authorities, such as West Yorkshire. Level 6 is the shire counties and unitary authorities. In London and the metropolitan areas there is nothing at level 6: the boroughs and metropolitan districts are level 8. The wiki gives metropolitan counties at level 6, but the data has none.
  * The missing English land is West and South Yorkshire with Greater Manchester (one joined piece, 5,326 km²), Greater London (1,586 km²), the West Midlands (899 km²) and Tyne and Wear (544 km²).
  * Scotland: council areas are level 6.
  * Northern Ireland: the 11 districts are level 7, not 8. The only level 6 area is a stray closed way named Belfast, which the build ignores, because it reads only relations.
  * France: every overseas département is missing at level 6: French Guiana, Réunion, Martinique and Guadeloupe.
  * Spain: Ceuta and Melilla, which are level 4 cities with no province.
* What this means for the design: a pack cannot assume that one admin level covers a whole country. Discussion point 101 recommends one general rule: level 6, with gaps filled by level 7 then level 8, and then by the region itself.

### The UK's islands

* The UK's land is in 19,854 separate pieces.
* OSM has 21,201 named islands and islets inside the UK's box. 8,030 of the land pieces have one of those names, and 11,823 have none.
* 2,035 pieces are 1 hectare or more, and 648 of those have no name. 170 are 1 km² or more. 41 are 20 km² or more. 3 are 2,000 km² or more.
* Drawing levels, simplified in a few seconds each:
  * world level: 3 pieces, 750 points;
  * country level: 41 pieces, 9,775 points;
  * 1 km level: all 19,854 pieces, 1.24 million points, but only 5 points in a 2 km view on Skye. So detailed drawing is cheap, because only the view is drawn.

### Neighbours meeting exactly (AD-16)

* The raw OSM borders of the UK's regions and counties meet exactly. After cutting to the land, they no longer did.
* Cause: the OSM land polygons are split into one-degree squares that overlap by a thin band, about 0.0005 degrees, at each split line. Where a border crossed a piece's edge, the cut added a point on one neighbour's border but not the other's.
* Fix 1, in the cut: a full union of the pieces instead of a coverage union, then removing points that lie within 0.1 mm of the border's line. With it, the UK's regions and France's départements meet exactly.
* Two kinds of problem remained:
  * where a border meets the coast, two spots in the UK were a few metres apart: Bridgend and the Vale of Glamorgan at the Ogmore estuary, and Bristol and South Gloucestershire near Avonmouth;
  * OSM's own borders overlap in Spain, before any cutting: Ceuta with the Plazas de Soberanía, and Burgos with Soria.
* Fix 2, coverage cleaning (GEOS, through Shapely 2.2): it closes tiny gaps and gives each overlap to the neighbour with the longer shared border. Tried on the saved shapes, every layer then meets exactly, and still does after simplifying. It moved no measurable area for the UK's counties, 0.14 km² for Spain's regions and 2.1 km² for Spain's provinces.
* So the method is: cut to the land, clean each layer, then simplify it as one coverage.
* The seventh run confirmed it end to end. All five layers meet exactly after cleaning and after simplifying, with no overlap: the UK's regions and counties, France's départements, and Spain's regions and provinces.
* Across levels, the UK's counties joined together differ from its regions by 8,696 km². About 8,350 km² of that is the metropolitan areas and London, which have no level 6 (discussion point 101). The rest, a few hundred km², comes from simplifying each level on its own. For the real pipeline: simplify only the finest level, and make each coarser level by joining its simplified parts, so the levels match by construction.
* Simplifying is fast: the UK's 139 county-level areas go from 3.24 million points to 92,770 in 22 seconds.

### Packs and places (sixth run)

* All 22 coastline places pass, including sea off Brittany, the Solent, the Strait of Gibraltar, Gibraltar, Ceuta, Melilla, Llívia and Andorra.
* Compact coordinates make the pack 4.5 times smaller: 38.4 MB instead of 172.3 MB.
* A lookup takes about 36 to 43 ms, at most about 110 ms, reading 2 to 7 pieces.
* The whole run takes about 30 minutes, and at most 6.6 GB of memory. Cutting to the land takes 5 minutes. Finding land in no division takes 11 minutes, which is the slowest step and needs a faster method for the whole world.
* Place names: the pack uses OSM's English names, such as "South Corsica" for Corse-du-Sud and "Ile-de-France" without the accent. The places check accepts either the English or the local name.

## How areas are cut to the coast

OSM boundaries include territorial waters, about 12 nautical miles out to sea. The build removes the sea with the OSM land polygons (AD-15), which the OSM coastline tools make every day from the coastline lines (natural=coastline). They come split into pieces of at most one degree square, about 870,000 for the world.

1. Read the land pieces inside the build's regions: one box for Europe and the Canary Islands, and one for each French overseas region. They are saved in the working folder.
2. For each area, find the land pieces that touch it, with a spatial index.
3. Keep a piece whole if it lies wholly inside the area. Cut a piece that crosses the area's boundary, keeping the part inside.
4. Join the kept parts into one shape. Islands stay as separate parts.
5. Remove the points that the cut adds along borders where the pieces overlap, within 0.1 mm of the border's line.
6. Clean each layer, then simplify it as one coverage.

The same land is used at every level, so countries, regions, counties and the coast all line up.

Limits:

* Lakes and rivers stay land: only the sea is removed. Lough Neagh is inside Northern Ireland. Water needs its own layer.
* Where a river meets the sea, mappers decide where the coastline crosses it. Upstream of that point, the river counts as land.
* The boundaries come from the planet file of 22 November 2025, and the land polygons from 31 October 2026. The checks found no mismatch, but the real pipeline should use both from close dates.

## For Phase 1

What stage 1 means for the real pipeline:

* Read the planet file in its own short-lived process, because GeoDesk gives its memory back only when the process ends.
* Use a planet file and land polygons from close dates.
* Cut to the land, clean each layer, then simplify as one coverage.
* Simplify only the finest level, and make each coarser level by joining its simplified parts, so the levels match exactly.
* Make the counties layer by the rule agreed in discussion point 101.
* Find land in no division faster: it takes 9 to 16 minutes for three countries, which is too slow for the world.
* Speed up lookups in the pack, about 40 ms now.
* Keep compact coordinates: they make packs 4.5 times smaller.

## Where it stood overnight

* Stage 1 covers the UK, France and Spain. Its build program is written: `.venv\Scripts\python.exe -m mapdata spike-s2-stage1`
* The first run was stopped by the computer during the night, because memory was running low. It had:
  * extracted every area;
  * cut 99 of about 360 of them to the land.
* Those 99 are cached in the data folder's tobymap\working folder, so the next run carries on from there.
* It has not been run again, because it needs your go-ahead. It can be started when the computer is not busy with anything else.

## Found so far

### The tools

* GeoDesk for Python 2.3.0 is LGPL-3.0, which is compatible with GPL-3.0. It opens your planet and UK GOL files read-only, and reads them quickly. For example, finding the UK's level 4 areas took 1.5 seconds.
* The OSM land polygons were downloaded into tobymap\downloads: 885 MB, dated 31 October 2026.
* Your planet GOL file is dated 22 November 2025, so the data is about a year old.

### What was extracted

* 14 countries at level 2: the three, plus their neighbours, so their land borders can be checked.
* France's six country units: metropolitan France, French Guiana, Guadeloupe, Martinique, Réunion and Mayotte.
* United Kingdom: 4 areas at level 4 and 139 at level 6.
* France: 18 at level 4 and 98 at level 6.
* Spain: 20 at level 4 and 50 at level 6.
* One shape needed a repair: Northern Ireland, whose boundary had nested outlines.

### A trial run on the UK alone

* Cutting the UK to the land took 96 seconds.
* The result is 243,533 km² of land, close to the UK's official area.
* The land is in 19,854 separate pieces, almost all of them islands, with 2.2 million points.

## What the full run will produce

* A report in the data folder's tobymap\output\s2-stage1 folder. It covers:
  * the coastline places, such as 2 km off Brittany, Skye, Gibraltar, Ceuta and Llívia, from tests/acceptance/coastline_places.yaml;
  * land in no country, and land in a country but in none of its divisions;
  * the UK's islands, named and unnamed, at each size and drawing level;
  * whether neighbours still meet exactly after simplifying;
  * pack sizes with and without compact coordinates;
  * time, memory and disk use.
* Two small packs, one with each kind of coordinates, which `mapdata inspect` can query.
* Pictures for sighted reviewers.
