# P4-T1b report: every administrative level

26 November 2026. Written by Claude Code for the orchestrator and the product owner (PO). Not committed.

## What was done

* A new stage, local-areas (mapdata/stages/local_areas.py), makes the districts and parishes layers of a regional pack, as design section 3.5 says: read within the coverage through osm_source, each area given to the county holding most of it, slivers to the neighbour with the longest shared edge, land in no parish as one "Unparished area" for each district, and every parish simplified once as a coverage inside its county, so parishes, districts and counties meet exactly.
* A new record, mapdata/config/local_levels.yaml: the United Kingdom's levels (districts 8, parishes 10), the plain words for each designation, and the gap names for England, Scotland and Wales.
* The tiers record has two new tiers after county: district and parish. Their words are in templates.yaml under details.tiers. Each area's own tier name, such as "civil parish", comes from its designation, given by the stage, as there are too many areas to list in the tiers record.
* The stage's block in the three pack files, its section in docs/data-manager/configuration.md, and "Unparished area" in the glossary.

## On the test region

* Districts: Winchester and New Forest, which together are exactly Hampshire's land in the coverage.
* Parishes: Brockenhurst, Denny Lodge, Boldre, and Lymington and Pennington, under New Forest. One sliver of 0.0002 square kilometres went to Brockenhurst.
* Winchester's centre is in no parish, so it is "Unparished area", said in Details as "unparished area of Winchester". OpenStreetMap names the district "Winchester", not "City of Winchester".
* Details says "district of Hampshire" for New Forest and "civil parish of New Forest" for Brockenhurst.

## Level 9 in the United Kingdom

Checked on uk.gol. It has 80 areas at level 9, none of which belong in a layer:

* 70 are electoral divisions of Ireland, just over the border, caught by the extract.
* 9 are Buckinghamshire's community boards, advisory bodies, not a level of government.
* 1 is the Inner and Middle Temples in London, an extra-parochial liberty, a few hectares.

## Found on the way

* Scotland's community council areas are hardly mapped at level 10: 127 areas, some of them sea stacks and Rockall. So most of Scotland will be "Area with no community council", as the design expected in its risks.
* England has 6 areas drawn at level 10 as unparished areas, and 1 as a non-civil parish (Hucknall). They are read as areas of the parishes layer, said as "unparished area".

## Tests outside this work item's files

Three tests check the old list of four tiers and now fail, as the list has six: tests/mapcore/test_tiers.py (test_each_area_has_its_tier_and_the_pack_lists_the_tiers) and tests/mapdata/test_tiers_record.py (two tests). Each needs "district" and "parish" added at the end of the expected list.
