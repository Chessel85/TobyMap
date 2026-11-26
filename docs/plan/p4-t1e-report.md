# P4-T1e report: land use, parks, school grounds and national parks

## What was made

* The stage osm-land (mapdata/stages/osm_land.py) and its classes file (mapdata/config/land_classes.yaml).
* Its block in great-britain.yaml, hampshire-isle-of-wight.yaml and test-region.yaml.
* The build registration lists osm_lines as code of the stage, because it imports two functions from it. No other stage's fingerprint changes.
* Tests in tests/mapdata/test_land.py, and a section in docs/data-manager/configuration.md.

## Choices to check

* Joining touches, within 1 metre (meet_m), in one parish by each area's representative point. Only plain union and connected sets were needed, so the work did not need Opus.
* A joined area that is not one block becomes a multi-part shape.
* The first matching class wins; the order is national parks, school grounds, parks, land use.
* landuse=grass, flowerbed and similar values are not in the design's list, so they are left out. The samples hold many landuse=grass areas. Adding grass is one line in land_classes.yaml.
* Shortbread's layers and zooms in land_classes.yaml were entered from memory of its schema. They are to be checked against shortbread-tiles.org before the differences log is relied on.
* Type words are in land_classes.yaml, as the design says, not in templates.yaml, so templates.yaml is unchanged.
* National parks are cut to the countries layer of the stage before (the land), then to the coverage.

## Tests run

* tests/mapdata/test_land.py: 29 passed.
* test_core_rules, test_streets, test_waterways, test_osm_water, test_small_islands, test_local_areas, test_coverage: 125 passed, 1 expected failure (already marked).
