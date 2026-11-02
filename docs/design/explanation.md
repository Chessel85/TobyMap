# Explanations

This document explains how parts of TobyMap work, in plain words, for the product owner and anyone else who wants to understand the design without reading the code. Each section covers one topic. The words used follow the glossary (glossary.md), which gives each one exact meaning. The technical decisions themselves are in architecture.md.

## How the build trims countries to the coastline

### The problem

A country's boundary in OSM includes its territorial waters, usually 12 nautical miles out to sea. The UK's boundary covers 403,068 square kilometres, but only 243,533 square kilometres of that is land. Without trimming, standing 5 km off Brighton would say "United Kingdom" instead of the sea.

### Words used in this section

These are defined in full in the glossary.

* Area: one country, region or county, as its OSM boundary draws it, sea included.
* Land tile: one shape in the land polygons file. It is either a whole small island, or a slice of a bigger island or a continent, cut along the lines of latitude and longitude at every whole degree. So Great Britain is not one shape in the file; it is many land tiles, each no bigger than one degree north to south by one degree east to west. Each land tile overlaps its neighbours very slightly, so there are no cracks between them.
* Reading box: a rectangle on the map, given as its west, south, east and north edges in degrees. It is used only to decide which land tiles to read from the file. For example, the Europe reading box runs from 19 degrees west to 16 degrees east, and from 27 degrees north (below the Canary Islands) to 61.5 degrees north (above Shetland). The reading boxes for spike S2 are listed in mapdata/config/s2_stage1.yaml.
* Part: one separate bit of an area's finished shape. The mainland of Great Britain is one part of the UK, Skye is another, and every islet and rock is another.

### The land polygons

* OSM has a separate, worldwide product called the land polygons, made from the coastline lines that mappers draw (tagged natural=coastline).
* The OpenStreetMap community's coastline tools join all those lines into closed shapes every day. The result is all the land in the world, including every island, with the sea removed.
* It comes ready to download, already cut into land tiles: about 870,000 for the world. Spike S2 fetched it with `mapdata fetch land-polygons`, dated 31 October 2026.
* It was chosen instead of joining coastlines onto boundaries, which is the approach that failed in AtlasDL (decision AD-15).

### The steps

1. Read only the land tiles that are needed. Reading the whole world would be slow, so the build reads only the land tiles inside its reading boxes: one for Europe and the Canary Islands, and one for each French overseas region (French Guiana, Guadeloupe, Martinique, Réunion and Mayotte). The Europe reading box holds 86,656 land tiles. They are saved in the build's working folder, so later runs skip this step.
2. For each area, find the land tiles that overlap it. A spatial index, which works like a catalogue sorted by position, finds them quickly without checking every land tile. England, for example, overlaps a few thousand land tiles.
3. Keep or cut each of those land tiles:
   * a land tile wholly inside the area's boundary is kept as it is. That covers most inland tiles, and small islands that lie well inside the territorial waters;
   * a land tile that crosses the area's boundary is cut, keeping only the part inside. That happens at land borders, such as between England and Wales, where one land tile can lie partly in each;
   * land tiles on the coast need no special handling: the sea was never in them, so the coastline comes through as it is.
4. Join the kept land tiles into one shape for the area. Joining removes the one-degree cuts between neighbouring land tiles, so the mainland becomes one part again. Islands stay separate, because there is sea between them. That's why the UK comes out as 19,854 parts: the mainland, the big islands, and thousands of islets and rocks.
5. Remove the seam points. The land tiles overlap by a thin band along each one-degree line. Where a border between two areas crosses that band, cutting in step 3 can add an extra point to the border on one side but not the other. The build removes points that lie within 0.1 mm of the border line, so two neighbours keep exactly the same border.
6. Clean each layer. A layer means all the areas at one level, such as all the countries. Cleaning closes the tiny gaps that are left where a border meets the coast. It also settles places where OSM's own borders overlap, such as between Burgos and Soria in Spain, by giving each overlap to the neighbour that shares the longer border with it.

The same steps are applied at every level: countries, regions and counties. Because they all use the same land tiles, they line up with each other and with the coast.

### What comes out

These results are from spike S2, stage 1.

* Gibraltar: 93 square kilometres with its waters, 7 square kilometres of land.
* Andorra: unchanged at 467 square kilometres. It has no coast, so every land tile is either wholly inside it or cut only at its land borders.
* Islands: they come out without any special handling. Skye, the Isle of Wight and the Canary Islands each end up as part of the right country and county.
* Checks: sea points, such as off the Pointe du Raz and in the Solent, are in no area. The build also looks for land that ended up in no country, and found none.

### Limits worth knowing

* Lakes and rivers stay land. The land polygons remove only the sea, so Lough Neagh is still inside Northern Ireland. That's right for saying where you are, but water will need its own layer.
* Estuaries depend on mappers. Where a river meets the sea, mappers decide where the coastline crosses the river. Upstream of that point the river counts as land, so for example the Thames counts as land through London.
* The dates don't match. In spike S2, the boundaries came from the planet file of November 2025, and the land polygons from October 2026. Where either changed in that year, the two might not quite meet. The checks found no problem, but the real pipeline should use a planet file and land polygons from close dates. This is listed for Phase 1 in the S2 findings (docs/spikes/S2-countries-coastlines.md).

## How the build shares its work between the processor's cores

### The problem

Your laptop's processor has 4 cores, and each core can run two threads, so 8 things can happen at once. In spike S2, most of the build ran on one thread. While stage 3 was running, the laptop showed about 30% of the processor in use and 40% of the memory, and some steps took the better part of an hour. At that speed, building the whole world could take days.

The graphics card can't help. It is very fast at the arithmetic used in neural networks, which is why the OMR project uses it, but the map build does polygon geometry: cutting, joining and comparing shapes. The library that does this, GEOS, only runs on the processor.

### Workers

The build now works like a small office. The main process is the manager. It splits a slow step into many small jobs and hands them to worker processes, which run at the same time on different cores. Each worker sends its result back, and only the manager writes the files and the report, so nothing gets mixed up. This is the same method OMR uses.

These steps are shared out among workers:

* Cutting each area to the land. Each area is one job. The biggest go first, so a large country isn't left until the end.
* Checking that neighbours meet exactly. Each layer is one job.
* Writing the pack. The shapes are cut into pack tiles in batches, then the pack tiles are encoded in batches. Both kinds of pack (WKB and compact coordinates) are now written from one cutting, where before each was cut separately.
* Drawing the pictures. Each picture is one job, and the globe views are another.

### How many workers

* 3 by default, while you're using the laptop. The laptop stays usable, though a bit slower. Running all 8 threads flat out also makes the chip hot, and it then slows itself down.
* 6 with `--away`, when nobody is using the laptop.

### Memory comes first

Each worker holds its own copy of the shapes it's working on, so more workers means more memory. On 2 November, two builds running at once ran the laptop out of memory, and Claude Code stopped them both. So:

* a new job only starts while at least 6 GB of memory is free. When memory is short, fewer jobs run at once, and the build carries on more slowly instead of stopping;
* if free memory falls below 3 GB, the build stops by itself, writes its report so far and a note of where it stopped, and keeps everything it has finished, so the next run carries on from there;
* this check pauses while the planet file is being read, because reading it fills memory with a copy of the file that Windows can take back at any time.

### Before a heavy build

Claude Code tells you before a heavy build starts, so you know the laptop will be slower: which build, how many cores, and roughly how long. The first lines of the build's report say the same, including how long the last run of that build took.

### What made the biggest difference

Sharing the work between cores helps, but on 2 November the biggest gains came from doing less work, not from more cores:

* finding land in no county: from over half an hour to seconds, by working first with the boundaries as read, which have few points at sea, and only then cutting the small leftover to the land;
* matching Norway's 150,000 island names to its land: from over 25 minutes to seconds, by preparing each part of the land once;
* checking that neighbours meet: from over half an hour per layer to under two minutes, by checking only within 5 km of the land borders;
* looking up a place in the pack: from 0.75 seconds to 0.02 seconds, by not letting one pack tile hold too many points.
