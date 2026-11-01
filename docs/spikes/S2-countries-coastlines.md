# Spike S2 findings: countries, coastlines and islands

Task P0-T5. Architecture sections 6.12 and 12.3. Status note of 1 November 2026, updated in the evening. Stage 1 is complete: the seventh run passed every check below. Later stages wait for the PO's review and discussion point 101.

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
