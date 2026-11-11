# Size report for the complete base pack (P3-T1a, DP167, DP169)

The size trial, run on the night of 10 to 11 November 2026. This first report covers counties. Each new layer of P3-T1 is added to the trial as it is built, and this report gains a section for it: the named seas (P3-T1b) were added on 11 November. You decided from it that counties go into the world build (DP175). The thresholds for the world are still to decide (DP169).

## Islands (P3-T1d), 11 November 2026

### What was added

* A layer of areas, "Islands", at rank 5, between regions and counties. Land is named with the smallest named island (place=island or place=islet) that covers it.
* Islands that OpenStreetMap has only as a point name the landmass they are on. A landmass with no name at all, of 1 km2 or more, is an "Unnamed island".

### Its share of the trial pack (Western Europe)

The trial pack grew from 23.7 MB to 30.79 MB.

* Islands: 36,160 features, 7.54 MB, 24.5% of the pack. Feature records 2.33 MB, pack tiles 2.78 MB, and drawing levels 0 to 2 together 2.44 MB.
* The planet read found 36,512 named islands and islets as areas, 2 of them repaired, and 2,670 as points only. It took 11 seconds inside the osm-areas stage, which took 6 minutes 27 seconds in all.
* The join stage found 93,113 separate landmasses. 280 had land outside the named island areas and took the largest named island there; 204 were named from island points; 18 are "Unnamed island"; 67,615 smaller ones have no island.
* The join stage took 46 seconds. The whole build took 27 minutes 34 seconds.
* Checks: all 49 check places pass, and the no-gaps check passes (LOC-6). Majorca, and the Isle of Wight inside England's Isle of Wight county, come out as expected with `mapdata inspect`. Tenerife is outside this trial's box, so the world build will show it.

### The estimate for the world

Western Europe has many islands (Norway, Greece, Scotland), so the world's share will be larger than a plain share by area, but not by the same ratio. Taking the same 30% growth on the trial would add about 80 MB to the 273.93 MB world pack, which is an upper guide. The world build gives the real figure. The soft limit is about 400 MB (DP175).

### Found on the way

* One island of 0.10 km2 in no country, at 51.528 north, 2.498 east, is named Unclaimed. It is not on the list of unclaimed land yet.
* The test of the visible rule on the world pack (under 5 ms a frame) fails with or without this task, on timing. It is not caused by islands.

## Counties for the whole world (P3-T1c), 11 November 2026

### What changed

* The reading stage now reads the counties a country at a time. The planet file is still read once. Each county area is set aside on disk, in a file for its country. Then the countries are sorted one at a time, in 3 worker processes, and each area that can fill no gap is left out. So the world's level 7 and 8 areas are never all in memory at once, which was the risk this report named for the world build.
* A country is read only at its levels in the counties record, once it has an entry there. For example, Sweden is read at level 7 only.
* The counties record names level 5 for 18 countries, as corrected, whose real counties are there. Argentina, Tunisia and South Sudan were found by the trial. The other 15 were found by reading the whole world, below.
* A county is never the same area as its region. This matters where a country's counties and its regions could both come from level 5.
* The join stage lists, in the log and the quality report, each country's county levels, the land each holds, every gap filled by a later level (each area by name in the log), and every region used as county.
* The build writes the counties record, as "worked out", for each country it has whole. A trial with a reading box leaves out the countries its box cuts. A corrected entry is never overwritten, and an entry that is the same as before keeps its date.
* Correcting a country's levels in the record makes the next build read the planet file again. A new date alone does not.

### The whole world, read with counties

I ran the world build's reading stage alone, with 3 workers, to check memory before the world build.

* It took 16 minutes: about 10 to read the planet file and about 5 to sort the counties.
* It read 218 countries. At the region levels it read 3,058 areas at level 4 and 5,920 at level 5. At the county levels it set aside 47,603 areas at level 6, 30,078 at level 7 and 211,021 at level 8.
* The sort kept 64,639 of the 288,702 county areas, and left out the rest, as inside the levels before them.
* Memory: at most 18.3 GB in use on the laptop, of 32 GB, and at most 2.5 GB for any one process. The largest countries were sorted first, with no trouble.
* The reading's areas take 2.5 GB on disk, against 0.9 GB without counties. The grid squares stage loads them all, so the world build's next stage is the one to watch for memory.
* The record has changed since this reading (the 15 countries below), so the world build reads the planet file again, which takes 16 minutes.

### Countries whose counties are at level 5

Counted on the world reading, with each country's areas as read, which include its sea. Each has regions at level 4, and level 5 covers it well where levels 6 to 8 do not. The record now names level 5 first for each, then 6, 7 and 8 for any gaps:

* Afghanistan: 397 districts.
* Armenia: 81 communities.
* Bulgaria: 265 municipalities.
* East Timor: 70 administrative posts.
* Ethiopia: 91 zones.
* Indonesia: 514 regencies and cities.
* Ivory Coast: 31 regions.
* Lebanon: 25 districts.
* Mozambique: 161 districts.
* Papua New Guinea: 87 districts.
* Sierra Leone: 15 districts.
* Sri Lanka: 25 districts.
* Tanzania: 195 districts.
* Turkmenistan: 49 districts.
* Zambia: 116 districts.

Left at level 6, though level 5 also covers them: China and India, where level 6 covers the country too, and Canada, where it covers most of it. China's level 6 is its counties. India's is its subdistricts, below its districts at level 5. Each can be corrected in the record if you prefer.

Countries with nothing at levels 5 to 8, so each region stands as its own county: among them Egypt, Libya, Eritrea, Namibia, Botswana, the Central African Republic, Chad, Uruguay, Qatar and Bahrain, and many small island countries. Lesotho has its districts at level 5 and nothing at level 4, so they are its regions, and it has no counties below them.

### The Western Europe trial again

Both trials were built again on 11 November 2026 with counties for the whole world switched on.

Western Europe:
* Pack size: 23.7 MB, the same as before. Counties: 3,990 areas. Time: 23 minutes.
* All 49 of 49 check places pass.
* France now has counties: 97 areas, at level 6. Croatia uses level 7 and fills 63 gaps with level 8.
* The counties record had 14 countries unchanged and none written, as 19 countries are only partly in this trial.

South America:
* Pack size: 9.3 MB. Counties: 3,293 areas. Time: 6 minutes with 2 workers.
* Argentina's counties come from level 5, 386 areas, as corrected in the record.
* The counties record had 1 country unchanged and 6 not written, as the trial holds only part of them.
* The first build failed at the write stage, as a department in Argentina, Departamento Rinconada, was a region in one place and a county in another, so one id was used twice. A county that shares an id with a region now gets the ending "#as-county" in join.
* An earlier South America run with 3 workers was stopped by Claude Code because the laptop ran low on memory. With 2 workers it completed.

The whole world, built on 11 November 2026 with 3 workers:
* Pack size: 273.93 MB, under PCK-1's soft limit of about 400 MB.
* Counties: 61,942 areas. Regions: 3,207. Countries: 246. Seas, bays and straits: 275 areas, and 98,327 places.
* Time: 2 hours 53 minutes. The planet read took 16 minutes, the squares 1 hour 34 minutes, the join 14 minutes, the places 1 minute, and the write 47 minutes.
* All 108 check places pass, and all 7 other checks pass.
* The counties record now covers every country: 175 written as worked out, 19 unchanged and 18 left as corrected.

## Named seas, bays and straits (P3-T1b), 11 November 2026

### What was added

* A layer of areas, "Seas, bays and straits", below the oceans: Natural Earth's marine areas, as DP168 said for the case where the IHO Sea Areas are not free to share. They are still non-commercial (CC BY-NC-SA 4.0, on their record, checked on 11 November 2026). Natural Earth's are public domain: 283 named seas, gulfs, bays, straits, sounds, channels, fjords, lagoons and inlets, which cover the sea with no overlaps.
* A layer of places, "Bays and straits, as places": OpenStreetMap's named seas, bays and straits, read from the planet file by a new stage, osm-places. They are for search and Nearby, and are never said as where you are. Those that OSM has as an area are read as a place inside it, as the base pack does not hold OSM's bays as areas. One with the name of a sea already in the layer of areas, such as the North Sea, is left out.
* The new stage takes a list of OSM queries, so towns and peaks can use it later.

### What you hear

Checked in the trial pack with the application's own look-up:

* In the Solent, and at the Dover Strait: "English Channel, North Atlantic Ocean".
* North of Santander, and 2 km off the Pointe du Raz: "Bay of Biscay, North Atlantic Ocean".
* Off Marseille: "Gulf of Lion, Mediterranean Region".
* In the open Atlantic, west of Ireland: "North Atlantic Ocean" alone, as Natural Earth names no sea there.
* Nearby, in the Solent: Cowes Roads, Stanswood Bay, Gurnard Bay and Osborne Bay, each with its distance.
* All 49 check places pass, including 19 new sea check places in tests/acceptance/sea_places.yaml.

### Its share of the trial pack

The trial pack grew from 21.4 MB to 24.4 MB.

* Seas, bays and straits: 26 seas, 1.82 MB.
* Bays and straits, as places: 20,704 places, 2.25 MB: 19,640 bays, 1,057 straits and 7 seas. 18 were left out as already seas.

### The estimate for the world

* The seas follow the coast, as the oceans do. Scaling the trial's seas by the oceans, which are 15.6 times larger in the world pack, gives 28 MB. Scaling by the number of seas, 26 of Natural Earth's 283, gives 20 MB. So about 20 to 30 MB.
* The places: the planet file has about 99,000 named seas, bays and straits, as points and areas, against the trial's 20,704, at about 110 bytes each: about 11 MB.
* So P3-T1b adds about 30 to 40 MB to the world pack, which would then be about 330 MB with counties, against the soft limit of about 400 MB (DP175).

### Found on the way

* The water between Natural Earth's rough coast and the real one: 63 parts in the trial, each given the sea beside it. None was left with no sea.
* Natural Earth calls the Skagerrak a fjord. It is said as "Skagerrak"; the type is only in its record.
* In the Mediterranean the ocean is VLIZ's "Mediterranean Region", so a sea there is said as, for example, "Gulf of Lion, Mediterranean Region". The Baltic Sea is a VLIZ ocean and a Natural Earth sea with the same name, so it is said once.
* Seas are not inside one another, because Natural Earth's areas do not overlap: the Gulf of Lion is beside the Mediterranean Sea, not inside it, so Within has the Gulf of Lion and the ocean only.
* A large OSM bay or strait held as an area, such as the Solent, is in the places layer as one point inside it, which can be farther away than the water you are on. Its area comes with the regional packs.
* The places are kept in the three wide drawing levels, which are used only from 150 km out, though the layer is shown to 100 km. That is 0.86 MB of the 2.25 MB in the trial, about 4 MB for the world. As for counties, they are there in case you widen the layer's zoom range.
* The build read the planet file again, as a new layer of areas changes what the reading stage depends on. That is about 6 minutes in the world build.


## Summary

* The trial pack for Western Europe and the Alps, with counties, is 21.4 MB. Counties are 11.2 MB of it, just over half, in 5,317 counties. All 33 check places pass, and Winchester is in Hampshire.
* Counties for the whole world would add about 170 MB. The likely range is 135 to 210 MB.
* So the world pack, 127 MB now, would be about 295 MB with counties, and likely between 260 and 340 MB. That is over the 250 MB soft limit, before any of the other Phase 3 layers.
* Your question, what a larger pack means for the user: almost nothing, except the first download and the storage. Start-up, the time to the first place said, and memory hardly change, on the desktop and in both browsers. The download of a 295 MB pack takes about 4 minutes at 10 megabits a second, against under 2 minutes now.
* Counties make a build about one and a half times as long. The world build would take about 2 hours 20 minutes instead of about 1 hour 30.
* The estimate was checked on regions not used to make it, as agreed. Scaling Western Europe by area alone said 500 MB, and was more than 3 times too large for South America. So I built 7 more regions, and the estimate rests on all 8, which hold a third of the world's land.
* Questions for you are at the end: counties, and the size limit.

## What was built

* The trial pack: mapdata/config/packs/trial-western-europe.yaml. Western Europe and the Alps, from 11 degrees west to 17 east and 35 to 61 north. It is built as the world pack is, with the same base detail of 100 metres and the same drawing levels, and with counties added (DP167).
* Counties follow the rule of DP101: all land is in its country's level 6 area; where level 6 leaves a gap, the level 7 area, then the level 8 area; where none covers it, the region itself, as "region used as county". Countries already in the counties record use the levels written there, such as Sweden's level 7.
* A region used as county over less than 1 square kilometre in all is a sliver along a coast, or an islet, where the county levels do not quite reach. The first trial had 29 of these, such as a speck of "Corsica" as a county. Each is now given to the county beside it, or the nearest; 1 is left, and 24 regions used as county remain. Some are right: Berlin, Hamburg and Vienna have no counties below them. Others are land of over 1 km2 that the county levels miss, such as 262 km2 of Baden-Württemberg and 5 km2 of England; P3-T1c lists each in the quality report, to be put right in the counties record.
* The check region, as agreed for estimates: southern South America, mapdata/config/packs/trial-south-america.yaml.
* Six more sample regions, each a reading box of about 30 by 22 degrees, built the same way, in mapdata/config/packs/trial-sample-*.yaml: North America (the eastern United States and southern Canada), Africa (West and Central Africa), South Asia (India and its neighbours), East Asia (eastern China, Korea and western Japan), Russia (east of Moscow to the Urals) and Australia.
* Each of the 8 regions was also built without counties, the same in every other way, to measure what counties add to the size and the build time.

Times are with 6 workers, 75% of the processor, as you allowed.

## Each layer's share of the trial pack

The trial pack, 21.4 MB:

* Counties: 5,317 counties, 11.2 MB, 52% of the pack. Of that, 9.0 MB is exact shapes in pack tiles, with 2.3 million points; 1.8 MB is drawing levels; 0.4 MB is feature records.
* Regions: 263 regions, 3.9 MB, 18%.
* Countries: 37 countries, 2.9 MB, 13%.
* Oceans and seas: 4 oceans, 2.7 MB, 13%.
* Lines of latitude and longitude: 536 lines, 0.6 MB, 3%. They cover the whole world in every pack, so they do not grow with the area.
* Special lines: 8 lines, under 0.1 MB.

Without counties, the same pack is 10.2 MB. Counties more than double it, because a county's border is usually not a region's or a country's, so most of their points are new.

## The estimate for the world

### Counties in each region

Megabytes of counties for each million square kilometres of land:

* Western Europe: 3.71. 5,317 counties.
* South Asia: 2.32. 7,463 counties, mostly India's level 6 areas, which are its tehsils and talukas.
* East Asia: 2.08. 4,977 counties.
* South America: 1.12. 4,737 counties.
* North America: 0.82. 2,715 counties.
* Russia: 0.76. 1,006 counties.
* Australia: 0.41. 613 counties.
* Africa: 0.33. 1,543 counties.

So the same land area holds over 10 times more county data in Western Europe than in Africa. That is why one region cannot be scaled up to the world.

### How the estimate is made

* The 8 regions hold 55 MB of counties, measured, on 44 million square kilometres of land, a third of the world's land without Antarctica, which has no counties.
* The rest of the world's land, 90 million square kilometres, is given the average rate of all 8 regions together: 1.24 MB for each million square kilometres. That gives 168 MB for the world.
* How sure is that? Drawing the 8 regions again at random, 10,000 times, and working it out each time, gives 133 MB or more 9 times in 10, and 210 MB or less 9 times in 10.
* A second method, fitting both the land area and the regions' size, gives 210 MB, at the top of that range.
* The first method, Western Europe's rate alone, gives 499 MB. The check showed it is wrong: it predicted 26 MB of counties for southern South America, which really has 7.9 MB.

### The world pack

* Now: 127.4 MB: regions 52.3 MB, oceans 37.0 MB, countries 36.4 MB, lines 1.6 MB.
* With counties: about 295 MB, likely between 260 and 340 MB.
* Against the soft limit of 250 MB: about 45 MB over, likely 10 to 90 MB over.
* The other Phase 3 layers come on top: named seas, islands, continents, mountain ranges, rivers, lakes, roads and railways, and towns. Each is measured in this trial as it is built.

### Smaller ways to save

* Counties are shown to 100 km, but they are also in the two widest drawing levels, which are used only from 150 km out. That is about 5% of counties, about 8 MB for the world. They are there in case you widen the Counties layer's zoom range in its settings. Leaving them out would save the 8 MB, and the layer would then not draw past 150 km whatever its setting.

## Build time

The 8 regions took 52 minutes in all with counties, and 36 minutes without: counties make a build 1.46 times as long. Each stage:

* Reading the planet file: 1.4 times as long. It reads 3 more levels.
* Building the grid squares: 1.5 times as long.
* Writing the pack: 1.8 times as long, as there is twice as much to write.

The trial itself, Western Europe: 19 minutes with counties, 12 minutes without. Reading the planet file took 4.6 minutes, building the grid squares 11.7 minutes, joining 14 seconds, and writing the pack 2.7 minutes.

For the world, from the times of the last world build's stages: reading about 6 minutes, the grid squares about 83 minutes, joining about 4 minutes and writing about 46 minutes. About 2 hours 20 minutes in all, against about 1 hour 30 now. P3-T1k, the faster writing stage, comes before the world build.

A risk for the world build: the trial's planet reading kept 94,000 divisions for Western Europe, 1.3 GB of shapes. The world has many times that, so the world build cannot hold every level 7 and 8 area in memory at once. P3-T1c reads and sorts them a country at a time. I check its memory on the largest countries before the world build.

## What a larger pack means for you

Measured on 11 November, with nothing else running, on four packs:

* the trial pack, 21 MB;
* today's world pack, 127 MB;
* a padded copy of the world pack at 295 MB, the estimate;
* a padded copy at 340 MB, the top of the likely range.

A padded copy is the world pack with records added that the application never reads, as many as a real pack of that size would have. It stands in for a pack not built yet.

The place was Winchester. With the world pack, the first thing said is "England, United Kingdom. Press F1 for keys."; with the trial pack, the county comes first: Hampshire.

### The desktop

Each start is a new process, with no window on the screen and no sound. Three starts of each pack:

* Time to the first place said, the map named with the place as the window appears: 0.7 seconds with the trial pack, 0.7 with today's world pack, 0.7 with the 295 MB copy, and 0.9 with the 340 MB copy.
* The very first start, after other work, took 2.6 seconds, whatever the pack: that is Python and Qt being read from the disk, not the pack.
* Memory: 312 MB with today's world pack, 316 MB with the 340 MB copy.

The desktop reads the pack's directory when it starts, and then only the pack tiles near you. So a pack 2.7 times larger adds about 0.2 seconds and 4 MB of memory.

### The web version, in Chromium and Firefox

Each browser started with a new, empty profile, so the first visit downloads the pack into the browser's private storage, as from the internet. Here it came from this laptop, so the first visit shows the other work of the first visit, not the download.

* Return visit, the pack read from storage, until the map is ready and named with the place: Chromium 4.4 to 4.9 seconds, Firefox 4.3 to 4.6 seconds, for every pack. Most of it is starting Python in the browser.
* First visit, without the network's time: Chromium 4.9 to 6.0 seconds, Firefox 4.8 to 7.4 seconds. Firefox's grows with the pack, by about 1 second for each 100 MB, for writing it to storage.
* Memory, all the browser's processes: Chromium about 880 MB, Firefox about 1,300 MB, the same for every pack. The pack is read from storage as needed, not held in memory.
* Storage: the pack, plus about 65 MB for the application itself. Firefox reported 85, 191, 359 and 404 MB for the four packs. Chromium's own figure is rounded and larger: 97, 197, 466 and 466 MB.
* In a private window, browsers give no private storage, so the whole pack is held in memory instead: a 295 MB pack would add 295 MB of memory there. Not measured.

### The download

Worked out from the size, not measured:

* Today's pack, 127 MB: 1.7 minutes at 10 megabits a second, 20 seconds at 50.
* 295 MB: 3.9 minutes at 10 megabits a second, 47 seconds at 50.
* 340 MB: 4.5 minutes at 10, 54 seconds at 50.

It is downloaded once, and again only when the pack is updated.

## What the trial found about counties

These are for P3-T1c, counties for the whole world. Each can be put right in the counties record, which is what it is for (DP101).

* Most countries fit the rule well: France's départements (97 in the box), Germany's districts (406), Italy's provinces, Spain's provinces (51), the United Kingdom's counties and unitary authorities (220), Ireland's counties (26), Austria's districts (94), Portugal's districts (18), Belgium's provinces (11).
* Some countries use municipalities for their counties, because no level 6 exists: the Netherlands (342, level 8), Croatia (456, level 7), Slovenia (190), Norway (177) and Sweden (205, both level 7, from the record), and most of Brazil (2.5 million km2 of level 8 in its box). Correct by the rule, but small, and many.
* Some countries' counties are mostly the region itself, because their real counties are at level 5, which the rule does not look at: Argentina's departments, and parts of Africa, such as Chad, the Central African Republic, South Sudan and Angola. Uruguay has no level below its departments, which are level 4. For these, the record should name level 5 where it exists.
* Tunisia's level 6 areas are its sectors, the smallest units it has: 1,533 of them, more than a quarter of the trial's 5,317 counties, and 194 under 1 km2. Its delegations, at level 5, would suit better, and would make the trial pack smaller. Also for the record.
* A country can mix kinds of area in its counties, such as Argentina's departments and municipalities, where level 6 covers only part of it.

## Changes made in this task

* The run switch: now only a first line of yes lets a build carry on. No, or anything else, pauses it; a missing file still means carry on (your request of 10 November). The guide, the configuration reference and the glossary say so.
* Counties in the build: a new setting of the grid squares stage, counties: true, gives the Counties layer by the rule of DP101. Level 7 and 8 areas that can fill no gap are left out first, which left out 87,402 of Western Europe's 88,929. Levels a country's counties do not use are left out too. The join stage gives sliver counties to their neighbour.
* tools/pack_layers.py: each layer's share of a pack, in megabytes and points.
* tools/time_pack_start.py: padded copies, and the start-up, memory and storage measurements on the desktop and in both browsers.
* The glossary gains: size trial, sample region, padded copy, region used as county.
* The counties record is not written by the trial; P3-T1c does that.

## Not measured yet

* The other Phase 3 layers, and so the thresholds of DP169: added to this report as each is built.
* A start just after the laptop is switched on, when nothing is in the disk's cache.
* A real download over the internet.

## Questions for you

You answered both questions on 11 November 2026. Counties go into the world pack, and the soft limit is about 400 MB (DP175, PCK-1). The thresholds wait for the other layers (DP169).

### Counties in the base pack (DP167)

The figures say counties for the whole world cost about 170 MB of download and storage, and nothing you would notice in use. The choices:

1. Counties in the base pack, and the soft limit raised, to perhaps 400 MB, to leave room for the other layers. Hampshire is in the Phase 3 gate. The cost is the first download: about 5.5 minutes at 10 megabits a second for 400 MB.
2. Counties in the regional packs (Phase 4) instead, as the plan first proposed. The base pack stays near 250 MB with the other layers. Hampshire, and hierarchy mode below regions, wait for Phase 4.
3. Decide after the next layers are measured, so the whole size is known. The trial goes on with counties until then.

My suggestion is choice 1, because a larger pack costs you only its first download and its storage. But if the other layers turn out large, the total could pass 400 MB, so choice 3 is also sensible: it delays nothing, as the world build waits for all the layers anyway.

### The thresholds (DP169)

Nothing yet: none of the layers they apply to is built. I keep your answer for the trial until they are.
