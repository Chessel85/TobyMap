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
