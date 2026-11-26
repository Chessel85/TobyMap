# P4-T1c report: every island and every lake

Design: docs/plan/p4-t1-design.md section 3.6. Requirements: DAT-1, DAT-3, LOC-3, DP87.

## What was made

* mapdata/stages/small_islands.py, the small-islands stage: every landmass under 1 km2 that holds no island area and does not reach the coverage's edge becomes an island. It is named by an islet that OpenStreetMap has only as a point, where there is one on it, or is "Unnamed island" with id "island:unnamed:" and its point to 5 decimals.
* mapdata/stages/osm_water.py, the osm-water stage: every other water area, named or not, of any size, into the lakes layer. An unnamed one is named by its type's words, such as "Pond" or "Unnamed lake". An id already in the pack is skipped. A river's area is left out.
* The words for unnamed islands and water are in mapcore/describe/templates.yaml, under details, unnamed. Nothing approved was changed.
* The pack files: both stages in all three. The real packs also have the osm-layer stage for the named lakes, with the world's queries, min_km2 0, tolerance_m 5 and the outline's box.
* docs/data-manager/configuration.md: a section for each stage.

## Tests

* tests/mapdata/test_small_islands.py and tests/mapdata/test_osm_water.py: 30 tests, all passing.
* The related tests also pass: core rules, tiers, the tiers record, local areas, session wording, coverage and osm_source.

## Things to know

* The Lymington cooked sample has no islet. Its land is the mainland and a small part of Walhampton, which the box cuts. The salt marsh is not land in the land polygons. So the islet tests add two made-up islets to the sample's sea. The test region checks that the Walhampton part, which the coverage cuts, is not taken for an island.
* No sample has an islet as an OpenStreetMap point, so naming from a point is tested with a made-up point record.
* An unnamed island's type is "unnamed island", the same as the join's, so the match stage can compare the two. The design says "island".
* The osm-layer stage cannot read the raw samples, so the test region leaves it out, as the design says. The rule "a lake already read is not read twice" is tested by running osm-water after a stage that already holds Mirror Pond.
* The osm-layer stage is not changed, so it does not cut its lakes to the coverage. It reads within the outline's box. Lakes in the box but outside the coverage may need cutting by a later work item, such as the match stage.
* In the test region, osm-water adds 45 water areas (21 ponds, 20 lakes, 4 basins), 39 of them with no name, and leaves out 9 river areas.
