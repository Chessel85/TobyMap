# P4-T13a Groups of islands: the source and the method

Research for P4-T13, by Claude Code, 21 November 2026. It follows the research approach in the Phase 4 ledger. The PO asked the orchestrator to choose the source without the PO's input, so this report ends with a recommendation and the method for P4-T13b.

## In short

* Choice: OpenStreetMap's groups of islands (place=archipelago) say which islands belong to each group. Wikidata (CC0) joins groups that sit inside other groups, such as Santorini inside the Cyclades. A small record of our own fills the few gaps: the Balearic Islands, the British Isles, and some names.
* OpenStreetMap has 11 of the 12 test groups as an outline or a list of islands. Only the Balearic Islands as a whole is missing, and its islands are the islands inside the region Illes Balears, already in the pack.
* Each group's outline is made from its own islands in our Islands layer: the islands are grown out over the sea until the group joins up, then shrunk back to 3 kilometres off the outer coasts, and any other land is cut away. At every test position, on the islands and at sea between them, this said the right thing, in all 15 groups and sub-groups tested.
* Natural Earth's groups of islands are too rough to say "you are in": its outlines miss Orkney's own Mainland, Streymoy in the Faroes, Sylt, and every channel between islands. They are dropped as outlines. Natural Earth is kept only as a list of member islands, for its groups that OpenStreetMap does not have.
* The British Isles fault (Cornwall, Essex and the Isle of Wight "overlapping" it at 99 percent) is already gone in the world build of 21 November, as the DP220 change cuts the regions to the land as the pack draws it. What is still wrong is that Natural Earth's outline leaves out Shetland and the Channel Islands. The new layer makes the British Isles from its member islands, which puts both in.

## Words used in this report

These two terms are new. P4-T13b should add them to the glossary.

* Group of islands: an area in the new Groups of islands layer, such as the Channel Islands. Its outline covers its islands and the sea between them.
* Member island: an island of our Islands layer that belongs to a group of islands.

## How the research was done

* The test set: the Channel Islands, the Isles of Scilly, the Inner Hebrides, the Outer Hebrides, Orkney, Shetland, the Balearic Islands, the Azores, the Canary Islands, the Faroe Islands, the Frisian Islands (the whole group, and the West, East and North Frisian Islands), and the Cyclades. The British Isles was tested on its own.
* Our islands: the Islands layer of the world build of 21 November (its physical stage folder), 199,278 islands.
* OpenStreetMap: one reading of the planet file of 26 October 2026, for every feature tagged place=archipelago or place=islands.
* Wikidata: each group's item, its "has part" (P527) list, and the items that say they are "part of" it (P361) or "located on" it (P706). Read from Wikidata's own interface, as its query service was limiting every client to one query a minute that morning.
* Natural Earth: its physical regions of class "Island group", the file already in the data folder.
* For each group: which of our islands each source names as members, matched by OpenStreetMap id, by Wikidata id, or by lying inside the source's outline.
* Then several ways of making the outline from the member islands, each tested at chosen positions: on islands, at sea between them, on nearby mainland, and in open sea. A few positions have no clear right answer, such as the Sound of Mull; they are listed as open questions, not counted.

## The sources

### OpenStreetMap

* The planet file has 2,883 features tagged place=archipelago, and only 3 tagged place=islands.
* 2,424 are areas: groups drawn as multipolygons, or as boundaries that are also council areas, such as Shetland and the Outer Hebrides. 194 are relations with no area, such as the Cyclades, a list of its islands. 265 are only a place, with no outline and no list, such as the British Isles.
* 1,111 have a Wikidata link.
* An area's outline is the coast of its islands, not the sea between them. So it says which islands belong, but its outline cannot be used to say "you are in" at sea.
* Matching by OpenStreetMap id alone finds few islands, as most group outlines are drawn from coastline ways, not from the islands' own areas: 2 of the 121 islands of the Isles of Scilly. Matching by lying inside the group's outline finds them all.
* Licence: ODbL 1.0, as for the rest of the pack.

### Wikidata

* Every test group has an item, including the British Isles (Q38272).
* Its membership is uneven. It lists the main islands well, but few of the small ones, and it mixes in other things: villages, hills, councils, a shipping forecast area, and Rockall as part of the Outer Hebrides.
* It has one island, Lewis and Harris, where OpenStreetMap and our layer have two, Lewis and Harris, so the Outer Hebrides' two largest islands do not match.
* It lists some islands of the Scottish mainland coast as Inner Hebrides, such as Eilean Donan and the Isle of Ewe.
* What it does well is say which group is part of which: Santorini, the Christiana Islands and the Pityusic Islands are parts of the Cyclades or the Balearic Islands, where OpenStreetMap does not join them.
* Licence: CC0 1.0. Already a source of the pack.

### Natural Earth

* 160 groups of islands worldwide, already in the pack as "group of islands" in the Deserts, plateaus, plains and other regions layer.
* It has 9 of the 12 test groups. It has no Channel Islands, Isles of Scilly or Inner Hebrides, and one Frisian Islands only.
* Its outlines are very rough: 9 to 40 points for each test group. In the pack they are cut to the land, so at sea you are never in them, and parts of the land are left out too.
* Of its 160 groups, 87 are also in OpenStreetMap (77 by Wikidata link, 10 by name). Many of the other 73 are not groups at all but single islands or countries, such as Maui, Tahiti, Japan and New Zealand. A few are real groups that OpenStreetMap lacks, such as the Maldive Islands, the Kerguelen Islands and the Queen Elizabeth Islands.
* Licence: public domain.

### GeoNames

* Not needed: OpenStreetMap, Wikidata and our own record leave no gap in the test set. GeoNames is CC BY 4.0, which would need a credit line, and it has only a point for each group, so it would not say which islands belong.

### A record of our own

* Needed for a handful of groups. It would sit in mapdata/config, like the counties record. See the method below for what it holds.

## The groups, one by one

### Channel Islands

* OpenStreetMap: yes, "Channel Islands", an outline (osm:r6031891, Wikidata Q42314), holding the sub-groups Pierres de Lecq and the Écréhous. 79 of our islands lie inside it: Jersey, Guernsey, Alderney, Sark, Herm, Brecqhou, Jethou, Lihou, Burhou, Les Casquets, the Minquiers and the rest. Chausey, which is French, is not in it.
* Wikidata: yes; 10 of our islands, the named ones only. Its parts include the two bailiwicks.
* Natural Earth: no.
* Outline from the islands: right at all 9 positions, including the sea between Guernsey and Jersey, between Guernsey and Sark, and between Alderney and Guernsey. The sea 5 kilometres off the Cotentin coast and Chausey are not in it.

### Isles of Scilly

* OpenStreetMap: yes, an outline that is also its council area (osm:r158039, Q180209). 129 of our islands, with its sub-groups Norrad Rocks and the Eastern Isles.
* Wikidata: yes; 14 islands.
* Natural Earth: no (only inside the British Isles).
* Outline from the islands: right at all 4 positions, including St Mary's Road; Land's End is not in it.

### Outer Hebrides

* OpenStreetMap: yes, as the council area Na h-Eileanan Siar, English name "Western Isles" (osm:r1959008, Q80967). 891 islands, including St Kilda, 60 kilometres west.
* Wikidata: yes; 83 islands, but not Lewis or Harris (see above), and it adds Rockall.
* Natural Earth: yes, "Outer Hebrides", without St Kilda. Its outline, cut to the land, leaves out the Sound of Harris and the Sound of Barra.
* Outline from the islands: right at all 5 positions, including both sounds; the middle of the Minch and Skye are not in it. St Kilda is in it, as a separate part.
* The name: OpenStreetMap's English name is "Western Isles"; Wikidata's is "Outer Hebrides". See names in the method.

### Inner Hebrides

* OpenStreetMap: yes (osm:r16304867, Q81052). 536 islands. A larger group, the Hebrides (osm:r16304905, Q123377), holds both Inner and Outer.
* Wikidata: yes; 92 islands, some of them on the mainland coast.
* Natural Earth: no.
* Outline from the islands: right at all 7 positions, including the Sound of Islay and the sea between Coll and Tiree. Kintyre, Loch Linnhe and Harris are not in it. The Sound of Mull, between Mull and the mainland, is not in it either; that is an open question.

### Orkney

* OpenStreetMap: yes, "Orkney Islands" (osm:r3067412), with no Wikidata link. 62 islands. The Pentland Skerries are a group of their own.
* Wikidata: yes (Q100166); 49 islands.
* Natural Earth: yes, "Orkney Islands". Its outline is so rough that a position on Orkney's own Mainland is outside it, as are Scapa Flow and the sea between Mainland and Stronsay.
* Outline from the islands: right at all 4 positions, including Scapa Flow; Caithness is not in it. The Pentland Firth is not in it either (open question).

### Shetland

* OpenStreetMap: yes, as the council area (osm:r2235077, Q47134), English name "Shetland". 260 islands, with Fair Isle and Foula, and the Out Skerries as a sub-group.
* Wikidata: yes; 61 islands.
* Natural Earth: yes, "Shetland Islands"; Yell Sound is outside its outline.
* Outline from the islands: right at all 5 positions, including Yell Sound, Bluemull Sound and Fair Isle.

### Balearic Islands

* OpenStreetMap: no group for the whole. It has only the Pityusic Islands (Ibiza and Formentera, osm:r17646331) and some small groups. The region Illes Balears (osm:r348981, in our Regions layer) holds 138 islands; with the Pityusic Islands, 142.
* Wikidata: yes (Q5765), but through two sub-groups, the Gymnesian and Pityusic Islands; 18 islands. Wikidata links the item to the OpenStreetMap region.
* Natural Earth: yes; its outline leaves out the sea between Mallorca and Menorca, and between Ibiza and Formentera.
* Outline from the islands of the region: right at all 4 positions. The 80 kilometres of sea between Ibiza and Mallorca is not in it, so the group is two parts (open question).

### Azores

* OpenStreetMap: yes, "Arquipélago dos Açores" (osm:r21692014), with no English name and no Wikidata link. 47 islands.
* Wikidata: two items, the autonomous region (Q25263) and the archipelago (Q4058447); 15 islands.
* Natural Earth: yes; the channel between Faial and Pico, and the sea between Pico and São Jorge, are outside it.
* Outline from the islands: right at all 3 positions. The 150 kilometres of open sea between São Miguel and Terceira is not in it, so the Azores are three parts, east, centre and west (open question).

### Canary Islands

* OpenStreetMap: yes, "Islas Canarias", English name "Canary Islands" (osm:r5392189, Q5813). 50 islands.
* Wikidata: yes (Q23988230, the archipelago); 14 islands.
* Natural Earth: yes; the sea between Tenerife and Gran Canaria, and La Bocayna between Lanzarote and Fuerteventura, are outside it.
* Outline from the islands: right at all 5 positions; the sea off Morocco and the African coast are not in it.

### Faroe Islands

* OpenStreetMap: yes, "Føroyar", English name "Faroe Islands" (osm:r3067431, Q4628). 48 islands.
* Wikidata: yes; 19 islands.
* Natural Earth: yes; a position on Streymoy is outside it.
* Outline from the islands: right at all 3 positions.

### Frisian Islands

* OpenStreetMap: yes, the whole group (osm:r16029665, Q76936), holding the West Frisian Islands (osm:r8339800, Q21192), the East Frisian Islands (osm:r963669, Q27769), the North Frisian Islands (osm:r1132508, Q27937), the Danish Wadden Sea Islands and Heligoland as sub-groups. 61 islands in the whole; 15, 12 and 19 in the three named sub-groups.
* Wikidata: yes for all four; 28 islands in the whole, missing Texel and Ameland.
* Natural Earth: one "Frisian Islands", with no Wikidata link; Sylt is outside it.
* Outline from the islands: right at every position for the whole group and each sub-group. The Marsdiep between Den Helder and Texel is in the group; the Wadden Sea behind Vlieland and Terschelling is not, and near the Halligen it is (open questions: the Wadden Sea is a sea of its own in the pack).

### Cyclades

* OpenStreetMap: yes, but as a list of islands with no outline (osm:r3304283, Q171132). 42 of our islands by OpenStreetMap id. Santorini is missing: OpenStreetMap has it as a group of its own (osm:r18766085), not in the list.
* Wikidata: yes; 45 islands. It says the Santorini group and the Christiana Islands are part of the Cyclades. With them, 50 islands.
* Natural Earth: yes; the sea between Naxos and Paros, and south of Naxos, are outside it.
* Outline from the islands: right at all 5 positions once Santorini's group is joined through Wikidata. Without it, Santorini was outside the Cyclades by every method.

### British Isles

* OpenStreetMap: only a place, with a Wikidata link (n5284251522, Q38272); no outline and no list.
* Wikidata: yes. Its parts are Great Britain, Ireland, the Isle of Man, Anglesey, and the groups Isles of Scilly, Channel Islands, Hebrides, Orkney and Shetland, with a few small islands. It does not list the Isle of Wight, Sheppey, Canvey or Foulness.
* Natural Earth: yes, the only test group it draws in detail (1,480 points). 5,178 of our islands lie inside it, but not Shetland, Jersey, Guernsey or Alderney.
* In the world build of 21 November, Cornwall, Essex and the Isle of Wight are now wholly in the British Isles (the relationships stage lists it under "in" for each). The 99 percent fault was from the cut used before DP220. The remaining fault is that you are not in the British Isles on Shetland or Jersey, or anywhere at sea.
* Outline from the islands, with members from Natural Earth's outline and Wikidata's parts together (tested with a fixed reach of 20 kilometres): Cornwall, Essex, Kent, the Isle of Wight and Highland are all 100 percent inside; Shetland and the sea round the Channel Islands are in it; the middle of the English Channel, the Belgian coast and the Irish Sea between Belfast Lough and the Isle of Man are not. With the reach set for each group, as chosen below, the reach will be larger, as the Channel Islands lie over 100 kilometres from Great Britain, so more of the Irish Sea and the western Channel may be in it: check this on the world build.
* Wikidata's parts alone are not enough: when land that is not a member is cut away, the Isle of Wight is cut out (0.02 percent left inside), and Kent and Essex lose their islands (97 percent inside). Keeping land parts that lie wholly inside the outline saves Kent's, but not the Isle of Wight, which reaches further from Great Britain than the 3 kilometre edge.
* The name "British Isles" is disputed in Ireland. That is a wording question for the PO, not for this report; the layer can rename it through our own record if the PO wishes.

### Sark

* Sark (osm:w2956937) is in our Islands layer, and lies inside the Channel Islands outline, so it is a member island of the Channel Islands. Wikidata also lists Sark as part of the Channel Islands.
* So "Within" on Sark would list Sark (the island and the region of Guernsey, said once since P4-T14k), then the Channel Islands, then Guernsey, then Europe. Search finds Sark once, as now (DP71); its result can say where it is from the group: "Sark, Channel Islands".

## The outline: the methods tested

All the methods start from the member islands in our Islands layer, whose coasts are the pack's own. Each cuts away land that is not a member island, such as France near the Channel Islands, so a group never covers a mainland. The results, over the 15 groups and sub-groups:

* Each island grown by 2 or 5 kilometres: wrong at sea wherever islands are further apart, such as Guernsey to Jersey, Tenerife to Gran Canaria, and Mallorca to Menorca.
* A concave hull (a tight outline round the islands): wrong at sea between Guernsey and Jersey, and between Alderney and Guernsey.
* The convex hull (the tightest outline with no inward bends), cut to the sea: right at the counted positions, but it takes in much open sea: 50,582 km2 of sea for the Azores, including the 150 kilometres between São Miguel and Terceira, and 57,899 km2 for the Canary Islands.
* The convex hull kept within 25 kilometres of an island: wrong between Tenerife and Gran Canaria.
* Closing with a fixed reach (grow by a fixed distance, then shrink back): 20 kilometres is wrong between Guernsey and Jersey; 40 kilometres is right but too wide for tight groups.
* Closing with a reach set for each group (the chosen method): right at every counted position in all 15. Its sea area is far smaller than the convex hull's: 1,788 km2 for the Channel Islands against 3,031; 6,553 km2 for the Azores against 50,582; 12,592 km2 for the Canary Islands against 57,899.

## The method for P4-T13b

### Which islands belong to a group

In this order, each adding to the one before:

1. OpenStreetMap: every feature tagged place=archipelago that is an area, or a relation of type group, multipolygon or boundary. Its member islands are the islands of our Islands layer that lie inside its outline (tested with the full outline from the planet, not a simplified one), and, for a relation with no outline such as the Cyclades, the islands it lists, by OpenStreetMap id. Relations of type land_area, site and cluster are left out: in the test set, "Guernsey (land mass)" and "Jersey (land mass)" are land_area relations wrongly tagged as groups.
2. Groups inside groups: a group listed in another group (OpenStreetMap's subarea members, such as the Frisian Islands' three parts), or whose Wikidata item is a part of another group's item (Wikidata P361 or P527, such as Santorini in the Cyclades). The inner group's islands are members of the outer group too. Only links between groups are taken from Wikidata, never single islands, as its island lists are uneven.
3. Our own record, mapdata/config/island_groups.yaml, for what the sources lack: the Balearic Islands (the islands inside the region osm:r348981, Wikidata Q5765), the British Isles (its Wikidata parts and the islands inside Natural Earth's outline), a Wikidata link where OpenStreetMap has none (Orkney Q100166, the Azores Q4058447), names, and any group to leave out.
4. Natural Earth: its groups that match no OpenStreetMap group by Wikidata link or name. The islands inside its outline become members, and its outline is not used. A Natural Earth group that is one island or a country, such as Maui or Japan, is left out: in practice, one whose largest member island holds most of its land, or whose name is already a country's.
5. A group is kept when it has at least two member islands. P4-T13b should set a smallest size for the world, such as a Wikidata link or 1 km2 of land, so that the many small groups of rocks do not crowd the layer; the trial will show how many there are.

### The outline

For each group, worked in kilometres:

1. Join the member islands' shapes into one.
2. Find the reach that joins the group into one part: the smallest distance that, growing every island by it, makes them touch. In the test set it was 3 kilometres for Orkney and the Faroes, 13 for the Channel Islands, 19 for Shetland and 32 for the Outer Hebrides.
3. Grow the islands by twice that reach, at least 10 and at most 60 kilometres, then shrink them back by the reach less 3 kilometres. The gaps between islands fill, and the outer edge lies 3 kilometres off the outer coasts. A group whose islands are more than about 120 kilometres apart, such as the Azores, stays in parts.
4. Cut away land that is not in the group: each land part of the pack (the countries as the join stage drew them, physical.DrawnLand) that crosses the outline's edge, such as France or the Scottish mainland. A land part wholly inside the outline stays in, as an island the sources forgot. This rule was tested on the British Isles only; P4-T13b should confirm it on the trial. It does not save a large island the sources forgot, which is why the British Isles takes its members from Natural Earth's outline as well as Wikidata.
5. Simplify to the pack's tolerance, 100 metres, and keep the cut coast exactly the pack's own, as the physical stage does since DP220.

### Natural Earth's groups and the British Isles

* Natural Earth's groups of islands leave the physical regions: remove "Island group: group of islands" from the physical stage's classes in world.yaml and the trial. This changes the physical stage's fingerprint, so the world rerun starts at the physical stage, which takes about 6 minutes more than starting at the new stage.
* Natural Earth's groups that OpenStreetMap lacks come back in the new layer, as lists of member islands with the new outline (step 4 above).
* The British Isles comes back in the new layer from our own record, with Shetland and the Channel Islands in it, and the sea between its islands.

### Names

* The name is OpenStreetMap's English name, then Wikidata's English label, then OpenStreetMap's own name; our record can override. For the test set: the Azores need a name from the record or from Wikidata, as OpenStreetMap has only "Arquipélago dos Açores"; the Outer Hebrides are "Western Isles" in OpenStreetMap, so the record should name them "Outer Hebrides".
* Many groups share their name with an area already in the pack: the Canary Islands (a country area by DP191 and a region), the Balearic Islands, the Azores and Shetland (regions or council areas), the Faroe Islands (a country), the Isles of Scilly (a county). They are different features, as the group covers the sea between the islands, so both stay. P4-T13b must check how "Within" and Space say two features of one name, one after the other; session._same_as_one_before, used for Sark, may say them once.

## How P4-T13b fits the pipeline

* A new stage, "island-groups", in mapdata/stages/island_groups.py, after the physical stage and the territorial-waters stage, as territorial_waters.py is. It keeps the features of the stage before and adds the new ones after them.
* Its inputs:
  * The Islands layer as built: the osm-areas stage reads the named islands (islands: true, read_islands in osm_areas.py), the squares stage cuts them to the land, and the join stage names the land that no island area covers. Read them with features.load_layers from the stage before, with the regions layer (for the Balearic Islands) and the land layer, countries.
  * The planet file, read in a short-lived process as osm_places.py does, for the groups: one query by tag over the whole planet. It took 69 seconds.
  * The links between groups from Wikidata, fetched once and kept in the data folder beside the facts (such as downloads/wikidata/groups-<refresh>.jsonl), so a rebuild fetches nothing and the pack is the same byte for byte (DMT-1). Only about 1,100 groups have a Wikidata link.
  * Natural Earth's physical regions file, for its groups that OpenStreetMap lacks.
  * Our own record, mapdata/config/island_groups.yaml.
* A new layer in mapdata/config/layers/base.yaml, such as {id: island-groups, name: Groups of islands, kind: land, made_by: island-groups, group: Physical features, geometry: area, fill: none}. Groups overlap each other (the Hebrides hold the Inner and Outer Hebrides), so the layer is not painted, and its drawing levels are made one area at a time, as for the physical regions.
* Wikidata facts: add the layer to the wikidata stage's match list, so groups get their facts and labels.
* The rehearsal: the Western Europe trial (mapdata/config/packs/trial-western-europe.yaml, 11 west to 17 east, 35 to 61 north) holds the Channel Islands, the Isles of Scilly, the Hebrides, Orkney, Shetland, the Balearic Islands and the Frisian Islands. The Faroe Islands (north of 61), the Azores, the Canary Islands and the Cyclades are outside it, so check those on the world build. A group crossing the edge of the trial's bounding box should be cut there, not dropped.
* The test pack has no Islands layer today. It needs a sample, such as tests/samples/osm/channel-islands.geojson, made from the world build's data: the islands Guernsey, Sark, Herm, Jethou, Brecqhou, Alderney and Jersey (layer islands), Guernsey and Jersey (countries), Sark and Alderney (regions of Guernsey), and the Channel Islands group as the planet reading gives it. It also needs the links-between-groups file in tests/samples/wikidata, read offline. The England and France sample already has the Cotentin, for the test that the sea off France is not in the group. Tests to write first: at sea between Guernsey and Jersey you are in the Channel Islands; on Sark "Within" lists Sark, then the Channel Islands; 5 kilometres off the Cotentin you are not in them.

## Licences

* OpenStreetMap, including place=archipelago: ODbL 1.0. Already the pack's licence. Credit "© OpenStreetMap contributors".
* Wikidata: CC0 1.0. Already a source.
* Natural Earth: public domain. Already a source.
* Our own record: written for TobyMap, from the sources above.
* GeoNames: not used, so its CC BY 4.0 credit line is not needed.
* No new package is needed, so tools/check_licences.py has nothing new to check.
* docs/design/data sources.md, section Islands, says "Named island groups (OSM place=archipelago) are a later improvement." P4-T13b should replace that line with the decision: groups of islands from OpenStreetMap's place=archipelago (ODbL), joined through Wikidata (CC0), with Natural Earth (public domain) for the groups OpenStreetMap lacks, and outlines made from the pack's own islands.

## What was run on the planet file

* One reading, in its own short-lived process, with nothing else running: every feature tagged place=archipelago or place=islands in planet-2026-10-26.gol, over the whole planet, by tag. It took 69 seconds. Free memory fell from 21.4 GB to 17.1 GB at its lowest, so it used about 4 GB; the process's own peak was not caught, as the virtual environment's launcher starts Python as a second process.
* Everything else read the world build's stage folders, Natural Earth's file and Wikidata, and wrote only to a scratch folder outside the repository and the data folder.
