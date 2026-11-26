# P4-T1f report: points of interest

Work item P4-T1f, design docs/plan/p4-t1-design.md section 3.10. Not committed.

## What was made

* The category table, mapdata/config/poi_categories.yaml: 52 point of interest categories in four layers (stops, shops-food, services, street-furniture), tried in order, the first that matches winning. Their words are in mapcore/describe/templates.yaml, under poi_categories, words.
* The osm-pois stage, mapdata/stages/osm_pois.py: reads them within the coverage through osm_source. A node is a place where it is; an area is a place at a point inside it. An unnamed place is named by its words with a capital first letter, such as "Bench".
* The villages layer: in great-britain.yaml and hampshire-isle-of-wight.yaml, the existing osm-places stage, unchanged, within the outline's box, with the areas each village is in.
* say_type: a layer field (in SHOWN_FIELDS), read by the layer catalogue. The core's one naming function, Naming.name_of in mapcore/names.py, says an item of such a layer with its type after its name: "Broadway (Stop E), bus stop". Its name is said once when it is already the type's words: "Bench". This reaches Within, Nearby, Contains, search and the map alike, as the condominium's owners do.
* The CSV for the product owner, docs/plan/p4-t1f-poi-categories.csv, made by tools/make_poi_categories_csv.py.

## Choices made, for the orchestrator to check

* The test region's villages. The osm-places stage reads only the planet file, so it cannot read the raw samples. Changing it would change the world's fingerprints. The osm-pois stage therefore has a setting, places, that reads named places as osm-places does, through osm_source. The test region uses it for its villages. The two real packs use osm-places as the design says.
* The real packs' villages are not cut to the coverage, as osm-places has no coverage step. A village just outside the coverage but inside the box is kept.
* How the naming function learns which layers have say_type. The layer catalogue tells mapcore/names.py when it is made, as a set of layer ids for the process. Neither the store nor the session changed. A layer id means the same layer in every pack, so one set is enough.
* say_type is not yet set in mapdata/config/layers/regional.yaml: that is P4-T1i's. Until then nothing is said differently. The Nearby test sets it on the pack's layer definitions itself.
* The design's example "Broadway (Stop E)" is not in the samples. The test uses the sample's real bus stop on the Broadway, "Broadway St Johns (Stand 8)". The approved wording in tests/mapcore/test_session.py uses the design's example.
* Shops: the kinds of shop named in the design (supermarket, convenience shop, bakery, butcher, chemist, hairdresser) are categories of their own, before "shop" for any other shop value. So each has its own count in the CSV.

## The counts

Both count columns come from the product owner's uk.gol (E: drive data folder), counted on 26 November 2026, each object in the first category that matches it. The column "count in the rehearsal" is counted within the box of hampshire-isle-of-wight.yaml's osm-areas stage, which is a little larger than the rehearsal's coverage. The count took 69 seconds: 1,852,315 points of interest in the United Kingdom. They agree with the design note: bus stops 283,943 (expected 283,345), crossings 305,951, post boxes 89,074, benches 147,286, bins 73,579. Car parks are the largest category after crossings and bus stops: 281,591.

## Tests

* tests/mapdata/test_pois.py: the category table, the first category winning, the query, unnamed places, the CSV made again identical, and, on the regional test pack, the Broadway bus stop, unnamed benches, a supermarket mapped as an area, and Brockenhurst in villages with its areas.
* tests/mapcore/test_poi_words.py: say_type read by the catalogue, the naming, and the Broadway bus stop said with its type in Nearby.
* tests/mapcore/test_session.py: the approved wording, added only.
