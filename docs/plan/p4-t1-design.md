# P4-T1 design: the regional pipeline

Version 0.1, 21 November 2026. Written by Claude Code (the designer for P4-T1) for the orchestrator, the subagents that do P4-T0e, P4-T1a to P4-T1k and P4-T3a to P4-T3e, and the product owner (PO).

Every work item of P4-T1 follows this note, so the stages fit together and no two work items change the same lines. Where this note and docs/plan/phase-4-plan.md differ, this note wins for P4-T1, and the difference is listed under "Choices for the PO". Words follow docs/design/glossary.md. New words are listed in section 10, and each is added to the glossary by the work item that first uses it.

## 1. In short

1. A regional pack is a pack with street detail for one region. The first is the Great Britain pack, rehearsed first on Hampshire and the Isle of Wight.
2. Its region outline is Geofabrik's boundary file (.poly), fetched by `mapdata fetch` into the data folder. Its data is read from the same planet file as the world pack (DP107), so identifiers and borders agree.
3. Its coverage is a list of covered pack tiles: every pack tile at tile level 12 (about 6 by 5 kilometres) that holds land inside the outline. Inside its coverage the regional pack holds everything of its layers, complete, including land and sea that lie just beyond the outline in those pack tiles.
4. It holds its own countries, regions, counties, islands, oceans and seas in its coverage, made by the world's own stages with the world's settings at 10 metres instead of 100, so the coast under the streets is the coast the streets meet.
5. It adds new layers: districts, parishes, every island, every lake and pond, streams, main roads, streets, paths, land use, parks, school grounds, national parks, points of interest in four layers, and villages.
6. It leaves to the world pack: continents, mountain ranges, physical regions, territorial waters, bays and straits as places, peaks, cities and towns, enclaves and exclaves, and the graticule.
7. The build is the world's stages, unchanged in code, with a box and finer settings; then a coverage stage cuts everything to the coverage; then new stages, each in a new module, add the new layers; then a match stage gives each feature the world pack's identifier where the two packs share it, keeping its own as an alias.
8. The world pack itself is the identifier register: the match stage reads world.pack. No separate register file is needed, so P4-T1h needs no world rebuild.
9. The pack format number stays 4. The manifest's coverage member gets its regional form, and feature records gain two optional fields, partial and aliases. app_versions keeps older applications from opening a regional pack.
10. Estimates: Hampshire and the Isle of Wight about 35 to 60 MB and under an hour; Great Britain about 800 MB (somewhere from 550 MB to 1.1 GB) and 6 to 12 hours, run overnight with --away.

## 2. The pack

### 2.1 The settings files

Three new pack settings files in mapdata/config/packs, all made by P4-T1a:

* great-britain.yaml: the Great Britain pack. name great-britain, title "Great Britain: streets, paths, land use, parks, school grounds, points of interest and every administrative level.", version 0.1.0, coverage {kind: region, outline: great-britain-outline}, layer_groups [base, regional].
* hampshire-isle-of-wight.yaml: the rehearsal. The same stages and settings as great-britain.yaml, with the outline sources hampshire-outline and isle-of-wight-outline (the coverage stage joins two outlines into one).
* test-region.yaml: the regional test pack (section 5), built from the samples in the repository, so the tests never need the data folder.

great-britain.yaml and hampshire-isle-of-wight.yaml must stay the same apart from name, title, outline, box and space_needed_mb. A test (P4-T1a) compares their stages with those lines taken out, so a setting changed in one is not forgotten in the other.

### 2.2 The outline

* Sources, added to mapdata/config/sources.yaml by P4-T1a, each fetched by `mapdata fetch <key>` into <data folder>/tobymap/downloads/geofabrik-outlines:
  * great-britain-outline: https://download.geofabrik.de/europe/great-britain.poly
  * hampshire-outline: https://download.geofabrik.de/europe/united-kingdom/england/hampshire.poly
  * isle-of-wight-outline: https://download.geofabrik.de/europe/united-kingdom/england/isle-of-wight.poly
* Licence: P4-T1a reads Geofabrik's terms for the .poly files and writes them into sources.yaml and docs/design/data sources.md. The outline only chooses which pack tiles are covered; no shape of it goes into the pack. If Geofabrik's terms do not allow even that, P4-T1a stops and tells the orchestrator.
* The .poly format is plain text (a name line, then sections of "lon lat" lines, each ended by END, a section starting with "!" being a hole). P4-T1a writes the reader, standard library and Shapely only, in mapdata/stages/coverage.py. No new package.
* DP223: Great Britain as Geofabrik draws it: England, Scotland and Wales with their islands. Northern Ireland, the Isle of Man and the Channel Islands are outside it.

### 2.3 The coverage

The coverage stage (P4-T1a) works it out once, after the join:

1. The land inside the outline is the land of the countries layer of the stage before (the land as the countries draw it, as DrawnLand does for the physical stage), intersected with the outline.
2. A pack tile at the coverage's tile level (setting tile_level, 12 for both real packs, 14 for the test region) is covered if it holds any of that land, of any size. Pack tiles of open sea are not covered: the world pack answers there.
3. Four covered pack tiles that make one pack tile at the level above are written as that one, up to tile level 6, so Great Britain's coverage is a few thousand entries, not tens of thousands.
4. The coverage shape is the union of the covered pack tiles. Every feature of every stage from here on is cut to it.

What the pack records, in its manifest (the builder gives it; the writer checks it):

    "coverage": {
      "kind": "region",
      "region": "great-britain",
      "tile_level": 12,
      "tiles": ["8/127/203", "12/2034/3271", ...],
      "layers": ["countries", "regions", "counties", "islands", "oceans", "seas", "lakes", "rivers",
                 "roads", "railways", "districts", "parishes", ...],
      "draw_below_km": 250
    }

* tiles: each covered pack tile as "level/x/y", in the grid of docs/developer/pack-format.md, sorted.
* layers: the layers the regional pack answers for inside its coverage: every layer it holds features of. For any other layer, such as the continents, the world pack answers everywhere.
* draw_below_km: the regional pack draws only views narrower than this; at wider views the world pack draws alone (its layers all end at 100 kilometres or closer anyway).
* A world pack keeps {"kind": "world"}.

How the core finds it (P4-T3a): for a point, it checks the pack tile holding the point at each level from 6 to the coverage's tile_level against a set made from tiles at start-up. That is at most seven set lookups, so it costs nothing against NFR-1.

### 2.4 Format changes

* No new format number. Format 4 readers already ignore fields they do not know, the manifest's coverage member was left "to be settled in Phase 4", and no regional pack has been published. As with the search records of 13 November, docs/developer/pack-format.md gets a version history line.
* Manifest coverage: the regional form above (P4-T1a).
* Feature records, two optional fields (P4-T1a lets the writer pass them through; P4-T1h fills aliases):
  * partial: true when the pack holds only part of the feature, because the coverage cut it: the United Kingdom without Northern Ireland, the North Atlantic Ocean, a street leaving the coverage. A feature is partial when the cut leaves less than 99.9 percent of its area, or of its length.
  * aliases: the feature's own identifiers in this pack's sources when the match stage gave it the world pack's identifier, such as a lake read under a different way.
* app_versions: {from: <the version in version.txt when P4-T3a is merged>}. An older application would read a regional pack as a world pack and answer wrongly, so it must refuse it with its usual message (packs.app_too_old). P4-T3a sets the number in both pack files.

### 2.5 What the regional pack holds and what it leaves

Held, inside the coverage (the coverage's layers list):

* Made by the world's own stages with the world's settings, so they keep the world's identifiers: countries, regions, counties, islands, oceans, seas (osm-areas, squares, join), lakes (osm-layer), rivers (osm-rivers), roads and railways (osm-lines).
* Added by new stages: districts, parishes, every island under 1 km2, every other lake and pond, every other river and canal, streams, main roads, streets, paths, land use, parks, school grounds, national parks, the four layers of points of interest, and villages.

Left to the world pack everywhere: continents, territorial waters, bays and straits as places, mountain ranges, physical regions, peaks, cities and towns, enclaves and exclaves, the graticule and the special lines, and later the groups of islands (P4-T13). The regional pack has no continents, distant-parts, disputes, enclaves, physical, territorial-waters or graticule stage.

Why the regional pack holds its own countries, counties and seas: the world pack's coast is simplified to 100 metres. A street on the seafront could lie in the world's sea, and a point 50 metres offshore in the world's land. Holding the areas at 10 metres in the covered pack tiles keeps "where am I" and the streets on the same coast, and the oceans and seas there keep LOC-6: every point of a covered pack tile is in a land area or a sea. A check (P4-T1a's test, and the checks stage of each build) proves it.

The world-only layers stay as the world built them. At the very edge of the coast, a mountain range or a continent cut to the world's 100-metre land can miss a point that the regional pack calls land, by up to about 100 metres. This is accepted (see Risks).

## 3. The stages

### 3.1 Rules for every stage of P4-T1

* No existing stage's code is changed, except write.py (P4-T1a) and relationships.py (P4-T1k). A stage's code is in its fingerprint, so changing, say, osm_lines.py would make the next world build read the planet file again for no gain. New behaviour goes in new modules, and a new module may import functions from an existing one (and list it in its own code tuple in mapdata/pipeline/build.py).
* Every new setting of an existing module must default to the old behaviour.
* Every new stage keeps the features of the stage before and adds its own after them, as osm-layer does.
* Every new layer has made_by in its layer definition, so adding it never reruns the squares and join stages (architecture 6.11b).
* Reading the planet file is done in a short-lived process (GeoDesk keeps its memory until the process ends), through the one helper of section 3.4.
* Each new stage cuts its shapes to the coverage, with osm_source.clip_to_coverage, and marks partial features.
* Each new stage simplifies to its tolerance_m setting: 2 metres for streets, paths and waterways, 5 metres for land use, parks, school grounds and lakes, 10 metres for districts and parishes (the counties' detail).
* Ids: an OpenStreetMap object keeps "osm:" and its type letter and number, as now. A feature joined from several ways takes the id of its smallest way, as osm-lines does. An id the build makes itself has its own prefix, such as "unparished:osm:r2783442".
* Every stage writes a plain-lines log, and puts in features.json what the quality report needs (counts, repairs).
* Settings are documented in docs/data-manager/configuration.md, one section per new stage, by the work item that makes the stage.

### 3.2 The stages of great-britain.yaml, in order

Each is: the stage, who makes or sets it, what it reads, what it writes, and what is in its fingerprint besides the usual (its settings, the pack's layers, the stage before, its code).

1. osm-areas. Existing, unchanged; settings as the world's (levels [3, 4, 5], counties: true, islands: true) plus box: the outline's bounding box, widened by 0.1 degrees. Reads the planet file. Writes countries, regions, county areas and islands as read. Fingerprint: the planet file, the counties record.
2. squares. Existing, unchanged; settings as the world's (land-polygons, vliz-oceans, seas: naturalearth-marine-areas, counties: true, the Moselle condominium is outside the box and may be left out) plus the same box and tolerance_m: 10. Writes the grid squares. Fingerprint: the land polygons, VLIZ, Natural Earth's marine areas.
3. join. Existing, unchanged, no settings. Writes countries, regions, counties, islands (unnamed ones of 1 km2 or more, as the world), oceans and seas.
4. coverage. New, P4-T1a, mapdata/stages/coverage.py. Settings: outline (one source key or a list), tile_level (12), merge_from_level (6). Reads the .poly files and the countries layer of the stage before. Writes coverage.json (the tiles, the coverage shape as WKB, the outline's name) and the features of the stage before cut to the coverage, each marked partial where cut. Fingerprint: the outline files' bytes.
5. local-areas. New, P4-T1b, mapdata/stages/local_areas.py. Every administrative level below the counties (section 3.5). Reads the planet file within the coverage, mapdata/config/local_levels.yaml. Writes the layers districts and parishes. Fingerprint: the planet file, local_levels.yaml (fingerprint_extra).
6. small-islands. New, P4-T1c, mapdata/stages/small_islands.py. Every island under 1 km2 (section 3.6). Reads the stage before only. Writes more features in the layer islands.
7. osm-layer (lakes). Existing, unchanged; the world's queries with min_km2: 0 and tolerance_m: 5. Writes every named lake, with the world's ids.
8. osm-water. New, P4-T1c, mapdata/stages/osm_water.py. Every other water area: unnamed lakes and ponds, reservoirs, basins (section 3.6). Writes more features in the layer lakes.
9. osm-rivers. Existing, unchanged; the world's settings (min_km 50, min_km_unlinked 200) with tolerance_m: 2 and no check. Writes the rivers the world pack has, with the world's ids.
10. osm-waterways. New, P4-T1g, mapdata/stages/osm_waterways.py. Every other river and canal into rivers; every stream, ditch and drain into streams (section 3.9).
11. osm-lines. Existing, unchanged; the world's two layers (roads, railways) with tolerance_m: 2. Writes motorways, trunk roads and main railway lines, with the world's ids.
12. osm-streets. New, P4-T1d, mapdata/stages/osm_streets.py. Main roads, streets and paths (section 3.7).
13. osm-land. New, P4-T1e, mapdata/stages/osm_land.py. Land use, parks, school grounds and national parks (section 3.8). Reads mapdata/config/land_classes.yaml (fingerprint_extra).
14. osm-pois. New, P4-T1f, mapdata/stages/osm_pois.py. The four layers of points of interest, from mapdata/config/poi_categories.yaml (fingerprint_extra) (section 3.10).
15. osm-places (villages). Existing, unchanged; queries n[place=village][name], n[place=suburb][name], n[place=hamlet][name], n[place=neighbourhood][name], n[place=quarter][name], each with its type and population: true; layer villages; within: [countries, regions, counties, districts, parishes].
16. match. New, P4-T1h, mapdata/stages/match.py. Gives features the world pack's ids (section 3.11). Reads the source world-pack. Writes the features with ids changed and aliases added, and matches.csv. Fingerprint: world.pack's size and date (the source's fingerprint).
17. wikidata. Existing; settings as the world's, refresh the same label, so facts already fetched are read from the data folder; match: [lakes]. Which layers get facts is decided by P4-T1k on the rehearsal's figures (section 3.12).
18. relationships. Existing, with P4-T1k's new setting light_layers (section 3.12).
19. coast-stretches. Existing, unchanged.
20. corrections. Existing, unchanged, with the same rules file as the world. A rule for an id not in the regional pack is expected; the stage already lists it, and the quality report says the pack is regional.
21. write. Existing, with P4-T1a's changes: the coverage into the manifest, partial and aliases passed through, the regional drawing levels (section 3.13).
22. checks. Existing; places: tests/acceptance/street_places_hampshire.yaml (P4-T1j) for the rehearsal, and the Great Britain files of P4-T2c for great-britain.yaml.

Stages of the world pack's settings that are not here: graticule, distant-parts, continents, osm-places for sea places, peaks and towns, physical, territorial-waters, disputes, enclaves.

### 3.3 The test region's stages

test-region.yaml (section 5) has the same new stages in the same order, with the samples stage in place of stages 1 to 3, and source keys of samples in place of the planet file:

1. samples: the test pack's own files for the area layers (sample-world, sample-oceans, england-france-channel, hampshire-wiltshire, isle-of-wight-solent) and the new cooked sample lymington-coast.geojson.
2. water, land_layer: countries (as the test pack).
3. coverage, outline: sample-outline, tile_level: 14.
4. Then local-areas, small-islands, osm-water, osm-waterways, osm-streets, osm-land, osm-pois, osm-places (villages), each with source: sample-osm-raw instead of planet.
5. match, with world: the test pack (section 5.4).
6. relationships, corrections (file: tests/samples/corrections.yaml), write.

The existing stages osm-layer, osm-rivers and osm-lines cannot read the raw samples, as their code stays unchanged; the test region leaves them out, and their behaviour is already tested.

### 3.4 One way to read OpenStreetMap: osm_source.py (P4-T1a)

mapdata/stages/osm_source.py, used by every new reading stage:

* open_source(ctx, key): the planet file (a GeoDesk library) or a raw sample file (section 5.1), behind one small interface: query(goql, box) yields objects with id ("osm:w123"), kind (node, way, area), tags (a dict) and shape (Shapely, in degrees).
* For the raw samples, a matcher for the part of GeoDesk's query language the stages use: n, w, a and their combinations; [key]; [!key]; [key=a,b]; [key!=a,b]; [key>=n]. Anything else is refused with a clear message, so a stage cannot quietly use a query the samples do not understand.
* run_reading(ctx, module, request): writes request.json, starts `python -m mapdata read-osm <folder>`, which imports the module named in the request and calls its read_job(source, request, out_folder). P4-T1a adds the one subcommand read-osm to mapdata/__main__.py, so no later work item edits that file. With a raw sample, read_job runs in the same process.
* The request carries the coverage: its pack tiles at a coarse level (tile level 8, about 1.4 by 0.7 degrees) as reading boxes. A read_job reads one reading box at a time and writes each box's results to disk before the next, so no reading process holds all of Great Britain's streets at once.
* clip_to_coverage(records, geoms, coverage): cuts each shape to the coverage shape, drops what is left empty, and marks partial.
* GeoDesk's shapes are in its own Mercator; the helper gives the stages degrees, as the existing stages do (see osm_lines.py).

### 3.5 Every administrative level (P4-T1b)

What OpenStreetMap holds in Great Britain (checked against the PO's uk.gol, 21 November; P4-T1b checks again on the planet file):

* England: level 4 England, 5 the regions (South East), 6 the counties, unitary authorities, metropolitan counties and Greater London, 8 the districts and boroughs (non-metropolitan districts, metropolitan boroughs, London boroughs), 10 the civil parishes. In the rehearsal's box there are 16 level 8 areas and 514 level 10 areas; in the United Kingdom 241 and 21,718. Level 9 has 80 areas in the United Kingdom: P4-T1b finds what they are and says whether they belong in a layer.
* Scotland: 4 Scotland, 6 the council areas, 10 the community council areas. No level 8.
* Wales: 4 Wales, 6 the principal areas, 10 the communities. No level 8.
* Electoral wards are boundary=political, not administrative, and only 644 are mapped in the United Kingdom. They are left out (Choices for the PO).

The record: a new file mapdata/config/local_levels.yaml, beside the counties record, one entry per country (by id, osm:r62149 for the United Kingdom), each with the levels of its districts layer and of its parishes layer, the name for land in no parish, and why. For the United Kingdom: districts [8]; parishes [10]; gap names: England "Unparished area", Scotland "Area with no community council", Wales none (Wales is wholly in communities). Another country later gets its own entry.

The method, in local_areas.py:

1. Read the areas at the record's levels within the coverage, each with its OSM id, name (name:en first, as osm-areas does), level, and wikidata tag.
2. Cut each to the land of the stage before's countries layer, as every land area is (AD-15).
3. Districts: each district is cut to the county that holds most of it, so a district is never outside its county. Land of a county in no district gets no district: a unitary authority, such as Southampton, is its own county and has no district under it.
4. Slivers: land of a county in no district, or of a district (or of a county with no districts) in no parish, that is a sliver by the join's rule (under sliver_km2 0.1, or narrower than sliver_width_m 200) goes to the neighbour of that layer with the longest shared edge, and is listed in the log and features.json for the quality report.
5. Gaps: larger land in no parish becomes one area per district (or per county with no districts) named by the record's gap name, with id "unparished:" and the district's id, type "unparished area". So every point of the coverage's land is in exactly one parish-layer area, which is what the plan's test "every point in the sample has a parish or ward" asks.
6. Shared edges (AD-16): inside each county, the districts are cleaned and simplified as one coverage with the county's outline kept fixed (shapely.coverage_simplify, simplify_boundary=False, at tolerance_m 10); then, inside each district (or county with no districts), the parishes are cut to the simplified district and simplified the same way. So a parish meets its district, its district meets its county, and neighbours meet, exactly, with no gap and no overlap. The test: the union of a district's parishes equals the district, and of a county's districts equals the county, to within floating point.
7. Records: layer districts or parishes; type from OSM's designation tag where it has one (non_metropolitan_district, civil_parish, community), turned into plain words; parent the area of the layer above that holds it; wikidata from the tag.

The tiers record (mapdata/config/tiers.yaml), by P4-T1b: two new tiers after county, "district" and "parish"; layers districts: district and parishes: parish; and the tier names for Great Britain (district or borough; civil parish in England, community in Wales, community council area in Scotland) under the United Kingdom's entry or as areas, by the existing rules. The words for each tier go in mapcore/describe/templates.yaml under details.tiers.

### 3.6 Every island and every lake (P4-T1c)

Islands:

* The join already makes named islands from OSM (place=island, place=islet) and unnamed ones of 1 km2 or more, with ids island:unnamed:lat:lon. Its constant UNNAMED_ISLAND_KM2 stays, as changing join.py would rerun the world's join.
* small-islands (new) takes every part of the countries layer's land that is not a continent-sized landmass and holds no island area, and is under 1 km2, and adds it as "Unnamed island", type island, id island:unnamed: and its representative point rounded to 5 decimals, so the id is the same each build (DMT-1). An islet OSM names only with a point (the "island point" records of osm-areas) names the part it falls on.
* Every island, of any size (DP87). The drawing's size rule leaves small ones out at wide zooms, as now.

Lakes:

* osm-layer with the world's queries and min_km2: 0 reads every named lake, reservoir and lagoon, with the world's ids for those the world has.
* osm-water (new) reads every other water area: a[natural=water] with no name (any water=* value, or none), a[landuse=reservoir], a[landuse=basin], a[water=pond], a[natural=water][water=river] is left out (a river's area belongs to its line, and is the land polygons' business at the coast; see Choices). Each into the layer lakes, type from the water tag (lake, pond, reservoir, basin, lagoon), name from OSM or, where none, the type's words from the templates ("Pond", "Unnamed lake"). An id already in the stage before is skipped.
* Counts to expect: 239,606 water areas in the United Kingdom, 19,307 named; 9,179 in the rehearsal's box.

### 3.7 Roads and paths (P4-T1d)

Layers, and the OSM ways in each (Shortbread's streets layer is the check):

* main-roads: highway=primary, secondary, and their _link ways. In Great Britain, A roads that are not trunk roads, and B roads.
* streets: highway=tertiary, tertiary_link, unclassified, residential, living_street, road, pedestrian (as a line), busway, and service except service=driveway, parking_aisle and drive-through.
* paths: highway=footway except footway=sidewalk and footway=crossing, path, bridleway, cycleway, steps, track.
* motorways and trunk roads stay in the world's layer roads, read by the unchanged osm-lines stage, so their ids are the world's.

Type: the plain words of the highway tag (primary road, secondary road, residential street, service road, footpath, bridleway, cycle path, steps, track). Number: ref, as osm-lines keeps it ("A33").

Joining, in osm_streets.py, importing join_lines and length_km from the existing modules:

* A main road with a number is joined by its number, per country, with osm-lines' rules for stretches far apart (import group_layer and its settings from osm_lines.py; osm_lines.py itself unchanged). "A33" is one feature, "B3335" another.
* A street or path with a name is joined with the ways of the same name and the same layer that meet it, end to end or at a shared point, again and again (union-find). Ways of one name that do not meet are separate features: the High Street of Winchester and the High Street of Twyford are two. A gap of up to 30 metres also joins (a roundabout or a dual carriageway's two sides). This is "joined by its name within a town" without needing the town: a name joins only what is connected.
* Unnamed ways of one layer and type that meet are joined within one parish (the stage before's parishes layer), so the footpaths across a field are one "Footpath" feature in that parish, not hundreds. A long unnamed track crossing a parish boundary is two features.
* Name: OSM's name, with the number added as osm-lines does ("A33, Basingstoke Road" when most of its ways carry the name). Unnamed: the type's words from the templates ("Footpath", "Service road").
* The way ids: every feature's OSM way ids are kept in ways.json in the stage folder, beside features.json, for the network graph of Phase 5. They are not written into the pack (Choices for the PO). The writing stage never reads ways.json.
* Counts to expect in the United Kingdom (uk.gol): main roads 498,017 ways with tertiary; residential and similar 1,660,587; service 2,504,951, of which 937,708 are driveways, parking aisles and drive-throughs; footways 1,687,002, of which 276,981 are sidewalks and crossings; paths, bridleways, cycleways and steps 754,794; tracks 527,692. In the rehearsal's box: 169,880 street ways (1.26 million points, 23,263 km) and 128,768 path ways (0.96 million points, 21,838 km).

### 3.8 Land use, parks, school grounds and national parks (P4-T1e)

A new settings file, mapdata/config/land_classes.yaml, made by P4-T1e: for each layer, the OSM tags in it, the type words of each, and Shortbread's layer and first zoom for the same tags, as the check (data sources.md: Shortbread is a reference only). The stage reports, in its log, each tag whose layer or zoom differs from Shortbread's, so the differences are deliberate.

* land-use: landuse residential, commercial, retail, industrial, farmland, farmyard, meadow, orchard, vineyard, allotments, cemetery, religious, forest, quarry, landfill, military, construction, brownfield, greenfield, railway; amenity=grave_yard; natural wood, scrub, heath, grassland, wetland, moor, bare_rock, sand, beach.
* parks: leisure park, common, nature_reserve, recreation_ground, playground, dog_park, pitch, sports_centre, golf_course, stadium; landuse recreation_ground and village_green; leisure=garden only with a name or access=yes or permissive (private gardens left out: 308,494 of them in the United Kingdom).
* school-grounds: amenity school, college, university, kindergarten, as areas. A school mapped only as a point becomes a point of interest (P4-T1f).
* national_parks: boundary=national_park; boundary=protected_area with protect_class=5 (England and Wales's National Landscapes, Scotland's National Scenic Areas). The layer id stays national_parks, the test pack's, so its tests keep working. A protected area cut to the land as every land area is.

Joining: unnamed land use areas of the same type that touch are joined, within one parish, into one area ("Farmland", "Woodland"), as one shape; named ones stay separate. This shrinks the 1,995,109 land use areas and 892,320 natural areas of the United Kingdom to perhaps a third, and drops the shared edges between fields, which are most of their points (3.06 million points in the rehearsal's box alone).

Each area keeps its OSM id (the smallest of a joined group), name, type, and wikidata tag. Overlaps between land use areas are kept: OSM's land use does overlap, and these layers are not painted as one coverage (fill none in the layer, colours by kind in the views, P4-T1i).

### 3.9 Rivers and streams (P4-T1g)

* osm-rivers (unchanged, world settings) makes the rivers the world pack has, joined by Wikidata link, with the world's ids.
* osm-waterways (new) reads every waterway=river and canal way not used by them, and every stream, ditch and drain, and joins them as P3-T1g does (import join_lines from osm_rivers.py): ways of one name that meet, end to end, kept in the direction they are drawn, which is the way the water flows, so each feature runs from source to mouth with its sections in order. A river or canal goes into rivers (type river or canal); a stream, ditch or drain into streams (type stream, ditch, drain).
* Unnamed waterways of one type that meet are joined within one parish, as unnamed paths are.
* Counts to expect in the United Kingdom: 33,163 river ways, 428,910 stream ways, 202,881 ditches, drains and canals.

### 3.10 Points of interest (P4-T1f)

The category table, mapdata/config/poi_categories.yaml, made by P4-T1f: each category has a key, its OSM tags (a list of alternatives), its layer, and its words in the templates. The first categories, the ones heard most:

* stops (layer): bus stop (highway=bus_stop; public_transport=platform with bus=yes), tram stop (railway=tram_stop), railway station (railway=station, railway=halt; an area becomes a place at its point), crossing (highway=crossing), taxi rank.
* shops-food (layer): shop (shop=*, with the shop tag's own words where the table names them: supermarket, convenience shop, bakery, butcher, chemist, hairdresser; others "shop"), cafe, restaurant, pub, bar, fast food, ice cream.
* services (layer): post office, pharmacy, doctors, dentist, hospital, clinic, bank, cash machine, library, toilets, police, fire station, community centre, town hall, place of worship (with religion: church, mosque, synagogue, temple), theatre, cinema, museum, information board, hotel, school (as a point), fuel station, car park, charging point.
* street-furniture (layer): post box, bench, bin (amenity=waste_basket), recycling, drinking water, telephone.

Rules:

* Nodes become places where they are; areas (shops in buildings, car parks) become places at a point inside them, as osm-places does. A feature matching two categories takes the first in the table.
* Record: name from OSM, or where none, the category's words, capitalised ("Bus stop", "Bench"); type the category's words. A bus stop's name in OSM is the stop's name ("Broadway (Stop E)").
* So that "a bus stop is said with its category" (the plan's test): a new layer field say_type (true for the four layers), added to SHOWN_FIELDS in mapdata/pipeline/settings.py and read by mapcore/layers/catalogue.py. Where the core names an item of such a layer and its name is not already its type's words, it says the type after the name: "Broadway (Stop E), bus stop". The approved wording goes in tests/mapcore/test_session.py. P4-T1f owns these core edits.
* The CSV for the PO: docs/plan/p4-t1f-poi-categories.csv, columns category, words, layer, tags, count in the rehearsal, count in the United Kingdom (from uk.gol), one row per category, made from the YAML by tools/make_poi_categories_csv.py so it can be made again. The PO reviews it; the table can grow from the PO's notes without a code change (the table is in the stage's fingerprint, so a change reruns osm-pois and the stages after it).
* Counts to expect in the United Kingdom: bus stops 283,345, crossings 305,951, post boxes 89,074, benches 147,142, bins 73,579, shops 288,672 (171,379 as nodes, 117,293 as areas), other amenity nodes about 400,000 after these, tourism nodes 87,685.

Villages (by P4-T1f, with the existing osm-places stage, no new code): the layer villages, from place=village, suburb, hamlet, neighbourhood and quarter with a name; 90,219 in the United Kingdom (with locality and isolated dwellings, which are left out).

### 3.11 Matching to the world pack (P4-T1h)

The identifier register is the world pack itself: a new source world-pack in sources.yaml (find: tobymap/output/world/world.pack; licence ODbL 1.0, as the pack), read with mapcore.packs and mapcore.store, which the stage may import. Architecture 6.7's "the base pack publishes an identifier register" is met by the world pack's own feature records; P4-T1h updates 6.7's wording.

The match stage, for each feature of the regional pack in a layer the world pack also has (countries, regions, counties, islands, oceans, seas, lakes, rivers, roads, railways):

1. Same id, same layer: matched. This is nearly every feature, as both packs read the same planet file with the same settings.
2. Otherwise, the same Wikidata id (the record's wikidata, from OSM's tag) in the same layer: takes the world's id.
3. Otherwise, the same name made plain (mapcore.search.normalise), the same layer and type, and overlap: for areas, each covers at least half of the other inside the coverage; for lines, at least half of the regional line is within 200 metres of the world's; for unnamed islands, the overlap alone, each covering at least half of the other.
4. A matched feature takes the world's id; its own goes into aliases. Every id that refers to it in the stage's records (parent, within) is changed too.
5. A regional id that the world pack uses in another layer gets the ending "#as-" and its layer, as the writing stage does.
6. A world feature of those layers that lies in the coverage and has no match is listed in the log, as it will be hidden in the covered pack tiles (P4-T3a).

matches.csv in the stage folder lists every match made by Wikidata or by name, and every world feature left unmatched, with both ids, both names and the overlap; P4-T1h adds a section "Matches with the world pack" to mapdata/pipeline/report.py from it (Risks: a wrong match is found here).

Districts, parishes and the other new layers have no world features to match, but their parents are changed by step 4, so a parish sits under the world pack's Hampshire.

### 3.12 Relationships, facts and size at street scale (P4-T1k, a new work item)

The world's relationships stage took 3 hours 13 minutes for 612,356 features. Great Britain will have about 4 million features, nearly all of them streets, paths, land use and places. Working out neighbours, nearly-touching areas and overlaps between every field and footpath is not useful and would not finish in a night. So P4-T1k adds a setting to relationships.py:

* light_layers: a list of layers whose features get only containment (in, partly), and, for lines, crossings with the crossing_areas layers in order. They get no neighbours, no nearly touching, no overlaps, and are not counted in any area's counts. For great-britain.yaml: main-roads, streets, paths, streams, land-use, parks, school-grounds, stops, shops-food, services, street-furniture, villages. Districts, parishes, national parks, lakes and rivers keep everything.
* crossing_areas for the regional packs adds districts and parishes, so a street says which parishes it passes through.
* Empty by default, so the world's results are unchanged (its fingerprint changes once, with the code; the world's relationships run again at P4-T15 in any case).

P4-T1k also:

* measures each stage's peak memory and time on the rehearsal (P4-T1j gives the figures), and if features.json loaded whole would need more than 12 GB for Great Britain (scaled by feature count), changes the stages it must so they load only the layers they need (mapdata.pipeline.features.load_layers exists for this);
* sets which layers the wikidata stage fetches facts for, so tens of thousands of streets and shops with a Wikidata tag do not each wait on the internet: areas, lakes, rivers, parks and national parks only. If the stage has no such setting, P4-T1k adds one, defaulting to every layer.

### 3.13 Layers, zoom ranges, sounds and map views (P4-T1i)

P4-T1a writes mapdata/config/layers/regional.yaml with each new layer's build fields only (id, name, rank, kind, made_by, geometry, group), from section 4, so every stage item can build. P4-T1i then adds the shown fields: switched_on, min_zoom_m, max_zoom_m, min_size, fill, crossing_earcon, sound, say_type, shown_name. It also:

* changes mapcore/views.yaml: the drawing order (section 4.6), each view's said order, political_layers [countries, regions, counties, districts, parishes], and how each new layer is filled in Political and Physical (DP198);
* adds theme colours in mapcore/render/themes.yaml for the new kinds (streets, paths, land use kinds, parks, school grounds), each checked for contrast in every theme (VIS-2), with the existing theme tests;
* adds the sound events layer_path, layer_park and layer_poi to mapcore/describe/earcons.yaml, with placeholder sounds from tools/make_placeholder_sounds.py (no sound files committed);
* adds the words for each new layer under details.layers in templates.yaml;
* makes samples.yaml's national_parks definition the same as regional.yaml's, so the test pack and a regional pack never disagree about a layer;
* sets the write stage's drawing levels in the three pack files. Start with: {tolerance_m: 25, min_km2: 0.02, tile_level: 9, view_km: 50} and {tolerance_m: 150, min_km2: 0.5, tile_level: 7, view_km: 150}, and adjust on the rehearsal so a frame stays near 10,000 points a layer (VIS-1). Views of 25 kilometres or less use the exact pack tiles (mapcore/render/scene.py, EXACT_BELOW_KM), and the writing stage already leaves a layer out of a drawing level its zoom range does not reach.

## 4. Layers

All in mapdata/config/layers/regional.yaml, except the layers the world already has. Ranks are whole numbers; changing a world layer's rank would rebuild the world's areas, so the new area layers share rank 7 with the lakes and are ordered by size, smallest first, which puts a parish before its district (LOC-2). Each view's said order decides what is said first in any case.

### 4.1 Boundaries

* districts: name "Districts", shown_name "Districts and boroughs"; group Boundaries; area; rank 7; made_by local-areas; zoom to 50,000 m; sound layer_region. Source: boundary=administrative, admin_level 8.
* parishes: name "Parishes", shown_name "Parishes and communities"; group Boundaries; area; rank 7; made_by local-areas; zoom to 10,000 m; sound layer_region. Source: admin_level 10, with gaps as "Unparished area".
* national_parks: name "National parks", shown_name "National parks and National Landscapes"; group Boundaries; area; rank 6 (as the test pack's); fill none; made_by osm-land; no zoom limit. Source: boundary=national_park; boundary=protected_area with protect_class=5.
* islands: the world's layer; small ones added by small-islands.

### 4.2 Water

* lakes: the world's layer, now every lake, reservoir and pond.
* rivers: the world's layer, now every river and canal.
* streams: name "Streams and ditches"; group Water; line; rank 8; made_by osm-waterways; zoom to 5,000 m; crossing_earcon line_crossing; sound layer_river. Source: waterway=stream, ditch, drain.

### 4.3 Transport

* roads and railways: the world's layers, at 2 metres.
* main-roads: name "Main roads"; group Transport; line; rank 8; made_by osm-streets; zoom to 50,000 m; crossing_earcon line_crossing; sound layer_road. Source: highway=primary, secondary and links.
* streets: name "Streets and minor roads"; group Transport; line; rank 8; made_by osm-streets; zoom to 5,000 m; crossing_earcon line_crossing; sound layer_road. Source: highway=tertiary, unclassified, residential, living_street, road, pedestrian, busway, and service but not driveways, parking aisles or drive-throughs.
* paths: name "Paths and tracks"; group Transport; line; rank 8; made_by osm-streets; zoom to 2,500 m; crossing_earcon line_crossing; sound layer_path. Source: highway=footway (not sidewalks or crossings), path, bridleway, cycleway, steps, track.

### 4.4 Land use and parks (a new group, "Land use and parks")

* land-use: name "Land use"; area; rank 8; made_by osm-land; fill none; zoom to 2,500 m; no sound. Source: land_classes.yaml.
* parks: name "Parks and public spaces"; area; rank 8; made_by osm-land; fill none; zoom to 10,000 m; sound layer_park.
* school-grounds: name "Schools and colleges"; area; rank 8; made_by osm-land; fill none; zoom to 5,000 m; sound layer_park.

Rank 8, above the parishes, so standing in Abbey Gardens you hear the park first, then the parish or unparished area, the district and the county.

### 4.5 Places (points)

* stops: name "Stops and crossings"; group Places; point; rank 8; made_by osm-pois; zoom to 1,000 m; say_type; sound layer_poi.
* shops-food: name "Shops, cafes and pubs"; group Places; point; rank 8; made_by osm-pois; zoom to 1,000 m; say_type; sound layer_poi.
* services: name "Services and amenities"; group Places; point; rank 8; made_by osm-pois; zoom to 2,500 m; say_type; sound layer_poi.
* street-furniture: name "Post boxes, benches and bins"; group Places; point; rank 8; made_by osm-pois; zoom to 250 m; say_type; sound layer_poi.
* villages: name "Villages, suburbs and hamlets"; group Places; point; rank 8; made_by osm-places; zoom to 25,000 m; sound layer_town.

### 4.6 The drawing order (mapcore/views.yaml, P4-T1i)

oceans, seas, territorial-waters, countries, regions, counties, districts, parishes, land-use, parks, school-grounds, national_parks, physical-regions, islands, mountain-ranges, lakes, rivers, streams, outlines, paths, streets, main-roads, roads, railways; places last, as markers.

Said order in Political, starting from today's: lakes, school-grounds, parks, land-use, seas, oceans, territorial-waters, parishes, districts, national_parks, counties, regions, countries, exclaves, islands, mountain-ranges, physical-regions, continents.

## 5. Samples for the test pack (P4-T0e)

### 5.1 Raw samples: OpenStreetMap objects with their tags

The new stages read OpenStreetMap, so their samples are OpenStreetMap as GeoDesk gives it, not finished features. A new folder, tests/samples/osm-raw, with three files. Each is a GeoJSON FeatureCollection with the members licence (the ODbL notice, as the existing samples), about (where and when it was read), and box ([west, south, east, north]). Each feature's properties are osm ("n123", "w123" or "r123"), kind (node, way or area) and tags (every tag of the object). Its geometry is as GeoDesk gives it, in degrees: a Point for a node, a LineString for a way, a Polygon or MultiPolygon for an area. Coordinates are OSM's own, to 7 decimals, unsimplified, except administrative boundaries, which are simplified to 0.0001 degrees (about 10 metres) as they are long and only their shape matters.

Every object that meets the box is kept whole, with all its tags. Each box is a whole number of pack tiles at tile level 14 (0.02197 by 0.01099 degrees, about 1.5 by 1.2 kilometres), so the test region's coverage, at tile level 14, is exactly the sample boxes:

* winchester.geojson: the pack tile x 8132, y 12839 at level 14: west -1.31836, south 51.05347, east -1.29639, north 51.06445. It must hold: the High Street, the Broadway and their side streets; footpaths; Abbey Gardens (a park); a school ground (Winchester College's or another in the pack tile); bus stops on the Broadway and High Street; crossings, post boxes, benches and bins; shops, cafes and pubs; the Cathedral (place of worship); the River Itchen and its side streams; land use; and the City of Winchester district (level 8) and every level 10 area meeting the box (Winchester's centre is unparished, so the unparished area is tested here).
* brockenhurst.geojson: pack tiles x 8119 to 8120, y 12817: west -1.60400, south 50.81177, east -1.56006, north 50.82275. It must hold: Brockenhurst's streets, tracks and bridleways; heath, woodland and forest land use; ponds, named and unnamed; streams; the New Forest National Park outline (simplified to 0.0005 degrees, as it is long); Brockenhurst station; the parishes of Brockenhurst and its neighbours and the New Forest district.
* lymington.geojson: pack tiles x 8121 to 8122, y 12810 to 12811: west -1.56006, south 50.73486, east -1.51611, north 50.75684. It must hold: Lymington's streets and harbour, the Lymington River and its estuary, salt marsh, small named islets (place=islet) where OSM has them, the slipways and paths along the shore, and the parishes there.

The tool checks each "must hold" and stops, naming what is missing, if the planet file lacks it; it may then move a box by whole pack tiles and say so. Together the three should be under 3 MB; if one is larger, the tool leaves out building outlines (the stages never read building=*), which it may do from the start.

### 5.2 Cooked samples for the test region's areas

* tests/samples/osm/lymington-coast.geojson, with box the Lymington box above: the United Kingdom, England, Hampshire, the Isle of Wight's county where the box reaches it, and the named islands in the box, cut to the exact land of the land polygons (the land-polygons source in the data folder) inside the box, simplified to 0.00001 degrees (about 1 metre), shared borders kept as tools/make_phase3_samples.py does; same ids as the existing samples (osm:r62149, osm:r58447, and Hampshire's). The samples stage replaces the coarser samples' areas inside its box with these, so the test region's land there has the salt marsh's islets for small-islands to find.
* tests/samples/outlines/test-region.poly: a .poly file with three sections, each the sample box shrunk by 0.001 degrees, so exactly the sample boxes' pack tiles at level 14 are covered.

The Winchester and Brockenhurst boxes are inland, so the test pack's existing 10-metre and 100-metre areas serve there.

### 5.3 The tool and the sources

* tools/make_phase4_samples.py, as tools/make_phase3_samples.py: it finds the newest planet file in the data folder, reads it with GeoDesk in its own short-lived process, reads the land polygons for the Lymington box, and writes the five files. Running it again makes the same files byte for byte (sorted by id, fixed key order, fixed decimals).
* sources.yaml, by P4-T0e: sample-osm-raw (repo: tests/samples/osm-raw, ODbL 1.0) and sample-outline (repo: tests/samples/outlines/test-region.poly, made by TobyMap from the sample boxes; licence: the repository's own, as it holds no outside data).
* tests/samples/README.md gets a section for the Phase 4 samples.

### 5.4 The regional test pack

* mapdata/config/packs/test-region.yaml (P4-T1a makes it; each stage item adds its own stage, see section 6): name test-region, coverage {kind: region, outline: sample-outline}, layer_groups [base, regional], the stages of section 3.3.
* tests/conftest.py, by P4-T1a: a fixture test_region_pack, session-scoped like test_pack, that builds test-region after the test pack into its own folder. Its match stage's world-pack source must point at the test pack just built: the fixture copies mapdata/config into a temporary config folder and sets the world-pack source there to the built test pack (build() already takes config_dir).
* The test pack (test.yaml) itself does not change. P4-T3's tests open the test pack and the test region together.

## 6. The work items

In order. Each lists what it does, the files it may create or change, its tests, and its model. "Its block" means the stage's own block in the three pack files (great-britain.yaml, hampshire-isle-of-wight.yaml, test-region.yaml), where P4-T1a leaves a commented placeholder line "# <stage>: added by P4-T1x" in the right place; the work item replaces only that line. "Its section" means its own section in docs/data-manager/configuration.md. The glossary is changed only for the words in section 10.

Files owned once, for all of P4-T1, by P4-T1a: mapdata/pipeline/build.py (every new STAGES entry, each naming its module even before the module exists: a stage is imported only when a pack uses it), mapdata/__main__.py (the one read-osm subcommand), mapdata/config/layers/regional.yaml (build fields), mapdata/config/sources.yaml (outline and world-pack sources), tests/conftest.py (the test_region_pack fixture).

Files several work items touch, and who owns which part:

* mapcore/describe/templates.yaml: P4-T1b details.tiers; P4-T1c the words for unnamed water ("Pond", "Unnamed lake", "Unnamed island" exists); P4-T1d the street and path type words ("Footpath", "Service road"); P4-T1f a new section poi_categories; P4-T1i details.layers.
* mapdata/config/layers/regional.yaml: P4-T1a the build fields; P4-T1i the shown fields; nobody else.
* The three pack files: P4-T1a everything except each later stage's block.
* docs/data-manager/configuration.md: each item its own section.
* tests/mapcore/test_session.py (approved wording): P4-T1f only (say_type).

### P4-T0e Samples for the test pack (Sonnet)

* Does: section 5.1 to 5.3.
* Files: tools/make_phase4_samples.py; tests/samples/osm-raw/winchester.geojson, brockenhurst.geojson, lymington.geojson; tests/samples/osm/lymington-coast.geojson; tests/samples/outlines/test-region.poly; tests/samples/README.md; mapdata/config/sources.yaml (the two sample sources only); tests/tools/test_phase4_samples.py.
* Tests: each file has the licence and its box; each "must hold" of section 5.1 is there (counted by tag); the .poly reads as three boxes; the samples are under the size limit. The byte-for-byte remake is checked by running the tool twice locally (it needs the planet file), not in continuous integration.
* Runs: the tool once, reading the planet file for a few minutes (tell the PO; nothing else reading the planet file then).

### P4-T1a A regional pack's settings and coverage (Opus)

* Does: sections 2, 3.3, 3.4, 5.4; the writing stage's changes (coverage into the manifest, checked: tiles valid and sorted, layers all in the pack; partial and aliases passed through to feature records); the build fields of every new layer; the placeholders; docs/developer/pack-format.md (coverage's regional form, partial, aliases, version history); the glossary words of section 10 that it uses; data sources.md (Geofabrik's outline).
* Files: mapdata/config/packs/great-britain.yaml, hampshire-isle-of-wight.yaml, test-region.yaml; mapdata/config/layers/regional.yaml; mapdata/config/sources.yaml; mapdata/stages/coverage.py; mapdata/stages/osm_source.py; mapdata/stages/write.py; mapdata/pipeline/build.py; mapdata/__main__.py; tests/conftest.py; tests/mapdata/test_coverage.py; tests/mapdata/test_osm_source.py; docs/developer/pack-format.md; docs/data-manager/configuration.md (the coverage section and the new pack files); docs/design/data sources.md; docs/design/glossary.md.
* Tests first: the .poly reader (a hole, two sections); the covered pack tiles of a small made-up outline and land; four covered pack tiles written as one; a feature cut by the coverage is partial and one inside is not; every point of a covered pack tile in the test region is in a land area or a sea (LOC-6); the manifest's coverage of test-region; the query matcher on the raw samples (each operator, and a refused one); the two real pack files have the same stages apart from the allowed lines; the world's write fingerprint changes (expected) but its osm-areas, squares and join fingerprints do not.
* Runs: `mapdata fetch` for the three outline sources (small downloads; tell the PO).

### P4-T1b Every administrative level (Opus)

* Does: section 3.5.
* Files: mapdata/stages/local_areas.py; mapdata/config/local_levels.yaml; mapdata/config/tiers.yaml; templates.yaml details.tiers; its block in the three pack files; its section of configuration.md; tests/mapdata/test_local_areas.py; glossary "unparished area".
* Tests first, on the test region: every point of the samples' land has exactly one parish-layer area; a district's parishes join to the district and a county's districts to the county, with no gap or overlap; a sliver goes to the neighbour with the longest shared edge; Winchester's centre is "Unparished area" in the City of Winchester; the tiers of a district and a parish are said in Details.

### P4-T1c Every island and every lake (Opus)

* Does: section 3.6.
* Files: mapdata/stages/small_islands.py; mapdata/stages/osm_water.py; their blocks (and the osm-layer lakes block) in the three pack files; templates.yaml's unnamed water words; its sections of configuration.md; tests/mapdata/test_small_islands.py; tests/mapdata/test_osm_water.py.
* Tests first: the islets of the Lymington cooked sample become unnamed islands with ids that are the same when built again; an islet with an OSM point takes its name; an unnamed pond in the Brockenhurst sample is in lakes as "Pond"; a lake already read keeps its world id and is not read twice.

### P4-T1d Roads and paths (Opus)

* Does: section 3.7, including ways.json.
* Files: mapdata/stages/osm_streets.py; its block and the osm-lines block in the three pack files; templates.yaml's street and path type words; its section of configuration.md; tests/mapdata/test_streets.py.
* Tests first: Winchester's High Street is one feature, though OSM has it in several ways; two High Streets that do not meet are two; a roundabout's gap joins; unnamed footpaths meeting in one parish are one feature, and crossing a parish boundary are two; a driveway and a sidewalk are left out; ways.json holds every way id of a feature; a road numbered A33 has the number in its name.

### P4-T1e Land use, parks, public spaces, school grounds and national parks (Sonnet)

* Does: section 3.8.
* Files: mapdata/stages/osm_land.py; mapdata/config/land_classes.yaml; its block in the three pack files; its section of configuration.md; tests/mapdata/test_land.py.
* Tests first: Abbey Gardens is in parks; Winchester College's ground (or the school in the Winchester sample) is in school-grounds; two touching unnamed woods in one parish are one "Woodland"; a private garden is left out; the New Forest National Park is in national_parks, cut to the land; the log lists each tag where the layer differs from Shortbread's.
* If the joining of touching areas turns out to need more than this note says, the item stops and is handed to Opus (the plan's rule).

### P4-T1f Points of interest (Opus)

* Does: section 3.10, with villages, say_type in the core, and the CSV.
* Files: mapdata/config/poi_categories.yaml; mapdata/stages/osm_pois.py; tools/make_poi_categories_csv.py; docs/plan/p4-t1f-poi-categories.csv; templates.yaml's poi_categories section; mapdata/pipeline/settings.py (say_type in SHOWN_FIELDS only); mapcore/layers/catalogue.py; the core's item naming (the one function that names a Nearby, Within or Contains item, which P4-T1f finds); tests/mapcore/test_session.py (approved wording); its block and the villages block in the three pack files; its section of configuration.md; tests/mapdata/test_pois.py; tests/mapcore/test_poi_words.py; glossary "point of interest category".
* Tests first: a bus stop on the Broadway is in stops, said "Broadway (Stop E), bus stop" in Nearby; an unnamed bench is "Bench"; a shop mapped as an area becomes a place inside it; a node with two matching categories takes the first; the CSV is made again identical from the YAML; villages in the samples are in villages with their within areas.

### P4-T1g Rivers and streams at full detail (Opus)

* Does: section 3.9.
* Files: mapdata/stages/osm_waterways.py; its block and the osm-rivers block in the three pack files; its section of configuration.md; tests/mapdata/test_waterways.py.
* Tests first: the River Itchen's side streams in Winchester are streams, each running the way the water flows; a stream in several ways is one feature with its sections in order; a river the osm-rivers stage made is not read twice.

### P4-T1h Matching to the world pack (Opus)

* Does: section 3.11; the report section; architecture 6.7's wording.
* Files: mapdata/stages/match.py; its block in the three pack files; mapdata/config/sources.yaml (only if P4-T1a's world-pack source needs a change); mapdata/pipeline/report.py (the matches section); its section of configuration.md; tests/mapdata/test_match.py; docs/design/architecture.md 6.7; glossary "alias".
* Tests first, test region against the test pack: Hampshire has the test pack's id; a feature with a different id and the same Wikidata id takes the world's id and keeps its own as an alias; a parish's parent is the world's Hampshire; a feature with the same name far away is not matched; the report lists each match made by name.

### P4-T1i Layers, zoom ranges, sounds and map views (Sonnet)

* Does: section 3.13 and section 4's shown fields.
* Files: mapdata/config/layers/regional.yaml (shown fields); mapdata/config/layers/samples.yaml (national_parks made the same); mapcore/views.yaml; mapcore/render/themes.yaml; mapcore/describe/earcons.yaml; templates.yaml details.layers; the write blocks (drawing levels) of the three pack files; tests/mapcore/test_layers_regional.py; the theme contrast tests if they need a new case.
* Tests: each new layer has a zoom range from the zoom list, a word in details.layers, and a place in the drawing order and the said order; every new colour passes the contrast test in every theme; every sound named is an event in earcons.yaml.

### P4-T1k Relationships, facts and memory at street scale (Opus, new)

* Does: section 3.12. After P4-T1b to P4-T1h, before P4-T1j, so the rehearsal runs with it.
* Files: mapdata/stages/relationships.py; mapdata/stages/wikidata.py (only if it has no layers setting); mapdata/pipeline/features.py and any stage that must load fewer layers (named in its report); the relationships and wikidata blocks of the three pack files; their sections of configuration.md; tests/mapdata/test_relationships.py (new tests only), tests/mapdata/test_light_layers.py.
* Tests first: a street in light_layers has its parish, district and county in "in" and its parishes in order in its crossings, and no neighbours; with light_layers empty, the test pack's relationships are unchanged (compared whole with the file made before the change).

### P4-T1j The rehearsal (Opus)

* Does: builds hampshire-isle-of-wight from the planet file with the run switch and a stall watch, 3 workers; times each stage; measures peak memory per stage; the size by layer from the quality report; checks: the street places file tests/acceptance/street_places_hampshire.yaml (made here: about 20 places in Winchester, Southampton, the New Forest, Lymington and the Isle of Wight, each with what Space should say); estimates Great Britain's time, size by layer and memory, scaling each layer by the United Kingdom's counts from uk.gol (section 7); writes docs/plan/p4-t1j-rehearsal-report.md for the PO.
* Files: tests/acceptance/street_places_hampshire.yaml; docs/plan/p4-t1j-rehearsal-report.md; fixes to any P4-T1 module, each with a test that fails before and passes after (the ledger's rule for fixes found in runs).
* Before it starts: the world pack must exist (match reads it), nothing else heavy may run, and free memory is checked (the PO's rule).

### P4-T3a to P4-T3e Combining packs (after P4-T1h and the rehearsal pack)

* P4-T3a Several packs open together (Opus). The store opens every pack in the packs folder (the desktop already lists them, desktop/storage.py); orders regional before world; builds each regional pack's covered pack tile set at start-up; for a point, for each layer, asks the regional pack covering it if the layer is in its coverage's layers, else the world pack; the world pack's features of a covered layer are left out inside covered pack tiles, for where am I, Nearby and drawing; at views wider than draw_below_km the world pack draws alone. Files: mapcore/store/store.py, a new mapcore/store/packs_combined.py, mapcore/render/scene.py, mapcore/layers/visible.py (only the pack choice), app_versions in the two regional pack files, tests/mapcore/test_combining.py.
* P4-T3b Features and relationships merged (Opus). Records merged by id and alias: a record not partial in the regional pack wins; a partial one yields to the world's record for its area, bounding box, point and relationships, while its children (Contains) are the union of both packs', the regional ones' first. Within for a regional-only feature: its regional parents, then the world's parents of the top one. Files: mapcore/store/packs_combined.py, mapcore/store/contents.py, tests/mapcore/test_combining_records.py.
* P4-T3c Search across packs (Opus). One search over both packs' search records, a feature in two packs (by id or alias) listed once. Files: mapcore/search.py (only the merge), mapcore/store/store.py (Store.search), tests/mapcore/test_combined_search.py.
* P4-T3d The web version with two packs (Opus). The worker opens both packs; memory measured in Chromium and Firefox. Files: web/bridge.py, web/js/ (the worker's pack opening only), tests/web/test_two_packs_page.py.
* P4-T3e At the edge of the pack (Sonnet). Acceptance scripts on the real packs: Dover out into the Channel and on to Calais; Carlisle into Scotland (inside the Great Britain pack: checks no seam between its countries); Hampshire into Dorset on the rehearsal pack's edge (its coverage ends a few kilometres into Dorset); hearing only places, no silence, no message about detail; the same feature from either side of the edge is the same. Files: tests/acceptance/pack_edge_places.yaml, a script beside the existing acceptance scripts.
* P4-T3 needs nothing from P4-T1 beyond the manifest and record fields of section 2.4, so P4-T3a and P4-T3b can be written against the test region as soon as P4-T1a and P4-T1h are done.

### What can run in parallel

* The orchestrator runs one work item at a time in one working tree (the PO's instruction). Within that rule:
* P4-T0e must come first (the samples), then P4-T1a (the frame every other item builds on).
* P4-T1b, P4-T1c, P4-T1d, P4-T1e and P4-T1g touch only their own modules, tests, configuration sections and blocks, plus distinct parts of templates.yaml. They can be done in any order, and in parallel only in separate worktrees (isolation: worktree), merging the three pack files and templates.yaml by hand; the merges are line by line and do not conflict. Order recommended: b, c, d, g, e (osm-streets and osm-land use the parishes layer for joining unnamed ways and areas, so b first).
* P4-T1f after P4-T1b (villages within districts and parishes) and before P4-T1i (it adds say_type, which P4-T1i sets).
* P4-T1h after every reading stage (it changes ids the others refer to).
* P4-T1i after P4-T1f; P4-T1k after P4-T1h; P4-T1j last.
* P4-T3a and P4-T3b may start once P4-T1h is done, in parallel with P4-T1i and P4-T1k (no shared files), but the orchestrator's one-at-a-time rule makes that a choice, not a need.

## 7. Size and time

### 7.1 What was measured

From the world pack's quality report (21 November, 552.46 MB, 612,356 features):

* Area layers cost about 4 bytes a point, with their drawing levels: counties 120.5 MB for 29.7 million points.
* Line layers about 5 to 5.5 bytes a point: motorways and trunk roads 21.2 MB for 3.88 million points; rivers 23.6 MB for 5.0 million.
* Places about 90 to 170 bytes each, with their records, search and relationships: cities and towns 19.1 MB for 114,581; peaks 6.6 MB for 58,161.
* The pack's own records (search, relationships, directory) 104.5 MB, 19 percent.

From the PO's uk.gol (the United Kingdom, October 2025), counted with GeoDesk on 21 November (section 3 gives the counts). In the rehearsal's box (1.96 to 0.73 west, 50.57 to 51.39 north, about 7,800 km2, a little more than the rehearsal's coverage): streets 1.26 million points, paths 0.96 million, waterways 0.29 million, water areas 0.29 million, land use and natural areas 3.06 million, parks 0.09 million, school grounds 0.02 million, level 10 areas 0.35 million (whole outlines). The United Kingdom has about 21 to 30 times the box's numbers, layer by layer.

From the stage folders: the world's squares took 57 to 127 minutes, join 2 to 29, relationships 2 hours 28 minutes to 3 hours 14 minutes, write 70 to 90 minutes; reading one layer from the planet file 1 to 11 minutes; the Western Europe trial's squares about 13 minutes and relationships 10 minutes.

### 7.2 Hampshire and the Isle of Wight

* Features: about 250,000 to 300,000, after joining (about 50,000 streets, 25,000 path groups, 40,000 land use areas, 60,000 places, 9,000 water areas, 8,000 waterways, 500 parishes).
* Points: about 4.5 million after joining and simplifying.
* Size: about 35 to 60 MB.
* Time: osm-areas about 5 minutes, squares 5 to 10, join 1, coverage 1, local areas 2, the reading stages 2 to 5 each, match 2 to 5, wikidata a few minutes, relationships 10 to 20, write 10. About 45 to 60 minutes in all, as the plan expects.

### 7.3 Great Britain

Scaled layer by layer from the United Kingdom's counts, less about 3 percent for Northern Ireland:

* Streets and main roads: about 25 million points, 0.9 million features: about 200 MB.
* Paths: about 17 million points, 0.3 million features: about 110 MB.
* Land use, parks and school grounds after joining: about 23 million points, 0.9 million features: about 170 MB.
* Water areas and waterways: about 14 million points, 0.4 million features: about 90 MB.
* Points of interest and villages: about 1.3 million places: about 90 MB.
* Districts, parishes, and the countries, regions, counties, islands, oceans and seas at 10 metres (each holds Great Britain's coast once): about 20 million points: about 85 MB.
* Search, relationships and the pack's own records: about 60 to 100 MB.
* In all: about 800 MB, likely between 550 MB and 1.1 GB, against PCK-1's 1 GB. The rehearsal gives the true bytes per feature and per point for each layer, and P4-T1j's estimate replaces this one. If the estimate is over 1 GB, P4-T2b proposes a split to the PO (England, Scotland and Wales), or the first things to drop: unnamed service roads, street furniture, farmland.

Time: osm-areas 10 minutes; squares at 10 metres over a box holding Great Britain and Ireland 20 to 40 minutes; join 5 to 10; coverage 5; local areas 10 to 20; reading stages 2 to 3 hours together; match 10; wikidata 10 to 60; relationships 2 to 5 hours with light layers; coast stretches 15 minutes; write 2 to 4 hours. About 6 to 12 hours: an overnight run with --away and 6 workers, from a snapshot worktree as the world build was.

Space: each stage keeps its own copy of the features, perhaps 3 to 6 GB each for Great Britain, so 60 to 120 GB in the working folder; the data folder has 368 GB free. space_needed_mb in great-britain.yaml: 150,000 until the rehearsal gives a better figure.

### 7.4 Memory

* Reading: GeoDesk maps the planet file's pages as they are read and gives them back only when the process ends; reading Great Britain touches only its own part of the file (the whole of the United Kingdom is a 3.7 GB library), not the 24 GB of a planet-wide read. Each reading stage reads in its own short-lived process, one reading box at a time, writing each box's results to disk before the next (section 3.4).
* Joining: streets are joined box by box, then features whose ends meet across a box edge are joined in a second pass that holds only their keys and end points.
* The later stages: features.json for Great Britain may be 1.5 to 3 GB, several times that as Python objects. P4-T1k measures it on the rehearsal and changes the stages that must so they load only the layers they need.
* Workers: 3 while the PO uses the laptop, 6 with --away; a new job starts only while 6 GB is free, and the build stops cleanly below 3 GB (architecture 8.6).
* The aim: no stage above 12 GB, so the build fits in the 32 GB laptop with the PO's files and NVDA open. One heavy job at a time; free memory checked before the start (the PO's rule).

## 8. Choices for the PO

The PO is away and asked for best judgement. Each choice, with the other way:

1. Coverage by whole pack tiles of about 6 by 5 kilometres that hold land inside Geofabrik's outline, with full detail in them, even a little past the outline. The other way: cut exactly at the outline, which needs the core to join two packs along a line inside a pack tile. For Great Britain the difference is nil (no land border with land outside the outline); for the Hampshire rehearsal, its detail runs up to about 6 kilometres into Dorset, Wiltshire, Berkshire, Surrey and West Sussex.
2. The regional pack holds its own countries, regions, counties, islands, oceans and seas at 10 metres. The other way: only the new layers, with the world pack's 100-metre areas under them, so streets could run into the world's sea.
3. Continents, mountain ranges, physical regions, territorial waters, peaks, cities and towns, bays and straits as places, enclaves and the graticule stay in the world pack only. The other way: build them again in each regional pack.
4. The world pack itself is the identifier register; no separate register file, and no world rebuild for it. The other way: a register file written by the world build and published with it.
5. Detail: areas at 10 metres, streets, paths and waterways at 2 metres, land use, parks and lakes at 5 metres. The other way: OSM's own points, unsimplified, which costs perhaps 15 to 25 percent more.
6. Districts are level 8; parishes, Welsh communities and Scottish community council areas level 10. Land in no parish is said as "Unparished area" in England and "Area with no community council" in Scotland. Electoral wards are left out (they are political, and few are mapped). The other way: fill the gaps with wards where mapped, or say nothing there.
7. Left out of streets: driveways, parking aisles and drive-throughs (937,708 in the United Kingdom); left out of paths: sidewalks and crossing ways (276,981), as the street and the crossing point already say them. The other way: include them all.
8. Unnamed paths, streets, streams and land use of one kind that meet are one feature within a parish ("Footpath", "Farmland"). The other way: one feature per OSM way, several times more features and perhaps 200 MB more.
9. Private gardens are left out of parks; farmland, meadows and woods are kept as land use. The other way: leave farmland out too, to save size.
10. OpenStreetMap way ids are kept in the build's stage folder for Phase 5, not in the pack. The other way: in the pack, about 15 MB more, unused until Phase 5.
11. National parks keep the id national_parks (the test pack's), and take in England and Wales's National Landscapes and Scotland's National Scenic Areas. The other way: a separate layer for them.
12. Points of interest are in four layers, each with its own switch and zoom range: stops and crossings, shops cafes and pubs, services, and post boxes benches and bins (only at 250 metres and closer). The other way: one layer.
13. A point of interest is said with its kind after its name: "Broadway (Stop E), bus stop". The other way: only its name, with the kind in Details.
14. Villages, suburbs and hamlets come with the regional pack, as a layer of places. The other way: wait for a later phase.
15. Districts, parishes and the lakes share rank 7, and parks, land use and school grounds rank 8, ordered by size, so no world layer's rank changes (which would rebuild the world's areas).
16. Facts from Wikidata only for areas, lakes, rivers, parks and national parks, not for each street or shop with a Wikidata tag. The other way: all, at perhaps an hour more of fetching.
17. Built from the same planet file as the world pack (planet-latest.gol, October 2025), not a fresh download, as DP107 needs the two to match. A fresh planet file means rebuilding both.
18. The format number stays 4, and app_versions keeps older versions of TobyMap from opening a regional pack. The other way: format 5, which would also refuse every world pack in older versions.
19. A new work item, P4-T1k, for relationships, facts and memory at street scale, which the plan did not list.

## 9. Risks

* Size over 1 GB. The estimate's range reaches 1.1 GB; land use and the per-feature cost are the least certain. The rehearsal measures, and P4-T2b proposes a split or what to drop before anything is cut.
* Time. Relationships and writing at 4 million features have never been tried; light_layers is the defence. If the rehearsal scales to more than 12 hours, P4-T1k looks again before the Great Britain build.
* Memory. Stages that load every feature at once may not fit with 4 million features; P4-T1k measures on the rehearsal. A run killed for memory is not restarted as it is (the PO's rule): the stage is changed first.
* Matching. A wrong match by name and overlap joins two features; a missed one makes a feature appear twice. Nearly every feature is matched by id, and every other match is listed in the quality report.
* The world pack must be built from the same planet file as the regional pack. A world rebuild changes the match stage's source fingerprint, so the regional build reruns from match onwards (a few hours for Great Britain).
* At the coast, world-only layers (continents, mountain ranges, territorial waters) were cut to the world's 100-metre land. A point on the regional land up to about 100 metres beyond the world's coast may not be in Europe, and one in the regional sea may be in a range. Small, and only in Within's longer lists.
* Changing write.py and relationships.py changes the world's fingerprints for those stages: the next world build reruns them (planned at P4-T15 anyway, about 5 hours). No other world stage's code changes.
* Geofabrik's terms for the .poly files are not yet read. If they forbid this use, the outline is drawn from OSM's own boundaries of England, Scotland and Wales instead (same planet file), with the islands they hold.
* The raw samples are small, so some behaviour (joining across a reading box's edge, the coverage of a real outline) is tested only by unit tests with made-up shapes and by the rehearsal.
* Scotland's community council areas and England's parishes are incomplete in OSM in places; the gap areas say so rather than leaving silence, and the quality report lists them by district.

## 10. New words for the glossary

Each added by the work item named, before its first use in a report or a document for the PO:

* Coverage (of a regional pack): the covered pack tiles where it answers instead of the world pack (P4-T1a).
* Covered pack tile: a pack tile, at the coverage's tile level, where a regional pack answers for its layers (P4-T1a).
* Region outline: the shape, from Geofabrik's .poly file, that decides a regional pack's coverage (P4-T1a).
* Partial (feature): a feature a pack holds only part of, as its coverage cut it, such as the United Kingdom in the Great Britain pack (P4-T1a).
* Alias: another identifier of the same feature, kept when matching gave it the world pack's identifier (P4-T1h).
* Unparished area: land in a district that is in no parish, said so in the parishes layer (P4-T1b).
* Point of interest category: the friendly kind of a point of interest, such as bus stop, from the category table (P4-T1f).
